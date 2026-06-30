import logging
from typing import TYPE_CHECKING

import asqlite
import httpx
import twitchio
from twitchio import eventsub
from twitchio.ext import commands

if TYPE_CHECKING:
    import sqlite3

import global_value as g

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
            eventsub.ChannelFollowSubscription(
                broadcaster_user_id=payload.user_id, moderator_user_id=self.bot_id
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
    def __init__(self, bot: TwitchBot) -> None:
        self.bot = bot
        self.http_client = httpx.AsyncClient()

    @commands.Component.listener()
    async def event_follow(self, payload: twitchio.ChannelFollow) -> None:
        # twitchio.ChannelFollow モデルから情報を取得
        user_id = payload.user.id
        user_name = payload.user.name
        logger.info("[Alert] フォロー検知: %s (ID: %s)", user_name, user_id)

        # AI処理へタスクを逃がす
        await self.handle_ai_alert(user_id, user_name, "follow")

    @commands.Component.listener()
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        # twitchio.ChannelRaid モデルから情報を取得
        user_id = payload.from_broadcaster.id
        user_name = payload.from_broadcaster.name
        viewers = payload.viewers
        logger.info("[Alert] レイド検集: %s から %s 人", user_name, viewers)

        await self.handle_ai_alert(user_id, user_name, "raid", viewers=viewers)

    async def handle_ai_alert(self, user_id: str, user_name: str, event_type: str, viewers: int = 0):
        try:
            # 最新のユーザープロフィールを取得してアイコンURLを特定
            users = await self.bot.fetch_users(ids=[int(user_id)])
            if not users:
                logger.warning("ユーザー情報が見つかりませんでした: %s", user_name)
                return

            profile_image_url = users[0].profile_image_url

            # URLから画像をバイトデータとしてダウンロード
            response = await self.http_client.get(profile_image_url)
            if response.status_code != 200:
                logger.error("アイコンのダウンロードに失敗しました。Status: %s", response.status_code)
                return

            image_bytes = response.content
            image_mime_type = response.headers.get("Content-Type", "image/png")

            # Gemini APIにそのまま投入できるデータ構造
            alert_payload = {
                "event_type": event_type,
                "user_name": user_name,
                "viewers": viewers,
                "image_data": {
                    "bytes": image_bytes,
                    "mime_type": image_mime_type
                }
            }

            logger.info(alert_payload)
            logger.info("[Success] AI用データ集約完了: %s のアイコン取得成功", user_name)
            # 次のステップの関数へ受け渡す
            # await self.generate_card_data(alert_payload)

        except Exception as e:
            logger.error("アラート情報収集フェーズでエラーが発生しました: %s", e, exc_info=True)


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
                    eventsub.ChannelFollowSubscription(
                        broadcaster_user_id=row["user_id"], moderator_user_id=bot_id
                    ),
                    eventsub.ChannelRaidSubscription(
                        to_broadcaster_user_id=row["user_id"]
                    ),
                ]
            )

    return tokens, subs
