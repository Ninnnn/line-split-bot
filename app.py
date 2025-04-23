from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

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

import os

app = Flask(__name__)

# 環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

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
    text = event.message.text.strip()
    reply = ""

    if text.startswith("記帳 "):
        try:
            parts = text[3:].split()
            user = parts[0]
            amount = int(parts[1])
            date = parts[2] if len(parts) > 2 else None
            append_personal_record(user, amount, date)
            reply = f"{user} 已記帳 {amount} 元"
        except Exception as e:
            reply = f"記帳失敗：{e}"

    elif text.startswith("查詢個人記帳 "):
        user = text[7:]
        records, total = get_personal_records_by_user(user)
        if records:
            reply = "\n".join(records) + f"\n總共：{total} 元"
        else:
            reply = "查無紀錄"

    elif text.startswith("重設個人記帳 "):
        user = text[7:]
        reset_personal_record_by_name(user)
        reply = f"{user} 的個人記帳已重設"

    elif text.startswith("分帳 "):
        try:
            group_items = text[3:].split()
            for item in group_items:
                name, amount = item.split(":")
                append_group_record(name, int(amount))
            reply = "分帳完成"
        except Exception as e:
            reply = f"分帳失敗：{e}"

    elif text.startswith("查詢團體記帳"):
        records = get_all_group_records()
        reply = "\n".join(records) if records else "查無團體紀錄"

    elif text.startswith("刪除個人記帳 "):
        name = text[8:]
        records = get_all_personal_records_by_user(name)
        if records:
            lines = [f"{idx+1}. {r}" for idx, r in enumerate(records)]
            reply = f"{name} 的個人記帳紀錄如下，請回覆『刪除 1』或『刪除 1,2』：\n" + "\n".join(lines)
        else:
            reply = "查無紀錄"

    elif text.startswith("刪除團體記帳"):
        records = get_all_group_records()
        if records:
            lines = [f"{idx+1}. {r}" for idx, r in enumerate(records)]
            reply = f"團體記帳如下，請回覆『刪除 1』或『刪除 1,2』：\n" + "\n".join(lines)
        else:
            reply = "查無紀錄"

    elif text.startswith("刪除 "):
        try:
            indexes = list(map(int, text[3:].split(",")))
            for idx in sorted(indexes, reverse=True):
                delete_personal_record_by_index(idx - 1)
            reply = "已刪除指定筆數"
        except Exception as e:
            reply = f"刪除失敗：{e}"

    elif text.startswith("查詢中獎"):
        try:
            user = None
            if len(text) > 4:
                user = text[5:]
            reply = get_invoice_lottery_results(user)
        except Exception as e:
            reply = f"中獎查詢失敗：{e}"

    elif text == "指令說明":
        reply = (
            "📌 指令列表：\n"
            "記帳 小明 100 [2025/04/20] - 個人記帳\n"
            "查詢個人記帳 小明\n"
            "重設個人記帳 小明\n"
            "分帳 小明:50 小美:100\n"
            "查詢團體記帳\n"
            "刪除個人記帳 小明\n"
            "刪除團體記帳\n"
            "刪除 1 或 刪除 1,2\n"
            "查詢中獎 或 查詢中獎 小明\n"
            "指令說明 - 顯示這個說明"
        )

    else:
        reply = "請輸入有效指令，輸入「指令說明」查看可用指令。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
