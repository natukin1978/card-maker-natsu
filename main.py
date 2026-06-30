import asyncio
import logging
import os
import sys

import asqlite

import global_value as g
from config_helper import read_config
from logging_setup import setup_app_logging

g.app_name = "card_maker_natsu"
g.base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

g.config = read_config()

# ロガーの設定
setup_app_logging(g.config["logLevel"], log_file_path=f"{g.app_name}.log")
logger = logging.getLogger(__name__)

import constants
from twitch_bot import (
    TwitchBot,
    setup_database,
)


async def main():
    print(constants.CALLBACK_URL_BOT)
    print(constants.CALLBACK_URL_OWNER)

    bot = None
    async with asqlite.create_pool("tokens.db") as tdb:
        tokens, subs = await setup_database(tdb)

        bot = TwitchBot(token_database=tdb, subs=subs)
        for pair in tokens:
            await bot.add_token(*pair)

        #await bot.start(load_tokens=False, with_adapter=False)
        await bot.start(load_tokens=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        pass
