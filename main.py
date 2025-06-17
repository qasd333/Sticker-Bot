import asyncio
import os
import sys
import urllib3
from loguru import logger
from src.console.main import Console
from src.modules.create_telethon_session import create_telethon_session
from src.modules.snipe import Snipe


async def main():
    configuration()
    module = Console().build()

    if module == '🔑 Create session':
        you_sure = input(
            "Are you sure want to create a new session? (y/n): ")
        if you_sure.lower() == 'y':
            if os.path.exists("data/session.session"):
                os.remove("data/session.session")
            await create_telethon_session()
        else:
            logger.info("Session creation canceled")
            return
    elif module == '🎯 Start sniping':
        if not validate_session():
            return
        await Snipe().start()
    elif module == '💰 Buy with your data':
        if not validate_session():
            return
        await Snipe().start(buy_with_your_data=True)

    else:
        logger.error(f"Invalid module: {module}")
        return


log_format = (
    "<light-blue>[</light-blue><yellow>{time:HH:mm:ss}</yellow><light-blue>]</light-blue> | "
    "<level>{level: <8}</level> | "
    "<cyan>{file}:{line}</cyan> | "
    "<level>{message}</level>"
)


def configuration():
    urllib3.disable_warnings()
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format=log_format,
    )
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="1 month",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} - {message}",
        level="INFO",
    )


def validate_session():
    if not os.path.exists("data/session.session"):
        logger.error("Session file not found, creating session!")
        return False

    return True


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program stopped by user.")
        exit(0)
