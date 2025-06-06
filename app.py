from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import re
from sheet_utils import (
    create_group, split_group_expense, query_group_records, 
    top_up_group_fund, query_group_fund_history, delete_group_meal, reset_group_records
)

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

HELP_MESSAGE = """
📌 團體記帳指令總覽

1. 🏗️ 建立團體記帳
建立團體記帳 [團名] [成員1] [成員2] ...
例：建立團體記帳 大阪 寧 誌 小白

2. 🍱 分帳
分帳 [團名] [餐別] [總金額] [人名+/-調整金額...]
例：分帳 大阪 早餐 2300 寧+300

3. 📊 查詢團體記帳
查詢團體記帳 [團名]

4. 💰 儲值公費
儲值公費 [團名] [總金額]
儲值公費 [團名] 小明+300 小花+200
例：儲值公費 大阪 3000
例：儲值公費 大阪 小明+500 小花+200

5. 📜 查詢公費紀錄
查詢公費紀錄 [團名]

6. ❌ 刪除餐別
刪除餐別 [團名] [日期] [餐別]
例：刪除餐別 大阪 2024/06/03 早餐

7. 🔄 重設團體記帳
重設團體記帳 [團名]
"""

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
    text = event.message.text.strip()

    if text == "/help":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=HELP_MESSAGE))
        return

    try:
        if text.startswith("建立團體記帳"):
            args = text.split()
            group_name = args[1]
            members = args[2:]
            result = create_group(group_name, members)

        elif text.startswith("分帳"):
            pattern = r"分帳 (\\S+) (\\S+) (\\d+)(.*)"
            match = re.match(pattern, text)
            if match:
                group_name = match.group(1)
                meal_name = match.group(2)
                total_amount = int(match.group(3))
                adjustments = match.group(4).strip().split()
                result = split_group_expense(group_name, meal_name, total_amount, adjustments)
            else:
                result = "❗格式錯誤，請參考：分帳 [團名] [餐別] [總金額] [人名+/-調整金額...]"

        elif text.startswith("查詢團體記帳"):
            group_name = text.split()[1]
            result = query_group_records(group_name)

        elif text.startswith("儲值公費"):
            parts = text.split()
            group_name = parts[1]
            if len(parts) == 3 and parts[2].isdigit():
                amount = int(parts[2])
                result = top_up_group_fund(group_name, amount)
            else:
                contributions = parts[2:]
                result = top_up_group_fund(group_name, contributions=contributions)

        elif text.startswith("查詢公費紀錄"):
            group_name = text.split()[1]
            result = query_group_fund_history(group_name)

        elif text.startswith("刪除餐別"):
            _, group_name, date_str, meal_name = text.split()
            result = delete_group_meal(group_name, date_str, meal_name)

        elif text.startswith("重設團體記帳"):
            group_name = text.split()[1]
            result = reset_group_records(group_name)

        else:
            result = f"❓ 無法識別的指令，請參考以下指令：\n\n{HELP_MESSAGE}"

    except Exception as e:
        result = f"⚠️ 發生錯誤：{str(e)}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

if __name__ == "__main__":
    app.run(debug=True)
