from pydantic import BaseModel, Field


class CharacterParams(BaseModel):
    title: str = Field(description="キャラクターの二つ名（例: 疾風の開拓者）")
    attribute: str = Field(description="属性（炎、水、風、光、闇など）")
    attack_power: int = Field(description="攻撃力（1000〜9999の間）")
    defense_power: int = Field(description="防御力（1000〜9999の間）")
    skill_name: str = Field(description="必殺技の名前")
    flavor_text: str = Field(description="キャラクターの短いフレーバーテキスト（説明文）")
    image_prompt: str = Field(description="このキャラクターのカードイラストを描画するための、詳細で高品質な英語の画像生成プロンプト")
