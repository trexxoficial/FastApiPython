
FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    shared-mime-info \
    libgobject-2.0-0 \
    ffmpeg \
    curl \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar Deno
ENV DENO_INSTALL=/usr/local
RUN curl -fsSL https://deno.land/install.sh | sh

ENV PATH="/usr/local/bin:${PATH}"

# Instalar dependencias Python
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -U -r requirements.txt

# Copiar proyecto
COPY . .

# Verificar herramientas
RUN deno --version && ffmpeg -version

# Iniciar FastAPI
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
