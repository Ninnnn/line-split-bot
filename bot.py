import os
import re
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, MessageEvent, TextMessage
from linebot.exceptions import LineBotApiError

# Initialize LINE Bot API
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

def send_message(reply_token, message):
    try:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=message))
    except LineBotApiError as e:
        print(f"Error sending message: {e}")

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
    elif text.startswith("查詢個人記帳"):
        # Handle individual query logic
        pass
    elif text.startswith("查詢團體記帳"):
        # Handle group query logic
        pass
    elif text.startswith("發票記帳"):
        # Handle receipt logging logic
        pass
    elif text.startswith("刪除記錄"):
        # Handle deletion logic
        pass
    elif text.startswith("查詢中獎"):
        # Handle lottery checking logic
        pass
