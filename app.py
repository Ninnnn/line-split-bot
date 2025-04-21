import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime
from google.cloud import vision
from google.cloud.vision import types
from io import BytesIO

from sheet_utils import (
    append_group_record,
    append_personal_record,
    get_personal_records_by_user,
    reset_personal_record_by_name
)

app = Flask(__name__)
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# Google Vision 客戶端初始化
client = vision.ImageAnnotatorClient()

def detect_text_from_image(image_bytes):
    image = types.Image(content=image_bytes)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts

group_records = []
personal_records = {}

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
    user_id = event.source.user_id
    msg = event.message.text.strip()

    if msg.startswith("記帳 "):
        try:
            parts = msg.split()
            payer = parts[1]
            raw_member_part = parts[2]
            note = parts[3] if len(parts) > 3 else ""
            date = parts[4] if len(parts) > 4 else datetime.now().strftime("%Y-%m-%d")

            members = []
            total_amount = 0
            member_amounts = {}

            # 檢查是否為個別金額格式（例如：張三:100,李四:200）
            if ":" in raw_member_part:
                pairs = raw_member_part.split(",")
                for p in pairs:
                    name, amt = p.split(":")
                    amt = int(amt)
                    member_amounts[name] = amt
                    total_amount += amt
                    members.append(name)
            else:
                # 均分格式
                members = raw_member_part.split(",")
                total_amount = int(parts[2])
                share = total_amount / len(members)
                for m in members:
                    member_amounts[m] = share

            # 儲存記錄
            group_records.append({
                'payer': payer,
                'amount': total_amount,
                'members': members,
                'note': note,
                'date': date,
                'individual': member_amounts
            })

            try:
                append_group_record(payer, total_amount, members, note, date)
            except Exception as e:
                print("寫入 Google Sheet 失敗（團體）:", e)

            msg = f"已記帳：{payer} 支付 {total_amount} 元\n"
            if ":" in raw_member_part:
                msg += "\n".join([f"{k}：{v}元" for k, v in member_amounts.items()])
            else:
                msg += f"均分每人 {round(share)} 元\n"
            msg += f"\n備註：{note}\n消費日：{date}"

        except Exception as e:
            msg = "格式錯誤！請使用：\n- 均分：記帳 張三 300 張三,李四 晚餐 2025-04-20\n- 個別：記帳 張三 張三:100,李四:200 晚餐 2025-04-20"

    elif msg == "查帳":
        total = {}
        for record in group_records:
            payer = record['payer']
            individual = record['individual']
            for name, amt in individual.items():
                if name != payer:
                    total[name] = total.get(name, 0) + amt
            total[payer] = total.get(payer, 0) - (record['amount'] - individual.get(payer, 0))

        summary = "\n".join([f"{k} 應付 {round(v)} 元" for k, v in total.items()])
        msg = f"【結算報告】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{summary}"

    elif msg == "重啟":
        group_records.clear()
        msg = "已清除所有團體記帳資料"

    elif msg.startswith("個人記帳 "):
        try:
            parts = msg.split()
            amount = int(parts[1])
            note_full = parts[2] if len(parts) > 2 else ""
            date = parts[3] if len(parts) > 3 else datetime.now().strftime("%Y-%m-%d")

            if "/" in note_full:
                note, name = note_full.split("/")
            else:
                note = note_full
                name = user_id  # 預設使用 user_id 當作名字

            if user_id not in personal_records:
                personal_records[user_id] = []
            personal_records[user_id].append({
                'amount': amount,
                'note': note,
                'date': date,
                'name': name
            })

            try:
                append_personal_record(user_id, name, amount, note, date)
            except Exception as e:
                print("寫入 Google Sheet 失敗（個人）:", e)

            msg = f"已記錄：{amount} 元，備註：{note}，消費日：{date}（記錄對象：{name}）"

        except Exception as e:
            msg = "格式錯誤！請使用：個人記帳 金額 備註/對象 日期(選填)"

    elif msg.startswith("查詢個人"):
        try:
            parts = msg.split()
            if len(parts) < 2:
                msg = "格式錯誤，請使用：查詢個人 名稱"
            else:
                name = parts[1]
                records = get_personal_records_by_user(name)
                total = sum([int(r['amount']) for r in records])
                detail = "\n".join([f"{r['date']}: {r['amount']} 元 - {r['note']}" for r in records])
                msg = f"【{name} 的個人記帳查詢】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{detail}\n\n總金額：{total} 元"
        except Exception as e:
            msg = "查詢失敗，請確認輸入格式與名稱"

    elif msg.startswith("重設個人"):
        try:
            parts = msg.split()
            if len(parts) < 2:
                msg = "格式錯誤，請使用：重設個人 名稱"
            else:
                name = parts[1]
                reset_personal_record_by_name(name)
                msg = f"{name} 的個人記帳資料已重設"
        except Exception as e:
            msg = "重設失敗，請確認輸入格式與名稱"

    elif msg.startswith("發票記帳"):
        # 取得圖片並解析文字
        if event.message.type == "image":
            message_content = line_bot_api.get_message_content(event.message.id)
            image_bytes = BytesIO(message_content.content)
            texts = detect_text_from_image(image_bytes)

            # 抽取發票內容（簡化範例，假設文字為金額與品項）
            invoice_text = texts[0].description
            print("發票內容：", invoice_text)

            # 解析金額與品項，這裡是示範邏輯，可以根據需求進一步處理
            amounts = [int(amount) for amount in invoice_text.split() if amount.isdigit()]

            # 以金額分配品項，並提示使用者選擇對應的人
            msg = "發票金額已識別，請輸入指令來選擇分配給誰。"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

    elif msg.startswith("個人發票記帳"):
        name = msg.split()[1]  # 取得名稱（如：小美）
        amounts = [40, 60]  # 假設從 OCR 識別到的金額
        note = "發票消費"
        date = datetime.now().strftime("%Y-%m-%d")
        
        # 記錄發票金額到個人記帳
        for amount in amounts:
            append_personal_record(user_id, name, amount, note, date)
        msg = f"{name}的發票記錄已完成。"

    else:
        msg = "請輸入指令，例如：\n- 記帳 張三 300 張三,李四 晚餐 2025-04-20\n- 查帳\n- 個人記帳 150 便當/寧 2025-04-20\n- 查詢個人 寧\n- 重設個人 寧\n- 發票記帳"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )

if __name__ == "__main__":
    app.run()
