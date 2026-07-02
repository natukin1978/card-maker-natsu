import asyncio
import logging
import os
import sys

import asqlite
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

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

# --- FastAPIの初期化 ---
app = FastAPI()

# output フォルダを静的ファイルとして公開 (例: http://localhost:8000/output/fuyuka_ai.json でアクセス可能に)
output_dir = os.path.join(g.base_dir, "output")
os.makedirs(output_dir, exist_ok=True)
app.mount("/output", StaticFiles(directory=output_dir), name="output")

# ※ 後ほど、完成したReactのビルド済ファイルを丸ごと配信する設定もここに追加できます


# FastAPIを裏側で動かすための非同期タスク
async def run_web_server():
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    print(constants.CALLBACK_URL_BOT)
    print(constants.CALLBACK_URL_OWNER)

    bot = None
    async with asqlite.create_pool("tokens.db") as tdb:
        tokens, subs = await setup_database(tdb)

        bot = TwitchBot(token_database=tdb, subs=subs)
        for pair in tokens:
            await bot.add_token(*pair)

        # Webサーバー(FastAPI) と TwitchBot を並行して同時に走らせる
        await asyncio.gather(
            run_web_server(),
            # bot.start(load_tokens=False, with_adapter=False)
            bot.start(load_tokens=False)
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        pass
