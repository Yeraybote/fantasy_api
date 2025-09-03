FROM python:3.11-slim

# Instalar dependencias necesarias para Chromium
RUN apt-get update && apt-get install -y \
    wget gnupg \
    libnss3 libxss1 libasound2 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libdbus-1-3 libgbm1 \
    libxkbcommon0 libxcomposite1 libxrandr2 libgtk-3-0 \
    libpango-1.0-0 libpangocairo-1.0-0 libxdamage1 libxfixes3 libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Carpeta de trabajo
WORKDIR /app

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Descargar Chromium para Playwright (forzado)
RUN playwright install chromium --with-deps

# Copiar el resto del código
COPY . .

# Arrancar FastAPI (usando shell para expandir ${PORT})
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]


