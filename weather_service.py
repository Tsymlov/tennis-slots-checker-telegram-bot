import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class WeatherService:
    """Сервис для получения прогноза погоды через Open-Meteo API."""

    # Константы API
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    MAX_FORECAST_DAYS = 16
    REQUEST_TIMEOUT = 10
    CACHE_DURATION = 3600  # 1 час в секундах
    TIMEZONE = "Europe/Moscow"

    # Коды погоды WMO (World Meteorological Organization)
    # Диапазоны кодов для разных типов погоды
    DRIZZLE_CODES = range(51, 58)      # 51-57: морось
    RAIN_CODES = range(61, 68)         # 61-67: дождь
    SNOW_CODES = range(71, 78)         # 71-77: снег
    RAIN_SHOWER_CODES = range(80, 83)  # 80-82: ливни
    SNOW_SHOWER_CODES = [85, 86]       # 85-86: снегопад
    THUNDERSTORM_CODES = range(95, 100)  # 95-99: гроза

    # Эмодзи для кодов погоды
    WEATHER_EMOJI = {
        0: "☀️",      # Ясно
        1: "🌤️",     # Преимущественно ясно
        2: "🌤️",     # Переменная облачность
        3: "☁️",      # Пасмурно
        45: "🌫️",    # Туман
        48: "🌫️",    # Изморозь
        **{code: "🌦️" for code in range(51, 58)},  # Морось
        **{code: "🌧️" for code in range(61, 68)},  # Дождь
        **{code: "🌨️" for code in range(71, 78)},  # Снег
        **{code: "🌦️" for code in range(80, 83)},  # Ливни
        85: "❄️",     # Снегопад
        86: "❄️",     # Снегопад
        95: "⛈️",     # Гроза
        96: "⛈️",     # Гроза с градом
        99: "⛈️",     # Сильная гроза с градом
    }

    def __init__(self, latitude: float, longitude: float):
        """
        Инициализация сервиса погоды.

        Args:
            latitude: Широта местоположения
            longitude: Долгота местоположения
        """
        self.latitude = latitude
        self.longitude = longitude
        self.cache = {}
        self.cache_timestamp = None

    def _is_cache_valid(self) -> bool:
        """Проверяет, актуален ли кэш."""
        if not self.cache_timestamp:
            return False
        elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
        return elapsed < self.CACHE_DURATION

    def get_weather_forecast(self, days: int = 7) -> Optional[Dict]:
        """
        Получает прогноз погоды на указанное количество дней.

        Args:
            days: Количество дней для прогноза (максимум 16)

        Returns:
            Словарь с прогнозом погоды или None при ошибке
        """
        cache_key = f"forecast_{days}"
        if self._is_cache_valid() and cache_key in self.cache:
            logger.info("Используем кэшированный прогноз погоды")
            return self.cache[cache_key]

        try:
            params = {
                'latitude': self.latitude,
                'longitude': self.longitude,
                'hourly': 'temperature_2m,precipitation,precipitation_probability,weathercode',
                'forecast_days': min(days, self.MAX_FORECAST_DAYS),
                'timezone': self.TIMEZONE
            }

            response = requests.get(self.BASE_URL, params=params, timeout=self.REQUEST_TIMEOUT)
            response.raise_for_status()

            data = response.json()

            # Сохраняем в кэш
            self.cache[cache_key] = data
            self.cache_timestamp = datetime.now()

            logger.info(f"Получен прогноз погоды на {days} дней")
            return data

        except Exception as e:
            logger.error(f"Ошибка при получении прогноза погоды: {e}")
            return None

    def get_weather_for_datetime(self, target_datetime: datetime) -> Optional[Dict]:
        """
        Получает прогноз погоды для конкретной даты и времени.

        Args:
            target_datetime: Дата и время для прогноза

        Returns:
            Словарь с температурой, осадками и кодом погоды
        """
        days_ahead = self._calculate_days_ahead(target_datetime)

        if days_ahead is None:
            return None

        forecast = self.get_weather_forecast(days=min(days_ahead + 1, self.MAX_FORECAST_DAYS))
        if not forecast:
            return None

        return self._extract_weather_data(forecast, target_datetime)

    def _calculate_days_ahead(self, target_datetime: datetime) -> Optional[int]:
        """Вычисляет количество дней от сегодня до целевой даты."""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        target_date = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        days_ahead = (target_date - today).days + 1

        if days_ahead > self.MAX_FORECAST_DAYS or days_ahead < 0:
            logger.debug(f"Дата {target_datetime} вне диапазона прогноза")
            return None

        return days_ahead

    def _extract_weather_data(self, forecast: Dict, target_datetime: datetime) -> Optional[Dict]:
        """Извлекает данные о погоде для конкретного времени из прогноза."""
        try:
            hourly = forecast.get('hourly', {})
            times = hourly.get('time', [])
            target_str = target_datetime.strftime('%Y-%m-%dT%H:00')

            if target_str not in times:
                return None

            idx = times.index(target_str)

            # Извлекаем данные
            temperatures = hourly.get('temperature_2m', [])
            precipitations = hourly.get('precipitation', [])
            precipitation_probs = hourly.get('precipitation_probability', [])
            weathercodes = hourly.get('weathercode', [])

            # Проверяем корректность индекса
            if not self._is_valid_index(idx, temperatures, precipitations, weathercodes):
                logger.warning(f"Неполные данные для времени {target_str}")
                return None

            # Формируем результат
            weather_info = self._build_weather_info(
                temperatures[idx],
                precipitations[idx],
                precipitation_probs[idx] if idx < len(precipitation_probs) else None,
                weathercodes[idx]
            )

            logger.debug(f"Погода для {target_datetime}: {weather_info}")
            return weather_info

        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Ошибка при парсинге данных погоды: {e}")
            return None

    def _is_valid_index(self, idx: int, *arrays) -> bool:
        """Проверяет, что индекс находится в пределах всех массивов."""
        return all(idx < len(arr) for arr in arrays)

    def _build_weather_info(self, temp: float, precip: float, precip_prob: Optional[float],
                           weather_code: int) -> Dict:
        """Создает словарь с информацией о погоде."""
        # Безопасно получаем значения с проверкой на None
        temp_value = temp if temp is not None else 0
        precip_value = precip if precip is not None else 0
        code = weather_code if weather_code is not None else 0

        # Округляем вероятность осадков до ближайших 5%
        prob = None
        if precip_prob is not None:
            prob = round(precip_prob / 5) * 5

        return {
            'temperature': round(temp_value),
            'precipitation': round(precip_value, 1),
            'precipitation_probability': prob,
            'weather_code': code,
            'weather_emoji': self._get_weather_emoji(code)
        }

    def _get_weather_emoji(self, code: int) -> str:
        """Возвращает эмодзи для кода погоды."""
        return self.WEATHER_EMOJI.get(code, "🌡️")

    def _get_precipitation_codes(self) -> set:
        """Возвращает все коды погоды с осадками."""
        return set(
            list(self.DRIZZLE_CODES) +
            list(self.RAIN_CODES) +
            list(self.SNOW_CODES) +
            list(self.RAIN_SHOWER_CODES) +
            self.SNOW_SHOWER_CODES +
            list(self.THUNDERSTORM_CODES)
        )

    def _get_snow_codes(self) -> set:
        """Возвращает коды погоды со снегом."""
        return set(list(self.SNOW_CODES) + self.SNOW_SHOWER_CODES)

    def format_weather_info(self, weather: Dict) -> str:
        """
        Форматирует информацию о погоде для отображения.

        Args:
            weather: Словарь с информацией о погоде

        Returns:
            Отформатированная строка
        """
        if not weather:
            return ""

        temp = weather.get('temperature', 0)
        precip_prob = weather.get('precipitation_probability')
        weather_code = weather.get('weather_code', 0)
        emoji = weather.get('weather_emoji', '🌡️')

        # Форматируем температуру с знаком
        temp_str = f"+{temp}" if temp > 0 else str(temp)

        # Добавляем вероятность осадков если есть
        precip_str = self._format_precipitation(weather_code, precip_prob)

        return f"{emoji} {temp_str}°C{precip_str}"

    def _format_precipitation(self, weather_code: int, precip_prob: Optional[int]) -> str:
        """Форматирует строку с вероятностью осадков."""
        precipitation_codes = self._get_precipitation_codes()

        if weather_code not in precipitation_codes:
            return ""

        # Определяем минимальную вероятность если не указана
        if not precip_prob or precip_prob == 0:
            # Лёгкие осадки (морось, небольшой дождь/снег)
            if weather_code in [51, 61, 71]:
                precip_prob = 20
            else:
                precip_prob = 40

        # Выбираем иконку в зависимости от типа осадков
        snow_codes = self._get_snow_codes()
        icon = "❄️" if weather_code in snow_codes else "💧"

        return f", {icon}{precip_prob}%"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Координаты Сквера Волкова, Калуга
    weather_service = WeatherService(latitude=54.511394, longitude=36.226019)

    # Тестируем для завтра в 15:00
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)

    weather = weather_service.get_weather_for_datetime(tomorrow)
    if weather:
        print(f"Погода на {tomorrow.strftime('%Y-%m-%d %H:%M')}:")
        print(f"  Температура: {weather['temperature']}°C")
        print(f"  Осадки: {weather['precipitation']}мм")
        print(f"  Вероятность осадков: {weather.get('precipitation_probability', 'N/A')}%")
        print(f"  Форматированно: {weather_service.format_weather_info(weather)}")
    else:
        print("Не удалось получить прогноз погоды")
