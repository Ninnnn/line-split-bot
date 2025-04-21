import os
import json
from datetime import datetime
from flask import Flask, request, abort
from io import BytesIO
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, TextSendMessage
from google.cloud import vision

from sheet_utils import (
    append_group_record,
    append_personal_record,
    get_personal_records_by_user,
    reset_personal_record_by_name
)

app = Flask(__name__)
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# Google Vision Client 初始化
vision_client = vision.ImageAnnotatorClient()

# 暫存 OCR 資料：{user_id: {"items": [(品項, 金額), ...]}}
ocr_temp_data = {}

def detect_invoice_items_from_image(image_bytes):
    image = vision.Image(content=image_bytes)
    response = vision_client.text_detection(image=image)
    texts = response.text_annotations
    if not texts:
        return []

    full_text = texts[0].description
    lines = full_text.split('\n')
    items = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].replace('.', '').isdigit():
            try:
                amount = int(float(parts[-1]))
                item_name = ' '.join(parts[:-1])
                items.append((item_name, amount))
            except:
                continue
    return items

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=(TextMessage, ImageMessage))
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message

    if isinstance(msg, ImageMessage):
        image_content = line_bot_api.get_message_content(msg.id)
        image_bytes = BytesIO(image_content.content).read()
        items = detect_invoice_items_from_image(image_bytes)
        if items:
            ocr_temp_data[user_id] = {"items": items}
            item_list = '\n'.join([f"{i+1}. {name} - {amt}元" for i, (name, amt) in enumerate(items)])
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                text=f"已擷取以下發票品項：\n{item_list}\n\n請輸入分帳指令，如：發票記帳 小明:40,100 小美:60"
            ))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="無法從圖片辨識到發票內容，請確認發票清晰。"))
        return

    msg_text = msg.text.strip()

    if msg_text.startswith("記帳"):
        try:
            parts = msg_text.split()
            payer = parts[1]
            raw_member_part = parts[2]
            note = parts[3] if len(parts) > 3 else ""
            date = parts[4] if len(parts) > 4 else datetime.now().strftime("%Y-%m-%d")

            members = []
            total_amount = 0
            member_amounts = {}

            if ":" in raw_member_part:
                pairs = raw_member_part.split(",")
                for p in pairs:
                    name, amt = p.split(":")
                    amt = int(amt)
                    member_amounts[name] = amt
                    total_amount += amt
                    members.append(name)
            else:
                members = raw_member_part.split(",")
                total_amount = int(parts[2])
                share = total_amount / len(members)
                for m in members:
                    member_amounts[m] = share

            append_group_record(payer, total_amount, members, note, date)

            msg = f"已記帳：{payer} 支付 {total_amount} 元\n"
            if ":" in raw_member_part:
                msg += "\n".join([f"{k}：{v}元" for k, v in member_amounts.items()])
            else:
                msg += f"均分每人 {round(share)} 元\n"
            msg += f"\n備註：{note}\n消費日：{date}"

        except:
            msg = "格式錯誤！請使用：\n- 均分：記帳 張三 300 張三,李四 晚餐 2025-04-20\n- 個別：記帳 張三 張三:100,李四:200 晚餐 2025-04-20"

    elif msg_text.startswith("發票記帳"):
        try:
            if user_id not in ocr_temp_data:
                msg = "請先上傳發票圖片再輸入指令。"
            else:
                parts = msg_text.replace("發票記帳", "").strip().split()
                all_mapping = " ".join(parts)
                people_map = {}
                for pair in all_mapping.split():
                    for p in pair.split(","):
                        name, amt = p.split(":")
                        amt = int(amt)
                        if name not in people_map:
                            people_map[name] = []
                        people_map[name].append(amt)

                used_items = []
                ocr_items = ocr_temp_data[user_id]['items'][:]
                note = "發票記帳"
                date = datetime.now().strftime("%Y-%m-%d")
                confirm_list = []

                for name, amounts in people_map.items():
                    for amt in amounts:
                        matched = None
                        for i, (item_name, item_amt) in enumerate(ocr_items):
                            if item_amt == amt:
                                matched = ocr_items.pop(i)
                                break
                        if matched:
                            append_personal_record(user_id, name, amt, matched[0], date)
                            confirm_list.append(f"{name} - {matched[0]}：{amt} 元")
                        else:
                            append_personal_record(user_id, name, amt, note, date)
                            confirm_list.append(f"{name} - 未對應品項：{amt} 元")
                del ocr_temp_data[user_id]
                msg = "已完成發票記帳：\n" + "\n".join(confirm_list)
        except Exception as e:
            msg = "發票記帳失敗，請確認指令格式。"

    elif msg_text.startswith("個人發票記帳"):
        try:
            name = msg_text.split()[1]
            if user_id not in ocr_temp_data:
                msg = "請先上傳發票圖片。"
            else:
                note = "發票消費"
                date = datetime.now().strftime("%Y-%m-%d")
                for item_name, amt in ocr_temp_data[user_id]['items']:
                    append_personal_record(user_id, name, amt, item_name, date)
                del ocr_temp_data[user_id]
                msg = f"{name} 的發票記帳已完成"
        except:
            msg = "格式錯誤，請使用：個人發票記帳 小美"

    elif msg_text == "查帳":
        try:
            from sheet_utils import get_all_group_records
            records = get_all_group_records()
            total = {}
            for record in records:
                payer = record['payer']
                individual = json.loads(record['individual'])
                for name, amt in individual.items():
                    if name != payer:
                        total[name] = total.get(name, 0) + float(amt)
                total[payer] = total.get(payer, 0) - (float(record['amount']) - float(individual.get(payer, 0)))

            summary = "\n".join([f"{k} 應付 {round(v)} 元" for k, v in total.items()])
            msg = f"【結算報告】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{summary}"
        except:
            msg = "查帳時發生錯誤。"

    elif msg_text.startswith("個人記帳"):
        try:
            parts = msg_text.split()
            amount = int(parts[1])
            note_full = parts[2] if len(parts) > 2 else ""
            date = parts[3] if len(parts) > 3 else datetime.now().strftime("%Y-%m-%d")
            if "/" in note_full:
                note, name = note_full.split("/")
            else:
                note = note_full
                name = user_id
            append_personal_record(user_id, name, amount, note, date)
            msg = f"已記錄：{amount} 元，備註：{note}，消費日：{date}（記錄對象：{name}）"
        except:
            msg = "格式錯誤！請使用：個人記帳 金額 備註/對象 日期(選填)"

    elif msg_text.startswith("查詢個人"):
        try:
            parts = msg_text.split()
            if len(parts) < 2:
                msg = "格式錯誤，請使用：查詢個人 名稱"
            else:
                name = parts[1]
                records = get_personal_records_by_user(name)
                total = sum([int(r['amount']) for r in records])
                detail = "\n".join([f"{r['date']}: {r['amount']} 元 - {r['note']}" for r in records])
                msg = f"【{name} 的個人記帳查詢】\n查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{detail}\n\n總金額：{total} 元"
        except:
            msg = "查詢失敗，請確認輸入格式與名稱"

    elif msg_text.startswith("重設個人"):
        try:
            parts = msg_text.split()
            if len(parts) < 2:
                msg = "格式錯誤，請使用：重設個人 名稱"
            else:
                name = parts[1]
                reset_personal_record_by_name(name)
                msg = f"{name} 的個人記帳資料已重設"
        except:
            msg = "重設失敗，請確認輸入格式與名稱"

    else:
        msg = "請輸入指令，例如：\n- 記帳 張三 300 張三,李四 晚餐 2025-04-20\n- 查帳\n- 個人記帳 150 便當/名稱 2025-04-20\n- 查詢個人 名稱\n- 重設個人 名稱\n- 上傳發票圖片後輸入：發票記帳 小明:60 小美:40 或 個人發票記帳 小美"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=msg)
    )

if __name__ == '__main__':
    app.run(debug=True)
