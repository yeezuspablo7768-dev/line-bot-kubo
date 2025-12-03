from flask import Flask

# 1. アプリ（お店）を作る
app = Flask(__name__)

# 2. 受付係（ルーティング）を作る
@app.route("/")
def hello_world():
    # 3. 接客（処理）をして返す
    return "OK"

# 4. お店をオープンする
if __name__ == "__main__":
    app.run(port=5000)