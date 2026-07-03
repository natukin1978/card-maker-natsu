import base64

from google import genai
from google.genai import types

import global_value as g
from character_params import CharacterParams


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
        event_type: str,
        viewers: int = 0,
        image_bytes: bytes | None = None,
        mime_type: str | None = None
    ) -> CharacterParams:
        
        prompt_text = f"""
        あなたは凄腕のソーシャルゲームキャラクターデザイナーです。
        Twitchでの配信イベント「{event_type}」が発生しました。
        アクションを起こしたユーザー名: {user_name}
        イベントの規模（レイド人数など）: {viewers}人

        添付された画像（ユーザーの現在のTwitchプロフィールアイコン）のビジュアル要素を深く分析してください。
        このユーザー名とアイコンの雰囲気をモチーフにした、魅力的で最高にかっこいいソシャゲ風キャラクターカードの設定を考えてください。
        
        image_promptには、このアイコンの要素を取り込みつつ、アニメ風のハイクオリティなイラストを生成するための詳細な英語プロンプトを出力してください。
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
            print(f"[Banana] 画像生成リクエストを送信中... モデル: {self.get_image_model()}")

            response = self.genai_client.interactions.create(
                model=self.get_image_model(),
                input=[
                    {
                      "type": "text",
                      "text":
                        "A complete, masterful anime-style character illustration, reimagining the input profile icon as a full-fledged, highly detailed single artwork. "
                        "The character, based on the features of the input icon, is depicted in a [Pose/Action] within a [Detailed Background]. "
                        "Ensure there are absolutely no card frames, no user interface elements, and no game stats displayed.\n"
                        + image_prompt
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

            print("[Error] Bananaからのレスポンスに画像データが含まれていませんでした。")
            return None

        except Exception as e:
            print(f"[Error] Banana画像生成中に例外が発生しました: {e}")
            return None
