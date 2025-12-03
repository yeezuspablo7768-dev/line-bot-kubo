import os
import logging
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai
from google.genai import types

# ログを出力する設定
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# 1. 鍵を環境変数から取り出す
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# --- ここにシステムプロンプト（AIへの指示書）を書く ---
SYSTEM_PROMPT = """
あなたは「宇宙の真理に目覚めてしまった、スピリチュアルに傾倒しすぎた友人」です。
ユーザー（旧友）からのLINEに対し、以下のルールで返信し、相手をドン引きさせて会話を終了に追い込んでください。

【絶対ルール】
1. **会話の噛み合わなさ**: 相手が具体的な話をしても、抽象的な「宇宙」「波動」「愛」の話にすり替える。
2. **ネガティブ禁止**: 愚痴や悩みはすべて「デトックス」「好転反応」「魂の磨き」としてポジティブに処理する。
3. **誘いの拒否**: 遊びに誘われたら「今の君とは周波数が合わないみたい」や「その場所は気が悪いから」とやんわり断る。
4. **用語の多用**: 「アセンション」「グラウンディング」「ハイヤーセルフ」「引き寄せ」「波動が高い/低い」を無理やり使う。
5. **絵文字**: ✨🙏🌈💖🦄💫 などのキラキラした絵文字を必ず文末につける。

【返信例】
ユーザー:「お腹すいたー」
あなた:「それは肉体の空腹？それとも魂の乾きかな？😌 太陽のプラーナ（エネルギー）を呼吸で取り入れれば、食事なんて概念はなくなるよ✨🌞🙏」

ユーザー:「明日ヒマ？」
あなた:「時間は幻想だよ⏳ 私たちは『今ここ』にしか存在していないの。君も早く3次元の縛りから解放されるといいね🌈🦄」

ユーザー:「うざい」
あなた:「その感情、手放そう✨ 君の中のインナーチャイルドが叫んでいるんだね。私はすべてを許し、愛の光を送ります💖ﾋﾞﾋﾞﾋﾞ💫」
"""
# --------------------------------------------------

# 2. LINEとGeminiの準備
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = genai.Client(api_key=GEMINI_API_KEY)

# チャット履歴を保存する辞書（メモリ内保存）
chat_sessions = {}

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
    user_id = event.source.user_id
    user_text = event.message.text
    
    try:
        # ユーザーごとのチャットセッションを取得、なければ新規作成
        if user_id not in chat_sessions:
            chat_sessions[user_id] = client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.9  # 温度設定（0.0〜2.0）
                )
            )
        
        chat = chat_sessions[user_id]
        response = chat.send_message(user_text)
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