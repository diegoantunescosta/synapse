from fastapi import FastAPI, File, UploadFile
import cv2
import easyocr
from ultralytics import YOLO
import numpy as np
import shutil

app = FastAPI()
model = YOLO("best1.pt")
reader = easyocr.Reader(['pt'])

@app.post("/detect-ocr/")
async def detect_ocr(file: UploadFile = File(...)):
    with open("temp.jpg", "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    image = cv2.imread("temp.jpg")
    results = model(["temp.jpg"])
    response = []
    for i, box in enumerate(results[0].boxes.xyxy):
        x1, y1, x2, y2 = map(int, box.tolist())
        cropped_img = image[y1:y2, x1:x2]
        cropped_path = f"crop{i}.jpg"
        cv2.imwrite(cropped_path, cropped_img)
        ocr_results = reader.readtext(cropped_path)
        for bbox, text, conf in ocr_results:
            response.append({"text": text, "conf": float(conf)})
    return {"results": response} 