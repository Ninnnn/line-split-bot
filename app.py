from sheet_utils import append_group_record, append_personal_record, get_personal_records_by_name, reset_personal_record_by_name
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from datetime import datetime
import json

# 新增匯入 Google Sheet 函式
from sheet_utils import append_group_record, append_personal_record

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
    user_id = event.source.user_id
    msg = event.message.text.strip()

    if msg.startswith("記帳 "):
        try:
            parts = msg.split()
            payer = parts[1]
            amount = int(parts[2])
            members = parts[3].split(",")
            note = parts[4] if len(parts) > 4 else ""
            date = parts[5] if len(parts) > 5 else datetime.now().strftime("%Y-%m-%d")
            
            # 儲存記錄
            group_records.append({
                'payer': payer,
                'amount': amount,
                'members': members,
                'note': note,
                'date': date
            })

            # 寫入 Google Sheet
            try:
                append_group_record(payer, amount, members, note, date)
            except Exception as e:
                print("寫入 Google Sheet 失敗（團體）:", e)

            msg = f"已記帳：{payer} 支付 {amount} 元，成員：{','.join(members)}，備註：{note}，消費日：{date}"

        except Exception as e:
            msg = "格式錯誤！請使用：記帳 付款人 金額 A,B,C 備註 日期(選填)"

    elif msg.startswith("查帳"):
        total = {}
        for record in group_records:
            payer = record['payer']
            amount = record['amount']
            members = record['members']
            share = amount / len(members)
            for m in members:
                if m != payer:
                    total[m] = total.get(m, 0) + share
            total[payer] = total.get(payer, 0) - (amount - share)

        summary = "\n".join([f"{k} 應付 {round(v)} 元" for k, v in total.items()])
        msg = f"【結算報告】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{summary}"

    elif msg == "重啟":
        group_records.clear()
        msg = "已清除所有團體記帳資料"

    elif msg.startswith("個人記帳 "):
        try:
            parts = msg.split()
            amount = int(parts[1])
            note = parts[2] if len(parts) > 2 else ""
            date = parts[3] if len(parts) > 3 else datetime.now().strftime("%Y-%m-%d")

            # 儲存個人記錄
            if user_id not in personal_records:
                personal_records[user_id] = []
            personal_records[user_id].append({
                'amount': amount,
                'note': note,
                'date': date
            })

            # 寫入 Google Sheet
            try:
                append_personal_record(user_id, amount, note, date)
            except Exception as e:
                print("寫入 Google Sheet 失敗（個人）:", e)

            msg = f"已記錄：{amount} 元，備註：{note}，消費日：{date}"

        except Exception as e:
            msg = "格式錯誤！請使用：個人記帳 金額 備註 日期(選填)"

    elif msg.startswith("查詢個人"):
        try:
            parts = msg.split()
            if len(parts) < 2:
                raise ValueError("需要提供查詢對象")

            target_user = parts[1]

            # 查詢指定使用者的記錄
            records = get_personal_records_by_name(target_user)
            if not records:
                msg = f"查無 {target_user} 的記錄"
            else:
                total = sum([r['amount'] for r in records])
                detail = "\n".join([f"{r['date']}: {r['amount']} 元 - {r['note']}" for r in records])
                msg = f"【{target_user} 的個人記帳查詢】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{detail}\n\n總金額：{total} 元"

        except Exception as e:
            msg = f"查詢格式錯誤！請使用：查詢個人 使用者名稱"

    elif msg == "重設個人":
        try:
            # 重設個人記錄
            if user_id not in personal_records:
                personal_records[user_id] = []
            personal_records[user_id] = []  # 清空該使用者的個人記錄

            # 清除 Google Sheet 中的記錄
            try:
                reset_personal_record_by_name(user_id)
                msg = "已清除您的個人記帳資料"
            except Exception as e:
                msg = f"清除個人記錄失敗：{e}"

        except Exception as e:
            msg = f"重設錯誤！ {str(e)}"

    else:
        msg = "請輸入指令，例如：\n- 記帳 張三 300 張三,李四 晚餐 2025-04-20\n- 查帳\n- 個人記帳 150 便當 2025-04-20\n- 查詢個人 寧\n- 重設個人\n- 重啟（清除團體資料）"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )

if __name__ == "__main__":
    app.run()
