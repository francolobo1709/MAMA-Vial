# Imagen base liviana de Python para producción
FROM python:3.11-slim

# Evitar escritura de bytecode y buffer en stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema requeridas para audio y fuentes
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código fuente y plantilla base
COPY services/ ./services/
COPY data/ ./data/
COPY telegram_bot.py .
COPY 12-10-26.xlsx .

# Crear carpeta de datos y permisos
RUN mkdir -p data/cola_uploads

CMD ["python", "telegram_bot.py"]
