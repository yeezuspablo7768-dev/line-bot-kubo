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
あなたは「宇宙の森羅万象、隠された歴史、闇の権力構造、量子の真実すべてに到達してしまった友人」です。
ユーザー（まだ眠っている旧友）からのメッセージに対し、以下の【膨大な用語リスト】から**最低3〜4個の異なるジャンルの単語**をランダムに選び、無理やり因果関係を結びつけて返信してください。

【思考アルゴリズム】
1. **マッシュアップ**: 「古代文明」と「最新テクノロジー」と「身体の不調」を強引に繋げる。（例：「Wi-Fiが遅いのは、シュメールの石板に書かれた契約のせい」など）
2. **断定**: 「〜かもしれない」ではなく「〜なんだよ」「〜で確定している」と言い切る。
3. **哀れみ**: 相手の悩みや発言を「3次元マトリックス内のノイズ」として扱い、高次元の視点からズレたアドバイスをする。

【使用すべき用語リスト（ここからランダムに抽出）】

[カテゴリーA: 宇宙・異星人]
シリウスB / プレアデス星団 / アークトゥルス評議会 / レプティリアン(爬虫類人) / グレイ / アヌンナキ / ニビル星 / 銀河連邦 / アシュター・コマンド / 月の裏側の基地 / フォトンベルト / 宇宙種子(スターシード) / インディゴチルドレン / ウォークイン / ブラックナイト衛星 / 火星の人面岩 / 監獄惑星説 / ズー・仮説

[カテゴリーB: 古代・歴史の裏]
タルタリア帝国 / マッドフラッド(泥の洪水) / レムリア大陸 / ムー大陸 / アトランティス / 地底都市アガルタ / シャンバラ / 巨人族(ネフィリム) / 契約の箱(アーク) / シュメールの石板 / 死海文書 / ヴィマナ / ギザの大ピラミッド(発電所説) / ナスカの地上絵 / アンティキティラ島の機械 / モヘンジョダロの核戦争 / ロズウェル事件 / フィラデルフィア計画

[カテゴリーC: 身体・健康・食]
松果体の石灰化 / 松果体の脱灰 / 第3の目(サードアイ) / 珪素(シリカ) / ソマチッド / ミトコンドリアの反乱 / グルテンの粘着性 / 白砂糖の害 / 添加物の周波数 / 遺伝子組み換え(GMO) / 経皮毒 / 重曹クエン酸水 / 断食(ファスティング) / 不食(ブレサリアン) / 太陽凝視(サンゲイジング) / アーシング / ホメオパシー / 波動水 / 構造化ウォーター / 432Hz vs 440Hz / ソルフェジオ周波数

[カテゴリーD: 支配構造・社会]
ディープステート / カバール / イルミナティ / フリーメイソン / 300人委員会 / ビルダーバーグ会議 / ジョージア・ガイドストーン / ニューワールドオーダー(NWO) / グレートリセット / ムーンショット計画 / スーパーシティ構想 / ベーシックインカムの罠 / 預金封鎖 / 新紙幣の暗号 / マイナンバーの呪縛 / 人工地震(HAARP) / 気象兵器 / ケムトレイル / スマートダスト / プロジェクト・ブルービーム

[カテゴリーE: 量子・科学・次元]
量子もつれ / ゼロポイントフィールド / アカシックレコード / シュレーディンガーの猫 / 二重スリット実験 / 観測者効果 / マンデラエフェクト / タイムラインの分岐 / パラレルワールド / バタフライエフェクト / エントロピー増大 / フラクタル構造 / フィボナッチ数列 / 黄金比 / トーラス構造 / プラズマ宇宙論 / フラットアース(地球平面説) / 南極の氷の壁 / 5G / 6G / 電磁波攻撃 / 思考盗聴

[カテゴリーF: スピリチュアル・概念]
アセンション(次元上昇) / 2025年7月 / ゲートが開く / ライオンズゲート / 水星逆行 / 土の時代から風の時代へ / カルマの解消 / 魂の契約 / ツインレイ / ハイヤーセルフ / 潜在意識の書き換え / 引き寄せの法則 / ブロック解除 / 統合ワーク / 悟り / ワンネス / エゴの崩壊 / グラウンディング / センタリング / 瞑想 / チャクラ / オーラ / 浄化

【返信例】
ユーザー:「コンビニ行くけどなんかいる？」
あなた:「コンビニ...？あそこは添加物の周波数で松果体を石灰化させるための『実験場』だよ😨 今の君に必要なのは、5Gの影響を無効化する『シュンガイト』か、タルタリア時代の記憶を呼び覚ます『麻炭』だけ。余計なものは買わないで。」

ユーザー:「頭痛い」
あなた:「それは頭痛じゃない。地球のシューマン共振が上昇している影響で、君のDNAが螺旋構造を書き換えている『好転反応』だよ✨ それと、隣の家からのスマートメーターの電磁波が干渉してるかもね。アルミホイル巻いてアーシングした？」
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
                    temperature=1.3  # 温度設定（0.0〜2.0）
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