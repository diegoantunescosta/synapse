from flask import Flask, request, jsonify
from ultralytics import YOLO
import boto3
import easyocr
import cv2
import numpy as np
from io import BytesIO
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET")

db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

s3_client = boto3.client(
    "s3",
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

yolo_model = YOLO("best1.pt")
ocr_reader = easyocr.Reader(['pt', 'en'])

@app.route("/processar", methods=["POST"])
def processar_imagem():
    if "file" not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    npimg = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    # Detecta placas com YOLO
    results = yolo_model.predict(image, imgsz=640)
    boxes = results[0].boxes.xyxy.cpu().numpy()

    if len(boxes) == 0:
        return jsonify({"mensagem": "Nenhuma placa detectada"}), 200

    placas_detectadas = []

    for box in boxes:
        x1, y1, x2, y2 = map(int, box[:4])
        recorte = image[y1:y2, x1:x2]

        # OCR no recorte para extrair texto da placa
        ocr_result = ocr_reader.readtext(recorte)
        if not ocr_result:
            continue

        # Pega texto com maior confiança
        ocr_result.sort(key=lambda x: x[2], reverse=True)
        placa_text = ocr_result[0][1].replace(" ", "").upper()

        if not placa_text:
            continue

        # Salvar a placa no banco com dados padrão para os campos NOT NULL
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()

            # Evitar duplicata
            cursor.execute("SELECT id FROM placas WHERE placa = %s", (placa_text,))
            exists = cursor.fetchone()
            if exists:
                cursor.close()
                conn.close()
                placas_detectadas.append(placa_text)
                continue

            cursor.execute("""
                INSERT INTO placas (placa, motorista, cargo, funcao_cargo, modelo_veiculo, cor_veiculo)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                placa_text,
                "Desconhecido",     # motorista
                "CONVIDADO",        # cargo - valor válido do ENUM
                "",                 # funcao_cargo vazio
                "Indefinido",       # modelo_veiculo
                "Indefinido"        # cor_veiculo
            ))
            conn.commit()
            cursor.close()
            conn.close()
            placas_detectadas.append(placa_text)

        except mysql.connector.Error as err:
            return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500

    if not placas_detectadas:
        return jsonify({"mensagem": "Nenhuma placa reconhecida pelo OCR"}), 200

    return jsonify({
        "mensagem": "Placas detectadas e salvas no banco de dados.",
        "placas": placas_detectadas
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
