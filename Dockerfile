FROM python:3.9-slim

WORKDIR /app

# Install system dependencies needed for libraries like Pillow or Psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip install --no-cache-dir flask gunicorn psycopg2-binary bcrypt pyotp qrcode pillow

# Copy the entire project structure into the container workspace
COPY . /app/

# Expose port 3001 (Matches the portal nginx proxy configuration)
EXPOSE 3001

# Environment variable to ensure python output isn't buffered
ENV PYTHONUNBUFFERED=1

# Run Gunicorn pointing directly to the app module inside webapp folder
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:3001", "webapp.app:app"]