"""
PDF Search Platform — Local Standalone Backend.
Runs entirely with SQLite + PyMuPDF. No Docker, PostgreSQL, Redis, or Elasticsearch needed.
"""

import os
import sys
import io

# Force UTF-8 output for Windows console (prevents EasyOCR progress bar crash)
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except Exception:
        pass
import uuid
import math
import shutil
import json
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import DictCursor
import boto3

S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
S3_REGION = os.environ.get("S3_REGION", "ap-southeast-2")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "pdfs")

if S3_ENDPOINT:
    s3_client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION
    )
else:
    s3_client = None

class PostgresConnection:
    def __init__(self, dsn):
        self.conn = psycopg2.connect(dsn, cursor_factory=DictCursor)
        self.conn.autocommit = False
        
    def execute(self, sql, params=()):
        sql = sql.replace("?", "%s")
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur
        
    def executescript(self, sql):
        # execute multiple statements by executing them directly
        cur = self.conn.cursor()
        cur.execute(sql)
        
    def commit(self):
        self.conn.commit()
        
    def close(self):
        self.conn.close()

# ── Database Setup ──
def get_db():
    return PostgresConnection(os.environ.get("DATABASE_URL"))

def init_database():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            page_count INTEGER DEFAULT 0,
            author TEXT,
            title TEXT,
            subject TEXT,
            creation_date TEXT,
            upload_date TEXT NOT NULL,
            primary_language TEXT DEFAULT 'en',
            processing_status TEXT DEFAULT 'pending',
            processing_progress REAL DEFAULT 0,
            processing_error TEXT,
            metadata_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pages (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            extracted_text TEXT,
            language TEXT DEFAULT 'en',
            has_text_layer INTEGER DEFAULT 0,
            ocr_applied INTEGER DEFAULT 0,
            word_count INTEGER DEFAULT 0,
            page_width REAL,
            page_height REAL,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS text_blocks (
            id TEXT PRIMARY KEY,
            page_id TEXT NOT NULL,
            block_index INTEGER DEFAULT 0,
            text_content TEXT,
            x REAL DEFAULT 0,
            y REAL DEFAULT 0,
            width REAL DEFAULT 0,
            height REAL DEFAULT 0,
            confidence REAL,
            font_name TEXT,
            font_size REAL,
            FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT,
            hashed_password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
# ── OCR Support ──
from PIL import Image
import io

OCR_ENGINE = None

try:
    import pytesseract
    # Explicitly set path to Tesseract installed in LocalAppData (no admin rights)
    tesseract_path = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    # Check if tesseract is working
    pytesseract.get_tesseract_version()
    OCR_ENGINE = "tesseract"
    print(f"[OK] Tesseract OCR available at {pytesseract.pytesseract.tesseract_cmd}")
except Exception as e:
    print(f"[WARN] Tesseract OCR not found or error: {e}")
    OCR_ENGINE = None

if not OCR_ENGINE:
    print("[WARN] No OCR engine available")
    print("[WARN] PDFs with custom fonts (Gujarati, Hindi, etc.) may show garbled text")


def is_text_garbled(text: str) -> bool:
    """Detect if extracted text is garbled (custom font encoding issue).
    
    Garbled text has high concentration of:
    - Latin characters mixed with symbols in non-Latin PDFs
    - Unusual Unicode ranges (private use area, symbol blocks)
    - Very high ratio of non-alphanumeric, non-space characters
    """
    if not text or len(text.strip()) < 20:
        return False
    
    # Count character categories
    total = 0
    garbled_chars = 0
    for ch in text:
        if ch.isspace():
            continue
        total += 1
        code = ord(ch)
        # Characters commonly seen in garbled text from custom fonts
        if code in range(0x2018, 0x201F):  # Smart quotes used as text
            garbled_chars += 1
        elif code in range(0x2039, 0x203B):  # Single angle quotes
            garbled_chars += 1
        elif code in range(0x00C0, 0x00FF) and code not in range(0x0900, 0x097F):  # Latin Extended used oddly
            garbled_chars += 1
        elif code in range(0xFB00, 0xFB50):  # Alphabetic presentation forms
            garbled_chars += 1
        elif code in range(0x2200, 0x22FF):  # Mathematical operators used as text
            garbled_chars += 1
        elif code in range(0x2010, 0x2027):  # General punctuation oddly
            garbled_chars += 1
    
    if total == 0:
        return False
    
    ratio = garbled_chars / total
    return ratio > 0.15  # More than 15% unusual chars = likely garbled


def ocr_page(page, lang_list=None):
    """Render PyMuPDF page as image and run OCR."""
    if OCR_ENGINE is None:
        return ""
    
    try:
        pix = page.get_pixmap(dpi=150)  # Lower DPI for memory-constrained environments
        img_data = pix.tobytes("png")
        del pix  # Free pixmap memory immediately
        img = Image.open(io.BytesIO(img_data))
        
        if OCR_ENGINE == "tesseract":
            lang_str = "+".join(lang_list) if lang_list else "guj+hin+eng"
            text = pytesseract.image_to_string(img, lang=lang_str)
            return text.strip()
        
        return ""
    except Exception as e:
        print(f"[WARN] OCR failed: {e}")
        return ""


import fitz  # PyMuPDF


# ── PDF Processing ──
def process_pdf(filename: str, document_id: str):
    """Extract text from PDF using PyMuPDF, with OCR fallback for garbled text."""

    print(f"[PROCESS] Starting processing for {document_id} ({filename})")
    conn = get_db()
    temp_path = f"/tmp/{filename}"
    try:
        print(f"[PROCESS] Downloading from S3...")
        s3_client.download_file(S3_BUCKET, filename, temp_path)
        print(f"[PROCESS] Downloaded. Opening PDF...")
        doc = fitz.open(temp_path)

        # Update document metadata
        metadata = doc.metadata or {}
        conn.execute("""
            UPDATE documents SET
                page_count = ?,
                author = ?,
                title = ?,
                subject = ?,
                creation_date = ?,
                processing_status = 'processing',
                processing_progress = 10,
                metadata_json = ?
            WHERE id = ?
        """, (
            len(doc),
            metadata.get("author", ""),
            metadata.get("title", ""),
            metadata.get("subject", ""),
            metadata.get("creationDate", ""),
            json.dumps(metadata),
            document_id,
        ))
        conn.commit()

        total_pages = len(doc)
        
        # Check first page to detect if OCR is needed
        first_page_text = doc[0].get_text("text") if total_pages > 0 else ""
        use_ocr = OCR_ENGINE is not None and (not first_page_text.strip() or is_text_garbled(first_page_text))
        if use_ocr:
            print(f"[PROCESS] OCR mode: No text or garbled text detected for {document_id}")
        else:
            print(f"[PROCESS] Text mode: Good text layer found for {document_id}")

        for page_num in range(total_pages):
            page = doc[page_num]
            
            # Try standard extraction first
            raw_text = page.get_text("text") or ""
            
            # If garbled, use OCR
            if use_ocr:
                text = ocr_page(page)
                ocr_applied = 1
                has_text = len(text.strip()) > 0
            else:
                text = raw_text
                ocr_applied = 0
                has_text = len(text.strip()) > 0
            
            rect = page.rect

            page_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO pages (id, document_id, page_number, extracted_text,
                    language, has_text_layer, ocr_applied, word_count, page_width, page_height)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                page_id,
                document_id,
                page_num + 1,
                text,
                "guj" if use_ocr else "en",
                1 if has_text else 0,
                ocr_applied,
                len(text.split()) if text else 0,
                rect.width,
                rect.height,
            ))

            # Extract text blocks with coordinates
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            block_index = 0
            for block in blocks.get("blocks", []):
                if block.get("type") == 0:  # Text block
                    block_text = ""
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            block_text += span.get("text", "")
                        block_text += "\n"

                    block_text = block_text.strip()
                    if not block_text:
                        continue

                    bbox = block.get("bbox", [0, 0, 0, 0])
                    first_span = {}
                    if block.get("lines") and block["lines"][0].get("spans"):
                        first_span = block["lines"][0]["spans"][0]

                    conn.execute("""
                        INSERT INTO text_blocks (id, page_id, block_index, text_content,
                            x, y, width, height, confidence, font_name, font_size)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        page_id,
                        block_index,
                        block_text,
                        bbox[0],
                        bbox[1],
                        bbox[2] - bbox[0],
                        bbox[3] - bbox[1],
                        1.0,
                        first_span.get("font", ""),
                        first_span.get("size", 0),
                    ))
                    block_index += 1

            # Update progress
            progress = 10 + (90 * (page_num + 1) / total_pages)
            conn.execute(
                "UPDATE documents SET processing_progress = ? WHERE id = ?",
                (progress, document_id),
            )
            conn.commit()
            print(f"[PROCESS] Page {page_num + 1}/{total_pages} done for {document_id}")

        # Mark as completed
        conn.execute("""
            UPDATE documents SET
                processing_status = 'completed',
                processing_progress = 100,
                updated_at = ?
            WHERE id = ?
        """, (datetime.now(timezone.utc).isoformat(), document_id))
        conn.commit()
        doc.close()

    except Exception as e:
        print(f"[ERROR] Processing failed for {document_id}: {e}")
        try:
            conn.execute("""
                UPDATE documents SET
                    processing_status = 'failed',
                    processing_error = ?,
                    updated_at = ?
                WHERE id = ?
            """, (str(e), datetime.now(timezone.utc).isoformat(), document_id))
            conn.commit()
        except Exception as db_err:
            print(f"[ERROR] Failed to update error status: {db_err}")
    finally:
        try:
            doc.close()
        except:
            pass
        if os.path.exists(temp_path):
            os.remove(temp_path)
        conn.close()


# ── Pydantic Models ──
class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str


# ── App Setup ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[*] Starting PDF Search Platform (Cloud Mode)...")
    init_database()
    print("[OK] PostgreSQL database initialized")

    # Recover stuck documents (interrupted by previous server restart)
    try:
        conn = get_db()
        stuck = conn.execute(
            "SELECT id, filename FROM documents WHERE processing_status IN ('processing', 'pending')"
        ).fetchall()
        if stuck:
            print(f"[RECOVERY] Found {len(stuck)} stuck document(s), re-queuing...")
            for doc in stuck:
                conn.execute(
                    "UPDATE documents SET processing_status = 'pending', processing_progress = 0 WHERE id = ?",
                    (doc["id"],)
                )
                # Delete any partially processed pages
                conn.execute("DELETE FROM text_blocks WHERE page_id IN (SELECT id FROM pages WHERE document_id = ?)", (doc["id"],))
                conn.execute("DELETE FROM pages WHERE document_id = ?", (doc["id"],))
            conn.commit()
            conn.close()

            # Re-process in background threads
            import threading
            for doc in stuck:
                print(f"[RECOVERY] Re-processing: {doc['id']} ({doc['filename']})")
                t = threading.Thread(target=process_pdf, args=(doc["filename"], doc["id"]))
                t.daemon = True
                t.start()
        else:
            conn.close()
    except Exception as e:
        print(f"[WARN] Recovery check failed: {e}")

    print("[OK] Ready!")
    yield
    print("[*] Shutting down...")


app = FastAPI(
    title="PDF Search Platform",
    description="Cloud mode — PostgreSQL + Supabase S3 + PyMuPDF",
    version="1.0.0-cloud",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan,
)

# CORS — allow frontend origins
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "https://pdf-ocr-g53d.onrender.com,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# (Uploads are served via S3 directly)


# ── Health Check ──
@app.api_route("/", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
@app.api_route("/api/v1/health", methods=["GET", "HEAD"])
async def health_check():
    return {
        "status": "healthy",
        "service": "PDF Search Platform",
        "version": "1.0.0-cloud",
        "environment": "cloud",
        "database": "postgresql",
        "storage": "supabase-s3",
    }


# ── Upload ──
@app.post("/api/v1/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed.")

    doc_id = str(uuid.uuid4())
    # Use ASCII-only S3 key (UUID + extension) to avoid Unicode issues
    safe_filename = f"{doc_id}.pdf"

    # Save file to S3
    content = await file.read()
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=safe_filename,
        Body=content,
        ContentType="application/pdf"
    )

    now = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    conn.execute("""
        INSERT INTO documents (id, filename, original_filename, file_size,
            upload_date, processing_status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
    """, (doc_id, safe_filename, file.filename, len(content), now, now, now))
    conn.commit()
    conn.close()

    # Process PDF asynchronously in the background so it doesn't block the event loop
    background_tasks.add_task(process_pdf, safe_filename, doc_id)

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "file_size": len(content),
        "task_id": None,
        "message": "PDF uploaded and processed successfully.",
    }


@app.post("/api/v1/upload/batch")
async def upload_batch(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        result = await upload_pdf(file)
        results.append(result)
    return results


@app.get("/api/v1/upload/status/{document_id}")
async def upload_status(document_id: str):
    conn = get_db()
    row = conn.execute(
        "SELECT processing_status, processing_progress, processing_error FROM documents WHERE id = ?",
        (document_id,),
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, "Document not found")

    return {
        "document_id": document_id,
        "status": row["processing_status"],
        "progress": row["processing_progress"],
        "message": None,
        "error": row["processing_error"],
    }


# ── Documents ──
@app.get("/api/v1/documents")
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
):
    conn = get_db()

    where_clauses = []
    params = []

    if status:
        where_clauses.append("processing_status = ?")
        params.append(status)
    if language:
        where_clauses.append("primary_language = ?")
        params.append(language)
    if search:
        where_clauses.append("original_filename LIKE ?")
        params.append(f"%{search}%")

    where_sql = " AND ".join(where_clauses)
    if where_sql:
        where_sql = "WHERE " + where_sql

    total = conn.execute(f"SELECT COUNT(*) as c FROM documents {where_sql}", params).fetchone()["c"]

    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM documents {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    ).fetchall()
    conn.close()

    return {
        "documents": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


@app.get("/api/v1/documents/stats")
async def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]
    total_pages = conn.execute("SELECT COUNT(*) as c FROM pages").fetchone()["c"]
    completed = conn.execute("SELECT COUNT(*) as c FROM documents WHERE processing_status = 'completed'").fetchone()["c"]
    processing = conn.execute("SELECT COUNT(*) as c FROM documents WHERE processing_status = 'processing'").fetchone()["c"]
    pending = conn.execute("SELECT COUNT(*) as c FROM documents WHERE processing_status = 'pending'").fetchone()["c"]
    total_size = conn.execute("SELECT COALESCE(SUM(file_size), 0) as s FROM documents").fetchone()["s"]
    conn.close()

    return {
        "total_documents": total,
        "total_pages": total_pages,
        "completed_documents": completed,
        "processing_documents": processing,
        "pending_documents": pending,
        "total_storage_bytes": total_size,
    }


@app.get("/api/v1/documents/{document_id}")
async def get_document(document_id: str):
    conn = get_db()
    doc = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if not doc:
        conn.close()
        raise HTTPException(404, "Document not found")

    pages = conn.execute(
        "SELECT * FROM pages WHERE document_id = ? ORDER BY page_number",
        (document_id,),
    ).fetchall()
    conn.close()

    result = dict(doc)
    result["pages"] = [dict(p) for p in pages]
    # Convert integer booleans for frontend
    for p in result["pages"]:
        p["has_text_layer"] = bool(p.get("has_text_layer"))
        p["ocr_applied"] = bool(p.get("ocr_applied"))

    return result


@app.get("/api/v1/documents/{document_id}/page/{page_number}")
async def get_page(document_id: str, page_number: int):
    conn = get_db()
    page = conn.execute(
        "SELECT * FROM pages WHERE document_id = ? AND page_number = ?",
        (document_id, page_number),
    ).fetchone()

    if not page:
        conn.close()
        raise HTTPException(404, "Page not found")

    page_dict = dict(page)
    page_dict["has_text_layer"] = bool(page_dict.get("has_text_layer"))
    page_dict["ocr_applied"] = bool(page_dict.get("ocr_applied"))

    blocks = conn.execute(
        "SELECT * FROM text_blocks WHERE page_id = ? ORDER BY block_index",
        (page_dict["id"],),
    ).fetchall()
    conn.close()

    page_dict["text_blocks"] = [dict(b) for b in blocks]
    return page_dict


@app.get("/api/v1/documents/{document_id}/file")
async def get_document_file(document_id: str):
    conn = get_db()
    doc = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    conn.close()

    if not doc:
        raise HTTPException(404, "Document not found")

    # Generate a presigned URL (works even if bucket is private)
    try:
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": doc["filename"]},
            ExpiresIn=3600,  # 1 hour
        )
    except Exception as e:
        print(f"[ERROR] Failed to generate presigned URL: {e}")
        # Fallback to public URL
        presigned_url = f"{S3_ENDPOINT.replace('/s3', '')}/object/public/{S3_BUCKET}/{doc['filename']}"

    return {
        "document_id": document_id,
        "filename": doc["original_filename"],
        "file_path": presigned_url,
    }


@app.delete("/api/v1/documents/{document_id}")
async def delete_document(document_id: str):
    conn = get_db()
    doc = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    if not doc:
        conn.close()
        raise HTTPException(404, "Document not found")

    # Delete file from S3
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=doc["filename"])
    except:
        pass

    # Delete from DB (cascade will handle pages and text_blocks)
    conn.execute("DELETE FROM text_blocks WHERE page_id IN (SELECT id FROM pages WHERE document_id = ?)", (document_id,))
    conn.execute("DELETE FROM pages WHERE document_id = ?", (document_id,))
    conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    conn.commit()
    conn.close()

    return {"message": f"Document {document_id} deleted successfully."}


# ── Search ──
@app.get("/api/v1/search")
async def search_documents(
    q: str = Query(..., min_length=1),
    search_type: str = Query("fulltext"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    language: Optional[str] = None,
    filename: Optional[str] = None,
):
    conn = get_db()

    query_lower = f"%{q.lower()}%"

    # Search in page text
    sql = """
        SELECT p.*, d.original_filename as filename, d.id as document_id,
               d.primary_language, d.author, d.upload_date
        FROM pages p
        JOIN documents d ON p.document_id = d.id
        WHERE LOWER(p.extracted_text) LIKE ?
    """
    params = [query_lower]

    if language:
        sql += " AND d.primary_language = ?"
        params.append(language)
    if filename:
        sql += " AND d.original_filename LIKE ?"
        params.append(f"%{filename}%")

    sql += " ORDER BY d.created_at DESC"

    all_results = conn.execute(sql, params).fetchall()

    total = len(all_results)
    offset = (page - 1) * page_size
    results = all_results[offset:offset + page_size]

    hits = []
    for r in results:
        text = r["extracted_text"] or ""
        idx = text.lower().find(q.lower())
        start = max(0, idx - 80)
        end = min(len(text), idx + len(q) + 80)
        snippet = text[start:end]

        # Create highlighted version
        highlighted = snippet.replace(q, f"<mark>{q}</mark>")

        hits.append({
            "document_id": r["document_id"],
            "page_id": r["id"],
            "filename": r["filename"],
            "page_number": r["page_number"],
            "content_snippet": f"...{snippet}...",
            "highlighted_content": f"...{highlighted}...",
            "language": r["primary_language"],
            "author": r["author"],
            "upload_date": r["upload_date"],
            "word_count": r["word_count"],
            "score": 1.0,
        })

    conn.close()

    return {
        "query": q,
        "search_type": search_type,
        "total_hits": total,
        "hits": hits,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
        "took_ms": 1,
        "suggestions": [],
    }


@app.get("/api/v1/search/suggestions")
async def search_suggestions(q: str = Query(..., min_length=1)):
    return {"suggestions": []}


# ── Auth (simplified for local mode) ──
@app.post("/api/v1/auth/register")
async def register(data: RegisterRequest):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    conn = get_db()

    # Check if user exists
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (data.username, data.email),
    ).fetchone()

    if existing:
        conn.close()
        raise HTTPException(400, "Username or email already registered.")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn.execute("""
        INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, 'user', 1, ?)
    """, (user_id, data.email, data.username, data.full_name, pwd_context.hash(data.password), now))
    conn.commit()
    conn.close()

    return {
        "id": user_id,
        "email": data.email,
        "username": data.username,
        "full_name": data.full_name,
        "role": "user",
        "is_active": True,
        "created_at": now,
    }


@app.post("/api/v1/auth/login")
async def login(data: LoginRequest):
    from passlib.context import CryptContext
    import jwt
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (data.username, data.username),
    ).fetchone()
    conn.close()

    if not user or not pwd_context.verify(data.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid credentials.")

    token = jwt.encode(
        {"sub": user["username"], "exp": datetime.now(timezone.utc).timestamp() + 86400},
        "local-dev-secret-key",
        algorithm="HS256",
    )

    return {
        "access_token": token,
        "refresh_token": token,
        "token_type": "bearer",
        "expires_in": 86400,
    }


# ── Run ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
