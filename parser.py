import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
import os
from dotenv import load_dotenv
# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



load_dotenv()
SESSION_ID = os.getenv("SESSION_ID")

class TennisSlotsParser:
    def __init__(self):
        self.base_url = "https://kort40.online/api/get-available-times/"
        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'ru,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Cookie': f'csrftoken=k02j4ggNvdjUKOwPf6M48HGaKW1cDTsR; sessionid={SESSION_ID}',
            'Host': 'kort40.online',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 YaBrowser/25.8.0.0 Safari/537.36',
            'dnt': '1',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "YaBrowser";v="25.8", "Yowser";v="2.5"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-gpc': '1'
        }

    def get_dates_for_period(self, start_date: str, days: int = 7) -> List[str]:
        """
        Получает список дат на неделю, начиная с указанной даты.
        
        Args:
            start_date: Дата в формате YYYY-MM-DD
            
        Returns:
            Список дат в формате YYYY-MM-DD
        """
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            dates = []
            for i in range(days):
                date = start + timedelta(days=i)
                dates.append(date.strftime('%Y-%m-%d'))
            return dates
        except ValueError as e:
            logger.error(f"Ошибка в формате даты: {e}")
            return []

    def get_available_slots_for_date(self, date: str) -> List[int]:
        """
        Получает доступные слоты для конкретной даты.
        
        Args:
            date: Дата в формате YYYY-MM-DD
            
        Returns:
            Список доступных часов
        """
        url = f"{self.base_url}?date={date}"
        
        try:
            logger.info(f"Запрашиваем слоты для даты: {date}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            available_hours = data.get('available_hours', [])
            logger.info(f"Найдено {len(available_hours)} доступных слотов для {date}")
            return list(map(lambda x: int(x) + 3, available_hours))  # +3 часа для Московского времени
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе к API для даты {date}: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при парсинге JSON для даты {date}: {e}")
            return []
        except Exception as e:
            logger.error(f"Неожиданная ошибка для даты {date}: {e}")
            return []

    def get_available_slots_for_period(self, start_date: str, days: int = 7) -> List[datetime]:
        """
        Получает все доступные слоты на указанный период.

        Args:
            start_date: Дата начала периода в формате YYYY-MM-DD
            days: Количество дней для проверки (по умолчанию 7)

        Returns:
            Список datetime объектов с доступными слотами
        """
        dates = self.get_dates_for_period(start_date, days)
        if not dates:
            logger.error("Не удалось получить список дат")
            return []
        
        all_available_slots = []
        
        for date in dates:
            available_hours = self.get_available_slots_for_date(date)
            
            for hour in available_hours:
                # Создаем datetime объект для каждого доступного часа
                slot_datetime = datetime.strptime(f"{date} {hour:02d}:00:00", '%Y-%m-%d %H:%M:%S')
                all_available_slots.append(slot_datetime)
        
        # Сортируем слоты по времени
        all_available_slots.sort()
        
        logger.info(f"Всего найдено {len(all_available_slots)} доступных слотов на {days} дней")
        return all_available_slots


def main():
    """
    Основная функция для тестирования парсера.
    """
    parser = TennisSlotsParser()
    
    # Пример использования - получаем слоты на неделю с 15 сентября 2025
    start_date = "2025-09-15"
    
    print("🎾 Парсер свободных слотов теннисного корта")
    print("=" * 50)
    
    # Тестируем разные периоды
    print("\n📅 Слоты на неделю:")
    week_slots = parser.get_available_slots_for_period(start_date, days=7)
    print(f"Найдено: {len(week_slots)} слотов")

    print("\n📅 Слоты на две недели:")
    two_weeks_slots = parser.get_available_slots_for_period(start_date, days=14)
    print(f"Найдено: {len(two_weeks_slots)} слотов")

    print("\n📅 Слоты на месяц:")
    month_slots = parser.get_available_slots_for_period(start_date, days=30)
    print(f"Найдено: {len(month_slots)} слотов")


if __name__ == "__main__":
    main()
