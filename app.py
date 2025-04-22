import os
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage
from bot import send_message
from sheet_utils import append_record, get_personal_records
from invoice_utils import extract_invoice_data
from invoice_record import log_invoice_to_personal_record
from delete_record import delete_personal_record
from lottery_check import check_lottery

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    reply_token = event.reply_token

    if text == "指令說明":
        help_message = '''
        1. 查詢個人記帳 [姓名] - 顯示個人記帳紀錄
        2. 查詢團體記帳 - 顯示團體記帳紀錄
        3. 發票記帳 [金額] [品項] - 記錄發票
        4. 刪除記錄 [姓名] - 刪除指定記錄
        5. 查詢中獎 [發票號碼] - 查詢發票是否中獎
        '''
        send_message(reply_token, help_message)
    elif text.startswith("發票記帳"):
        # Extract invoice data and log it
        items, amount = extract_invoice_data('path_to_image')
        log_invoice_to_personal_record("小美", items, amount)
        send_message(reply_token, f"發票記錄成功：{items}, 金額：{amount}")
    elif text.startswith("查詢中獎"):
        # Check lottery
        invoice_number = text.split()[1]
        result = check_lottery(invoice_number)
        send_message(reply_token, result)
    elif text.startswith("刪除記錄"):
        # Handle record deletion
        delete_personal_record("小美", 1)  # Example to delete record 1 for 小美
        send_message(reply_token, "已刪除指定記錄")
