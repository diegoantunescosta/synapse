from flask import Flask, request, jsonify
import boto3
import easyocr
import cv2
import numpy as np
from io import BytesIO
import mysql.connector
from datetime import datetime
import os
from dotenv import load_dotenv

# --- Carregar variáveis do .env ---
load_dotenv()

# --- Verificação de variáveis obrigatórias ---
required_vars = [
    "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_BUCKET",
    "DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"
]
for var in required_vars:
    if not os.getenv(var):
        raise EnvironmentError(f"Variável de ambiente {var} não está definida.")

# --- Configurações ---
app = Flask(__name__)
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET")

# --- Configuração do Banco de Dados ---
db_config = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

# --- Cliente MinIO ---
s3_client = boto3.client(
    "s3",
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
)

# Criar bucket se não existir
try:
    s3_client.head_bucket(Bucket=MINIO_BUCKET)
except:
    s3_client.create_bucket(Bucket=MINIO_BUCKET)

# --- OCR ---
ocr_reader = easyocr.Reader(['pt', 'en'])

@app.route("/processar", methods=["POST"])
def processar_imagem():
    if "file" not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    filename = file.filename
    npimg = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    # OCR com EasyOCR
    resultados = ocr_reader.readtext(image)
    textos_concat = " | ".join([r[1] for r in resultados])

    # Upload imagem ao MinIO
    _, buffer = cv2.imencode('.jpg', image)
    img_bytes = BytesIO(buffer.tobytes())
    s3_client.upload_fileobj(img_bytes, MINIO_BUCKET, filename)
    url_minio = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{filename}"

    # Salvar dados no banco MySQL
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        query = """
            INSERT INTO registros (nome_arquivo, texto_detectado, link_minio)
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (filename, textos_concat, url_minio))
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        return jsonify({"erro": f"Erro no banco de dados: {err}"}), 500

    return jsonify({
        "mensagem": "Imagem processada, enviada ao MinIO e salva no banco MySQL.",
        "link_minio": url_minio,
        "texto_detectado": textos_concat
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
