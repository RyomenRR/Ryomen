# Base Python
FROM python:3.13-slim

# Set timezone and install dependencies
RUN apt-get update && \
    apt-get install -y tzdata gcc libffi-dev python3-dev make curl && \
    ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && \
    dpkg-reconfigure --frontend noninteractive tzdata && \
    apt-get clean

# Install ntp for time sync
RUN apt-get update && apt-get install -y ntpdate && apt-get clean

# Set working directory
WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .

# Time sync at container start to prevent Pyrogram [16] errors
CMD ntpdate -u pool.ntp.org && python bot.py
