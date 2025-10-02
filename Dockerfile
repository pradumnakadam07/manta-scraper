# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Chrome/undetected-chromedriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    wget \
    curl \
    gnupg2 \
    unzip \
    lsb-release \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files
COPY . .

# Set environment variable for Streamlit
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=3000
ENV STREAMLIT_SERVER_ENABLECORS=false

# Expose port (Render uses 3000 by default)
EXPOSE 3000

# Start Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=3000", "--server.address=0.0.0.0"]
