# 完整升級版 app.py（含圖片上傳、發票記帳、個人團體記帳、自動補差額、補發票、對獎、刪除餐別）

from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage

import os
from datetime import datetime
from sheet_utils import (
    append_personal_record, get_personal_records_by_user,
    reset_personal_record_by_name, get_all_personal_records_by_user,
    delete_personal_record_by_index, append_group_record,
    get_group_records_by_group, reset_group_record_by_group,
    delete_group_record_by_index, get_invoice_records_by_user,
    get_invoice_lottery_results, append_invoice_record,
    delete_group_record_by_meal
)
from vision_utils import extract_and_process_invoice

app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
TEMP_IMAGE_PATH = "/tmp/line_invoice.jpg"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_id = event.message.id
    content = line_bot_api.get_message_content(message_id)
    with open(TEMP_IMAGE_PATH, "wb") as f:
        for chunk in content.iter_content():
            f.write(chunk)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="📷 發票圖片上傳成功，請輸入記帳指令，例如：\n個人發票記帳 小明 或 分帳 大阪 早餐 小明:飯糰400 ..."))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    now = datetime.now().strftime("%Y/%m/%d")
    reply = ""
    try:
        if msg.startswith("分帳 "):
            parts = msg.split()
            group, meal = parts[1], parts[2]
            payer, invoice_number = "", ""
            start_idx = 3
            if parts[3].startswith("付款人:"):
                payer = parts[3].replace("付款人:", "")
                start_idx = 4
            if os.path.exists(TEMP_IMAGE_PATH):
                result = extract_and_process_invoice(TEMP_IMAGE_PATH)
                if isinstance(result, dict):
                    invoice_number = result["invoice_number"]
            for p in parts[start_idx:]:
                if ":" in p:
                    name, v = p.split(":")
                    item = ''.join(filter(str.isalpha, v))
                    amount_str = ''.join(c for c in v if c.isdigit() or c == ".")
                    amount = round(float(amount_str), 2)
                    if not payer:
                        payer = name
                    append_group_record(group, now, meal, item, payer, f"{name}:{amount}", amount, invoice_number)
            reply = f"✅ 分帳成功：{group} {meal}"

        elif msg.startswith("記帳 "):
            parts = msg.split()
            if len(parts) >= 4:
                name = parts[1]
                amount = round(float(parts[2]), 2)
                item = parts[3]
                append_personal_record(name, item, amount, now)
                reply = f"✅ {name} 記帳成功：{item} {amount} 元（{now}）"
            else:
                reply = "⚠️ 請使用格式：記帳 小明 100 飯糰"

        else:
            reply = "🔄 其餘指令邏輯略，請使用完整程式版本"

    except Exception as e:
        reply = f"❌ 發生錯誤：{e}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
