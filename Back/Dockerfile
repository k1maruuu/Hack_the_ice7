# Базовый образ
FROM python:3.9-slim

# Устанавливаем системные зависимости для Chromium / Playwright
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxkbcommon0 \
    libasound2 \
    libgbm1 \
    libxshmfence1 \
    libxrender1 \
    libxcb1 \
    libexpat1 \
    ca-certificates \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Ставим Python-зависимости + Chromium для Playwright
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install chromium

# Копируем приложение
COPY . .

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
