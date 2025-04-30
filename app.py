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
    delete_group_record_by_index, get_invoice_records_by_user
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
    try:
        message_id = event.message.id
        message_content = line_bot_api.get_message_content(message_id)
        with open(TEMP_IMAGE_PATH, 'wb') as f:
            for chunk in message_content.iter_content():
                f.write(chunk)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🖼️ 發票圖片上傳成功，請輸入「個人發票記帳 小明」或「分帳 ...」")
        )
    except Exception as e:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"❌ 發票圖片儲存失敗：{e}")
        )

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    msg = event.message.text.strip()
    reply = ""
    now = datetime.now().strftime("%Y/%m/%d")

    try:
        # 📘 說明指令
        if msg == "指令說明":
            reply = (
                "📘 指令快速教學：\n\n"
                "📍 個人記帳\n"
                "記帳 小明 100 飯糰\n"
                "個人發票記帳 小明（搭配發票圖片）\n"
                "查詢個人記帳 小明\n"
                "刪除個人記帳 小明\n"
                "刪除個人 1 或 刪除個人 1,2\n"
                "重設個人記帳 小明\n\n"
                "📍 團體記帳\n"
                "分帳 大阪 早餐 付款人:小明 小明:飯糰400 小花:鬆餅200 小強:壽司500\n"
                "查詢團體記帳 大阪\n"
                "刪除團體記帳 大阪\n"
                "刪除團體 大阪 1\n"
                "重設團體記帳 大阪\n\n"
                "📍 發票與中獎\n"
                "上傳發票 + 個人發票記帳 小明\n"
                "查詢中獎 小明\n"
            )

        # ✅ 個人發票記帳
        elif msg.startswith("個人發票記帳 "):
            name = msg.replace("個人發票記帳 ", "")
            result = extract_and_process_invoice(TEMP_IMAGE_PATH)
            if isinstance(result, str):
                reply = result
            else:
                append_personal_record(
                    name, "發票消費", result["total"], now, result["invoice_number"]
                )
                reply = f"✅ {name} 發票記帳完成\n金額：{result['total']} 元\n發票號碼：{result['invoice_number']}"

        # ✅ 個人記帳
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
            reply = f"📋 {name} 的紀錄：\n{records}\n\n💰 總金額：{total} 元"

        elif msg.startswith("刪除個人記帳 "):
            name = msg.replace("刪除個人記帳 ", "")
            df = get_all_personal_records_by_user(name)
            if not len(df):
                reply = "⚠️ 查無紀錄"
            else:
                reply = f"{name} 的記帳紀錄：\n"
                for idx, row in enumerate(df):
                    reply += f"{idx+1}. {row['Date']} {row['Item']} {row['Amount']}元\n"
                reply += "請回覆『刪除個人 1』或『刪除個人 1,2』"

        elif msg.startswith("刪除個人 "):
            parts = msg.replace("刪除個人 ", "").split(",")
            indexes = [int(i)-1 for i in parts]
            name = ""  # 可以替換為查詢者
            success = all(delete_personal_record_by_index(name, i) for i in indexes)
            reply = "✅ 已刪除指定記錄" if success else "⚠️ 刪除失敗"

        elif msg.startswith("重設個人記帳 "):
            name = msg.replace("重設個人記帳 ", "")
            reset_personal_record_by_name(name)
            reply = f"✅ 已清空 {name} 的所有記帳"

        # ✅ 團體分帳
        elif msg.startswith("分帳 "):
            parts = msg.split()
            if len(parts) < 4:
                reply = "⚠️ 請使用格式：分帳 團體名 餐別 名:品項金額 ..."
            else:
                group = parts[1]
                meal = parts[2]
                payer = ""
                invoice_number = ""
                start_index = 3

                if parts[3].startswith("付款人:"):
                    payer = parts[3].replace("付款人:", "")
                    start_index = 4

                if os.path.exists(TEMP_IMAGE_PATH):
                    result = extract_and_process_invoice(TEMP_IMAGE_PATH)
                    if isinstance(result, dict):
                        invoice_number = result["invoice_number"]

                for p in parts[start_index:]:
                    if ":" not in p:
                        continue
                    name, info = p.split(":")
                    item_name = ''.join(filter(str.isalpha, info))
                    amount = int(''.join(filter(str.isdigit, info)))
                    if not payer:
                        payer = name
                    append_group_record(group, now, meal, item_name, payer, f"{name}:{amount}", amount, invoice_number)

                reply = f"✅ 分帳完成：{group} - {meal}"

        elif msg.startswith("查詢團體記帳 "):
            group = msg.replace("查詢團體記帳 ", "")
            df = get_group_records_by_group(group)
            if df.empty:
                reply = f"⚠️ 查無 {group} 記帳資料"
            else:
                reply = f"📋 {group} 的記帳紀錄：\n"
                payers = {}
                spenders = {}

                for idx, row in df.iterrows():
                    date = row.get('Date', '')
                    meal = row.get('Meal', '')
                    item = row.get('Item', '')
                    payer = row.get('Payer', '')
                    members = row.get('Members', '')
                    amount = float(row.get('Amount', 0))

                    reply += f"{idx+1}. {date} {meal} {item} {members}（{amount}元）\n"

                    if payer not in payers:
                        payers[payer] = 0
                    payers[payer] += amount

                    for m in members.split():
                        if ":" in m:
                            name, amt = m.split(":")
                            amt = float(amt)
                            if name not in spenders:
                                spenders[name] = 0
                            spenders[name] += amt

                balances = {}
                all_names = set(payers.keys()) | set(spenders.keys())
                for person in all_names:
                    paid = payers.get(person, 0)
                    owe = spenders.get(person, 0)
                    balances[person] = round(paid - owe, 2)

                reply += "\n💸 結算結果：\n"
                for person, balance in balances.items():
                    if balance > 0:
                        reply += f"{person} 應收 {balance} 元\n"
                    elif balance < 0:
                        reply += f"{person} 應付 {abs(balance)} 元\n"
                    else:
                        reply += f"{person} 平均無需補款\n

        elif msg.startswith("刪除團體記帳 "):
            group = msg.replace("刪除團體記帳 ", "")
            df = get_group_records_by_group(group)
            if not len(df):
                reply = f"⚠️ 無 {group} 資料"
            else:
                reply = f"📋 {group} 的記錄：\n"
                for i, row in enumerate(df):
                    reply += f"{i+1}. {row['Date']} {row['Meal']}\n"
                reply += f"請回覆：刪除團體 {group} 1 或 1,2"

        elif msg.startswith("刪除團體 "):
            parts = msg.split()
            group = parts[1]
            indexes = [int(i)-1 for i in parts[2].split(",")]
            ok = all(delete_group_record_by_index(group, i) for i in indexes)
            reply = "✅ 已刪除指定紀錄" if ok else "⚠️ 刪除失敗"

        elif msg.startswith("重設團體記帳 "):
            group = msg.replace("重設團體記帳 ", "")
            reset_group_record_by_group(group)
            reply = f"✅ 已重設 {group} 的所有紀錄"

        elif msg.startswith("查詢中獎 "):
            name = msg.replace("查詢中獎 ", "")
            df = get_invoice_records_by_user(name)
            if not len(df):
                reply = f"⚠️ {name} 沒有發票紀錄"
            else:
                reply = f"📬 {name} 發票紀錄：\n"
                for row in df:
                    reply += f"{row['Date']} - {row['Invoice']} - {row['Amount']}元\n"

        else:
            reply = "請輸入有效指令，或輸入「指令說明」查看功能。"

    except Exception as e:
        reply = f"❌ 發生錯誤：{e}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
