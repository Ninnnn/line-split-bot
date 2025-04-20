from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime
import os
import json

from sheet_utils import append_group_record, append_personal_record, get_personal_records_by_name, reset_personal_record_by_name

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

group_records = []
personal_records = {}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    reply = ""

    if msg.startswith("記帳 "):
        try:
            parts = msg.split()
            payer = parts[1]
            amount = int(parts[2])
            members = parts[3].split(",")
            note = parts[4] if len(parts) > 4 else ""
            date = parts[5] if len(parts) > 5 else datetime.now().strftime("%Y-%m-%d")
            group_records.append({'payer': payer, 'amount': amount, 'members': members, 'note': note, 'date': date})
            try:
                append_group_record(payer, amount, members, note, date)
            except Exception as e:
                print("寫入 Google Sheet 失敗（團體）:", e)
            reply = f"已記帳：{payer} 支付 {amount} 元，成員：{','.join(members)}，備註：{note}，消費日：{date}"
        except:
            reply = "格式錯誤，請使用：記帳 張三 300 張三,李四 晚餐 2025-04-20"

    elif msg == "查帳":
        total = {}
        for r in group_records:
            payer, amount, members = r['payer'], r['amount'], r['members']
            share = amount / len(members)
            for m in members:
                total[m] = total.get(m, 0) + (share if m != payer else -amount + share)
        result = "\n".join([f"{name} 應付 {round(amt)} 元" for name, amt in total.items()])
        reply = f"【結算報告】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{result}"

    elif msg == "重啟":
        group_records.clear()
        reply = "已清除所有團體記帳資料"

    elif msg.startswith("個人記帳 "):
        try:
            parts = msg.split()
            amount = int(parts[1])
            if "/" not in parts[2]:
                reply = "格式錯誤，請使用：個人記帳 金額 備註/名字 日期(選填)"
            else:
                note, name = parts[2].split("/")
                date = parts[3] if len(parts) > 3 else datetime.now().strftime("%Y-%m-%d")
                try:
                    append_personal_record(name, amount, note, date)
                except Exception as e:
                    print("寫入 Google Sheet 失敗（個人）:", e)
                reply = f"已記錄：{amount} 元，備註：{note}，消費日：{date}，記錄人：{name}"
        except:
            reply = "格式錯誤，請使用：個人記帳 金額 備註/名字 日期(選填)"

    elif msg.startswith("查詢個人"):
        parts = msg.split()
        if len(parts) != 2:
            reply = "格式錯誤，請使用：查詢個人 名字"
        else:
            name = parts[1]
            records = get_personal_records_by_user(name)
            if not records:
                reply = f"{name} 沒有任何個人記帳紀錄。"
            else:
                total = sum(int(r['amount']) for r in records)
                detail = "\n".join([f"{r['date']} - {r['amount']} 元 - {r['note']}" for r in records])
                reply = f"【{name} 的個人記帳】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{detail}\n\n總金額：{total} 元"

    elif msg.startswith("重設個人"):
        parts = msg.split()
        if len(parts) != 2:
            reply = "格式錯誤，請使用：重設個人 名字"
        else:
            name = parts[1]
            reset_personal_record_by_name(name)
            reply = f"已清除 {name} 的所有個人記帳資料"

    else:
        reply = (
            "請使用以下指令：\n"
            "- 記帳 張三 300 張三,李四 晚餐 2025-04-20\n"
            "- 查帳\n"
            "- 重啟\n"
            "- 個人記帳 150 便當/寧 2025-04-20\n"
            "- 查詢個人 寧\n"
            "- 重設個人 寧"
        )

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run()
