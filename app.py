from linebot import LineBotApi, WebhookHandler
from linebot.models import *
from flask import abort
import re
from sheet_utils import *
from vision_utils import extract_invoice_data_from_image
from utils import parse_amount_mapping, format_group_records, format_personal_records, get_current_month_range, format_invoice_items
import datetime

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 暫存用戶上傳的圖片與 user_id
user_image_temp = {}

def send_help_message(reply_token):
    message = (
        "📌 拆帳機器人指令說明：\n"
        "\n【📥 記帳類】\n"
        "個人記帳 金額 項目/名稱\n"
        "團體記帳 均分 金額 項目\n"
        "團體記帳 A:金額1, B:金額2 項目\n"
        "個人發票記帳 名稱（先上傳發票照片）\n"
        "發票記帳 A:金額1, B:金額2（先上傳發票照片）\n"
        "\n【📤 查詢類】\n"
        "查詢個人 名稱\n"
        "查詢團體\n"
        "查詢中獎（或加上月份如 查詢中獎 2025/03-04）\n"
        "\n【🧹 刪除類】\n"
        "刪除個人記帳 名稱\n"
        "刪除團體記帳\n"
        "刪除 1 或 刪除 1,2（搭配查詢後使用）\n"
        "\n【📁 其他】\n"
        "匯出個人 名稱\n"
    )
    line_bot_api.reply_message(reply_token, TextSendMessage(text=message))

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()
    reply_token = event.reply_token

    # 指令說明
    if text in ["說明", "幫助", "指令"]:
        send_help_message(reply_token)
        return

    # 查詢功能
    if text.startswith("查詢個人"):
        from query_handlers import handle_query_personal
        handle_query_personal(text, reply_token)
        return

    if text.startswith("查詢團體"):
        from query_handlers import handle_query_group
        handle_query_group(reply_token)
        return

    if text.startswith("查詢中獎"):
        from query_handlers import handle_query_prize
        handle_query_prize(text, reply_token)
        return

    # 匯出功能
    if text.startswith("匯出個人"):
        from export_handlers import handle_export_personal
        handle_export_personal(text, reply_token)
        return

    # 刪除流程
    if text.startswith("刪除個人記帳") or text.startswith("刪除團體記帳"):
        from delete_handlers import handle_list_deletable
        handle_list_deletable(text, reply_token, user_id)
        return

    if text.startswith("刪除"):
        from delete_handlers import handle_delete_by_index
        handle_delete_by_index(text, reply_token, user_id)
        return

    # 發票流程
    if text.startswith("個人發票記帳"):
        from invoice_handlers import handle_invoice_personal
        handle_invoice_personal(text, user_id, reply_token)
        return

    if text.startswith("發票記帳"):
        from invoice_handlers import handle_invoice_group
        handle_invoice_group(text, user_id, reply_token)
        return

    # 一般記帳流程
    if text.startswith("個人記帳"):
        from record_handlers import handle_personal_record
        handle_personal_record(text, reply_token)
        return

    if text.startswith("團體記帳"):
        from record_handlers import handle_group_record
        handle_group_record(text, reply_token)
        return

    # 預設回應
    line_bot_api.reply_message(reply_token, TextSendMessage(text="❓ 請輸入「說明」查看可用指令。"))

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    message_id = event.message.id

    # 儲存圖片到 /tmp
    message_content = line_bot_api.get_message_content(message_id)
    image_path = f"/tmp/{user_id}_invoice.jpg"
    with open(image_path, 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    # 暫存圖片路徑供接下來的發票記帳指令使用
    user_image_temp[user_id] = image_path
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🧾 發票圖片已上傳，請輸入記帳指令。"))
