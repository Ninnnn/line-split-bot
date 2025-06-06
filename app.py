from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import re
from sheet_utils import (
    create_group, query_group_records,
    top_up_group_fund, query_group_fund_history, delete_group_meal, reset_group_records,
    append_group_record, get_group_members
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

def split_group_expense(group_name, meal_name, total_amount, adjustments_raw):
    adjustments = {}
    for item in adjustments_raw:
        match = re.match(r"(\S+)([+-]\d+)", item)
        if match:
            name, offset = match.groups()
            adjustments[name] = adjustments.get(name, 0) + int(offset)
        else:
            raise ValueError(f"格式錯誤：{item}，請使用人名+/-金額，例如 寧+300")

    members = get_group_members(group_name)
    n = len(members)
    if n == 0:
        raise ValueError("❗找不到團體成員")

    total_adjustment = sum(adjustments.get(name, 0) for name in members)
    adjusted_total = total_amount - total_adjustment
    share = round(adjusted_total / n)

    contributions = {}
    for m in members:
        offset = adjustments.get(m, 0)
        contributions[m] = share + offset

    append_group_record(group_name, meal_name, total_amount, contributions)
    detail = "\n".join(f"{m}：{contributions[m]:.0f}" for m in members)
    return f"✅ {group_name} 已分帳 {meal_name}：\n{detail}"

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
            if len(args) < 3:
                result = "❗請提供團名與至少一位成員，例如：建立團體記帳 大阪 寧 誌"
            else:
                group_name = args[1]
                members = args[2:]
                result = create_group(group_name, members)

        elif text.startswith("分帳"):
            pattern = r"分帳 (\S+) (\S+) (\d+)(.*)"
            match = re.match(pattern, text)
            if match:
                group_name = match.group(1)
                meal_name = match.group(2)
                total_amount = int(match.group(3))
                raw_adjustments = match.group(4).strip()
                adjustments = raw_adjustments.split() if raw_adjustments else []
                result = split_group_expense(group_name, meal_name, total_amount, adjustments)
            else:
                result = "❗格式錯誤，請參考：分帳 [團名] [餐別] [總金額] [人名+/-調整金額...]"

        elif text.startswith("查詢團體記帳"):
            parts = text.split()
            if len(parts) < 2:
                result = "❗請提供團名，例如：查詢團體記帳 大阪"
            else:
                group_name = parts[1]
                result = query_group_records(group_name)

        elif text.startswith("儲值公費"):
            parts = text.split()
            if len(parts) < 2:
                result = "❗請提供團名，例如：儲值公費 大阪 3000"
            else:
                group_name = parts[1]
                if len(parts) == 3 and parts[2].isdigit():
                    amount = int(parts[2])
                    result = top_up_group_fund(group_name, amount)
                elif len(parts) > 2:
                    contributions = parts[2:]
                    result = top_up_group_fund(group_name, contributions=contributions)
                else:
                    result = "❗請提供總金額或個人儲值明細，例如：儲值公費 大阪 3000 或 儲值公費 大阪 小明+500"

        elif text.startswith("查詢公費紀錄"):
            parts = text.split()
            if len(parts) < 2:
                result = "❗請提供團名，例如：查詢公費紀錄 大阪"
            else:
                group_name = parts[1]
                result = query_group_fund_history(group_name)

        elif text.startswith("刪除餐別"):
            parts = text.split()
            if len(parts) != 4:
                result = "❗請提供格式：刪除餐別 [團名] [日期] [餐別]\n例：刪除餐別 大阪 2024/06/03 早餐"
            else:
                _, group_name, date_str, meal_name = parts
                result = delete_group_meal(group_name, date_str, meal_name)

        elif text.startswith("重設團體記帳"):
            parts = text.split()
            if len(parts) < 2:
                result = "❗請提供團名，例如：重設團體記帳 大阪"
            else:
                group_name = parts[1]
                result = reset_group_records(group_name)

        else:
            result = f"❓ 無法識別的指令，請參考以下指令：\n\n{HELP_MESSAGE}"

    except Exception as e:
        result = f"⚠️ 發生錯誤：{str(e)}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))

if __name__ == "__main__":
    app.run(debug=True)
