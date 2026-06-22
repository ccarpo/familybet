FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Set environment variables
ENV FLASK_APP=run.py
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////app/data/familybet.db
ENV SECRET_KEY=change-me-in-production

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "run.py"]
