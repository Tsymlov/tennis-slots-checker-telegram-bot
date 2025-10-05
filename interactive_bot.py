#!/usr/bin/env python3
import os
import logging
import time
import threading
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from parser import TennisSlotsParser
from weather_service import WeatherService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# Координаты по умолчанию - Сквер Волкова, Калуга
DEFAULT_LATITUDE = 54.511394
DEFAULT_LONGITUDE = 36.226019

# Координаты для прогноза погоды (можно переопределить в .env файле)
LATITUDE = float(os.getenv("LATITUDE", DEFAULT_LATITUDE))
LONGITUDE = float(os.getenv("LONGITUDE", DEFAULT_LONGITUDE))


class TennisBotWithWeather:
    """Telegram бот для мониторинга теннисных кортов с прогнозом погоды."""

    # Константы
    BOOKING_URL = "https://kort40.online"
    COMMAND_TIMEOUT = 5  # Таймаут между одинаковыми командами (сек)
    CACHE_CLEANUP_THRESHOLD = 30  # Очистка старых команд (сек)

    # Периоды для отображения
    PERIODS = {
        7: "неделю",
        14: "две недели",
        30: "месяц"
    }

    # Эмодзи
    EMOJI = {
        'tennis': '🎾',
        'calendar': '📅',
        'clock': '⏰',
        'loading': '⏳',
        'error': '❌',
        'location': '📍',
        'phone': '📱',
        'rocket': '🚀',
        'checkmark': '✅'
    }

    # Названия дней недели
    WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

    def __init__(self, bot_token: str):
        """
        Инициализация бота.

        Args:
            bot_token: Токен Telegram бота
        """
        self.bot_token = bot_token
        self.parser = TennisSlotsParser()
        self.weather_service = WeatherService(LATITUDE, LONGITUDE)
        self.processed_updates = {}
        self.lock = threading.Lock()

    def is_duplicate_command(self, update: Update) -> bool:
        """Проверяет, является ли команда дубликатом."""
        if not update.message:
            return False

        with self.lock:
            current_time = time.time()
            user_id = update.effective_user.id
            message_id = update.message.message_id
            chat_id = update.effective_chat.id
            message_text = update.message.text or ""

            # Проверяем дубликаты
            if self._is_duplicate_by_message_id(chat_id, user_id, message_id):
                return True

            if self._is_duplicate_by_text(user_id, message_text, current_time):
                return True

            # Сохраняем команду и очищаем старые записи
            self._save_command(chat_id, user_id, message_id, message_text, current_time)
            self._cleanup_old_commands(current_time)

            return False

    def _is_duplicate_by_message_id(self, chat_id: int, user_id: int, message_id: int) -> bool:
        """Проверяет точный дубликат по message_id."""
        key = f"{chat_id}_{user_id}_{message_id}"
        if key in self.processed_updates:
            logger.warning(f"Дубликат message_id={message_id} от user_id={user_id}")
            return True
        return False

    def _is_duplicate_by_text(self, user_id: int, message_text: str, current_time: float) -> bool:
        """Проверяет быстрое повторение команды по тексту."""
        text_key = f"{user_id}_{message_text}"
        if text_key in self.processed_updates:
            last_time = self.processed_updates[text_key]
            if current_time - last_time < self.COMMAND_TIMEOUT:
                logger.warning(f"Дубликат команды '{message_text}' от {user_id}")
                return True
        return False

    def _save_command(
        self,
        chat_id: int,
        user_id: int,
        message_id: int,
        message_text: str,
        current_time: float
    ):
        """Сохраняет команду в кэш."""
        key = f"{chat_id}_{user_id}_{message_id}"
        text_key = f"{user_id}_{message_text}"
        self.processed_updates[key] = current_time
        self.processed_updates[text_key] = current_time

    def _cleanup_old_commands(self, current_time: float):
        """Очищает старые записи из кэша команд."""
        self.processed_updates = {
            k: v for k, v in self.processed_updates.items()
            if current_time - v < self.CACHE_CLEANUP_THRESHOLD
        }

    def get_period_name(self, days: int) -> str:
        """Возвращает название периода."""
        return self.PERIODS.get(days, f"{days} дней")

    def get_user_info(self, update: Update) -> str:
        """Возвращает информацию о пользователе для логирования."""
        user = update.effective_user
        return user.username if user.username else str(user.id)

    def _create_booking_button(self) -> InlineKeyboardButton:
        """Создает кнопку бронирования."""
        return InlineKeyboardButton(
            f"{self.EMOJI['tennis']} Забронировать на сайте",
            url=self.BOOKING_URL
        )

    def create_period_keyboard(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру для выбора периода."""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{self.EMOJI['calendar']} Неделя", callback_data="period_7"),
                InlineKeyboardButton(f"{self.EMOJI['calendar']} 2 недели", callback_data="period_14"),
                InlineKeyboardButton(f"{self.EMOJI['calendar']} Месяц", callback_data="period_30")
            ],
            [self._create_booking_button()]
        ])

    def create_booking_keyboard(self) -> InlineKeyboardMarkup:
        """Создает клавиатуру с кнопкой бронирования."""
        return InlineKeyboardMarkup([[self._create_booking_button()]])

    def format_slots_message(
        self,
        slots: List[datetime],
        title: str = "Доступные слоты",
        period_days: int = 7,
        include_weather: bool = True
    ) -> str:
        """
        Форматирует сообщение со слотами и погодой.

        Args:
            slots: Список слотов
            title: Заголовок сообщения
            period_days: Период в днях
            include_weather: Включить прогноз погоды

        Returns:
            Отформатированное сообщение
        """
        if not slots:
            return self._format_empty_slots_message(period_days)

        weather_available = self._check_weather_availability(include_weather, period_days)
        slots_by_date = self._group_slots_by_date(slots)

        return self._build_slots_message(title, slots_by_date, weather_available, len(slots))

    def _format_empty_slots_message(self, period_days: int) -> str:
        """Форматирует сообщение об отсутствии слотов."""
        period_name = self.get_period_name(period_days)
        return f"{self.EMOJI['tennis']} Нет доступных слотов на {period_name}"

    def _check_weather_availability(self, include_weather: bool, period_days: int) -> bool:
        """Проверяет доступность прогноза погоды."""
        if not include_weather:
            return False

        weather_forecast = self.weather_service.get_weather_forecast(
            days=min(period_days, WeatherService.MAX_FORECAST_DAYS)
        )

        if weather_forecast is None:
            logger.warning("Не удалось получить прогноз погоды")
            return False

        return True

    def _build_slots_message(
        self,
        title: str,
        slots_by_date: dict,
        weather_available: bool,
        total_slots: int
    ) -> str:
        """Строит итоговое сообщение со слотами."""
        message = f"{self.EMOJI['tennis']} <b>{title}</b>\n\n"

        for date_str in sorted(slots_by_date.keys()):
            message += self._format_date_slots(
                date_str,
                slots_by_date[date_str],
                weather_available
            )

        message += f"<i>Всего слотов: {total_slots}</i>"
        return message

    def _group_slots_by_date(self, slots: List[datetime]) -> dict:
        """Группирует слоты по датам."""
        slots_by_date = {}
        for slot in slots:
            date_str = slot.strftime('%d.%m.%Y')
            if date_str not in slots_by_date:
                slots_by_date[date_str] = []
            slots_by_date[date_str].append(slot)
        return slots_by_date

    def _format_date_slots(
        self,
        date_str: str,
        slot_times: List[datetime],
        include_weather: bool
    ) -> str:
        """Форматирует слоты для одной даты."""
        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
        weekday = self.WEEKDAYS[date_obj.weekday()]

        message = f"{self.EMOJI['calendar']} <b>{date_str} ({weekday})</b>:\n"

        for slot_datetime in sorted(slot_times):
            time_str = slot_datetime.strftime('%H:%M')
            line = f"  {self.EMOJI['clock']} {time_str}"

            # Добавляем погоду
            if include_weather:
                weather_info = self.weather_service.get_weather_for_datetime(slot_datetime)
                if weather_info:
                    weather_str = self.weather_service.format_weather_info(weather_info)
                    line += f" {weather_str}"

            message += line + "\n"

        return message + "\n"

    async def get_slots_and_format(
        self,
        days: int,
        title: Optional[str] = None
    ) -> str:
        """Получает и форматирует слоты на период."""
        today = datetime.now().strftime('%Y-%m-%d')
        slots = self.parser.get_available_slots_for_period(today, days=days)

        if title is None:
            period_name = self.get_period_name(days)
            title = f"Слоты на {period_name}"

        return self.format_slots_message(slots, title, days, include_weather=True)

    # === Обработчики команд ===

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start."""
        if self.is_duplicate_command(update):
            return

        user_info = self.get_user_info(update)
        logger.info(f"Команда /start от {user_info}")

        # Приветственное сообщение
        welcome_msg = (
            f"{self.EMOJI['tennis']} <b>Привет! Я бот для мониторинга теннисных кортов</b>\n\n"
            f"Показываю свободные слоты на kort40.online с прогнозом погоды."
        )
        await update.message.reply_text(welcome_msg, parse_mode='HTML')

        # Загрузка слотов
        loading_msg = await update.message.reply_text(
            f"{self.EMOJI['loading']} <i>Загружаю текущие слоты на неделю...</i>",
            parse_mode='HTML'
        )

        try:
            # Получаем слоты на неделю
            slots_message = await self.get_slots_and_format(7, "Доступные слоты на неделю")

            # Добавляем footer
            slots_message += "\n\n━━━━━━━━━━━━━━━━━━\n"
            slots_message += f"<b>{self.EMOJI['phone']} Выберите период для просмотра:</b>"

            await loading_msg.delete()
            await update.message.reply_text(
                slots_message,
                parse_mode='HTML',
                reply_markup=self.create_period_keyboard()
            )

        except Exception as e:
            logger.error(f"Ошибка при обработке /start: {e}")
            await self._handle_error(loading_msg, update, "загрузить слоты")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help."""
        if self.is_duplicate_command(update):
            return
        await self.start_command(update, context)

    async def slots_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /slots с выбором периода."""
        if self.is_duplicate_command(update):
            return

        user_info = self.get_user_info(update)
        logger.info(f"Команда /slots от {user_info}")

        await update.message.reply_text(
            f"{self.EMOJI['tennis']} <b>Выберите период для просмотра слотов:</b>\n\n"
            f"<i>Для каждого слота будет показан прогноз погоды.</i>",
            parse_mode='HTML',
            reply_markup=self.create_period_keyboard()
        )

    async def slots_period_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        days: int
    ):
        """Универсальный обработчик для команд с периодом."""
        if self.is_duplicate_command(update):
            return

        user_info = self.get_user_info(update)
        period_name = self.get_period_name(days)
        logger.info(f"Запрос слотов на {period_name} от {user_info}")

        loading_msg = await update.message.reply_text(
            f"{self.EMOJI['loading']} Загружаю слоты на {period_name}...\n"
            f"<i>и прогноз погоды...</i>",
            parse_mode='HTML'
        )

        try:
            message = await self.get_slots_and_format(days, f"Все доступные слоты на {period_name}")

            await loading_msg.delete()
            await update.message.reply_text(
                message,
                parse_mode='HTML',
                reply_markup=self.create_booking_keyboard()
            )

            logger.info(f"Отправлено слотов на {days} дней")

        except Exception as e:
            logger.error(f"Ошибка при обработке команды: {e}")
            await self._handle_error(loading_msg, update, f"получить слоты на {period_name}")

    async def slots_week_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрая команда для недели."""
        await self.slots_period_command(update, context, 7)

    async def slots_two_weeks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрая команда для двух недель."""
        await self.slots_period_command(update, context, 14)

    async def slots_month_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрая команда для месяца."""
        await self.slots_period_command(update, context, 30)

    # === Обработчики callback ===

    async def period_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик выбора периода через inline кнопки."""
        query = update.callback_query
        await query.answer()

        # Извлекаем количество дней
        period_days = int(query.data.split('_')[1])
        period_name = self.get_period_name(period_days)

        # Показываем индикатор загрузки
        await query.edit_message_text(
            f"{self.EMOJI['loading']} Загружаю слоты на {period_name}...\n"
            f"<i>и прогноз погоды...</i>",
            parse_mode='HTML'
        )

        try:
            message = await self.get_slots_and_format(period_days, f"Слоты на {period_name}")

            await query.edit_message_text(
                message,
                parse_mode='HTML',
                reply_markup=self.create_period_keyboard()
            )

            logger.info(f"Отправлено слотов на {period_days} дней через callback")

        except Exception as e:
            logger.error(f"Ошибка при получении слотов: {e}")
            await query.edit_message_text(
                f"{self.EMOJI['error']} Ошибка при получении слотов на {period_name}.\n"
                f"Попробуйте позже.",
                reply_markup=self.create_period_keyboard()
            )

    # === Вспомогательные методы ===

    async def _handle_error(self, loading_msg, update: Update, action: str):
        """Обработка ошибок с удалением loading сообщения."""
        try:
            await loading_msg.delete()
        except:
            pass

        await update.message.reply_text(
            f"{self.EMOJI['error']} <b>Не удалось {action}</b>\n\n"
            f"<i>Попробуйте выбрать период для просмотра:</i>",
            parse_mode='HTML',
            reply_markup=self.create_period_keyboard()
        )


def main():
    """Запуск бота."""
    if not BOT_TOKEN:
        logger.error("Не задан BOT_TOKEN в .env файле")
        return

    logger.info(f"{TennisBotWithWeather.EMOJI['rocket']} Запуск бота с поддержкой прогноза погоды...")
    logger.info(f"{TennisBotWithWeather.EMOJI['location']} Координаты для погоды: {LATITUDE}, {LONGITUDE}")

    # Создаем приложение
    app = Application.builder().token(BOT_TOKEN).build()

    # Создаем экземпляр бота
    bot = TennisBotWithWeather(BOT_TOKEN)

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", bot.start_command))
    app.add_handler(CommandHandler("help", bot.help_command))
    app.add_handler(CommandHandler("slots", bot.slots_command))
    app.add_handler(CommandHandler("slots_week", bot.slots_week_command))
    app.add_handler(CommandHandler("slots_two_weeks", bot.slots_two_weeks_command))
    app.add_handler(CommandHandler("slots_month", bot.slots_month_command))

    # Добавляем обработчики inline кнопок
    app.add_handler(CallbackQueryHandler(bot.period_callback, pattern="^period_"))

    # Запускаем
    logger.info(f"{TennisBotWithWeather.EMOJI['checkmark']} Бот готов. Нажмите Ctrl+C для остановки")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
