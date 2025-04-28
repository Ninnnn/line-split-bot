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
from datetime import datetime

app = Flask(__name__)

# 環境變數
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ========== LINE Webhook 路由 ==========
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# ========== 處理收到的文字訊息 ==========
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    reply = ""

    # === 個人記帳 ===
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
        records = get_personal_records_by_user(name)
        if records:
            total = sum(int(r["金額"]) for r in records)
            lines = [f"{r['日期']} {r['品項']} - {r['金額']}元" for r in records]
            reply = "\n".join(lines) + f"\n🔸總計：{total} 元"
        else:
            reply = "查無個人記帳紀錄"

    elif text.startswith("重設個人記帳 "):
        name = text[7:]
        reset_personal_record_by_name(name)
        reply = f"✅ 已重設 {name} 的個人記帳"

    # === 群組分帳 ===
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

    # === 刪除記錄 ===
    elif text.startswith("刪除個人記帳 "):
        name = text[8:]
        records = get_personal_records_by_user(name)
        if records:
            lines = [f"{idx+1}. {r['日期']} {r['品項']} - {r['金額']}元" for idx, r in enumerate(records)]
            reply = f"{name} 的個人記帳紀錄：\n請回覆『刪除個人 1』或『刪除個人 1,2』：\n" + "\n".join(lines)
        else:
            reply = "查無個人記帳紀錄"

    elif text.startswith("刪除團體記帳"):
        records = get_all_group_records()
        if records:
            lines = [f"{idx+1}. {r['日期']} {r['付款人']} - {r['金額']}元" for idx, r in enumerate(records)]
            reply = "團體記帳紀錄：\n請回覆『刪除團體 1』或『刪除團體 1,2』：\n" + "\n".join(lines)
        else:
            reply = "查無團體記帳紀錄"

    elif text.startswith("刪除個人 "):
        try:
            indexes = list(map(int, text[5:].split(",")))
            name = ""  # TODO：需要從上下文記錄 name
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

    # === 查詢發票中獎 ===
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
            reply = "\n".join(results) if results else "😢 很遺憾，這期沒中獎～"
        except Exception as e:
            reply = f"❌ 查詢中獎失敗：{e}"

    # === 指令說明 ===
    elif text == "指令說明":
        reply = (
            "📌 指令列表：\n"
            "記帳 小明 100 [2025/04/20]\n"
            "查詢個人記帳 小明\n"
            "重設個人記帳 小明\n"
            "分帳 小明:50 小美:100\n"
            "查詢團體記帳\n"
            "刪除個人記帳 小明\n"
            "刪除團體記帳\n"
            "刪除個人 1 或 刪除個人 1,2\n"
            "刪除團體 1 或 刪除團體 1,2\n"
            "查詢中獎 或 查詢中獎 小明\n"
            "指令說明 - 顯示這個說明"
        )

    else:
        reply = "❓ 請輸入有效指令，輸入「指令說明」查看可用指令喔～"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
