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

# 圖片暫存目錄
TEMP_IMAGE_PATH = "/tmp/line_temp.jpg"
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
        # 📌 指令：個人記帳
        if msg.startswith("記帳 "):
            parts = msg.split()
            if len(parts) >= 3:
                name = parts[1]
                amount = int(parts[2])
                item = parts[3] if len(parts) >= 4 else "未命名項目"
                append_personal_record(name, item, amount, now)
                reply = f"✅ 已幫 {name} 記帳 {item} {amount} 元（{now}）"
            else:
                reply = "⚠️ 請使用格式：記帳 小明 100 飯糰"

        # 📌 查詢個人記帳
        elif msg.startswith("查詢個人記帳 "):
            name = msg.replace("查詢個人記帳 ", "")
            records, total = get_personal_records_by_user(name)
            reply = f"📋 {name} 的記帳紀錄：\n{records}\n\n💰 總共：{total} 元"

        # 📌 重設個人記帳
        elif msg.startswith("重設個人記帳 "):
            name = msg.replace("重設個人記帳 ", "")
            reset_personal_record_by_name(name)
            reply = f"✅ 已清空 {name} 的所有記帳紀錄"

        # 📌 刪除個人記帳
        elif msg.startswith("刪除個人記帳 "):
            name = msg.replace("刪除個人記帳 ", "")
            df = get_all_personal_records_by_user(name)
            if df.empty:
                reply = f"{name} 沒有任何記帳紀錄"
            else:
                reply = f"{name} 的紀錄：\n"
                for idx, row in df.iterrows():
                    reply += f"{idx+1}. {row['Date']} - {row['Item']} {row['Amount']}元\n"
                reply += "\n請輸入：刪除個人 1 或 刪除個人 1,2"

        elif msg.startswith("刪除個人 "):
            parts = msg.replace("刪除個人 ", "").split()
            indexes = [int(i)-1 for i in parts[0].split(",")]
            name = ""  # 你可將最近操作的人名存在記憶中以辨識
            success = [delete_personal_record_by_index(name, i) for i in indexes]
            reply = "✅ 已刪除指定記錄" if all(success) else "⚠️ 有些索引刪除失敗"

        # 📌 分帳 群組 餐別 名:品項金額 ...
        elif msg.startswith("分帳 "):
            parts = msg.split()
            group = parts[1]
            meal = parts[2]
            invoice_number = ""
            payer = ""

            if user_id in LAST_IMAGE_USER and LAST_IMAGE_USER[user_id]:
                result = extract_and_process_invoice(TEMP_IMAGE_PATH)
                if isinstance(result, str):
                    reply = result
                else:
                    invoice_number = result["invoice_number"]
                    LAST_IMAGE_USER[user_id] = None

            for segment in parts[3:]:
                if ":" not in segment:
                    continue
                name, item_info = segment.split(":")
                item_name = ''.join(filter(str.isalpha, item_info))
                item_amount = ''.join(filter(str.isdigit, item_info))
                item_amount = int(item_amount) if item_amount else 0

                if payer == "":
                    payer = name
                append_group_record(group, now, meal, item_name, payer, f"{name}:{item_amount}", item_amount, invoice_number)
            reply = f"✅ 分帳完成（{group} - {meal}）"

        # 📌 查詢團體記帳
        elif msg.startswith("查詢團體記帳 "):
            group = msg.replace("查詢團體記帳 ", "")
            df = get_group_records_by_group(group)
            if df.empty:
                reply = f"⚠️ 查無 {group} 的記帳紀錄"
            else:
                reply = f"📋 {group} 記帳紀錄：\n"
                for idx, row in df.iterrows():
                    reply += f"{idx+1}. {row['Date']} {row['Meal']}：{row['Item']} {row['Members']}（{row['Amount']}元）\n"

        # 📌 重設團體記帳
        elif msg.startswith("重設團體記帳 "):
            group = msg.replace("重設團體記帳 ", "")
            reset_group_record_by_group(group)
            reply = f"✅ 已清空 {group} 的所有記帳紀錄"

        # 📌 刪除團體記帳
        elif msg.startswith("刪除團體記帳 "):
            group = msg.replace("刪除團體記帳 ", "")
            df = get_group_records_by_group(group)
            if df.empty:
                reply = f"⚠️ 查無 {group} 紀錄"
            else:
                reply = f"請輸入刪除編號，例如：刪除團體 {group} 1\n\n"
                for idx, row in df.iterrows():
                    reply += f"{idx+1}. {row['Date']} {row['Meal']}\n"

        elif msg.startswith("刪除團體 "):
            parts = msg.split()
            group = parts[1]
            indexes = [int(i)-1 for i in parts[2].split(",")]
            success = [delete_group_record_by_index(group, i) for i in indexes]
            reply = f"✅ 已刪除 {group} 指定記錄" if all(success) else "⚠️ 有些刪除失敗"

        # 📌 查詢中獎
        elif msg.startswith("查詢中獎 "):
            name = msg.replace("查詢中獎 ", "")
            df = get_invoice_records_by_user(name)
            if df.empty:
                reply = f"❌ 沒有找到 {name} 的發票記錄"
            else:
                reply = f"📬 {name} 發票紀錄：\n"
                for _, row in df.iterrows():
                    reply += f"{row['Date']} {row['Invoice']} - {row['Amount']}元\n"

        # 📌 查詢指令教學
        elif msg == "指令說明":
            reply = (
                "📘 指令快速教學：\n\n"
                "📍 個人記帳\n"
                "記帳 小明 100 飯糰\n"
                "查詢個人記帳 小明\n"
                "刪除個人記帳 小明\n"
                "刪除個人 1 或 刪除個人 1,2\n"
                "重設個人記帳 小明\n\n"
                "📍 團體記帳\n"
                "分帳 大阪 早餐 小明:飯糰400 小花:鬆餅200 小強:牛肉飯500\n"
                "查詢團體記帳 大阪\n"
                "刪除團體記帳 大阪\n"
                "刪除團體 大阪 1 或 刪除團體 大阪 1,2\n"
                "重設團體記帳 大阪\n\n"
                "📍 發票相關\n"
                "上傳發票（圖片）+ 輸入分帳指令\n"
                "查詢中獎 小明\n"
            )

        else:
            reply = "❓ 無效指令，請輸入「指令說明」查看可用功能"

    except Exception as e:
        reply = f"❌ 發生錯誤：{str(e)}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
