FROM python:3.11-slim

WORKDIR /app

# Copy requirements (now at root of context)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY models/ ./models/

# Copy training script and generate fresh model
COPY src/train.py ./src/
RUN python src/train.py

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000
CMD ["uvicorn", "src.predict:app", "--host", "0.0.0.0", "--port", "8000"]

