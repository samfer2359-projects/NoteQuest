# Lessons Learned & Engineering Decisions

This document captures the technical challenges encountered during the development of NoteQuest, the solutions implemented, and potential improvements identified during the project.

---

## Challenge: Processing Multiple Note Formats

### Problem

Users could upload study material in different formats such as PDF, DOCX, and TXT. While text-based documents were straightforward to process, scanned PDFs frequently returned empty results during extraction.

### Solution

An OCR fallback mechanism was implemented using Tesseract and pdf2image. When standard PDF text extraction failed, pages were converted into images and processed through OCR.

### Supporting Code

**File:** `m2.py`

```python
text = extract_pdf_text(file_path)

if text and text.strip():
    return text

pages = convert_from_path(
    file_path,
    poppler_path=POPPLER_PATH
)

for page in pages:
    text += pytesseract.image_to_string(page)
```

### Lesson Learned

Supporting real-world file uploads requires multiple extraction strategies because not all documents contain machine-readable text.

---

## Challenge: Preventing Duplicate Concept Storage

### Problem

Repeated uploads of similar notes resulted in duplicate concepts being stored, which could negatively affect question generation quality.

### Solution

Duplicate prevention was implemented both at the application layer and database layer.

### Supporting Code

**File:** `m2.py`

```python
cur.execute(
    "SELECT 1 FROM Concepts WHERE user_id=%s AND concept_text=%s",
    (user_id, concept)
)

if not cur.fetchone():
    cur.execute(
        "INSERT INTO Concepts (user_id, concept_text) VALUES (%s, %s)",
        (user_id, concept)
    )
```

**File:** `database.sql`

```sql
ALTER TABLE Concepts
ADD CONSTRAINT unique_user_concept
UNIQUE (user_id, concept_text);
```

### Lesson Learned

Critical data integrity rules should be enforced at both the application and database levels.

---

## Challenge: Validating AI-Generated Content

### Problem

Questions generated through the LLM occasionally returned malformed JSON or invalid answer structures.

### Solution

Strict validation was introduced before storing generated questions.

### Supporting Code

**File:** `question_generator.py`

```python
if (
    isinstance(data, dict)
    and "question" in data
    and isinstance(data.get("options"), list)
    and len(data["options"]) == 4
    and "correct_answer" in data
    and data["correct_answer"] in data["options"]
):
    return data
```

### Lesson Learned

AI-generated output should never be trusted blindly. Validation layers are essential before integrating LLM responses into production workflows.

---

## Challenge: Maintaining System Availability

### Problem

Question generation depended on an external LLM service. Any failure could prevent gameplay from continuing.

### Solution

A three-level fallback strategy was implemented:

1. Generate a new AI question
2. Use a cached AI-generated question
3. Use a predefined database question

### Supporting Code

**File:** `question_generator.py`

```python
qdata = generate_groq_question(...)
```

```python
cached = get_cached_llm_question(difficulty)
```

```python
db_q = get_db_question(difficulty)
```

### Lesson Learned

Applications that depend on external services should always include fallback mechanisms to preserve user experience.

---

## Challenge: Secure User Authentication

### Problem

Storing passwords directly would expose users to unnecessary security risks.

### Solution

Passwords were hashed before storage and verified using secure hash comparison methods.

### Supporting Code

**File:** `app.py`

```python
hashed = generate_password_hash(password)
```

```python
check_password_hash(
    user[2],
    password
)
```

### Lesson Learned

Security should be integrated from the beginning rather than added later.

---

## Challenge: Progress Tracking Consistency

### Problem

Users could encounter the same question more than once, potentially creating duplicate progress records.

### Solution

Database upsert operations were used to ensure a single progress record existed per user-question pair.

### Supporting Code

**File:** `question_generator.py`

```python
INSERT INTO Progress
(user_id, question_id, solved, score_awarded)

ON CONFLICT (user_id, question_id)
DO UPDATE SET solved=TRUE
```

### Lesson Learned

Database constraints can simplify application logic while improving consistency.

---

# Areas for Improvement

The following improvements would be prioritized.

## Configuration Management

Current implementation contains hardcoded values such as database credentials and Flask secret keys.

### Current

```python
DB_CONFIG = {
    "database": "notequest",
    "user": "postgres",
    "password": "root"
}
```

### Improvement

Move all sensitive configuration into environment variables.

---


## Enhanced Upload Validation

The current validation primarily relies on file extensions.

### Improvement

Validate MIME types and file signatures before processing uploads.

---


## Question Generation Optimization

Every new question may trigger an LLM request.

### Improvement

Pre-generate question batches and implement more aggressive caching strategies to reduce latency and API usage.

---

# Key Takeaways

This project provided practical experience with:

* Full-stack web application development
* PostgreSQL database design
* Authentication and session management
* OCR-based document processing
* NLP keyword extraction
* AI integration and validation
* Error handling and fallback design
* Backend and frontend integration
* Data integrity enforcement
* User progress tracking

The project also reinforced the importance of designing systems that remain functional even when external dependencies fail.
