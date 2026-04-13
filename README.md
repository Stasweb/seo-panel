# SEO Panel - Home SEO Management Panel

Легковесная SEO-панель для управления небольшим пулом сайтов (до 5–10 проектов) на маломощном сервере.

---

## 🧱 Стек

- **Backend:** Python 3.10+ (FastAPI)
- **DB:** SQLite (Async SQLAlchemy)
- **Frontend:** Jinja2 + HTMX + Tailwind CSS
- **HTTP Client:** HTTPX

---

## ⚙️ Установка на Ubuntu Server

### 1. Подготовка системы

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

---

### 2. Клонирование и настройка

```bash
git clone https://github.com/Stasweb/seo-panel.git
cd seo-panel

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
```

---

## 🚀 Запуск

### 🔹 DEV режим (для теста)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

---

### 🔹 PRODUCTION (рекомендуется)

Для серверов с 1–2 GB RAM:

```bash
gunicorn app.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  -b 127.0.0.1:8090 \
  --timeout 60
```

👉 Используем порт **8090**, чтобы избежать конфликтов

---

## 🔁 Systemd (автозапуск)

Создай файл:

```bash
sudo nano /etc/systemd/system/seo-panel.service
```

```ini
[Unit]
Description=SEO Panel FastAPI App
After=network.target

[Service]
User=youruser
WorkingDirectory=/home/youruser/seo-panel
Environment="PATH=/home/youruser/seo-panel/venv/bin"

ExecStart=/home/youruser/seo-panel/venv/bin/gunicorn app.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  -b 127.0.0.1:8090

Restart=always

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable seo-panel
sudo systemctl start seo-panel
```

Проверка:

```bash
sudo systemctl status seo-panel
```

---

## 🌐 Nginx (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8090;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📦 Функционал

- **Сайты:** CRUD управление проектами
- **Задачи:** Мини CRM
- **Контент-план:** Управление публикациями
- **SEO инструменты:**
  - keyword density
  - генерация meta description

- **Аналитика:**
  - импорт CSV из Google Search Console
  - история позиций

- **Проверки:**
  - HTTP статус
  - Title / H1

- **Фоновые задачи:**
  - проверки раз в 24 часа

---

## 💡 Рекомендации

- Для 1–2 GB RAM → не увеличивай workers > 2
- Используй SQLite только для небольших проектов
- Для роста → переходи на PostgreSQL

---
