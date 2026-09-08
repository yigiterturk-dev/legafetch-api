FROM python:3.12-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Gerekli sistem kütüphanelerini kur (Derleme için gcc gerekebilir)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Gereksinim dosyasını kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodları kopyala
COPY . .

# 8000 portunu dışarı aç
EXPOSE 8000

# Sunucuyu başlat (VPS üzerinde herkese açık IP dinler)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
