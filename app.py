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
        if msg == "指令說明":
            reply = (
                "📘 指令快速教學：\n\n"
                "📍 個人記帳\n"
                "記帳 小明 100 飯糰\n"
                "個人發票記帳 小明（搭配發票圖片）\n"
                "補發票 小明 AB12345678 2025/04/25 420\n"
                "查詢個人記帳 小明\n"
                "刪除個人記帳 小明\n"
                "刪除個人 1 或 刪除個人 1,2\n"
                "重設個人記帳 小明\n\n"
                "📍 團體記帳\n"
                "分帳 大阪 早餐 付款人:小明 小明:飯糰400 小花:鬆餅200 小強:壽司500\n"
                "查詢團體記帳 大阪\n"
                "刪除團體記帳 大阪\n"
                "刪除團體 大阪 1 或 刪除團體 大阪 1,2\n"
                "刪除餐別 大阪 2025/05/01 早餐\n"
                "重設團體記帳 大阪\n\n"
                "📍 發票與中獎\n"
                "上傳發票 + 個人發票記帳 小明\n"
                "查詢中獎 小明\n"
            )

        elif msg.startswith("補發票 "):
            parts = msg.replace("補發票 ", "").split()
            if len(parts) == 4:
                name, invoice_number, date, amount = parts
                append_invoice_record(name, invoice_number, date, amount)
                reply = f"✅ 補發票成功：{name} {invoice_number} {amount} 元"
            else:
                reply = "⚠️ 請使用格式：補發票 小明 AB12345678 2025/04/25 420"

        elif msg.startswith("查詢中獎 "):
            name = msg.replace("查詢中獎 ", "")
            reply = get_invoice_lottery_results(name)

        elif msg.startswith("個人發票記帳 "):
            name = msg.replace("個人發票記帳 ", "")
            result = extract_and_process_invoice(TEMP_IMAGE_PATH)
            if isinstance(result, str):
                reply = result
            else:
                append_personal_record(name, "發票消費", result["total"], now, result["invoice_number"])
                reply = f"✅ {name} 發票記帳成功：{result['total']} 元\n發票號碼：{result['invoice_number']}"

        elif msg.startswith("記帳 "):
            parts = msg.split()
            if len(parts) >= 4:
                name, amount, item = parts[1], int(parts[2]), parts[3]
                append_personal_record(name, item, amount, now)
                reply = f"✅ {name} 記帳成功：{item} {amount} 元（{now}）"
            else:
                reply = "⚠️ 請使用格式：記帳 小明 100 飯糰"

        elif msg.startswith("查詢個人記帳 "):
            name = msg.replace("查詢個人記帳 ", "")
            records, total = get_personal_records_by_user(name)
            reply = f"📋 {name} 記帳紀錄：\n{records}\n\n💰 總金額：{total} 元"

        elif msg.startswith("刪除個人記帳 "):
            name = msg.replace("刪除個人記帳 ", "")
            df = get_all_personal_records_by_user(name)
            if df.empty:
                reply = "⚠️ 無資料"
            else:
                reply = f"{name} 的記錄：\n"
                for idx, row in df.iterrows():
                    reply += f"{idx+1}. {row['Date']} {row['Item']} {row['Amount']}元\n"
                reply += "請回覆：刪除個人 1 或 刪除個人 1,2"

        elif msg.startswith("刪除個人 "):
            parts = msg.replace("刪除個人 ", "").split(",")
            name = ""
            success = all(delete_personal_record_by_index(name, int(i)-1) for i in parts)
            reply = "✅ 已刪除指定記錄" if success else "⚠️ 刪除失敗"

        elif msg.startswith("重設個人記帳 "):
            name = msg.replace("重設個人記帳 ", "")
            reset_personal_record_by_name(name)
            reply = f"✅ 已重設 {name} 的個人記帳"

        elif msg.startswith("分帳 "):
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
                    amount = int(''.join(filter(str.isdigit, v)))
                    if not payer:
                        payer = name
                    append_group_record(group, now, meal, item, payer, f"{name}:{amount}", amount, invoice_number)
            reply = f"✅ 分帳成功：{group} {meal}"

        elif msg.startswith("查詢團體記帳 "):
            group = msg.replace("查詢團體記帳 ", "")
            df = get_group_records_by_group(group)
            if df.empty:
                reply = f"⚠️ 查無 {group} 資料"
            else:
                payers, spenders = {}, {}
                lines = []
                for i, row in df.iterrows():
                    date, meal, item, payer, members, amt = row["Date"], row["Meal"], row["Item"], row["Payer"], row["Members"], float(row["Amount"])
                    lines.append(f"{i+1}. {date} {meal} {item} {members}（{amt}元）")
                    payers[payer] = payers.get(payer, 0) + amt
                    for m in members.split():
                        if ":" in m:
                            n, a = m.split(":")
                            spenders[n] = spenders.get(n, 0) + float(a)
                reply = "📋 " + group + " 記錄：\n" + "\n".join(lines) + "\n\n💸 結算：\n"
                for n in set(payers) | set(spenders):
                    diff = round(payers.get(n, 0) - spenders.get(n, 0), 2)
                    if diff > 0:
                        reply += f"{n} 應收 {diff} 元\n"
                    elif diff < 0:
                        reply += f"{n} 應付 {-diff} 元\n"
                    else:
                        reply += f"{n} 無需補款\n"

        elif msg.startswith("刪除團體記帳 "):
            group = msg.replace("刪除團體記帳 ", "")
            df = get_group_records_by_group(group)
            if df.empty:
                reply = f"⚠️ 無 {group} 資料"
            else:
                reply = f"📋 {group} 記錄如下：\n"
                for i, row in df.iterrows():
                    reply += f"{i+1}. {row['Date']} {row['Meal']}\n"
                reply += f"請回覆：刪除團體 {group} 1 或 刪除團體 {group} 1,2"

        elif msg.startswith("刪除團體 "):
            parts = msg.split()
            group = parts[1]
            indexes = [int(i)-1 for i in parts[2].split(",")]
            ok = all(delete_group_record_by_index(group, i) for i in indexes)
            reply = "✅ 已刪除指定紀錄" if ok else "⚠️ 刪除失敗"

        elif msg.startswith("刪除餐別 "):
            parts = msg.replace("刪除餐別 ", "").split()
            group, date, meal = parts[0], parts[1], parts[2]
            success = delete_group_record_by_meal(group, date, meal)
            reply = f"✅ 已刪除 {group} {date} {meal} 所有記錄" if success else "⚠️ 無匹配資料或刪除失敗"

        elif msg.startswith("重設團體記帳 "):
            group = msg.replace("重設團體記帳 ", "")
            reset_group_record_by_group(group)
            reply = f"✅ 已重設 {group} 所有記錄"

        else:
            reply = "請輸入有效指令，輸入『指令說明』可查詢所有功能"

    except Exception as e:
        reply = f"❌ 發生錯誤：{e}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
