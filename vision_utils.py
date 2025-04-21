from google.cloud import vision
import os
import json

def extract_text_from_image(image_path):
    # 使用 Render 的環境變數初始化
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
