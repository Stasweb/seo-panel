# SEO Studio (SEO Panel)

Легковесная SEO‑панель для управления небольшим пулом сайтов на маломощном сервере: проверки, задачи, ключевые слова, контент‑план, конкуренты, логирование, интеграции и локальный AI.

## Стек
- Backend: Python 3.10+ (FastAPI)
- DB: SQLite по умолчанию (SQLAlchemy Async)
- Frontend: статические HTML + HTMX + Tailwind CSS + немного JS
- HTTP: HTTPX

## Возможности
- Сайты: список сайтов, выбор активного сайта, настройки, запуск проверок и история.
- Быстрая SEO‑проверка URL: статус, title/h1, индекс/не индекс, подсказки ключевых слов.
- Углублённая SEO‑проверка URL: robots/canonical/meta/структура/ссылки/картинки/слова/скорость + антиспам + подсказки + история и сравнение + создание задач.
- Ключевые слова: добавление/удаление, история, дельты, каннибализация, подсказки из нескольких поисковиков, импорт CSV.
- Ссылки (доноры): импорт CSV, анализ, анкоры, top pages, битые ссылки, подсказки анкоров.
- Купленные ссылки: ручное добавление + мониторинг (проверка статуса/HTTP/метрик) + история и графики изменений.
- Задачи: приоритеты, фильтры, поиск, сортировка, быстрые изменения статуса/приоритета, карточка задачи с привязкой к отчёту.
- Конкуренты: быстрый анализ, импорт ссылок конкурента, доноры/анкоры/DR, donor gap, карточка донора, сохранение конкурентов и история метрик.
- Локальный AI (Ollama): генерация/подсказки/проверки и улучшение рекомендаций (если доступно).
- Логи: просмотр/фильтры/очистка.

## Требования
- Linux/Ubuntu (рекомендуется), также работает локально на macOS/Windows
- Python 3.10+
- (опционально) Node.js — если хотите собирать Tailwind в локальный CSS

## Установка (Ubuntu Server)
### 1) Подготовка системы

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git
```

### 2) Клонирование и окружение

```bash
git clone https://github.com/Stasweb/seo-panel.git
cd seo-panel

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Конфигурация (.env)

```bash
cp .env.example .env
```

Дальше отредактируйте `.env` (минимум: `SECRET_KEY` и `ADMIN_PASSWORD_HASH`).

## Генерация секретов и пароля админа
### SECRET_KEY

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### ADMIN_PASSWORD_HASH (bcrypt)
В проекте пароль хранится как bcrypt‑хеш. Сгенерируйте хеш и вставьте в `.env`.

Вариант 1 (скрипт из репозитория):

```bash
source venv/bin/activate
python3 create_admin.py
```

Вариант 2 (одной командой):

```bash
source venv/bin/activate
python3 -c "import bcrypt, getpass; p=getpass.getpass('Пароль: ').encode(); print(bcrypt.hashpw(p,bcrypt.gensalt()).decode())"
```

Пример `.env`:

```env
SECRET_KEY="случайная_строка"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD_HASH="$2b$12$...."
PORT=8090
DATABASE_URL="sqlite+aiosqlite:///./seo_studio.db"
```

Важно: если `ADMIN_PASSWORD_HASH` пустой, вход под админом не пройдёт.

## CSS (Tailwind)
Сейчас Tailwind подключён через CDN, но также подключается `/static/css/style.css`.

Если на сервере есть Node.js, можно собрать CSS локально:

```bash
npm install
npm run build:css
```

## Запуск
### DEV (для разработки)

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

### PRODUCTION (рекомендуется)
Для серверов 1–2 GB RAM:

```bash
source venv/bin/activate
gunicorn app.main:app \
  -w 2 \
  -k uvicorn.workers.UvicornWorker \
  -b 127.0.0.1:8090 \
  --timeout 60
```

Проверка здоровья:
- `GET /health`

## Автозапуск (systemd)
### 1) Создать сервис

```bash
sudo nano /etc/systemd/system/seo-studio.service
```

Пример юнита:

```ini
[Unit]
Description=SEO Studio (FastAPI)
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/seo-panel
EnvironmentFile=/home/youruser/seo-panel/.env
ExecStart=/home/youruser/seo-panel/venv/bin/gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8090 --timeout 60
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 2) Включить и запустить

```bash
sudo systemctl daemon-reload
sudo systemctl enable seo-studio
sudo systemctl start seo-studio
```

### 3) Проверка и логи

```bash
sudo systemctl status seo-studio
journalctl -u seo-studio -f
```

## Nginx (reverse proxy)
Пример конфигурации:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## База данных и миграции
- По умолчанию используется SQLite: `seo_studio.db` в корне проекта.
- При старте приложения таблицы создаются автоматически, а новые колонки (для SQLite) добавляются автоматически.
- Рекомендация: делайте бэкап файла БД перед обновлением.

## Импорт CSV (подсказки)
### Ссылки конкурента
Импортируйте CSV с колонками (достаточно минимума):
- `source_url` (страница‑донор)
- `target_url` (страница конкурента‑получатель)
- `anchor` (анкор, опционально)
- `type` или `link_type` (dofollow/nofollow, опционально)
- `dr` или `domain_score` (опционально)

### Ссылки вашего сайта
На странице “Ссылки” импортируйте CSV аналогично (используется для пересечений/разрывов доноров).

## Локальный AI (Ollama)
Если Ollama доступен, панель использует его для:
- генерации meta description / ключевых слов
- проверки title
- улучшения рекомендаций по конкуренту
- пояснений к SEO‑аудиту

Настройки:
- `OLLAMA_BASE_URL` (по умолчанию `http://127.0.0.1:11434`)
- `AI_PROVIDER`: `auto | ollama | off`
- `AI_MODEL` (опционально)

## Обновление проекта
```bash
cd /home/youruser/seo-panel
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart seo-studio
```

## Тесты
```bash
venv/bin/python -m unittest discover -s tests -p "test_*.py" -q
```

## Безопасность (минимум)
- Обязательно смените `SECRET_KEY` и задайте `ADMIN_PASSWORD_HASH`.
- Для внешнего доступа используйте Nginx + HTTPS (например, certbot).
- Не храните OAuth секреты в репозитории — только в `.env`.
