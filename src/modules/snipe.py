import asyncio
import sys
import os
import json
import time
import base64

from telethon import TelegramClient
from telethon.tl.functions.messages import RequestWebViewRequest
from telethon.tl.types import InputInvoiceSlug, InputPeerUser
from telethon.tl.functions.payments import GetPaymentFormRequest, SendStarsFormRequest, GetStarsStatusRequest

from data.config import API_ID, API_HASH, COUNT_FOR_BUY_STARS, COUNT_FOR_BUY_TON, STICKER_NAME, mnemonic

from curl_cffi.requests import AsyncSession
from loguru import logger
from fake_useragent import UserAgent
import random
from urllib.parse import unquote

from TonTools import *


class Snipe:
    HEADERS = {
        'accept': 'application/json',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,uk;q=0.6',
        'cache-control': 'no-cache',
        'origin': 'https://stickerdom.store',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://stickerdom.store/',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': UserAgent().random,
    }

    def __init__(self):
        self.telethon_session = TelegramClient(
            session="data/session.session",
            api_id=API_ID,
            api_hash=API_HASH
        )

        self.curl_session = AsyncSession(
            verify=False,
            timeout=10,
            impersonate="chrome136"
        )

    async def _handle_telethon_session_connection(self):
        while True:
            if not self.telethon_session.is_connected():
                try:
                    await self.telethon_session.start()
                    logger.success("Successfully connected to Telegram")
                except Exception as e:
                    logger.error(f"Error connecting to Telegram: {e}")
                    logger.info("Trying to reconnect in 5 seconds...")
                    await asyncio.sleep(5)
                    continue

            await asyncio.sleep(10)  # Проверяем соединение каждые 10 секунд

    async def _handle_token_refresh(self):
        """Обновляет bearer token каждые 20 минут"""
        while True:
            await asyncio.sleep(1200)  # 20 минут = 1200 секунд
            try:
                logger.info("Refreshing bearer token...")
                bearer_token = await self._auth()
                self.HEADERS['authorization'] = f'Bearer {bearer_token}'
                logger.success("Bearer token successfully refreshed")
            except Exception as e:
                logger.error(f"Error refreshing bearer token: {e}")

    async def _get_sticker_list(self):
        r = await self.curl_session.get(
            'https://api.stickerdom.store/api/v1/home',
            headers=self.HEADERS
        )

        return r

    async def _get_url_for_buy(self, collection_id, character_id):
        params = {
            'collection': str(collection_id),
            'character': str(character_id),
        }

        while True:
            try:
                r = await self.curl_session.post(
                    'https://api.stickerdom.store/api/v1/shop/buy',
                    headers=self.HEADERS,
                    params=params
                )

                if r.status_code == 200 and 'data' in r.json() and 'url' in r.json()['data']:
                    return r.json()['data']['url']

                logger.warning(
                    f"Failed to get URL for purchase. Status: {r.status_code} | Text: {r.text}. Trying again...")
            except Exception as e:
                logger.error(
                    f"Error getting URL for purchase: {e}. Trying again...")

            await asyncio.sleep(1)  # Пауза перед следующей попыткой

    async def _buy_sticker_for_stars(self, collection_id, character_id):
        logger.info(
            f'Buying {COUNT_FOR_BUY_STARS} stickers for stars.')

        url = await self._get_url_for_buy(collection_id, character_id)

        logger.success(f'Got URL for purchase: {url}')

        slug = url.split("$")[1]

        invoice = InputInvoiceSlug(slug)

        success_count = 0

        while success_count < COUNT_FOR_BUY_STARS:
            try:
                form = await self.telethon_session(GetPaymentFormRequest(invoice=invoice))

                result = await self.telethon_session(SendStarsFormRequest(
                    form_id=form.form_id, invoice=invoice))

                success_count += 1
                logger.success(
                    f'Successfully bought {success_count} sticker(s) for stars')
            except Exception as e:
                if hasattr(e, "message") and e.message == 'BALANCE_TOO_LOW':
                    logger.critical(f'Balance too low.')
                    sys.exit(1)
                else:
                    logger.error(f'Error buying sticker for stars: {e}')
                    await asyncio.sleep(1)

    async def _buy_sticker_for_ton(self, collection_id, character_id):
        if COUNT_FOR_BUY_TON == 0:
            return

        logger.info(
            f'Buying {COUNT_FOR_BUY_TON} stickers for ton.')

        params = {
            'collection': str(collection_id),
            'character': str(character_id),
            'currency': 'TON',
            'count': str(COUNT_FOR_BUY_TON),
        }

        while True:
            try:
                r = await self.curl_session.post(
                    'https://api.stickerdom.store/api/v1/shop/buy/crypto',
                    headers=self.HEADERS,
                    params=params
                )

                if r.status_code in [200, 205] and 'data' in r.json():
                    logger.success(
                        f'Order id: {r.json()["data"]["order_id"]} | Amount: {float(r.json()["data"]["total_amount"]) / 10**9} | Wallet: {r.json()["data"]["wallet"]}')

                    provider = TonCenterClient()

                    wallet = Wallet(
                        mnemonics=mnemonic, version=WalletVersionEnum.v4r2, provider=provider)

                    await wallet.transfer_ton(
                        destination_address=r.json()["data"]["wallet"],
                        amount=float(r.json()["data"]["total_amount"]) / 10**9,
                        message=r.json()["data"]["order_id"]
                    )

                    logger.success(
                        f'Successfully transferred {float(r.json()["data"]["total_amount"]) / 10**9} TON to {r.json()["data"]["wallet"]} with message {r.json()["data"]["order_id"]}')

                    break

                logger.warning(
                    f"Failed to buy sticker for ton. Status: {r.status_code} | Text: {r.text}. Trying again...")
            except Exception as e:
                logger.error(f'Error buying sticker for ton: {e}')

    async def start(self, buy_with_your_data=False):
        # Запускаем мониторинг соединения в фоне
        asyncio.create_task(self._handle_telethon_session_connection())

        # Запускаем обновление токена в фоне
        asyncio.create_task(self._handle_token_refresh())

        while not self.telethon_session.is_connected():
            await asyncio.sleep(1)

        bearer_token = await self._auth()

        self.HEADERS['authorization'] = f'Bearer {bearer_token}'

        result = await self.telethon_session(GetStarsStatusRequest(peer='me'))

        logger.success(f'Stars balance: {result.balance.amount}')

        bearer_token = await self._auth()

        self.HEADERS['authorization'] = f'Bearer {bearer_token}'

        logger.success("Successfully authorized")

        if buy_with_your_data == False:
            self.found_elements = []

            for _ in range(50):
                try:
                    current_sticker_list = await self._get_sticker_list()

                    # with open("./data/init_sticker_list.json", "r", encoding="utf-8") as f:
                    #     current_sticker_list = json.load(f)

                    for i in current_sticker_list.json()["data"]["promo"]:
                        character = i["character"]
                        ids = (character["collection_id"], character["id"])
                        self.found_elements.append(ids)
                except Exception as e:
                    pass

            # logger.success(f"Initialization completed")
            logger.info("Starting monitoring for new elements...")

            found = False
            count_of_requests = 0
            while not found:
                try:
                    r = await self._get_sticker_list()

                    # with open("./data/current_sticker_list.json", "r", encoding="utf-8") as f:
                    #     r = json.load(f)
                    # with open("./data/current_sticker_list.json", "w", encoding="utf-8") as f:
                    #     f.write(json.dumps(r.json(), ensure_ascii=False))

                    for i in r.json()["data"]["promo"]:
                        character = i["character"]
                        ids = (character["collection_id"], character["id"])

                        obj_str = json.dumps(i, ensure_ascii=False)
                        if ids not in self.found_elements and STICKER_NAME.lower() in obj_str.lower():
                            logger.success(
                                f'New sticker found. Name: {character["name"]} | Collection ID: {character["collection_id"]} | Character ID: {character["id"]} | Price: {character["price"]} stars.')
                            with open("./data/new_element.txt", "w") as file:
                                file.write(
                                    f"Collection ID: {character['collection_id']}. Character ID: {character['id']}. Price: {character['price']} stars. Name: {character['name']}")

                            await self.telethon_session.start()

                            buy_stars_task = asyncio.create_task(self._buy_sticker_for_stars(
                                character["collection_id"], character["id"]))

                            buy_ton_task = asyncio.create_task(self._buy_sticker_for_ton(
                                character["collection_id"], character["id"]))

                            await asyncio.gather(buy_stars_task, buy_ton_task)

                            found = True
                            break
                        else:
                            logger.info(
                                f'Sticker not eligible for filter. Name: {character["name"]} | Collection ID: {character["collection_id"]} | Character ID: {character["id"]} | Price: {character["price"]} stars.')

                    logger.info(
                        f'🔥🔥🔥Count of requests: {count_of_requests}🔥🔥🔥')
                    count_of_requests += 1

                except Exception as e:
                    print(e)

                await asyncio.sleep(1)

        if buy_with_your_data == True:
            collection_id = input("Enter collection ID: ")
            character_id = input("Enter character ID: ")

            await self._buy_sticker_for_stars(
                collection_id, character_id)

    async def _auth(self):
        # token_file = 'data/bearer_token.txt'

        # # Проверяем существующий токен
        # if os.path.exists(token_file):
        #     try:
        #         with open(token_file, 'r', encoding='utf-8') as f:
        #             existing_token = f.read().strip()

        #         if self._is_token_valid(existing_token):
        #             # logger.success("Using existing valid token")
        #             return existing_token
        #         else:
        #             # logger.warning("Existing token expired, getting new one")
        #             pass
        #     except Exception as e:
        #         # logger.warning(f"Error reading token: {e}")
        #         pass

        # Получаем новый токен
        logger.info("Authorization in StickerDOM...")
        query = await self._get_tg_web_view()

        r = await self.curl_session.post(
            'https://api.stickerdom.store/api/v1/auth',
            headers=self.HEADERS,
            data=query
        )

        if r.status_code != 200:
            logger.critical(f"Authorization error: {r.text}")
            sys.exit(1)

        new_token = r.json()['data']

        # # Сохраняем новый токен
        # os.makedirs('data', exist_ok=True)
        # with open(token_file, 'w', encoding='utf-8') as f:
        #     f.write(new_token)

        # logger.success("New token received and saved")
        return new_token

    def _is_token_valid(self, token):
        """Проверяет действительность JWT токена"""
        try:
            # Проверяем что токен не пустой
            if not token or not token.strip():
                return False

            # Разделяем JWT на части
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning(
                    f"Invalid token format: expected 3 parts, got {len(parts)}")
                return False

            header, payload, signature = parts

            # Добавляем padding если нужно
            payload += '=' * (4 - len(payload) % 4)

            # Декодируем payload
            decoded_payload = base64.urlsafe_b64decode(payload)
            payload_data = json.loads(decoded_payload)

            # Проверяем срок действия
            exp_time = payload_data.get('exp')
            if exp_time:
                current_time = int(time.time())
                # Добавляем небольшой буфер (10 минут) для безопасности
                return current_time < (exp_time - 1200)

            return False
        except Exception as e:
            logger.warning(f"Error checking token: {e}")
            return False

    async def _get_tg_web_view(self):
        try:
            bot = await self.telethon_session.get_entity('sticker_bot')
            bot_input_peer = InputPeerUser(bot.id, bot.access_hash)

            web_view = await self.telethon_session(RequestWebViewRequest(
                peer=bot_input_peer,
                bot=bot_input_peer,
                url='https://stickerdom.store/',
                platform='android',
                from_bot_menu=True,
                start_param='tid_Njc1NDY2NzYxOA'
            ))

            query = unquote(web_view.url.split('tgWebAppData=')
                            [1].split('&tgWebAppVersion')[0])

            return query

        except Exception as e:
            logger.critical(f"Authorization error: {e}")
            sys.exit(1)
