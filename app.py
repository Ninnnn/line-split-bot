import os
from flask import Flask, request, abort
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 匯入 Google Sheet 操作函式
from sheet_utils import append_personal_record, get_personal_records_by_user, reset_personal_record_by_name

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()

    if msg.startswith("個人記帳 "):
        try:
            parts = msg.split()
            amount = int(parts[1])
            content = parts[2] if len(parts) > 2 else ""
            if "/" in content:
                note, name = content.split("/")
            else:
                note = content
                name = user_id  # 若無指定名字，使用 user_id 當作名字
            date = parts[3] if len(parts) > 3 else datetime.now().strftime("%Y-%m-%d")

            # 寫入 Google Sheet
            try:
                append_personal_record(user_id, name, amount, note, date)
            except Exception as e:
                print("寫入 Google Sheet 失敗（個人）:", e)

            msg = f"已記錄：{amount} 元，備註：{note}，消費日：{date}，對象：{name}"

        except Exception as e:
            msg = "格式錯誤！請使用：個人記帳 金額 備註/對象 日期(選填)"

    elif msg.startswith("查詢個人"):
        try:
            parts = msg.split()
            if len(parts) < 2:
                msg = "格式錯誤！請使用：查詢個人 對象（例如：查詢個人 寧）"
            else:
                name = parts[1]
                records = get_personal_records_by_user(name)
                if not records:
                    msg = f"{name} 沒有任何記帳紀錄"
                else:
                    total = sum([int(r['amount']) for r in records])
                    detail = "\n".join([f"{r['date']}: {r['amount']} 元 - {r['note']}" for r in records])
                    msg = f"【{name} 的個人記帳查詢】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{detail}\n\n總金額：{total} 元"
        except Exception as e:
            msg = "查詢個人時發生錯誤，請確認格式與內容正確。"

    elif msg.startswith("重設個人"):
        try:
            parts = msg.split()
            if len(parts) < 2:
                msg = "格式錯誤！請使用：重設個人 對象（例如：重設個人 寧）"
            else:
                name = parts[1]
                reset_personal_record_by_name(name)
                msg = f"{name} 的個人記帳資料已重設"
        except Exception as e:
            msg = "重設個人時發生錯誤，請確認格式與內容正確。"

    else:
        msg = "請輸入指令，例如：\n- 個人記帳 150 晚餐/寧 2025-04-20\n- 查詢個人 寧\n- 重設個人 寧"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

if __name__ == "__main__":
    app.run()
