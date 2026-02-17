FROM python:3.9-slim

WORKDIR /app

# Copy requirements first (for better caching)
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

# Set environment variables
ENV ENV=production
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Run the application with gunicorn for better performance
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]