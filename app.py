from flask import Flask, request, abort
from bot import handler  # 從 bot 匯入 handler 物件

app = Flask(__name__)

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f"LINE webhook error: {e}")
        abort(400)

    return "OK"

if __name__ == "__main__":
    app.run()
