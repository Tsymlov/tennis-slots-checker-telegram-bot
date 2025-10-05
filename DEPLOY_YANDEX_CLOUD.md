# Деплой ботов на Yandex Cloud

## 🤖 Выбор варианта развертывания

В проекте два бота с разными вариантами развертывания:

### 📢 Notification Bot (`bot.py`)
**Рекомендуемый вариант:** Yandex Cloud Functions (serverless)
- ☁️ Без необходимости в постоянно работающей ВМ
- 💰 Платите только за фактическое использование
- 🔧 Автоматическое масштабирование
- ⏰ Запуск по расписанию (timer trigger)

### 💬 Interactive Bot (`interactive_bot.py`)
**Рекомендуемый вариант:** Yandex Compute Cloud (ВМ)
- 🖥️ Постоянно работающий сервер
- 🔄 Режим polling для получения обновлений
- 💾 Стабильная работа без ограничений времени выполнения

---

## 🎯 Вариант 1: Деплой Interactive Bot на Compute Cloud (ВМ)

### 📋 Что нужно подготовить

1. **Аккаунт в Яндекс.Облаке** с платежным аккаунтом
2. **Переменные окружения:**
   - `BOT_TOKEN` - токен бота из @BotFather
   - `SESSION_ID` - session ID для kort40.online
   - `LATITUDE` - широта (опционально, по умолчанию Калуга)
   - `LONGITUDE` - долгота (опционально, по умолчанию Калуга)

## 🚀 Пошаговая инструкция

### Шаг 1: Создание виртуальной машины

1. Зайдите в [консоль Яндекс.Облака](https://console.cloud.yandex.ru/)

2. Создайте новую ВМ:
   - **Название:** `tennis-bot`
   - **Зона:** `ru-central1-a` (или ближайшая к вам)
   - **Платформа:** Intel Ice Lake
   - **vCPU:** 2 (минимум)
   - **RAM:** 1 GB (достаточно для бота)
   - **Диск:** 10 GB HDD
   - **ОС:** Ubuntu 22.04 LTS
   - **Сеть:** Создать новый публичный IP

3. **Примерная стоимость:** ~500₽/месяц

### Шаг 2: Подключение к серверу

```bash
# Подключитесь по SSH
ssh ubuntu@<ВАШ_IP_АДРЕС>

# Или используйте веб-консоль в Яндекс.Облаке
```

### Шаг 3: Загрузка и установка бота

#### Вариант A: Через Git (если есть репозиторий)
```bash
# Клонируйте репозиторий
git clone https://github.com/YOUR_USERNAME/tennis-slots-checker-telegram-bot.git
cd tennis-slots-checker-telegram-bot
```

#### Вариант B: Ручная загрузка файлов
```bash
# Создайте директорию
mkdir ~/tennis-bot
cd ~/tennis-bot

# Загрузите файлы через SCP с вашего компьютера
# На вашем локальном компьютере выполните:
scp interactive_bot.py ubuntu@<IP_АДРЕС>:~/tennis-bot/
scp parser.py ubuntu@<IP_АДРЕС>:~/tennis-bot/
scp weather_service.py ubuntu@<IP_АДРЕС>:~/tennis-bot/
scp requirements.txt ubuntu@<IP_АДРЕС>:~/tennis-bot/

# Или используйте SFTP/FileZilla для загрузки файлов
```

### Шаг 4: Установка зависимостей

```bash
# Обновите систему
sudo apt update && sudo apt upgrade -y

# Установите Python
sudo apt install -y python3 python3-pip python3-venv

# Создайте виртуальное окружение
cd ~/tennis-bot
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### Шаг 5: Настройка переменных окружения

```bash
# Создайте файл .env
nano ~/tennis-bot/.env

# Добавьте ваши данные:
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
SESSION_ID=ваш_session_id_от_kort40
LATITUDE=54.511394
LONGITUDE=36.226019

# Сохраните: Ctrl+X, Y, Enter
```

### Шаг 6: Создание systemd сервиса

```bash
# Создайте файл сервиса
sudo nano /etc/systemd/system/tennis-bot.service

# Вставьте следующее:
[Unit]
Description=Tennis Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tennis-bot
Environment="PATH=/home/ubuntu/tennis-bot/venv/bin"
ExecStart=/home/ubuntu/tennis-bot/venv/bin/python interactive_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Сохраните файл
```

### Шаг 7: Запуск бота

```bash
# Перезагрузите systemd
sudo systemctl daemon-reload

# Включите автозапуск
sudo systemctl enable tennis-bot

# Запустите бота
sudo systemctl start tennis-bot

# Проверьте статус
sudo systemctl status tennis-bot
```

### Шаг 8: Мониторинг

```bash
# Просмотр логов в реальном времени
sudo journalctl -u tennis-bot -f

# Последние 100 строк логов
sudo journalctl -u tennis-bot -n 100

# Логи за последний час
sudo journalctl -u tennis-bot --since "1 hour ago"
```

## 🔧 Управление ботом

### Основные команды

```bash
# Остановить бота
sudo systemctl stop tennis-bot

# Перезапустить бота
sudo systemctl restart tennis-bot

# Посмотреть статус
sudo systemctl status tennis-bot

# Отключить автозапуск
sudo systemctl disable tennis-bot
```

### Обновление кода

```bash
# Остановите бота
sudo systemctl stop tennis-bot

# Обновите файлы
cd ~/tennis-bot
# ... загрузите новые файлы ...

# Перезапустите
sudo systemctl restart tennis-bot
```

## 🔒 Безопасность

1. **Настройте firewall:**
```bash
sudo ufw allow ssh
sudo ufw enable
```

2. **Регулярно обновляйте систему:**
```bash
sudo apt update && sudo apt upgrade -y
```

3. **Настройте резервное копирование** в Яндекс.Облаке

## 💡 Советы

1. **Мониторинг ресурсов:**
```bash
# CPU и память
htop

# Диск
df -h

# Сеть
netstat -tulpn
```

2. **Автоматические обновления:**
```bash
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

3. **Логирование:**
   - Логи хранятся в systemd journal
   - Для долгосрочного хранения настройте ротацию логов

## 🆘 Устранение проблем

### Бот не запускается
```bash
# Проверьте логи
sudo journalctl -u tennis-bot -n 50

# Проверьте права на файлы
ls -la ~/tennis-bot/

# Проверьте .env файл
cat ~/tennis-bot/.env
```

### Ошибка с зависимостями
```bash
cd ~/tennis-bot
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Проблемы с сетью
```bash
# Проверьте доступность Telegram API
curl https://api.telegram.org

# Проверьте доступность kort40.online
curl https://kort40.online
```

## 📊 Мониторинг в Яндекс.Облаке

1. Включите **Cloud Monitoring** для ВМ
2. Настройте алерты на:
   - CPU > 80%
   - RAM > 90%
   - Диск > 80%
3. Подключите уведомления в Telegram

---

## 🎯 Вариант 2: Деплой Notification Bot как Cloud Function

### Особенности serverless развертывания:

**Преимущества:**
- 💰 Бесплатный тариф: 1 млн вызовов и 10 ГБ•ч RAM в месяц
- ⏰ Автоматический запуск по расписанию (timer trigger)
- 🔄 Автоматическое масштабирование
- 🛡️ Встроенная отказоустойчивость

**Ограничения:**
- ⏱️ Максимальное время выполнения: 10 минут
- 💾 Только временное хранилище (используем Object Storage для состояния)

### Шаги развертывания:

1. **Подготовьте код:**
   - Файлы: `bot.py`, `parser.py`, `requirements.txt`
   - Точка входа: функция `main(event, context)` в `bot.py`

2. **Создайте Cloud Function в консоли:**
   - Runtime: Python 3.11
   - Точка входа: `bot.main`
   - Timeout: 60 секунд
   - Memory: 128 MB

3. **Настройте переменные окружения:**
   ```
   BOT_TOKEN=your_bot_token
   CHANNEL_ID=@your_channel
   SESSION_ID=your_session_id
   ```

4. **Создайте Object Storage bucket** для `last_slots.json`:
   - Название: `tennis-bot-storage`
   - Класс хранения: Стандартное
   - Доступ: Частный

5. **Создайте Timer Trigger:**
   - Cron выражение: `*/6 * * * ? *` (каждые 6 минут)
   - Service Account с правами на выполнение функции

6. **Мониторинг:**
   - Логи доступны в Cloud Logging
   - Метрики в Cloud Monitoring
   - Настройте алерты на ошибки выполнения

### Примечание:
Для Notification Bot рекомендуется использовать Cloud Functions, так как бот работает по расписанию и не требует постоянного подключения.