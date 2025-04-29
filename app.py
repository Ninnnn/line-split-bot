from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os
from datetime import datetime
from sheet_utils import (
    append_personal_record, get_personal_records_by_user,
    reset_personal_record_by_name, get_all_personal_records_by_user,
    delete_personal_record_by_index, append_group_record,
    get_group_records_by_group, reset_group_record_by_group,
    delete_group_record_by_index, get_invoice_records_by_user
)
from vision_utils import extract_and_process_invoice

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

TEMP_IMAGE_PATH = "/tmp/line_invoice.jpg"
LAST_IMAGE_USER = {}

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
    user_id = event.source.user_id
    msg = event.message.text.strip()
    reply = ""
    now = datetime.now().strftime("%Y/%m/%d")

    try:
        # 📌 個人記帳
        if msg.startswith("記帳 "):
            parts = msg.split()
            if len(parts) >= 4:
                name = parts[1]
                amount = int(parts[2])
                item = parts[3]
                append_personal_record(name, item, amount, now)
                reply = f"✅ {name} 記帳成功：{item} {amount} 元（{now}）"
            else:
                reply = "⚠️ 請使用格式：記帳 小明 100 飯糰"

        elif msg.startswith("查詢個人記帳 "):
            name = msg.replace("查詢個人記帳 ", "")
            records, total = get_personal_records_by_user(name)
            reply = f"📋 {name} 記帳紀錄：\n{records}\n\n💰 總金額：{total} 元"

        elif msg.startswith("重設個人記帳 "):
            name = msg.replace("重設個人記帳 ", "")
            reset_personal_record_by_name(name)
            reply = f"✅ 已清空 {name} 的記帳紀錄"

        elif msg.startswith("刪除個人記帳 "):
            name = msg.replace("刪除個人記帳 ", "")
            df = get_all_personal_records_by_user(name)
            if df.empty:
                reply = "⚠️ 無資料"
            else:
                reply = f"{name} 的紀錄：\n"
                for idx, row in df.iterrows():
                    reply += f"{idx+1}. {row['Date']} {row['Item']} {row['Amount']}元\n"
                reply += "請回覆：刪除個人 1 或 刪除個人 1,2"

        elif msg.startswith("刪除個人 "):
            parts = msg.replace("刪除個人 ", "").split(",")
            name = ""  # 建議實作：使用 session 或快取記憶最近查詢的人
            success = all(delete_personal_record_by_index(name, int(i)-1) for i in parts)
            reply = "✅ 已刪除指定記錄" if success else "⚠️ 刪除失敗"

        # 📌 個人發票記帳
        elif msg.startswith("個人發票記帳 "):
            name = msg.replace("個人發票記帳 ", "")
            result = extract_and_process_invoice(TEMP_IMAGE_PATH)
            if isinstance(result, str):
                reply = result
            else:
                append_personal_record(
                    name, "發票消費", result["total"], now, result["invoice_number"]
                )
                reply = f"✅ {name} 發票記帳完成\n金額：{result['total']} 元\n發票號：{result['invoice_number']}"

        # 📌 團體分帳
        elif msg.startswith("分帳 "):
            parts = msg.split()
            if len(parts) < 4:
                reply = "⚠️ 請使用：分帳 團體名 餐別 名:項目金額 ..."
            else:
                group = parts[1]
                meal = parts[2]
                invoice_number = ""
                payer = ""
                if os.path.exists(TEMP_IMAGE_PATH):
                    result = extract_and_process_invoice(TEMP_IMAGE_PATH)
                    if isinstance(result, dict):
                        invoice_number = result["invoice_number"]

                for p in parts[3:]:
                    if ":" not in p:
                        continue
                    name, info = p.split(":")
                    item_name = ''.join(filter(str.isalpha, info))
                    amount = int(''.join(filter(str.isdigit, info)))
                    if not payer:
                        payer = name
                    append_group_record(group, now, meal, item_name, payer, f"{name}:{amount}", amount, invoice_number)

                reply = f"✅ 分帳完成：{group} - {meal}"

        elif msg.startswith("查詢團體記帳 "):
            group = msg.replace("查詢團體記帳 ", "")
            df = get_group_records_by_group(group)
            if df.empty:
                reply = f"⚠️ 查無 {group} 記帳資料"
            else:
                reply = f"📋 {group} 的記帳紀錄：\n"
                for idx, row in df.iterrows():
                    reply += f"{idx+1}. {row['Date']} {row['Meal']} {row['Item']} {row['Members']}（{row['Amount']}元）\n"

        elif msg.startswith("重設團體記帳 "):
            group = msg.replace("重設團體記帳 ", "")
            reset_group_record_by_group(group)
            reply = f"✅ 已清空 {group} 的記帳紀錄"

        elif msg.startswith("刪除團體記帳 "):
            group = msg.replace("刪除團體記帳 ", "")
            df = get_group_records_by_group(group)
            if df.empty:
                reply = f"⚠️ 無 {group} 記帳資料"
            else:
                reply = f"📋 {group} 的紀錄：\n"
                for idx, row in df.iterrows():
                    reply += f"{idx+1}. {row['Date']} {row['Meal']}\n"
                reply += "\n請回覆：刪除團體 {group} 1 或 刪除團體 {group} 1,2"

        elif msg.startswith("刪除團體 "):
            parts = msg.split()
            group = parts[1]
            indexes = [int(i)-1 for i in parts[2].split(",")]
            success = all(delete_group_record_by_index(group, i) for i in indexes)
            reply = "✅ 已刪除" if success else "⚠️ 刪除失敗"

        elif msg.startswith("查詢中獎 "):
            name = msg.replace("查詢中獎 ", "")
            df = get_invoice_records_by_user(name)
            if df.empty:
                reply = f"⚠️ {name} 沒有發票紀錄"
            else:
                reply = f"📬 {name} 發票記錄：\n"
                for _, row in df.iterrows():
                    reply += f"{row['Date']} - 發票號碼：{row['Invoice']} - {row['Amount']}元\n"

        elif msg == "指令說明":
            reply = (
                "📘 指令快速教學：\n\n"
                "📍 個人記帳\n"
                "記帳 小明 100 飯糰\n"
                "個人發票記帳 小明（搭配發票圖片）\n"
                "查詢個人記帳 小明\n"
                "刪除個人記帳 小明\n"
                "刪除個人 1 或 刪除個人 1,2\n"
                "重設個人記帳 小明\n\n"
                "📍 團體記帳\n"
                "分帳 大阪 早餐 小明:飯糰400 小花:鬆餅200 小強:牛肉飯500\n"
                "查詢團體記帳 大阪\n"
                "刪除團體記帳 大阪\n"
                "刪除團體 大阪 1\n"
                "重設團體記帳 大阪\n\n"
                "📍 發票與中獎\n"
                "上傳發票 + 個人發票記帳 小明\n"
                "查詢中獎 小明\n"
            )

        else:
            reply = "請輸入有效指令，或輸入「指令說明」查看完整教學"

    except Exception as e:
        reply = f"❌ 發生錯誤：{e}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
