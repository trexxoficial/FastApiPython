# Usamos una imagen ligera de Python oficial
FROM python:3.11-slim

# Instalamos dependencias del sistema necesarias para Matplotlib y documentos
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos los requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código y la carpeta de plantillas
COPY . .

# Comando para arrancar Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]