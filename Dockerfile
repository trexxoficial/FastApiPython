# 1. Imagen base oficial de Python
FROM python:3.11-slim

# 2. Directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Instalación de dependencias del sistema obligatorias para WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    shared-mime-info \
    libgobject-2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Copiar e instalar los requerimientos de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar todo el código de tu proyecto
COPY . .

# 6. Exponer el puerto y arrancar Uvicorn
# Railway inyecta dinámicamente la variable $PORT
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}