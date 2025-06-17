from telethon import TelegramClient
from data.config import API_ID, API_HASH
from loguru import logger

async def create_telethon_session() -> bool:
    try:
        client = TelegramClient(
            session="data/session",
            api_id=API_ID,
            api_hash=API_HASH
        )

        await client.start()
        await client.disconnect()

        logger.success("Telethon session successfully created")

        return True
    except Exception as e:
        logger.error(f"Error creating Telethon session: {e}")
        return False