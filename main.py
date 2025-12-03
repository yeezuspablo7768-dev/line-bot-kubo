import os
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai

# ログを出力する設定
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# 1. 鍵を環境変数から取り出す
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# 2. LINEとGeminiの準備
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = genai.Client(api_key=GEMINI_API_KEY)

# 3. LINEからのアクセスを受け付ける「裏口」
@app.route("/callback", methods=['POST'])
def callback():
    # 署名の検証
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 4. メッセージが届いた時の処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    try:
        # Geminiに返信を考えてもらう
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_text
        )
        reply_text = response.text
    except Exception as e:
        reply_text = "エラーが発生しました: " + str(e)
        app.logger.error(f"Gemini Error: {e}")

    # LINEに返信する
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run()