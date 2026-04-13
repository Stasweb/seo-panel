# SEO Studio - Home SEO Management Panel

Легковесная SEO-панель для управления небольшим пулом сайтов.

## Стек
- **Backend:** Python 3.10+ (FastAPI)
- **DB:** SQLite (Async SQLAlchemy)
- **Frontend:** Jinja2 + HTMX + Tailwind CSS
- **HTTP Client:** HTTPX

## Установка на Ubuntu Server

### 1. Подготовка системы
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv git -y
```

### 2. Клонирование и настройка
```bash
git clone <your-repo-url> seo-studio
cd seo-studio
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Запуск через Gunicorn (для продакшена)
Для работы на 1-2 GB RAM рекомендуется использовать Gunicorn с Uvicorn workers.

```bash
pip install gunicorn uvicorn
gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 4. Настройка Systemd (автозапуск)
Создайте файл `/etc/systemd/system/seo-studio.service`:

```ini
[Unit]
Description=SEO Studio FastAPI App
After=network.target

[Service]
User=youruser
Group=www-data
WorkingDirectory=/home/youruser/seo-studio
Environment="PATH=/home/youruser/seo-studio/venv/bin"
ExecStart=/home/youruser/seo-studio/venv/bin/gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable seo-studio
sudo systemctl start seo-studio
```

### 5. Nginx (Reverse Proxy)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Функционал
- **Сайты:** CRUD управление проектами.
- **SEO инструменты:** Анализ плотности ключевых слов, генератор Meta Description.
- **Аналитика:** Импорт CSV из Google Search Console, история позиций.
- **Проверки:** Быстрый аудит URL (Title, H1, Status Code).
- **Фоновые задачи:** Автоматическая проверка статуса сайтов каждые 24 часа.
