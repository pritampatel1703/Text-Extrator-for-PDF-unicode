FROM python:3.12-slim

# Install system dependencies (Tesseract OCR for Gujarati, Hindi, English, Sanskrit)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-guj \
    tesseract-ocr-hin \
    tesseract-ocr-san \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces require running as a non-root user (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python dependencies
COPY --chown=user backend/requirements-local.txt .
RUN pip install --no-cache-dir -r requirements-local.txt

# Copy backend code
COPY --chown=user backend/ .

# Environment variables for persistent storage
# Hugging Face mounts persistent storage at /data
ENV UPLOAD_DIR=/data/uploads
ENV DB_PATH=/data/pdf_platform.db

# Expose the default Hugging Face port
EXPOSE 7860

CMD ["uvicorn", "local_server:app", "--host", "0.0.0.0", "--port", "7860"]
