# Use python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies including Poppler (needed for PDF to Image conversion in OCR)
RUN apt-get update && apt-get install -y \
    poppler-utils \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Run database setup to initialize the SQLite DB inside the container
RUN python database.py

# Expose port and configure LiveKit agents to listen on 8080
ENV PORT=8080
EXPOSE 8080

# Command to run the agent in start/production mode
CMD ["python", "voice_agent.py", "start"]
