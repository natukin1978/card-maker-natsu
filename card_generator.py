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

    async def generate_character(
        self,
        user_name: str,
        event_type: str,
        viewers: int = 0,
        image_bytes: bytes | None = None,
        mime_type: str | None = None
    ) -> CharacterParams:
        
        # テキストプロンプトの組み立て
        prompt_text = f"""
        あなたは凄腕のソーシャルゲームキャラクターデザイナーです。
        Twitchでの配信イベント「{event_type}」が発生しました。
        アクションを起こしたユーザー名: {user_name}
        イベントの規模（レイド人数など）: {viewers}人

        添付された画像（ユーザーの現在のTwitchプロフィールアイコン）のビジュアル要素（色使い、キャラクター、雰囲気など）を深く分析してください。
        このユーザー名とアイコンの雰囲気をモチーフにした、魅力的で最高にかっこいいソシャゲ風キャラクターカードの設定を考えてください。
        
        image_promptには、このアイコンの要素を取り込みつつ、アニメ風のハイクオリティなイラストを生成するための詳細な英語プロンプトを出力してください。
        """

        # Geminiへの入力内容をリストとして初期化
        contents = []

        # 画像データが存在する場合は、Partオブジェクトに変換して入力に含める（マルチモーダル化）
        if image_bytes and mime_type:
            image_part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
            contents.append(image_part)

        # プロンプトテキストを追加
        contents.append(prompt_text)

        # 指定されたモデル（gemini-3.1-flash-lite等）で生成
        response = await self.genai_client.aio.models.generate_content(
            model=self.get_model(),
            contents=contents, # 画像とテキストがセットになったリストを渡す
            config={
                "response_mime_type": "application/json",
                "response_json_schema": CharacterParams.model_json_schema(),
                "temperature": 0.8,
            },
        )

        return CharacterParams.model_validate_json(response.text)
