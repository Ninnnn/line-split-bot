from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage

from sheet_utils import (
    append_personal_record,
    append_group_record,
    get_personal_records_by_user,
    reset_personal_record_by_name,
    get_all_personal_records_by_user,
    get_all_group_records,
    delete_personal_record_by_index,
    delete_group_record_by_index,
    get_invoice_lottery_results,
)

from vision_utils import ocr_invoice_image

import os
from datetime import datetime

app = Flask(__name__)

# 環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ===== 狀態記錄（簡單記憶） =====
user_context = {}

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
def handle_text_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id
    reply = ""

    if text.startswith("記帳 "):
        try:
            parts = text[3:].split()
            name = parts[0]
            amount = int(parts[1])
            date = parts[2] if len(parts) > 2 else datetime.now().strftime("%Y/%m/%d")
            append_personal_record(name, "個人消費", amount, date)
            reply = f"✅ {name} 已記帳 {amount} 元"
        except Exception as e:
            reply = f"❌ 記帳失敗：{e}"

    elif text.startswith("查詢個人記帳 "):
        name = text[7:]
        user_context[user_id] = {"mode": "delete_personal", "name": name}
        records = get_personal_records_by_user(name)
        if records:
            total = sum(int(r["金額"]) for r in records)
            lines = [f"{idx+1}. {r['日期']} {r['品項']} - {r['金額']}元" for idx, r in enumerate(records)]
            reply = "\n".join(lines) + f"\n🔸總計：{total} 元"
        else:
            reply = "查無個人記帳紀錄"

    elif text.startswith("重設個人記帳 "):
        name = text[7:]
        reset_personal_record_by_name(name)
        reply = f"✅ 已重設 {name} 的個人記帳"

    elif text.startswith("分帳 "):
        try:
            parts = text[3:].split()
            today = datetime.now().strftime("%Y/%m/%d")
            for part in parts:
                name, amount = part.split(":")
                append_group_record(name, "", "群組分帳", int(amount), today)
            reply = "✅ 分帳記錄完成！"
        except Exception as e:
            reply = f"❌ 分帳失敗：{e}"

    elif text == "查詢團體記帳":
        records = get_all_group_records()
        if records:
            lines = [f"{r['日期']} {r['付款人']} - {r['金額']}元" for r in records]
            reply = "\n".join(lines)
        else:
            reply = "查無團體記帳紀錄"

    elif text.startswith("刪除個人 "):
        try:
            indexes = list(map(int, text[5:].split(",")))
            name = user_context.get(user_id, {}).get("name")
            if not name:
                reply = "❗ 請先輸入『查詢個人記帳 姓名』來選擇刪除紀錄。"
            else:
                for idx in sorted(indexes, reverse=True):
                    delete_personal_record_by_index(name, idx - 1)
                reply = "✅ 已刪除個人記帳指定筆數"
        except Exception as e:
            reply = f"❌ 刪除個人記帳失敗：{e}"

    elif text.startswith("刪除團體 "):
        try:
            indexes = list(map(int, text[5:].split(",")))
            for idx in sorted(indexes, reverse=True):
                delete_group_record_by_index(idx - 1)
            reply = "✅ 已刪除團體記帳指定筆數"
        except Exception as e:
            reply = f"❌ 刪除團體記帳失敗：{e}"

    elif text.startswith("查詢中獎"):
        try:
            name = text[5:] if len(text) > 5 else None
            winning_numbers = {
                "特別獎": "12345678",
                "特獎": "87654321",
                "頭獎": ["11112222", "33334444", "55556666"],
            }
            if name:
                records = get_personal_records_by_user(name)
            else:
                records = get_all_personal_records_by_user()
            results = get_invoice_lottery_results(records, winning_numbers)
            reply = "\n".join(results) if results else "😢 很遺憾，這期沒有中獎喔～"
        except Exception as e:
            reply = f"❌ 查詢中獎失敗：{e}"

    elif text == "指令說明":
        reply = (
            "📋 LINE 機器人指令說明：\n\n"
            "【個人記帳】\n"
            "記帳 小明 100 2025/04/20\n"
            "查詢個人記帳 小明\n"
            "重設個人記帳 小明\n"
            "刪除個人 1 或 刪除個人 1,2\n\n"
            "【群組分帳】\n"
            "分帳 小明:50 小美:100\n"
            "查詢團體記帳\n"
            "刪除團體 1 或 刪除團體 1,2\n\n"
            "【發票中獎】\n"
            "查詢中獎 或 查詢中獎 小明\n\n"
            "【發票拍照自動記帳】\n"
            "上傳發票圖片後輸入：個人記帳 小明"
        )

    else:
        reply = "❓ 請輸入有效指令，輸入「指令說明」查看可用指令～"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    """處理發票圖片上傳，OCR辨識"""
    try:
        message_id = event.message.id
        image_content = line_bot_api.get_message_content(message_id).content
        temp_path = "/tmp/invoice.jpg"
        with open(temp_path, "wb") as f:
            f.write(image_content)

        invoice_data = extract_and_process_invoice(temp_path)
        if isinstance(invoice_data, str):
            reply = invoice_data  # 錯誤訊息
        else:
            # 成功擷取，提示使用者記帳
            reply = f"📄 發票擷取成功！\n發票號碼：{invoice_data['invoice_number']}\n總金額：{invoice_data['total']}元\n請輸入：個人記帳 小明"

    except Exception as e:
        reply = f"❌ 圖片處理失敗：{e}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
