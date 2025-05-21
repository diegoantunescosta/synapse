import cv2
import pytesseract
from ultralytics import YOLO
import easyocr

model = YOLO("best1.pt")
image_paths = ["car.jpeg"]
results = model(image_paths)

reader = easyocr.Reader(['pt'])

for img_path, result in zip(image_paths, results):
    image = cv2.imread(img_path)

    for i, box in enumerate(result.boxes.xyxy):
        x1, y1, x2, y2 = map(int, box.tolist())
        cropped_img = image[y1:y2, x1:x2]
        cropped_path = f"{img_path}crop{i}.jpg"
        cv2.imwrite(cropped_path, cropped_img)
        # Usando easyocr para OCR
        ocr_results = reader.readtext(cropped_path)
        for bbox, text, conf in ocr_results:
            print(f'Texto: {text} | Confiança: {conf}')