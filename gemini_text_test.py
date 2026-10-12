import os
import google.generativeai as genai
from dotenv import load_dotenv

# .envからAPIキー取得
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY が .env に設定されていません")

# Gemini API 初期化
genai.configure(api_key=api_key)

# モデル名は "models/gemini-pro" に明示
model = genai.GenerativeModel(model_name="models/gemini-pro")

# テストプロンプト
prompt = "美しい森の写真にユニークな名前をつけてください（日本語で1文）"
response = model.generate_content(prompt)

# 出力表示
print("🔹 Gemini 応答:")
print(response.text)
