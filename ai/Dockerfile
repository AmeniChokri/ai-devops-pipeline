FROM python:3.9-slim

WORKDIR /app

# Copy requirements first for better caching
COPY ai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the AI service code and models
COPY ai/src/ ./src/
COPY ai/models/ ./models/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose the port
EXPOSE 8000

# Run the service
CMD ["uvicorn", "src.predict:app", "--host", "0.0.0.0", "--port", "8000"]
