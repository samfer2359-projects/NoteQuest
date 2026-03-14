import sys
import os
import re
import spacy
import yake
import psycopg2
from docx import Document
import fitz
import easyocr
import numpy as np

TOPIC = "DBMS"

DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}

print("Loading NLP model...")
nlp = spacy.load("en_core_web_sm")

print("Initializing EasyOCR...")
ocr_reader = easyocr.Reader(['en'])


def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^A-Za-z0-9 ,.-]', '', text)
    return text.strip()


def extract_text(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return clean_text(f.read())

    elif ext == ".docx":
        doc = Document(file_path)
        content = "\n".join([para.text for para in doc.paragraphs])
        return clean_text(content)

    elif ext == ".pdf":
        text = ""
        pdf_doc = fitz.open(file_path)
        for page in pdf_doc:
            page_text = page.get_text()
            if page_text.strip():
                text += clean_text(page_text) + "\n"
            else:
                pix = page.get_pixmap()
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                ocr_text = " ".join(ocr_reader.readtext(img, detail=0))
                text += clean_text(ocr_text) + "\n"
        return text

    else:
        raise ValueError("Only .txt, .docx, .pdf supported")


def connect_db():
    return psycopg2.connect(**DB_CONFIG)


def insert_note(conn, content):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Notes (topic, content) VALUES (%s, %s)", (TOPIC, content))
    conn.commit()
    cursor.close()


def store_concepts(conn, concepts, user_id):
    cursor = conn.cursor()
    for concept in concepts:
        cursor.execute(
            "INSERT INTO Concepts (topic, concept_text, user_id) VALUES (%s, %s, %s)",
            (TOPIC, concept, user_id)
        )
    conn.commit()
    cursor.close()


def extract_keywords(text):
    kw_extractor = yake.KeywordExtractor(lan="en", n=2, top=50)
    keywords = kw_extractor.extract_keywords(text)
    clean_keywords = []
    for kw, _ in keywords:
        kw = kw.strip()
        if len(kw) > 3:
            clean_keywords.append(kw)
    return list(set(clean_keywords))


def main():
    if len(sys.argv) != 3:
        print("Usage: python m2.py <file_path> <user_id>")
        sys.exit(1)

    file_path = sys.argv[1]
    user_id   = int(sys.argv[2])

    if not os.path.exists(file_path):
        print("File not found.")
        sys.exit(1)

    content = extract_text(file_path)

    if not content.strip():
        print("No readable text found.")
        sys.exit(1)

    conn = connect_db()
    insert_note(conn, content)
    concepts = extract_keywords(content)
    store_concepts(conn, concepts, user_id)
    conn.close()

    print("Concepts extracted and stored successfully.")


if __name__ == "__main__":
    main()
