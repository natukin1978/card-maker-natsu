import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import List

import asqlite
import uvicorn
from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import global_value as g
from config_helper import read_config
from logging_setup import setup_app_logging

g.app_name = "card_maker_natsu"
g.base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

g.config = read_config()

# ロガーの設定
setup_app_logging(g.config["logLevel"], log_file_path=f"{g.app_name}.log")
logger = logging.getLogger(__name__)

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
        logger.info(f"[WS] クライアントが接続しました。現在の接続数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"[WS] クライアントが切断しました。現在の接続数: {len(self.active_connections)}")

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

@app.get("/card-maker-natsu/output/{filename}")
async def get_card_image(filename: str):
    filepath = os.path.join("output", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(filepath, media_type="image/png")

# 静的マウントなどの設定は、関数の「下」に記述する ---
os.makedirs("output", exist_ok=True)
output_dir = os.path.join(g.base_dir, "output")
os.makedirs(output_dir, exist_ok=True)

# WebSocket エンドポイント (ws://localhost:34510/ws)
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await g.ws_manager.connect(websocket)
    try:
        while True:
            # クライアントからのメッセージ待ち受け（切断検知のため）
            data = await websocket.receive_text()
            logger.debug(data)
            # 必要であればクライアントからの命令をここで処理
    except WebSocketDisconnect:
        g.ws_manager.disconnect(websocket)

@app.post("/cards/upload")
async def upload_combined_card(
    file: UploadFile = File(...),
    user_name: str = Form(...),
    rarity: str = Form(...)
):
    try:
        # 1. フロントエンドから送られてきた画像データを読み込む
        card_bytes = await file.read()

        # 2. ローカル環境への保存処理
        save_dir = "generated_cards"
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(save_dir, f"{user_name}_{timestamp}.png")

        with open(filepath, "wb") as f:
            f.write(card_bytes)

        logger.info(f"フロントエンドから受信した合成済カードを保存しました: {filepath}")

        # logger.info(f"Discordへのカード画像の投稿が完了しました: {user_name}")
        return {"status": "success", "filepath": filepath}

    except Exception as e:
        logger.error(f"合成済カードの処理中にエラーが発生しました: {e}")
        return {"status": "error", "message": str(e)}

# FastAPIを裏側で動かすための非同期タスク
async def run_web_server():
    config = uvicorn.Config(app, host="127.0.0.1", port=34510, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():

    # conduit_id の警告を抑止したい…
    logging.getLogger("twitchio.client").setLevel(logging.ERROR)
    # StarletteAdapter の警告を抑止したい…
    logging.getLogger("twitchio.web.aio_adapter").setLevel(logging.ERROR)

    bot = None
    async with asqlite.create_pool("tokens.db") as tdb:
        tokens, subs = await setup_database(tdb)

        bot = TwitchBot(token_database=tdb, subs=subs)
        for pair in tokens:
            await bot.add_token(*pair)

        # Webサーバー(FastAPI) と TwitchBot を並行して同時に走らせる
        await asyncio.gather(
            run_web_server(),
            bot.start(load_tokens=False, with_adapter=False)
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
