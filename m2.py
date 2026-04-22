import os
import re
import psycopg2
import yake
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document
from PIL import Image
import pytesseract
from pdf2image import convert_from_path


# Tesseract & Poppler Config
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler\Library\bin"



# DATABASE CONFIGURATION
DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root",
    "host": "localhost",
    "port": "5432"
}


def connect_db():
    return psycopg2.connect(**DB_CONFIG)



DBMS_KEYWORDS = {
    "sql", "dbms", "database", "normalization", "transaction",
    "acid", "join", "primary key", "foreign key", "index",
    "schema", "er diagram", "tuple", "relation", "attribute",
    "functional dependency", "locking", "deadlock",
    "concurrency", "isolation", "aggregation"
}

STOPWORDS = {"the", "is", "and", "of", "in", "to", "a", "for", "on", "with"}



# TEXT CLEANING

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return text


def clean_concept(concept: str) -> str:
    words = concept.lower().split()
    words = [w for w in words if w not in STOPWORDS]
    return " ".join(words).strip()



# KEYWORD EXTRACTION 
def extract_yake_keywords(text: str) -> set:
    extractor = yake.KeywordExtractor(
        lan="en",
        n=3,
        dedupLim=0.9,
        top=40
    )
    return {kw for kw, _ in extractor.extract_keywords(text)}


def is_dbms_related(concept: str) -> bool:
    return any(keyword in concept for keyword in DBMS_KEYWORDS)



# CONCEPT EXTRACTION
def extract_concepts_from_text(text: str) -> list:
    concepts = set()

    cleaned = clean_text(text)

    keywords = extract_yake_keywords(cleaned)

    for kw in keywords:
        kw = clean_concept(kw)

        if not kw:
            continue

        if 2 <= len(kw.split()) <= 4 and is_dbms_related(kw):
            concepts.add(kw)

    # Fallback: capture uppercase words like DBMS, SQL
    uppercase = re.findall(r'\b[A-Z][A-Z0-9]{2,}\b', text)
    concepts.update(uppercase)

    return list(concepts)



# FILE TEXT EXTRACTION
def extract_text_from_file(file_path: str) -> str:
    ext = file_path.lower().split('.')[-1]

    # TXT
    if ext == "txt":
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    # DOCX
    elif ext == "docx":
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)

    # PDF (Text + OCR fallback)
    elif ext == "pdf":
        text = extract_pdf_text(file_path)

        if text and text.strip():
            return text

        print("Using OCR for scanned PDF...")
        text = ""
        pages = convert_from_path(file_path, poppler_path=POPPLER_PATH)

        for page in pages:
            text += pytesseract.image_to_string(page)

        return text

    # IMAGE OCR
    elif ext in ["jpg", "jpeg", "png", "tiff"]:
        img = Image.open(file_path)
        return pytesseract.image_to_string(img)

    else:
        raise ValueError(f"Unsupported file type: {ext}")



# STORE CONCEPTS

def store_concepts(user_id: int, concepts: list):
    if not concepts:
        return

    conn = connect_db()
    cur = conn.cursor()

    for concept in concepts:
        cur.execute(
            "SELECT 1 FROM Concepts WHERE user_id=%s AND concept_text=%s",
            (user_id, concept)
        )

        if not cur.fetchone():
            cur.execute(
                "INSERT INTO Concepts (user_id, concept_text) VALUES (%s, %s)",
                (user_id, concept)
            )

    conn.commit()
    cur.close()
    conn.close()



# MAIN PROCESS
def process_uploaded_file(user_id: int, file_path: str) -> list:
    if not os.path.exists(file_path):
        raise FileNotFoundError("File not found")

    text = extract_text_from_file(file_path)

    if not text.strip():
        raise ValueError("No text extracted")

    concepts = extract_concepts_from_text(text)

    if not concepts:
        raise ValueError("No concepts found")

    store_concepts(user_id, concepts)

    return concepts



# SAFE PRINT

def safe_print(msg):
    try:
        print(msg)
    except Exception:
        print(str(msg).encode("ascii", "ignore").decode())



if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        safe_print("Usage: python m2.py <file_path> <user_id>")
        exit(1)

    file_path = sys.argv[1]
    user_id = int(sys.argv[2])

    try:
        concepts = process_uploaded_file(user_id, file_path)
        safe_print(f"Extracted {len(concepts)} concepts")
        exit(0)

    except Exception as e:
        safe_print(f"Error: {e}")
        exit(1)