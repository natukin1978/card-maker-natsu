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
from card_generator import CardGenerator
from character_params import CharacterParams

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
        super().__init__()
        self.bot = bot
        self.card_generator = CardGenerator()
        # 画像ダウンロード用の非同期HTTPクライアント
        self.http_client = httpx.AsyncClient()

    # レイド検知
    @commands.Component.listener()
    async def event_raid(self, payload: twitchio.ChannelRaid) -> None:
        user_id = payload.from_broadcaster.id
        user_name = payload.from_broadcaster.name
        viewers = payload.viewer_count
        print(f"[Raid 検知] {user_name} ({viewers} viewers)")

        # アイコンの画像データを取得
        image_bytes, mime_type = await self._fetch_profile_image(user_id)

        # 画像データも含めてカード生成サービスを呼び出す
        card_data = await self.card_generator.generate_character(
            user_name=user_name,
            event_type="raid",
            viewers=viewers,
            image_bytes=image_bytes,
            mime_type=mime_type
        )
        self._process_card_data(user_name, card_data)

    # ユーザーIDからプロフィール画像をダウンロードする内部メソッド
    async def _fetch_profile_image(self, user_id: str) -> tuple[bytes | None, str | None]:
        try:
            users = await self.bot.fetch_users(ids=[int(user_id)])
            if not users:
                print(f"[Warning] ユーザー情報が見つかりませんでした: ID {user_id}")
                return None, None

            profile_image_url = users[0].profile_image.url

            response = await self.http_client.get(profile_image_url)
            if response.status_code != 200:
                print(f"[Error] アイコンのダウンロードに失敗しました。Status: {response.status_code}")
                return None, None

            image_bytes = response.content
            mime_type = response.headers.get("Content-Type", "image/png")
            print(f"[Success] アイコン取得成功: {users[0].name} ({mime_type})")
            return image_bytes, mime_type

        except Exception as e:
            print(f"[Error] アイコン取得中に例外が発生しました: {e}")
            return None, None

    def _process_card_data(self, user_name: str, card_data: CharacterParams) -> None:
        print(f"--- キャラクターカードデータ生成完了: {user_name} ---")
        print(f"二つ名: {card_data.title}")
        print(f"属性: {card_data.attribute}")
        print(f"攻撃力: {card_data.attack_power} / 防御力: {card_data.defense_power}")
        print(f"必殺技: {card_data.skill_name}")
        print(f"説明文: {card_data.flavor_text}")
        print(f"画像生成プロンプト: {card_data.image_prompt}")
        print("--------------------------------------------------")
        print("[Mock] ここで Banana API を叩いて画像を生成します...")

    # 手動お遊び用コマンド
    @commands.command(name="make_card")
    async def make_card_command(self, ctx: commands.Context, name: str = None) -> None:
        # 名前指定がない場合はコマンド送信者
        if name is None:
            user_id = ctx.author.id
            target_name = ctx.author.name
        else:
            # 名前が指定された場合はTwitchからユーザー情報を検索してIDを特定する
            try:
                users = await self.bot.fetch_users(names=[name])
                if not users:
                    await ctx.send(f"ユーザー {name} が見つかりませんでした。")
                    return
                user_id = users[0].id
                target_name = users[0].name
            except Exception:
                await ctx.send("ユーザー情報の取得に失敗しました。")
                return

        # 擬似レイドオブジェクトを作ってキック
        class MockRaid:
            def __init__(self, uid: str, uname: str):
                self.from_broadcaster = type("User", (), {"id": uid, "name": uname})()
                self.viewer_count = 1

        await self.event_raid(MockRaid(user_id, target_name))
        await ctx.send(f"【AIカード生成】{target_name} さんのアイコンを解析してソシャゲ風パラメーターを生成しました！")


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
                    eventsub.ChannelRaidSubscription(
                        to_broadcaster_user_id=row["user_id"]
                    ),
                ]
            )

    return tokens, subs
