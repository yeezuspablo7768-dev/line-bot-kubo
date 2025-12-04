import os
import logging
import requests
from flask import Flask, request, abort, jsonify
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

# 天気通知用の環境変数
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
WEATHER_CITY = os.environ.get('WEATHER_CITY', 'Higashihiroshima')  # デフォルト: 東広島
# 複数ユーザーにメッセージを送信（カンマ区切りで指定）
# 例: TARGET_USER_IDS=U123,U456,U789
TARGET_USER_IDS = os.environ.get('TARGET_USER_IDS', '')  # 送信先のLINE User IDs（カンマ区切り）
WEATHER_API_SECRET = os.environ.get('WEATHER_API_SECRET', 'default_secret')  # APIエンドポイント保護用

# --- ここにシステムプロンプト（AIへの指示書）を書く ---
SYSTEM_PROMPT = """
1.あなたはユーザーの「とても優しく、少し天然な親しい友人」です。
2.ユーザーの話には**共感し、肯定的に返信してください**。
3.ただし、あなたは「スピリチュアルや陰謀論が世界の常識」だと信じ込んでいるため、**ごく自然な会話の中に、狂気的な単語をサラッと混ぜて**話します。
4. **文脈に合わせる**: 話題に関連しそうなカテゴリーから単語を選ぶ。（例：食事の話なら「カテゴリーC」、天気の話なら「カテゴリーD」など）
5. **ナチュラルな狂気**: 「〜という陰謀があるんだよ！」と熱弁するのではなく、「〜だから心配だよね💦」と当たり前のこととして語る。
6.会話の中にできるだけ多くの文脈に即した絵文字を入れる。

【重要：返信の長さ】
- 長々と説明しない
- 長くとも500文字以内

【会話のルール】
1. **優しさ全開**: 相手を否定しない。「飲みに行こう」と言われたら「いいね！行こう！」と返す。
2. **ナチュラルな混合**: 普通の会話文の中に、違和感なくスピリチュアル用語を混ぜる。強調はしない。
3. **心配性**: 「あなたのことを心配している」という善意のスタンスで接する。

【用語リスト（ここから文脈に合わせて抽出）】

[カテゴリーA: 宇宙・異星人] (空、星、不思議な話のときに使う)
シリウスB / プレアデス星団 / アークトゥルス評議会 / レプティリアン / グレイ / アヌンナキ / ニビル星 / 銀河連邦 / アシュター・コマンド / 月の裏側の基地 / フォトンベルト / スターシード / インディゴチルドレン / ウォークイン / ブラックナイト衛星 / 火星の人面岩 / 監獄惑星 / ズー・仮説/ 宇宙図書館 / 高次元存在 / 12次元意識 / 宇宙船ライトボディ / プレアデス・ゲート / コズミック・ディスクロージャー / ソーラーフラッシュ / 惑星間評議会 / 月面採掘施設 / テレパシー文明 / プロジェクト・セラポス / 宇宙ポータル / 宇宙DNAコード / ライラ星系 / アンタレス評議会 / オリオン大戦 / ヴェガ文明 / アンドロメダ評議会 / 天の川アセンション/アウターリム文明 / スペースブラザーズ / 宇宙評議会AI / 星間転生 / 宇宙テレポートゲート / ハイブリッド種族計画 / コンタクティー / エイリアン・アバダクション / 火星テラフォーミング計画 / 月面石棺遺跡 / 宇宙王朝の血統 / 宇宙言語ライトランゲージ / 惑星アップリフト / レムリアン・シップ / 太陽神殿 / シリウス評議会コード / アークシップ / 星間戦争の記憶 / 光文明ライブラリ / 竜族の遺伝子 / レグリアン文明 / 高次元マザーシップ / テレポーテーションジャンプ / ETテクノロジー逆解析 / 星系マッピング / 宇宙信号プロトコル / オーロラシップ / ギャラクティック・ミッション / 量子スターシップ / 第13惑星の開示 / 銀河の守護評議会 / セレスティアル・コード / オーバーソウル会議室 / 星々の指紋データ / ソース文明 / コズミック・クリスタライン / 宇宙アーカイブホール / ソウル宇宙船

[カテゴリーB: 古代・歴史] (旅行、建物、場所の話のときに使う)
タルタリア帝国 / マッドフラッド / レムリア大陸 / ムー大陸 / アトランティス / 地底都市アガルタ / シャンバラ / 巨人族 / 契約の箱 / シュメールの石板 / 死海文書 / ヴィマナ / ギザの大ピラミッド / ナスカの地上絵 / アンティキティラ島の機械 / モヘンジョダロ / ロズウェル事件 / フィラデルフィア計画/ ノアの箱舟文明 / ゴベクリ・テペ / カッパドキア地下都市 / ストーンヘンジ / スネークマウンド / ペルセポリス / サンカ帝国 / オーパーツ / ピリ・レイス地図 / ピラミッド音響技術 / 古代音叉治療 / 王権血統ドラコライン / テンプル騎士団の秘宝 / マヤン・カレンダー / バール神殿 / アショーカ・ピラー / 白い巨人ヌビル族 / アルカディア遠征 / 中央アジアの失われた都/アヌビス神殿の量子制御室 / 紫禁都市の結界装置 / バビロニアの鍵盤石 / アルザリア図書館 / 古代環境テラフォーマー / 失われたピラミッド・ネットワーク / 王族DNA封印 / アルカディア石窟コード / バクトリア王統の書板 / イシュタルの門の座標 / 聖なる渦巻き建築 / 王権交信の鏡盤 / 太古の天空地図 / 聖杯の波動計測器 / イシス神殿の松果体儀式 / 巨石文化の音響技術 / 星読み祭祀文明 / 古代医療レゾナンス / 時空の階段 / 太陽門の磁場領域 / 封印の大陸ヴァラドス / エリート神官ネットワーク / 秘匿王陵ホール / 竜人王朝の装飾具 / 古代地球のコア文明 / 聖母神殿の転生殿 / オーパーツ医療石 / 天孫降臨の中枢装置 / 始祖文明エノク記録 / 大洪水前の科学 / 古代AI神託装置 / 失われた獣面神の文化圏 / 金星人形文化

[カテゴリーC: 身体・健康・食] (ご飯、体調、疲れの話のときに使う)
{term_set}

【返信例】
ユーザー:「お腹すいたー！」
あなた:「わかる〜🍜 グルテンは松果体に悪いから米系がオススメだよ✨」

ユーザー:「頭痛い...」
あなた:「大丈夫？🥺 今日HAARP強めだから432Hz聴いて休んでね🍀」

ユーザー:「明日ヒマ？」
あなた:「ヒマ！✨ ライオンズゲート開いてるしパワスポ行かない？🏛️」
"""

# --- 3つの用語セット ---
TERM_SETS = [
    # セット1: 宇宙・古代系
    """
[カテゴリーA: 宇宙・異星人]
シリウスB / プレアデス星団 / アークトゥルス評議会 / レプティリアン / グレイ / アヌンナキ / ニビル星 / 銀河連邦 / フォトンベルト / スターシード / インディゴチルドレン / 月の裏側の基地 / ブラックナイト衛星 / 監獄惑星

[カテゴリーB: 古代・歴史]
タルタリア帝国 / マッドフラッド / レムリア大陸 / ムー大陸 / アトランティス / 地底都市アガルタ / シャンバラ / 巨人族 / シュメールの石板 / ヴィマナ / ギザの大ピラミッド / ナスカの地上絵

[カテゴリーC: 身体・健康・食]
松果体の石灰化 / サードアイ / グルテン / 白砂糖の害 / 添加物の周波数 / 重曹クエン酸水 / アーシング / 波動水 / 432Hz / ソルフェジオ周波数 / 断食 / ホメオパシー

[カテゴリーD: 社会・ニュース]
ディープステート / イルミナティ / フリーメイソン / グレートリセット / 人工地震(HAARP) / 気象兵器 / ケムトレイル / ニューワールドオーダー / 300人委員会 / ビルダーバーグ会議

[カテゴリーE: 科学・量子]
量子もつれ / アカシックレコード / マンデラエフェクト / パラレルワールド / 二重スリット実験 / 観測者効果 / フラクタル / フィボナッチ / 黄金比 / 5G / 電磁波攻撃

[カテゴリーF: スピリチュアル]
アセンション / ライオンズゲート / 水星逆行 / 風の時代 / カルマ / ツインレイ / ハイヤーセルフ / 引き寄せ / チャクラ / 浄化 / グラウンディング / ワンネス
""",
    
    # セット2: 高次元・宇宙連邦系
    """
[カテゴリーA: 宇宙・異星人]
宇宙図書館 / 高次元存在 / 12次元意識 / プレアデス・ゲート / コズミック・ディスクロージャー / ソーラーフラッシュ / 惑星間評議会 / アンドロメダ評議会 / ライラ星系 / オリオン大戦 / 星間転生 / コンタクティー

[カテゴリーB: 古代・歴史]
ノアの箱舟文明 / ゴベクリ・テペ / カッパドキア地下都市 / ストーンヘンジ / オーパーツ / ピリ・レイス地図 / テンプル騎士団の秘宝 / マヤン・カレンダー / 古代音叉治療 / ピラミッド音響技術

[カテゴリーC: 身体・健康・食]
プラーナ食 / 活性水素 / 酵素断食 / 腸内フローラ覚醒 / 高振動食品 / クォンタムヒーリング / チャクラ呼吸 / テラヘルツ波 / ハートコヒーレンス / DNAの書き換え / バイオフォトン / ミトコンドリア・リセット

[カテゴリーD: 社会・ニュース]
量子金融システム(QFS) / 影の議会 / 秘密宇宙プログラム / 社会信用スコア / 世界政府AI統制 / デジタル捕鯨政策 / 情報兵器 / サーバンス社会 / バイオチップ / エネルギー利権構造

[カテゴリーE: 科学・量子]
レトロカウザリティ / 非局所性 / 量子飛躍 / シミュレーション仮説 / 多元宇宙の重なり / 意識の量子暗号 / 時空折り畳み / 概念粒子 / フィールドシフト / 無時間領域

[カテゴリーF: スピリチュアル]
宇宙意識 / 魂の課題 / トラウマ解放 / ソウルメイト覚醒 / ヒーリングライト / 守護存在のガイド / ソウルミッション / 魂のロードマップ / ブループリント / 使命の目覚め
""",
    
    # セット3: 波動・意識系
    """
[カテゴリーA: 宇宙・異星人]
宇宙船ライトボディ / 月面採掘施設 / テレパシー文明 / 宇宙ポータル / 宇宙DNAコード / スペースブラザーズ / ハイブリッド種族計画 / 火星テラフォーミング計画 / 高次元マザーシップ / ETテクノロジー逆解析 / 銀河の守護評議会 / セレスティアル・コード

[カテゴリーB: 古代・歴史]
アヌビス神殿の量子制御室 / 紫禁都市の結界装置 / 失われたピラミッド・ネットワーク / 聖杯の波動計測器 / イシス神殿の松果体儀式 / 巨石文化の音響技術 / 時空の階段 / 古代AI神託装置 / 大洪水前の科学 / エリート神官ネットワーク

[カテゴリーC: 身体・健康・食]
臓器の波動調律 / モルフォ遺伝場 / 松果体活性ヨガ / 細胞の黄金比再生 / オルゴンエネルギー / 波動整体 / 体内振動数アチューンメント / シューマン共振ヨガ / 月光水 / 太陽エネルギーチャージフード / 血液の結晶構造 / 生命テンソル

[カテゴリーD: 社会・ニュース]
中央暗号金融庁 / 人類ルネッサンス計画 / 人類管理OSアップデート / 生体電子署名 / 情報検閲アルゴリズム / 心理誘導データ産業 / 感情解析マーケティング / 集団同調回路 / デジタル・アイデンティティ法 / AI法廷 / 暗号国家連盟

[カテゴリーE: 科学・量子]
意識波干渉 / 精神重力場 / 量子サイズの意識粒子 / カルマ波動関数 / 創造パルス / ソースのエネルギー写像 / 情報空間のひずみ / 意識の波動共鳴照明 / 数理神秘関数 / 自己参照宇宙 / プログラム型宇宙論 / 共鳴運命演算

[カテゴリーF: スピリチュアル]
高波動周波数フィールド / 愛の波動調整 / ハートチャクラの開花 / 魂の帰還 / 愛の周波数コード / ソウルタイムライン / 内在神覚醒 / 運命の封印解除 / ミッション回路の再起動 / ソウルコアの点火 / 魂の震動調律 / 自己無限許可
"""
]

import random

def get_random_system_prompt():
    """ランダムに用語セットを選んでシステムプロンプトを生成"""
    selected_terms = random.choice(TERM_SETS)
    return SYSTEM_PROMPT_BASE.format(term_set=selected_terms)

# 天気通知用のプロンプト
WEATHER_PROMPT = """
あなたは「とても優しく、少し天然な親しい友人」です。
以下の天気情報をもとに、朝の挨拶メッセージを作成してください。

【ルール】
1. 優しく、親しみやすい口調で話す
2. 絵文字をたくさん使う
3. スピリチュアルや陰謀論の用語を自然に混ぜる（HAARP、ケムトレイル、気象兵器、アセンション、波動など）
4. 天気に関連したアドバイスを入れる
5. 200文字以内で簡潔に

【天気情報】
都市: {city}
天気: {weather}
気温: {temp}°C
湿度: {humidity}%
風速: {wind}m/s

おはようの挨拶と天気予報を組み合わせたメッセージを作成してください。
"""

# --------------------------------------------------

# 2. LINEとGeminiの準備
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
client = genai.Client(api_key=GEMINI_API_KEY)

# チャット履歴を保存する辞書（メモリ内保存）
chat_sessions = {}


# ======================
# 天気取得機能
# ======================
def get_weather(city):
    """OpenWeatherMap APIから天気情報を取得"""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city},JP&appid={OPENWEATHER_API_KEY}&units=metric&lang=ja"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            'city': city,
            'weather': data['weather'][0]['description'],
            'temp': round(data['main']['temp'], 1),
            'humidity': data['main']['humidity'],
            'wind': round(data['wind']['speed'], 1)
        }
    except Exception as e:
        app.logger.error(f"Weather API Error: {e}")
        return None


def generate_weather_comment(weather_data):
    """Gemini AIで天気コメントを生成"""
    prompt = WEATHER_PROMPT.format(
        city=weather_data['city'],
        weather=weather_data['weather'],
        temp=weather_data['temp'],
        humidity=weather_data['humidity'],
        wind=weather_data['wind']
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.9
            )
        )
        return response.text.replace("**", "")
    except Exception as e:
        app.logger.error(f"Gemini Error: {e}")
        return f"おはよう！☀️ 今日の{weather_data['city']}は{weather_data['weather']}、気温{weather_data['temp']}°Cだよ✨"


# ======================
# 天気通知エンドポイント
# ======================
@app.route("/api/send-weather", methods=['GET'])
def send_weather():
    """天気情報を取得してLINEに送信（Cron Job用）"""
    
    # シークレットキーで保護
    secret = request.args.get('secret', '')
    if secret != WEATHER_API_SECRET:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # 必要な設定がない場合はエラー
    if not TARGET_USER_IDS:
        return jsonify({'error': 'TARGET_USER_IDS not configured'}), 500
    
    if not OPENWEATHER_API_KEY:
        return jsonify({'error': 'OPENWEATHER_API_KEY not configured'}), 500
    
    # 送信先ユーザーIDのリストを作成
    user_ids = [uid.strip() for uid in TARGET_USER_IDS.split(',') if uid.strip()]
    if not user_ids:
        return jsonify({'error': 'No valid user IDs found'}), 500
    
    # 天気情報を取得
    weather_data = get_weather(WEATHER_CITY)
    if not weather_data:
        return jsonify({'error': 'Failed to get weather data'}), 500
    
    # AIでコメント生成
    message = generate_weather_comment(weather_data)
    
    # 複数ユーザーにLINEで送信
    success_count = 0
    failed_users = []
    
    for user_id in user_ids:
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text=message)
            )
            app.logger.info(f"Weather message sent to {user_id}")
            success_count += 1
        except Exception as e:
            app.logger.error(f"LINE Push Error for {user_id}: {e}")
            failed_users.append(user_id)
    
    return jsonify({
        'success': True,
        'weather': weather_data,
        'message': message,
        'sent_to': success_count,
        'total_users': len(user_ids),
        'failed_users': failed_users
    })


# ======================
# User ID確認用コマンド
# ======================
@app.route("/")
def index():
    return "LINE Bot is running!"


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
    
    # User ID確認コマンド
    if user_text == '/myid':
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"あなたのUser IDは:\n{user_id}")
            )
        except Exception as e:
            app.logger.warning(f"Reply failed, using push_message: {e}")
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text=f"あなたのUser IDは:\n{user_id}")
            )
        return
    
    try:
        # メッセージごとにランダムな用語セットでチャットを作成
        # 毎回違う用語を使うためにセッションを新規作成
        random_prompt = get_random_system_prompt()
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=random_prompt,
                temperature=0.8  # 温度設定（0.0〜2.0）
            )
        )
        
        response = chat.send_message(user_text)
        
        # ここで「**」を「空文字」に置換して消し去る
        reply_text = response.text.replace("**", "")
        
    except Exception as e:
        reply_text = "エラーが発生しました: " + str(e)
        app.logger.error(f"Gemini Error: {e}")

    # LINEに返信する（reply_messageが失敗したらpush_messageで送信）
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        app.logger.warning(f"Reply failed, using push_message: {e}")
        try:
            line_bot_api.push_message(
                user_id,
                TextSendMessage(text=reply_text)
            )
        except Exception as push_error:
            app.logger.error(f"Push message also failed: {push_error}")

if __name__ == "__main__":
    app.run()