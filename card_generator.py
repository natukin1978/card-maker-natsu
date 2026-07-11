import base64
import logging

from google import genai
from google.genai import types

import global_value as g
from character_params import CharacterParams

logger = logging.getLogger(__name__)


class CardGenerator:

    def __init__(self) -> None:
        self.genai_client = genai.Client(api_key=self.get_api_key())

    def get_api_key(self) -> str:
        return g.config["google"]["geminiApiKey"]

    def get_model(self) -> str:
        return g.config["google"]["modelName"]

    def get_image_model(self) -> str:
        return g.config["google"].get("modelNameImage", "gemini-3.1-flash-lite-image")

    async def generate_character(
        self,
        user_name: str,
        event_label: str,
        event_power_text: str,
        image_bytes: bytes | None = None,
        mime_type: str | None = None
    ) -> CharacterParams:

        prompt_text = f"""
        あなたは凄腕のソーシャルゲームキャラクターデザイナーです。
        Twitchでの配信イベント「{event_label}」が発生しました。
        添付された画像（ユーザーのTwitchプロフィールアイコン）を分析し、その「中心的なモチーフや全体の雰囲気」を捉えてください。

        【image_prompt 出力の重要なルール（トークン最適化とクオリティ向上）】
        画像生成モデルが直接アイコン画像を参照して特徴を引き継ぐため、アイコンの細かなビジュアル（髪の色や服の形など）を一から十まで言葉で説明する必要はありません。
        代わりに、以下の要素に特化した、アニメ風ハイクオリティイラスト用の詳細な英語プロンプトを作成してください。

        1. イベントの規模・熱量（{event_power_text}）に応じた「派手なエフェクト（魔法、オーラ、光、お祝いの演出など）」や「ドラマチックな構図・ポーズ」
        2. ユーザー名（{user_name}）から連想される、衣装のアレンジや背景の世界観
        3. 枠線（カードフレーム）、文字、ゲームUI、ステータスアイコンなどを絶対に生成させないための指示（例: "single cohesive artwork, no border, no text, no UI" などの表現を含める）

        元のアイコンの魂を引き継ぎつつ、イベントの熱量が伝わる最高の一枚絵（イラスト）にするための「拡張演出」に集中して出力してください。
        """

        contents = []
        if image_bytes and mime_type:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            contents.append(image_part)

        contents.append(prompt_text)

        response = await self.genai_client.aio.models.generate_content(
            model=self.get_model(),
            contents=contents,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": CharacterParams.model_json_schema(),
                "temperature": 0.8,
            },
        )

        return CharacterParams.model_validate_json(response.text)

    async def generate_image(
        self,
        image_prompt: str,
        icon_bytes: bytes | None = None,
        mime_type: str | None = None
    ) -> bytes | None:
        try:
            logger.info(f"[Banana] 画像生成リクエストを送信中... モデル: {self.get_image_model()}")

            response = self.genai_client.interactions.create(
                model=self.get_image_model(),
                input=[
                    {
                      "type": "text",
                      "text":
                        "A masterful, full-fledged anime-style character illustration, reimagining the input profile icon into a highly detailed single artwork. "
                        "While faithfully inheriting the core visual identity, character features, and color palette of the input icon, dynamically render the scene based on the following specific descriptions: "
                        f"{image_prompt} "
                        ", dynamic action pose, dramatic low-angle shot."
                        "Strictly ensure there are absolutely no card frames, borders, text, user interface elements, or game statistics displayed in the final image."
                    },
                    {
                        "type": "image",
                        "data": base64.b64encode(icon_bytes).decode('utf-8'),
                        "mime_type": mime_type,
                    },
                ],
                response_format={
                    "type": "image",
                    "mime_type": "image/jpeg",
                    "aspect_ratio": "1:1",
                    "image_size": "1K",
                },
            )

            generated_image = response.output_image
            if generated_image:
                return base64.b64decode(generated_image.data)

            logger.error("[Error] Bananaからのレスポンスに画像データが含まれていませんでした。")
            return None

        except Exception as e:
            logger.error(f"[Error] Banana画像生成中に例外が発生しました: {e}")
            return None
