import asyncio
import logging
import os
import sys
from typing import List

import asqlite
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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


# --- WebSocket 接続マネージャー ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] クライアントが接続しました。現在の接続数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"[WS] クライアントが切断しました。現在の接続数: {len(self.active_connections)}")

    async def broadcast_json(self, data: dict):
        # 配信中に接続が切れたクライアントを掃除しながら送信
        for connection in self.active_connections[:]:
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)

# グローバルにマネージャーを保持
g.ws_manager = ConnectionManager()

# --- FastAPIの初期化 ---
app = FastAPI()

origins = [
    "http://localhost:9345",
    "http://127.0.0.1:9345",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("output", exist_ok=True)
# output フォルダを静的ファイルとして公開
app.mount("/card-maker-natsu/output", StaticFiles(directory="output"), name="output")
output_dir = os.path.join(g.base_dir, "output")
os.makedirs(output_dir, exist_ok=True)
app.mount("/output", StaticFiles(directory=output_dir), name="output")

# WebSocket エンドポイント (ws://localhost:34510/ws)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await g.ws_manager.connect(websocket)
    try:
        while True:
            # クライアントからのメッセージ待ち受け（切断検知のため）
            data = await websocket.receive_text()
            logger.info(data)
            # 必要であればクライアントからの命令をここで処理
    except WebSocketDisconnect:
        g.ws_manager.disconnect(websocket)

# FastAPIを裏側で動かすための非同期タスク
async def run_web_server():
    config = uvicorn.Config(app, host="127.0.0.1", port=34510, log_level="info")
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
