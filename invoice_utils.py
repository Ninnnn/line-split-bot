from google.cloud import vision
import os

# Initialize Google Vision Client
client = vision.ImageAnnotatorClient()

def extract_invoice_data(image_path):
    """Extract items and amount from the invoice image."""
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    
    texts = response.text_annotations
    if texts:
        items = []
        amount = 0
        
        for text in texts:
            # Add logic to detect items and amounts
            if re.match(r'\d+', text.description):  # Example for amount detection
                amount = float(text.description)
            else:
                items.append(text.description)
        
        return items, amount
    return [], 0
