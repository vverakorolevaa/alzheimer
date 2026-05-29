# Развёртывание на сервере

Инструкция, как выложить веб-приложение на свой сервер. Локально оно запускается так:
`streamlit run app.py` → http://localhost:8501.

## Что нужно на сервере

- Linux (Ubuntu/Debian), Python 3.10+;
- открытый порт (например, 8501) или nginx как обратный прокси на 80/443;
- ~1 ГБ свободного места (данные + модель).

## Вариант 1. Быстрый запуск (venv)

```bash
git clone <адрес-репозитория> ad-blood-stage && cd ad-blood-stage
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# подготовить данные и модель (один раз)
python cli.py download
python cli.py panel

# запустить сервер (доступен снаружи)
streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
```

Откроется по адресу `http://IP-сервера:8501`.

## Вариант 2. Как сервис (systemd) — чтобы работало после перезагрузки

Файл `/etc/systemd/system/adblood.service`:

```ini
[Unit]
Description=AD Blood Stage (Streamlit)
After=network.target

[Service]
User=ВАШ_ПОЛЬЗОВАТЕЛЬ
WorkingDirectory=/путь/к/ad-blood-stage
ExecStart=/путь/к/ad-blood-stage/venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now adblood
sudo systemctl status adblood     # проверить, что работает
```

## Вариант 3. Nginx как обратный прокси (красивый адрес + HTTPS)

`/etc/nginx/sites-available/adblood`:

```nginx
server {
    listen 80;
    server_name ваш-домен.ru;
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;          # WebSocket — нужен Streamlit
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/adblood /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
# HTTPS бесплатно:
sudo certbot --nginx -d ваш-домен.ru
```

## Вариант 4. Docker

`Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python cli.py download && python cli.py panel
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501", "--server.headless", "true"]
```

```bash
docker build -t ad-blood-stage .
docker run -p 8501:8501 ad-blood-stage
```

## Бесплатный хостинг (без своего сервера)

**Streamlit Community Cloud** (share.streamlit.io): подключить GitHub-репозиторий, указать `app.py`. Внимание: нужен публичный репозиторий, а модель собирается командой `python cli.py panel` — добавьте её в шаги сборки или закоммитьте готовый `results/panel_model.pkl`.

## Частые проблемы

- **Не открывается снаружи** → проверьте `--server.address 0.0.0.0` и что порт открыт в фаерволе (`sudo ufw allow 8501`).
- **Интерфейс «висит» / не обновляется** → в nginx обязательны заголовки `Upgrade`/`Connection` (WebSocket).
- **«Модель не найдена»** → сначала `python cli.py download` и `python cli.py panel`.
- **Не качаются данные из РФ** → запасной источник refine.bio (см. `download_data.py`), либо положить файлы в `data/` вручную.
