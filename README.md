# 🎾 Tennis Slots Checker Telegram Bot

Telegram бот для мониторинга свободных слотов теннисного корта kort40.online с уведомлениями в канал. Развернут на Яндекс Облаке как Cloud Function с триггером по расписанию.

## 🚀 Возможности

- **Автоматический мониторинг** - проверка слотов по расписанию (cron)
- **Уведомления в Telegram** - отправка сообщений о новых доступных слотах
- **Сохранение состояния** - запоминание последних слотов в JSON файле
- **Логирование** - подробные логи работы бота
- **Обработка ошибок** - устойчивость к сбоям сети и API

## 📋 Требования

- Python 3.8+
- Telegram Bot Token
- Telegram канал для уведомлений
- SESSION_ID для авторизации на kort40.online

## 🛠 Настройка

1. **Создайте Telegram бота:**
   - Напишите @BotFather в Telegram
   - Создайте нового бота командой `/newbot`
   - Сохраните полученный токен

2. **Получите SESSION_ID:**
   - Войдите на сайт kort40.online
   - Откройте инструменты разработчика (F12)
   - Перейдите в Application/Storage → Cookies
   - Скопируйте значение `sessionid`

3. **Настройте переменные окружения в .env:**
   ```env
   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   CHANNEL_ID=@your_channel_username
   SESSION_ID=your_session_id_here
   ```

4. **Добавьте бота в канал:**
   - Добавьте бота в ваш канал как администратора
   - Убедитесь, что бот может отправлять сообщения

## ☁️ Развертывание на Яндекс Облаке

Бот развернут как Cloud Function с триггером по расписанию:

- **Функция:** `tennis-slots-checker`
- **Триггер:** Timer (cron выражение)
- **Расписание:** каждые 5-7 минут (рандомный интервал)
- **Хранилище:** `/function/storage/tmp/last_slots.json`

## 📁 Структура проекта

```
tennis-slots-checker-telegram-bot/
├── parser.py                    # Парсер API kort40.online
├── bot.py                       # Основной файл бота (Cloud Function)
├── requirements.txt             # Зависимости Python
├── .env                         # Переменные окружения
├── function/
│   └── storage/
│       └── tmp/
│           └── last_slots.json  # Сохраненные слоты
└── README.md                    # Документация
```

## ⚙️ Переменные окружения

- `BOT_TOKEN` - токен вашего Telegram бота
- `CHANNEL_ID` - ID канала для уведомлений (@channel_name или -1001234567890)
- `SESSION_ID` - ID сессии для авторизации на kort40.online

## 🔧 API kort40.online

Бот использует API `https://kort40.online/api/get-available-times/` для получения информации о слотах.

### Формат ответа API:
```json
{
    "available_hours": [16],
    "reserved": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20],
    "reserved_hours_by_current_user": []
}
```

## 🚨 Устранение неполадок

### Бот не отправляет сообщения:
1. Проверьте, что бот добавлен в канал как администратор
2. Убедитесь, что `CHANNEL_ID` указан правильно
3. Проверьте токен бота

### Ошибки авторизации:
1. Проверьте актуальность `SESSION_ID`
2. Убедитесь, что сессия не истекла. Сессия действует 1 год с момента получения токена.
3. Получите новый SESSION_ID при необходимости

### Бот не находит новые слоты:
1. Проверьте, что файл `last_slots.json` создается
2. Убедитесь, что парсер работает корректно
3. Проверьте логи Cloud Function

## 📝 Локальное тестирование

```python
from parser import TennisSlotsParser

parser = TennisSlotsParser()
slots = parser.get_week_available_slots("2025-01-15")
print(f"Найдено {len(slots)} слотов")
```

## 📄 Лицензия

MIT License
