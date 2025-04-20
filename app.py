from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from datetime import datetime

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 記憶體儲存
session_data = []
personal_data = {}

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

    # --- 均分制記帳 ---
    if text.startswith("記帳 "):
        try:
            msg = text[2:].strip()
            main_part, payer = msg.split("/")
            amount_str, purpose, *members = main_part.strip().split()
            amount = int(amount_str)
            payer = payer.strip()
            purpose = purpose.strip()
            participants = [m.strip() for m in members if m.strip()]
            if not participants or payer not in participants:
                raise ValueError("付款人必須包含在參與者中")

            session_data.append({
                "type": "split",
                "amount": amount,
                "purpose": purpose,
                "payer": payer,
                "members": participants
            })

            reply_text = (
                f"【記帳成功】\n"
                f"金額：{amount} 元\n"
                f"用途：{purpose}\n"
                f"付款人：{payer}\n"
                f"參與者：{', '.join(participants)}"
            )

        except:
            reply_text = (
                "【記帳格式錯誤】\n"
                "請使用：\n記帳 金額 用途 名單 / 付款人\n"
                "範例：\n記帳 500 晚餐 小明 小美 / 小明"
            )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    # --- 個別金額記帳 ---
    elif text.startswith("記帳詳細"):
        try:
            msg = text[5:].strip()
            main_part, payer = msg.split("/")
            parts = main_part.strip().split()
            purpose = parts[0]
            payer = payer.strip()
            people = parts[1:]

            member_amounts = {}
            for p in people:
                name, amt = p.split(":")
                member_amounts[name.strip()] = int(amt)

            if payer not in member_amounts:
                raise ValueError("付款人必須包含在參與者中")

            session_data.append({
                "type": "individual",
                "purpose": purpose,
                "payer": payer,
                "member_amounts": member_amounts
            })

            reply = (
                f"【記帳成功｜個別金額】\n"
                f"用途：{purpose}\n"
                f"付款人：{payer}\n"
                + "\n".join([f"{name}：{amt} 元" for name, amt in member_amounts.items()])
            )

        except:
            reply = (
                "【記帳詳細格式錯誤】\n"
                "請使用：\n記帳詳細 用途 名:金額 名:金額... / 付款人\n"
                "範例：\n記帳詳細 晚餐 小明:300 小美:250 / 小明"
            )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    # --- 結算 ---
    elif text == "結算":
        if not session_data:
            reply = "目前沒有任何記帳紀錄，請先輸入「記帳」或「記帳詳細」。"
        else:
            paid = {}
            share = {}
            lines = ["【所有消費記錄】"]

            for i, record in enumerate(session_data, start=1):
                if record["type"] == "split":
                    amt = record["amount"]
                    payer = record["payer"]
                    members = record["members"]
                    per_person = amt / len(members)

                    paid[payer] = paid.get(payer, 0) + amt
                    for m in members:
                        share[m] = share.get(m, 0) + per_person

                    lines.append(f"{i}. {amt} 元（{record['purpose']}），{payer} 付款，參與：{', '.join(members)}")

                elif record["type"] == "individual":
                    payer = record["payer"]
                    member_amounts = record["member_amounts"]
                    total_amt = sum(member_amounts.values())

                    paid[payer] = paid.get(payer, 0) + total_amt
                    for m, amt in member_amounts.items():
                        share[m] = share.get(m, 0) + amt

                    detail = "，".join([f"{k}:{v}" for k, v in member_amounts.items()])
                    lines.append(f"{i}. {total_amt} 元（{record['purpose']}），{payer} 付款，{detail}")

            summary_lines = ["", "【金錢統計】", "姓名    實付     應付     差額", "－" * 30]
            names = sorted(set(paid) | set(share))
            for name in names:
                p = paid.get(name, 0)
                s = share.get(name, 0)
                diff = p - s
                status = (
                    f"+{diff:.0f}（多付）" if diff > 0 else
                    f"{diff:.0f}（需補）" if diff < 0 else
                    "0（剛好）"
                )
                summary_lines.append(f"{name:<6} {p:>5.0f}元   {s:>5.0f}元   {status}")

            reply = "\n".join(lines + summary_lines)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    # --- 重設全部資料 ---
    elif text in ["重設", "重啟"]:
        session_data.clear()
        personal_data.clear()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="【已清空】\n所有記帳資料已重設，可重新開始記帳。"))

    # --- 個人記帳 ---
    elif text.startswith("個人記帳"):
        try:
            msg = text[4:].strip()
            main_part, person = msg.split("/")
            amount_str, purpose = main_part.strip().split(maxsplit=1)
            amount = int(amount_str)
            person = person.strip()
            purpose = purpose.strip()
            date_str = datetime.now().strftime("%Y/%m/%d")

            if person not in personal_data:
                personal_data[person] = []

            personal_data[person].append({
                "date": date_str,
                "amount": amount,
                "purpose": purpose
            })

            reply = (
                f"【個人記帳成功】\n"
                f"{person} 登記了 {amount} 元（{purpose}）\n"
                f"日期：{date_str}"
            )

        except:
            reply = (
                "【個人記帳格式錯誤】\n"
                "請使用：\n個人記帳 金額 用途 / 姓名\n"
                "範例：\n個人記帳 150 早餐 / 小明"
            )

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    # --- 查詢個人記帳 ---
    elif text.startswith("查詢個人"):
        name = text[5:].strip()
        today = datetime.now().strftime("%Y/%m/%d")
        records = personal_data.get(name)

        if not records:
            reply = f"【查詢日期】：{today}\n{name} 尚未有個人記帳紀錄。"
        else:
            total = sum(r["amount"] for r in records)
            lines = [f"【查詢日期】：{today}", f"【{name}的個人記帳紀錄】"]
            for i, r in enumerate(records, start=1):
                lines.append(f"{i}. {r['date']} {r['purpose']} {r['amount']} 元")
            lines.append(f"\n總消費：{total} 元")
            reply = "\n".join(lines)

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    # --- 重設個人記帳 ---
    elif text.startswith("重設個人"):
        name = text[5:].strip()
        if name in personal_data:
            del personal_data[name]
            reply = f"【個人記帳清除成功】\n已清空 {name} 的所有個人記帳紀錄。"
        else:
            reply = f"{name} 尚無個人記帳資料，無需清除。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

    # --- 指令說明 ---
    else:
        reply = (
            "【指令說明】\n"
            "● 記帳 金額 用途 名單 / 付款人\n"
            "  例：記帳 300 晚餐 小明 小美 / 小明\n"
            "● 記帳詳細 用途 姓名:金額 姓名:金額 / 付款人\n"
            "  例：記帳詳細 晚餐 小明:300 小美:250 / 小明\n"
            "● 結算：計算所有人分帳結果\n"
            "● 重設：清空所有記帳資料\n\n"
            "【個人記帳】\n"
            "● 個人記帳 金額 用途 / 姓名\n"
            "  例：個人記帳 150 早餐 / 小明\n"
            "● 查詢個人 姓名\n"
            "  例：查詢個人 小明\n"
            "● 重設個人 姓名\n"
            "  例：重設個人 小明"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
