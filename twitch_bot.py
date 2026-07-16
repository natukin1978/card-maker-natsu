import json
import logging
import os

# import time
from typing import TYPE_CHECKING

import asqlite
import httpx
import twitchio
from twitchio import eventsub
from twitchio.ext import commands

if TYPE_CHECKING:
    import sqlite3

import global_value as g
from card_generator import CardGenerator
from character_params import CharacterParams

BACKEND_SERVER_URL = "http://localhost:34510"

logger = logging.getLogger(__name__)


class TwitchBot(commands.AutoBot):
    def __init__(
        self, *, token_database: asqlite.Pool, subs: list[eventsub.SubscriptionPayload]
    ) -> None:
        self.token_database = token_database

        ctw = g.config["twitch"]
        super().__init__(
            client_id=ctw["clientId"],
            client_secret=ctw["clientSecret"],
            bot_id=ctw["bot"]["id"],
            owner_id=ctw["owner"]["id"],
            prefix="!",
            subscriptions=subs,
            force_subscribe=True,
        )

    async def setup_hook(self) -> None:
        # Add our component which contains our commands...
        await self.add_component(AlertComponent(self))

    async def event_oauth_authorized(
        self, payload: twitchio.authentication.UserTokenPayload
    ) -> None:
        await self.add_token(payload.access_token, payload.refresh_token)

        if not payload.user_id:
            return

        if payload.user_id == self.bot_id:
            # We usually don't want subscribe to events on the bots channel...
            return

        # A list of subscriptions we would like to make to the newly authorized channel...
        subs: list[eventsub.SubscriptionPayload] = [
            eventsub.ChatNotificationSubscription(
                broadcaster_user_id=payload.user_id, user_id=self.bot_id
            ),
            eventsub.ChannelRaidSubscription(
                to_broadcaster_user_id=payload.user_id
            ),
        ]

        resp: twitchio.MultiSubscribePayload = await self.multi_subscribe(subs)
        if resp.errors:
            logger.warning(
                "Failed to subscribe to: %r, for user: %s", resp.errors, payload.user_id
            )

    async def add_token(
        self, token: str, refresh: str
    ) -> twitchio.authentication.ValidateTokenPayload:
        # Make sure to call super() as it will add the tokens interally and return us some data...
        resp: twitchio.authentication.ValidateTokenPayload = await super().add_token(
            token, refresh
        )

        # Store our tokens in a simple SQLite Database when they are authorized...
        query = """
        INSERT INTO tokens (user_id, token, refresh)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            token = excluded.token,
            refresh = excluded.refresh;
        """

        async with self.token_database.acquire() as connection:
            await connection.execute(query, (resp.user_id, token, refresh))

        logger.info("Added token to the database for user: %s", resp.user_id)
        return resp

    async def event_ready(self) -> None:
        bot = self.user
        logger.info("Successfully logged in as: %s (%s)", bot.display_name, bot.name, extra={'force': True})
        owner_user = self.owner
        g.owner_attr = {
            "id": owner_user.id,
            "name": owner_user.name,
            "display_name": owner_user.display_name,
            "description": owner_user.description,
        }


class AlertComponent(commands.Component):

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.card_generator = CardGenerator()
        self.http_client = httpx.AsyncClient()

    @commands.Component.listener()
    async def event_chat_notification(self, payload: twitchio.ChatNotification) -> None:
        logger.info(payload, extra={'force': True})

    @commands.Component.listener()
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        # 💡 「自動検出は止めたい」とのことでしたので、もし完全に無効化する場合は
        # このメソッドごとコメントアウトするか、以下のようにログだけに留めて処理をスキップしてください。
        raw_name = payload.from_broadcaster.name
        viewers = payload.viewer_count
        logger.info(f"[Raid 自動検知（スキップ中）] {raw_name} ({viewers} viewers)")

        # もし自動検知も残すなら、以下を有効にすれば手動と同じルートで動きます
        # await self.process_make_card(raw_name=raw_name, event_type="raid", viewers=viewers)

    # ユーザー情報（アイコン・表示名）を取得するメソッド
    async def _fetch_profile_image_and_display_name(self, raw_name: str) -> tuple[bytes | None, str | None, str]:
        try:
            users = await self.bot.fetch_users(logins=[raw_name.lower()])
            if not users:
                logger.error(f"[Warning] ユーザー情報が見つかりませんでした: {raw_name}")
                return None, None, raw_name

            user_obj = users[0]
            # 表示名（display_name）があれば取得、なければ英小文字名をフォールバックに
            display_name = user_obj.display_name if user_obj.display_name else user_obj.name
            profile_image_url = user_obj.profile_image.url

            # アイコンをダウンロード
            response = await self.http_client.get(profile_image_url)
            if response.status_code != 200:
                logger.error("[Error] アイコンのダウンロードに失敗しました。")
                return None, None, display_name

            image_bytes = response.content
            mime_type = response.headers.get("Content-Type", "image/png")

            logger.info(f"[Success] ユーザー情報取得完了: {display_name} (ID: {raw_name})")
            return image_bytes, mime_type, display_name

        except Exception as e:
            logger.error(f"[Error] ユーザー情報取得中に例外が発生しました: {e}")
            return None, None, raw_name

    # パラメータと画像をローカルに保存する処理
    async def _process_card_data(
        self,
        raw_name: str,
        display_name: str,
        card_data: CharacterParams,
        icon_bytes: bytes | None = None,
        mime_type: str | None = None
    ) -> None:
        logger.info(f"--- キャラクターカードデータ生成完了: {display_name} ---")

        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        # Banana APIを呼び出してイラスト（画像）を生成（アイコン画像も一緒に渡す！）
        generated_image_bytes = await self.card_generator.generate_image(
            image_prompt=card_data.image_prompt,
            icon_bytes=icon_bytes,
            mime_type=mime_type
        )

        file_base_name = raw_name.lower()

        if generated_image_bytes:
            image_path = os.path.join(output_dir, f"{file_base_name}.png")
            with open(image_path, "wb") as f:
                f.write(generated_image_bytes)
            logger.info(f"[Success] イラストを保存しました: {image_path}")
        else:
            logger.error("[Warning] 画像生成に失敗したため、イメージファイルの保存をスキップします。")

        # パラメーター（JSON）を保存
        card_dict = card_data.model_dump()
        card_dict["display_name"] = display_name
        card_dict["image_path"] = f"/{output_dir}/{file_base_name}.png" if generated_image_bytes else None

        json_path = os.path.join(output_dir, f"{file_base_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(card_dict, f, ensure_ascii=False, indent=4)
        logger.info(f"[Success] パラメーターJSONを保存しました: {json_path}")

        if hasattr(g, "ws_manager"):
            # React側で画像を表示しやすいよう、URLを調整
            # 例: /output/fuyuka_ai.png -> http://localhost:34510/output/fuyuka_ai.png
            card_dict["image_url"] = f"{BACKEND_SERVER_URL}/card-maker-natsu{card_dict['image_path']}" if card_dict["image_path"] else None

            logger.info("[WS] フロントエンドへ最新のカードデータを送信します...")
            await g.ws_manager.broadcast_json({
                "event": "NEW_CARD",
                "data": card_dict,
            })

        logger.info("--------------------------------------------------")


    # FastAPIとチャットコマンド両方から使える「新規生成コアロジック」
    async def process_make_card(self, raw_name: str, event_type: str = "raid", event_value: int = 1, ctx: commands.Context = None) -> None:
        logger.info(f"[Card Make] 処理開始: {raw_name} (Event: {event_type}, Value: {event_value})")

        if hasattr(g, "ws_manager"):
            await g.ws_manager.broadcast_json({
                "event": "START_GENERATION",
                "data": {"user_name": raw_name},
            })

        # イベントの日本語名と、値の意味をマッピングする
        event_mapping = {
            "raid": {"label": "レイド（応援枠）", "unit": f"{event_value}人の視聴者を引き連れての襲来"},
            "sub": {"label": "サブスクリプション", "unit": f"継続 {event_value}ヶ月目の登録"},
            "cheer": {"label": "ビッツ（投げ銭）", "unit": f"{event_value} ビッツの応援"},
            "follow": {"label": "新規フォロー", "unit": "新たなフォローの絆"}
        }

        # 万が一、未定義のイベントが来たらデフォルト値にする
        mapping = event_mapping.get(event_type, {"label": event_type, "unit": f"規模・数値: {event_value}"})

        event_label = mapping["label"]  # 例: "サブスクリプション"
        event_power_text = mapping["unit"]  # 例: "継続 3ヶ月目の登録"

        # ユーザー情報（アイコン・表示名）の取得
        image_bytes, mime_type, display_name = await self._fetch_profile_image_and_display_name(raw_name)

        # パラメータの生成
        card_data = await self.card_generator.generate_character(
            user_name=display_name,
            event_label=event_label,
            event_power_text=event_power_text,
            image_bytes=image_bytes,
            mime_type=mime_type
        )

        # イラスト生成・保存・WebSocket配信
        await self._process_card_data(raw_name, display_name, card_data, image_bytes, mime_type)

    # FastAPIとチャットコマンド両方から使える「再表示コアロジック」
    async def process_repost(self, target_user: str, ctx: commands.Context = None) -> None:
        logger.info(f"[Card Repost] 処理開始: {target_user}")

        # if hasattr(g, "ws_manager"):
        #     await g.ws_manager.broadcast_json({
        #         "event": "START_GENERATION",
        #         "data": {"user_name": target_user},
        #     })
        #     time.sleep(7.5)

        file_base_name = target_user.lower()
        output_dir = "output"
        json_path = os.path.join(output_dir, f"{file_base_name}.json")

        # ファイルが存在するかチェック
        if not os.path.exists(json_path):
            if ctx:
                await ctx.send(f"[Error] {target_user} のカードデータが見つかりません。")
            logger.error(f"[Repost] ファイルが見つかりません: {json_path}")
            return

        try:
            # JSONファイルを読み込む
            with open(json_path, "r", encoding="utf-8") as f:
                card_dict = json.load(f)

            # WebSocket配信用に画像URLを組み立てて送信
            if hasattr(g, "ws_manager"):
                if card_dict.get("image_path") and not card_dict.get("image_url"):
                    card_dict["image_url"] = f"{BACKEND_SERVER_URL}/card-maker-natsu{card_dict['image_path']}"

                logger.info(f"[WS] [Repost] {card_dict['display_name']} のデータを再送信します...")
                await g.ws_manager.broadcast_json({
                    "event": "NEW_CARD",
                    "data": card_dict,
                })

            else:
                logger.error("[Warning] WebSocketマネージャー(g.ws_manager)が準備できていません。")

        except Exception as e:
            logger.error(f"[Error] Repost処理中に例外が発生しました: {e}")
            if ctx:
                await ctx.send("データの再送中にエラーが発生しました。")

    @commands.command(name="make_card")
    async def make_card_command(self, ctx: commands.Context, name: str = None) -> None:
        author_id = ctx.author.id
        if not is_owner_or_bot(author_id):
            await ctx.send(f"@{ctx.author.name} このコマンドはモデレーター以上のみ使用できます。")
            return

        target_raw_name = name if name else ctx.author.name

        await self.process_make_card(raw_name=target_raw_name, event_type="raid", viewers=1, ctx=ctx)

    @commands.command(name="repost")
    async def command_repost(self, ctx: commands.Context, target_user: str = None) -> None:
        if not is_owner_or_bot(ctx.author.id):
            await ctx.send(f"@{ctx.author.name} このコマンドはモデレーター以上のみ使用できます。")
            return

        if not target_user:
            await ctx.send("ユーザー名を指定してください。例: !repost fuyuka_ai")
            return

        await self.process_repost(target_user=target_user, ctx=ctx)

def is_owner_or_bot(id) -> bool:
    return id in [g.config["twitch"]["owner"]["id"], g.config["twitch"]["bot"]["id"]]

async def setup_database(
    db: asqlite.Pool,
) -> tuple[list[tuple[str, str]], list[eventsub.SubscriptionPayload]]:
    # Create our token table, if it doesn't exist..
    # You should add the created files to .gitignore or potentially store them somewhere safer
    # This is just for example purposes...

    query = """CREATE TABLE IF NOT EXISTS tokens(user_id TEXT PRIMARY KEY, token TEXT NOT NULL, refresh TEXT NOT NULL)"""
    async with db.acquire() as connection:
        await connection.execute(query)

        # Fetch any existing tokens...
        rows: list[sqlite3.Row] = await connection.fetchall("""SELECT * from tokens""")

        tokens: list[tuple[str, str]] = []
        subs: list[eventsub.SubscriptionPayload] = []

        bot_id = g.config["twitch"]["bot"]["id"]

        for row in rows:
            tokens.append((row["token"], row["refresh"]))

            if row["user_id"] == bot_id:
                continue

            subs.extend(
                [
                    eventsub.ChatNotificationSubscription(
                        broadcaster_user_id=row["user_id"], user_id=bot_id
                    ),
                    eventsub.ChannelRaidSubscription(
                        to_broadcaster_user_id=row["user_id"]
                    ),
                ]
            )

    return tokens, subs
