"""
Вспомогательные функции.
"""
import os
from pathlib import Path
import datetime
import time
import sys
import config

def print_colored(text: str, color: str = 'white') -> None:
    """
    Вывод цветного текста в консоль.
    """
    colors = config.COLORS
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def print_streaming(text: str, delay: float = 0.01) -> None:
    """
    Плавный вывод текста символ за символом.
    
    Args:
        text: Текст для вывода
        delay: Задержка между символами в секундах
    """
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)

def print_banner() -> None:
    """Вывод красивого баннера при запуске"""
    banner = """
    🤖 CODE ASSISTANT v3.0 🤖
    ==========================
    Локальный AI-помощник для программирования
    Модель: Llama 3.1 8B
    Поддержка множества файлов и языков
    """
    print_colored(banner, "cyan")

def detect_language_from_extension(file_path: str) -> str:
    """
    Автоматическое определение языка программирования по расширению файла.
    """
    extension = Path(file_path).suffix.lower()
    return config.LANGUAGE_MAP.get(extension, 'Text')

def format_file_size(size: int) -> str:
    """
    Форматирование размера файла в читаемый вид.
    """
    if size < 1024:
        return f"{size} байт"
    elif size < 1024 * 1024:
        return f"{size/1024:.1f} KB"
    else:
        return f"{size/(1024*1024):.1f} MB"

def format_timestamp(timestamp: float) -> str:
    """
    Форматирование временной метки.
    """
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def safe_list_directory(path: str) -> list:
    """
    Безопасное получение списка файлов в директории.
    """
    try:
        return os.listdir(path)
    except (PermissionError, OSError):
        return []

def clear_line():
    """Очистка текущей строки в консоли."""
    print('\r' + ' ' * 100 + '\r', end='', flush=True)

def progress_bar(iteration: int, total: int, length: int = 50) -> str:
    """
    Создание строки прогресс-бара.
    
    Args:
        iteration: Текущая итерация
        total: Общее количество
        length: Длина прогресс-бара в символах
    
    Returns:
        str: Строка прогресс-бара
    """
    percent = (iteration / total) * 100
    filled_length = int(length * iteration // total)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f'|{bar}| {percent:.1f}%'
