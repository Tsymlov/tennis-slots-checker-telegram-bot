import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import List, Set
import logging
from pathlib import Path

import requests
from telegram import Bot
from telegram.error import TelegramError

from parser import TennisSlotsParser

MIN_INTERVAL = 300  # 5 минут
MAX_INTERVAL = 420  # 7 минут

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TennisSlotsBot:
    def __init__(self, bot_token: str, channel_id: str):
        """
        Инициализация бота для мониторинга теннисных слотов.
        
        Args:
            bot_token: Токен Telegram бота
            channel_id: ID канала для отправки уведомлений
        """
        self.bot = Bot(token=bot_token)
        self.channel_id = channel_id
        self.parser = TennisSlotsParser()
        self.last_slots_file = Path("/function/storage/tmp/last_slots.json")
        self.last_slots: Set[str] = set()
        
        # Загружаем последние слоты при инициализации
        self.load_last_slots()

    def load_last_slots(self):
        """Загружает последние сохраненные слоты из файла."""
        try:
            if self.last_slots_file.exists():
                with open(self.last_slots_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_slots = set(data.get('slots', []))
                    logger.info(f"Загружено {len(self.last_slots)} последних слотов")
            else:
                logger.info("Файл с последними слотами не найден, начинаем с пустого списка")
        except Exception as e:
            logger.error(f"Ошибка при загрузке последних слотов: {e}")
            self.last_slots = set()

    def save_last_slots(self, slots: List[datetime]):
        """Сохраняет текущие слоты в файл."""
        try:
            slots_str = [slot.strftime('%Y-%m-%d %H:%M') for slot in slots]
            data = {
                'slots': slots_str,
                'last_update': datetime.now().isoformat()
            }
            
            with open(self.last_slots_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.last_slots = set(slots_str)
            logger.info(f"Сохранено {len(slots_str)} слотов")
        except Exception as e:
            logger.error(f"Ошибка при сохранении слотов: {e}")

    def get_current_week_slots(self) -> List[datetime]:
        """Получает слоты на текущую неделю."""
        today = datetime.now().strftime('%Y-%m-%d')
        return self.parser.get_week_available_slots(today)

    def find_new_slots(self, current_slots: List[datetime]) -> List[datetime]:
        """Находит новые слоты по сравнению с последними сохраненными."""
        current_slots_str = {slot.strftime('%Y-%m-%d %H:%M') for slot in current_slots}
        new_slots_str = current_slots_str - self.last_slots
        
        # Конвертируем обратно в datetime объекты
        new_slots = []
        for slot_str in new_slots_str:
            try:
                slot_dt = datetime.strptime(slot_str, '%Y-%m-%d %H:%M')
                new_slots.append(slot_dt)
            except ValueError as e:
                logger.error(f"Ошибка при парсинге даты {slot_str}: {e}")
        
        return sorted(new_slots)

    def format_slots_message(self, slots: List[datetime]) -> str:
        """Форматирует сообщение со слотами для отправки в канал."""
        if not slots:
            return "🎾 Новых доступных слотов не найдено"
        
        message = f"🎾 <b>Новые доступные слоты!</b>\n\n"
        
        # Группируем слоты по датам
        slots_by_date = {}
        for slot in slots:
            date_str = slot.strftime('%Y-%m-%d')
            time_str = slot.strftime('%H:%M')
            
            if date_str not in slots_by_date:
                slots_by_date[date_str] = []
            slots_by_date[date_str].append(time_str)
        
        # Формируем сообщение
        for date_str in sorted(slots_by_date.keys()):
            times = sorted(slots_by_date[date_str])
            message += f"📅 <b>{date_str}</b>:\n"
            for time_str in times:
                message += f"  ⏰ {time_str}\n"
            message += "\n"
        
        message += f"<i>Всего новых слотов: {len(slots)}</i>"
        return message

    async def send_notification(self, message: str):
        """Отправляет уведомление в Telegram канал."""
        try:
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info("Уведомление отправлено в канал")
        except TelegramError as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке: {e}")

    async def check_and_notify(self):
        """Проверяет новые слоты и отправляет уведомления."""
        try:
            logger.info("Начинаем проверку слотов...")
            
            # Получаем текущие слоты
            current_slots = self.get_current_week_slots()
            logger.info(f"Найдено {len(current_slots)} слотов на текущую неделю")
            
            # Ищем новые слоты
            new_slots = self.find_new_slots(current_slots)
            
            if new_slots:
                logger.info(f"Найдено {len(new_slots)} новых слотов!")
                
                # Формируем и отправляем сообщение
                message = self.format_slots_message(new_slots)
                await self.send_notification(message)
                
                # Сохраняем текущие слоты как последние
                self.save_last_slots(current_slots)
            else:
                logger.info("Новых слотов не найдено")
                # Все равно сохраняем текущие слоты (на случай если что-то изменилось)
                self.save_last_slots(current_slots)
                
        except Exception as e:
            logger.error(f"Ошибка при проверке слотов: {e}")

    async def run_monitoring(self):
        """Запускает мониторинг с рандомным интервалом."""
        logger.info("🚀 Запуск мониторинга теннисных слотов")
        logger.info(f"📱 Канал для уведомлений: {self.channel_id}")
        
        # Первая проверка сразу
        await self.check_and_notify()
        
        while True:
            try:
                # Рандомный интервал от 5 до 7 минут (300-420 секунд)
                interval = random.randint(MIN_INTERVAL, MAX_INTERVAL)
                logger.info(f"⏰ Следующая проверка через {interval // 60} минут {interval % 60} секунд")
                
                await asyncio.sleep(interval)
                await self.check_and_notify()
                
            except KeyboardInterrupt:
                logger.info("🛑 Мониторинг остановлен пользователем")
                break
            except Exception as e:
                logger.error(f"Критическая ошибка в мониторинге: {e}")
                logger.info("⏳ Ждем 60 секунд перед повторной попыткой...")
                await asyncio.sleep(60)


async def main(event, context):
    """Основная функция для запуска бота."""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    CHANNEL_ID = os.getenv("CHANNEL_ID")
    
    
    # Создаем и запускаем бота
    bot = TennisSlotsBot(BOT_TOKEN, CHANNEL_ID)
    await bot.check_and_notify()


if __name__ == "__main__":
    asyncio.run(main(None, None))
