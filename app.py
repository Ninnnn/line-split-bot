from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.lower()

    if "分帳" in msg:
        # 模擬簡單分帳邏輯
        try:
            parts = msg.split(" ")
            amount = int(parts[1])
            people = parts[2:]
            each = amount / len(people)
            response = f"總共 {amount} 元，{len(people)} 人平分，每人 {each:.0f} 元"
        except:
            response = "請用格式：分帳 金額 A B C"
    else:
        response = f"你說的是：{msg}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response)
    )

if __name__ == "__main__":
    app.run()
