from google import genai

import global_value as g
from character_params import CharacterParams


class CardGenerator:
    def __init__(self) -> None:
        self.genai_client = genai.Client(api_key=self.get_api_key())

    def get_api_key(self) -> str:
        return g.config["google"]["geminiApiKey"]

    def get_model(self) -> str:
        return g.config["google"]["modelName"]

    async def generate_character(self, user_name: str, event_type: str, viewers: int = 0) -> CharacterParams:
        prompt = f"""
        あなたは凄腕のソーシャルゲームキャラクターデザイナーです。
        Twitchでの配信イベント「{event_type}」が発生しました。
        アクションを起こしたユーザー名: {user_name}
        イベントの規模（レイド人数など）: {viewers}人

        このユーザーをモチーフにした、魅力的で最高にかっこいいソシャゲ風キャラクターカードの設定を考えてください。
        image_promptには、アニメ風のハイクオリティなイラストを生成するための詳細な英語プロンプトを出力してください。
        """

        response = await self.genai_client.aio.models.generate_content(
            model=self.get_model(),
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": CharacterParams.model_json_schema(),
                "temperature": 0.8,
            },
        )

        return CharacterParams.model_validate_json(response.text)
