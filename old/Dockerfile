FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OS deps: audio and e-ink display hardware support (libgpiod + SPI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev build-essential \
    libasound2-dev portaudio19-dev \
    libopenblas0 \
    python3-dev \
    python3-pip \
    python3-pil \
    python3-numpy \
    libfreetype6-dev \
    libjpeg-dev \
    libopenjp2-7 \
    libtiff6 \
    fonts-noto \
    fontconfig \
    libgpiod3 \
    python3-libgpiod \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./app/

CMD ["python", "-m", "app.main"]