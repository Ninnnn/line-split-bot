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
    delete_group_record_by_meal, create_group, add_group_fund,
    get_group_fund_balance, get_group_members, get_group_fund_history,
    get_group_fund_summary, get_group_id
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
    line_bot_api.reply_message(event.reply_token, TextSendMessage(
        text="📷 發票圖片上傳成功，請輸入記帳指令，例如：\n個人發票記帳 小明 或 分帳 名古屋 早餐 1000"))

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
                "📍 團體記帳與公費\n"
                "建立團體記帳 大阪 小明 小花\n"
                "分帳 名古屋 早餐 1000 小明+300 小強-100\n"
                "刪除分帳 名古屋 1 或 刪除分帳 名古屋 1,2\n"
                "刪除分帳 名古屋 早餐\n"
                "儲值公費 名古屋 3000\n"
                "儲值公費 名古屋 小明+300 小花+200\n"
                "扣款公費 名古屋 早餐 900 小明+400 小花+500\n"
                "查詢團體記帳 名古屋\n"
                "查詢公費 名古屋\n"
                "預覽公費紀錄 名古屋\n"
                "刪除公費 名古屋 1 或 刪除公費 名古屋 1,2\n\n"
                "刪除團體記帳 名古屋\n"
                "刪除團體 名古屋 1 或 刪除團體 名古屋 1,2\n"
                "刪除餐別 名古屋 2025/06/01 早餐\n"
                "重設團體記帳 名古屋\n\n"
                "📍 發票與中獎\n"
                "上傳發票 + 個人發票記帳 小明\n"
                "查詢中獎 小明\n"
            )

        elif msg.startswith("補發票 "):
            parts = msg.replace("補發票 ", "").split()
            if len(parts) == 4:
                name, invoice_number, date, amount = parts
                append_invoice_record(name, invoice_number, date, float(amount))
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
                append_personal_record(name, "發票消費", float(result["total"]), now, result["invoice_number"])
                reply = f"✅ {name} 發票記帳成功：{result['total']} 元\n發票號碼：{result['invoice_number']}"

        elif msg.startswith("記帳 "):
            parts = msg.split()
            if len(parts) >= 4:
                name, raw_amount, item = parts[1], parts[2], parts[3]
                amount = float(''.join(filter(lambda c: c.isdigit() or c == '.', raw_amount)))
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
            indexes = msg.replace("刪除個人 ", "").split(",")
            name = ""  # 這裡應該補上當前操作的使用者名稱（或設計交互流程記錄該名稱）
            success = all(delete_personal_record_by_index(name, int(i)-1) for i in indexes)
            reply = "✅ 已刪除指定記錄" if success else "⚠️ 刪除失敗"

        elif msg.startswith("重設個人記帳 "):
            name = msg.replace("重設個人記帳 ", "")
            reset_personal_record_by_name(name)
            reply = f"✅ 已重設 {name} 的個人記帳"

        elif msg.startswith("建立團體記帳 "):
            parts = msg.replace("建立團體記帳 ", "").split()
            group_name, members = parts[0], parts[1:]
            source = event.source
            group_id = source.group_id if hasattr(source, 'group_id') else None
            if not group_id:
                reply = "⚠️ 請在群組中使用此指令"
            else:
                create_group(group_name, members, group_id)
                reply = f"✅ 已建立團體 {group_name}，成員：{'、'.join(members)}"

        elif msg.startswith("儲值公費 "):
            parts = msg.replace("儲值公費 ", "").split()
            group_name = parts[0]
            members = get_group_members(group_name)
            if not members:
                reply = f"⚠️ 找不到團體 {group_name}"
            else:
                contributions = {}
                if len(parts) == 2:
                    total = float(parts[1])
                    per_person = round(total / len(members), 2)
                    for m in members:
                        contributions[m] = per_person
                else:
                    for item in parts[1:]:
                        if "+" in item:
                            name, amt = item.split("+")
                            if name in members:
                                contributions[name] = contributions.get(name, 0) + float(amt)
                for m, amt in contributions.items():
                    add_group_fund(group_name, m, amt, now)
                reply = f"✅ {group_name} 公費儲值完成：\n" + "\n".join([f"{k} +{v}" for k, v in contributions.items()])

        elif msg.startswith("查詢公費紀錄 "):
            group = msg.replace("查詢公費紀錄 ", "")
            reply = get_group_fund_history(group)

        elif msg.startswith("分帳 "):
            parts = msg.replace("分帳 ", "").split()
            group, meal, amount_raw = parts[0], parts[1], parts[2]
            amount = float(amount_raw)
            extra = parts[3:]
            members = get_group_members(group)
            if not members:
                reply = f"⚠️ 找不到團體 {group}"
            elif len(members) == 0:
                reply = "⚠️ 團體沒有成員"
            else:
                adjustments = {name: 0 for name in members}
                for adj in extra:
                    for name in members:
                        if name in adj:
                            if "+" in adj:
                                adjustments[name] += float(adj.split("+")[1])
                            elif "-" in adj:
                                adjustments[name] -= float(adj.split("-")[1])
                            break
                total_adjustment = sum(adjustments.values())
                base_amount = amount - total_adjustment
                if base_amount < 0:
                    reply = f"⚠️ 加總調整金額大於總金額，請確認指令"
                else:
                    per_person_base = round(base_amount / len(members), 2)
                    breakdown = []
                    for name in members:
                        actual_amount = round(per_person_base + adjustments[name], 2)
                        append_group_record(group, now, meal, meal, name, f"{name}:{actual_amount}", actual_amount, "")
                        breakdown.append(f"{name}:{actual_amount}")
                    reply = (
                        f"✅ {group} 已分帳 {meal} {amount} 元\n" +
                        f"📊 分帳結果：{'、'.join(breakdown)}"
                    )

        elif msg.startswith("查詢團體記帳 "):
            group = msg.replace("查詢團體記帳 ", "")
            df = get_group_records_by_group(group)
            if df.empty:
                reply = f"⚠️ 查無 {group} 資料"
            else:
                total_spent = df["Amount"].sum()
                group_id = get_group_id(group)
                balances = calculate_group_fund_balances(group_id)

                suggestions = []
                for name, info in balances.items():
                    if info['balance'] < 0:
                        suggestions.append(f"{name} 補 {-info['balance']:.0f} 元")
                        
                    if suggestions:
                        suggestion_msg = '\n'.join(suggestions)
                    else:
                        suggestion_msg = "無需補錢"

                    lines = [
                        f"{row['Date']} {row['Meal']} {row['Members']}（{row['Amount']}元）"
                        for _, row in df.iterrows()
                    ]
                    
                    total_fund = sum(info['topup'] for info in balances.values())
                    reply = (
                        f"📋 {group} 記錄：\n" +
                        "\n".join(lines) +
                        f"\n\n💰 公費總額：{total_fund:.2f} 元\n🧾 花費總額：{total_spent:.2f} 元\n" +
                        f"📉 剩餘金額：{total_fund - total_spent:.2f} 元"
                    )
                    reply += f"\n\n📈 儲值建議：\n{suggestion_msg}"

                    reply += "\n\n👥 各成員餘額："
                    for name, info in balances.items():
                        reply += f"\n{name}：{info['balance']:.2f} 元"

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
            reply = "⚠️ 請輸入有效指令，或輸入『指令說明』"

    except Exception as e:
        reply = f"❌ 發生錯誤：{e}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
