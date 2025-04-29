from google.cloud import vision
import os
import json
import re

def extract_text_from_image(image_path):
    """
    使用 Google Vision API 擷取圖片中的文字
    """
    credentials_info = json.loads(os.environ.get("GOOGLE_CREDENTIALS"))
    client = vision.ImageAnnotatorClient.from_service_account_info(credentials_info)

    with open(image_path, "rb") as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    response = client.text_detection(image=image)

    texts = response.text_annotations
    if not texts:
        return ""

    return texts[0].description  # 回傳擷取到的整段文字


def extract_invoice_data_from_image(image_path):
    """
    使用 Vision API 擷取發票品項、金額和發票號碼
    """
    extracted_text = extract_text_from_image(image_path)
    if not extracted_text:
        return {"invoice_number": "", "total": 0, "items": []}

    invoice_number_pattern = r'\b[A-Z]{2}\d{8}\b'  # 例如 AB12345678
    amount_pattern = r'(\d+(?:,\d{3})*(?:\.\d{2})?)'
    item_pattern = r'(\D+?)\s+(\d+(?:,\d{3})*(?:\.\d{2})?)'

    invoice_number_matches = re.findall(invoice_number_pattern, extracted_text)
    invoice_number = invoice_number_matches[0] if invoice_number_matches else ""

    amounts = re.findall(amount_pattern, extracted_text)
    total = float(amounts[-1].replace(",", "")) if amounts else 0

    items = []
    item_matches = re.findall(item_pattern, extracted_text)
    for match in item_matches:
        item_name = match[0].strip()
        item_amount = float(match[1].replace(",", ""))
        items.append({"name": item_name, "amount": item_amount})

    return {
        "invoice_number": invoice_number,
        "total": total,
        "items": items
    }


def extract_and_process_invoice(image_path):
    """
    提取發票並返回處理過的資料
    """
    invoice_data = extract_invoice_data_from_image(image_path)
    if not invoice_data["invoice_number"]:
        return "❌ 無法識別發票號碼，請確認圖片清晰度。"

    if not invoice_data["items"]:
        return "❌ 無法識別發票品項，請確認圖片清晰度。"

    return invoice_data
