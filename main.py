import os
import requests
import json
from pathlib import Path
from typing import Tuple, List, Dict, Any
import datetime

# Константы для безопасности и конфигурации
MAX_FILE_SIZE = 1_000_000  # 1MB
OLLAMA_URL = "http://localhost:11434/api/generate"
SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.html', '.css', '.md', '.txt', '.json', '.xml', '.yaml', '.yml'}
TIMEOUT_SECONDS = 120  # Таймаут для запросов к Ollama

# Расширенный системный промт для код-помощника
SYSTEM_PROMPT = """Ты - опытный AI-помощник для программирования с многолетним опытом. Твоя задача - помогать в написании, анализе, оптимизации и отладке кода.

## Основные принципы:
1. **Качество кода**: Всегда пиши чистый, читаемый и поддерживаемый код
2. **Комментарии**: Добавляй понятные комментарии на русском или английском языках
3. **Best Practices**: Следуй лучшим практикам и стандартам языка/фреймворка
4. **Безопасность**: Учитывай аспекты безопасности при написании кода
5. **Производительность**: Оптимизируй код для лучшей производительности

## Языки комментариев:
- Используй русский язык для комментариев, если пользователь пишет на русском
- Используй английский язык для комментариев, если пользователь пишет на английском
- В международных проектах предпочтительнее английский язык

## Структура комментариев:
- Заголовочные комментарии для функций/классов
- Inline-комментарии для сложных логик
- Комментарии к параметрам и возвращаемым значениям
- TODO/FIXME комментарии для заметок на будущее

## Требования к коду:
- Соблюдай стиль кода (PEP8 для Python, ESLint для JS, etc.)
- Используй осмысленные имена переменных и функций
- Декомпозируй сложные задачи на простые функции
- Обрабатывай ошибки и крайние случаи
- Пиши документацию для публичных API

## Области экспертизы:
- Backend разработка (Python, JavaScript, Java, Go, Rust)
- Frontend разработка (React, Vue, Angular, TypeScript)
- Базы данных (SQL, NoSQL, оптимизация запросов)
- DevOps и инфраструктура (Docker, Kubernetes, CI/CD)
- Алгоритмы и структуры данных
- Тестирование (unit tests, integration tests)
- Code review и рефакторинг

При анализе кода пользователя:
1. Внимательно изучи предоставленный код
2. Найди потенциальные проблемы и улучшения
3. Предложи конкретные исправления с объяснениями
4. Покажи примеры улучшенного кода
5. Объясни почему твое решение лучше

Всегда будь точным, профессиональным и готовым помочь!
"""

class CodeAssistant:
    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.url = OLLAMA_URL
        self.conversation_history: List[Dict[str, str]] = []
        self.current_directory = os.getcwd()
        self.system_prompt = SYSTEM_PROMPT
        self.session = requests.Session()  # Сессия для повторного использования соединения
    
    def _validate_path(self, path: str) -> Tuple[str, bool]:
        """
        Валидация и нормализация пути с защитой от traversal атак.
        
        Args:
            path: Путь для валидации
            
        Returns:
            Tuple[строка, bool]: (нормализованный путь или сообщение об ошибке, успех валидации)
        """
        try:
            if not path or path.strip() == "":
                return "Ошибка: путь не может быть пустым", False
            
            # Нормализация пути
            if not os.path.isabs(path):
                path = os.path.join(self.current_directory, path)
            
            path = os.path.abspath(os.path.expanduser(path))
            
            # Защита от Path Traversal атак
            if not path.startswith(os.path.abspath(self.current_directory)):
                return f"Ошибка: выход за пределы рабочей директории не разрешен. Текущая: {self.current_directory}", False
            
            return path, True
            
        except Exception as e:
            return f"Ошибка валидации пути: {str(e)}", False
    
    def read_file(self, file_path: str) -> str:
        """
        Безопасное чтение содержимого файла с улучшенной обработкой ошибок и поддержкой кодировок.
        
        Args:
            file_path: Путь к файлу для чтения
            
        Returns:
            str: Содержимое файла или сообщение об ошибке
        """
        try:
            validated_path, is_valid = self._validate_path(file_path)
            if not is_valid:
                return validated_path
            
            if not os.path.exists(validated_path):
                return f"Ошибка: файл {validated_path} не найден"
            
            if os.path.isdir(validated_path):
                return f"Ошибка: {validated_path} является директорией, а не файлом"
            
            # Проверка размера файла
            file_size = os.path.getsize(validated_path)
            if file_size > MAX_FILE_SIZE:
                return f"Ошибка: файл слишком большой ({file_size} байт). Лимит: {MAX_FILE_SIZE}"
            
            # Проверка расширения файла (информационно)
            file_ext = Path(validated_path).suffix.lower()
            if file_ext not in SUPPORTED_EXTENSIONS:
                return f"Предупреждение: формат {file_ext} может не поддерживаться полностью"
            
            # Попытка чтения с разными кодировками
            encodings = ['utf-8', 'cp1251', 'iso-8859-1', 'latin-1']
            for encoding in encodings:
                try:
                    with open(validated_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    
                    file_info = self._get_file_stats(validated_path)
                    return f"{file_info}\nСодержимое файла {validated_path} ({encoding}):\n```\n{content}\n```"
                    
                except UnicodeDecodeError:
                    continue
            
            # Если ни одна кодировка не подошла, читаем как бинарный
            try:
                with open(validated_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')
                return f"Файл прочитан с заменой нечитаемых символов:\n```\n{content}\n```"
            except Exception as binary_error:
                return f"Ошибка: не удалось прочитать файл. Детали: {str(binary_error)}"
            
        except PermissionError:
            return f"Ошибка: нет прав доступа к файлу {file_path}"
        except Exception as e:
            return f"Ошибка при чтении файла: {str(e)}"
    
    def _get_file_stats(self, file_path: str) -> str:
        """Получение статистики файла"""
        try:
            stat = os.stat(file_path)
            created = datetime.datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            return (
                f"📊 Информация о файле:\n"
                f"Размер: {stat.st_size} байт\n"
                f"Создан: {created}\n"
                f"Изменен: {modified}\n"
                f"Расширение: {Path(file_path).suffix}"
            )
        except:
            return "📊 Информация о файле: недоступна"
    
    def list_directory(self, path: str = ".") -> str:
        """
        Безопасное отображение содержимого директории с улучшенным форматированием.
        
        Args:
            path: Путь к директории
            
        Returns:
            str: Форматированный список содержимого или сообщение об ошибке
        """
        try:
            validated_path, is_valid = self._validate_path(path)
            if not is_valid:
                return validated_path
            
            if not os.path.exists(validated_path):
                return f"Ошибка: путь {validated_path} не найден"
            
            if not os.path.isdir(validated_path):
                return f"Ошибка: {validated_path} не является директорией"
            
            items = os.listdir(validated_path)
            files = []
            directories = []
            
            for item in items:
                item_path = os.path.join(validated_path, item)
                try:
                    if os.path.isdir(item_path):
                        # Подсчет содержимого директории
                        dir_items = len(os.listdir(item_path))
                        directories.append(f"📁 {item}/ ({dir_items} items)")
                    else:
                        file_ext = Path(item).suffix.lower()
                        icon = "📄" if file_ext in SUPPORTED_EXTENSIONS else "📎"
                        size = os.path.getsize(item_path)
                        size_str = f"{size} bytes" if size < 1024 else f"{size/1024:.1f} KB"
                        files.append(f"{icon} {item} ({size_str})")
                except PermissionError:
                    if os.path.isdir(item_path):
                        directories.append(f"📁 {item}/ (нет доступа)")
                    else:
                        files.append(f"📎 {item} (нет доступа)")
            
            result = f"📂 Содержимое {validated_path}:\n"
            result += f"Всего элементов: {len(items)}\n\n"
            
            if directories:
                result += "📁 Директории:\n" + "\n".join(sorted(directories)) + "\n\n"
            if files:
                result += "📄 Файлы:\n" + "\n".join(sorted(files))
            
            return result
            
        except PermissionError:
            return f"Ошибка: нет прав доступа к директории {path}"
        except Exception as e:
            return f"Ошибка при чтении директории: {str(e)}"
    
    def change_directory(self, new_path: str) -> Tuple[str, bool]:
        """
        Смена текущей рабочей директории с улучшенной валидацией.
        
        Args:
            new_path: Новая целевая директория
            
        Returns:
            Tuple[str, bool]: (сообщение результата, успех операции)
        """
        try:
            validated_path, is_valid = self._validate_path(new_path)
            if not is_valid:
                return validated_path, False
            
            if not os.path.exists(validated_path):
                return f"Ошибка: путь {validated_path} не найден", False
            
            if not os.path.isdir(validated_path):
                return f"Ошибка: {validated_path} не является директорией", False
            
            # Проверка прав доступа
            if not os.access(validated_path, os.R_OK | os.X_OK):
                return f"Ошибка: нет прав доступа к директории {validated_path}", False
            
            old_directory = self.current_directory
            self.current_directory = os.path.abspath(validated_path)
            
            return f"✅ Текущая директория изменена:\n{old_directory} → {self.current_directory}", True
            
        except Exception as e:
            return f"Ошибка при смене директории: {str(e)}", False
    
    def get_file_info(self, file_path: str) -> str:
        """
        Получение детальной информации о файле.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            str: Детальная информация о файле
        """
        try:
            validated_path, is_valid = self._validate_path(file_path)
            if not is_valid:
                return validated_path
            
            if not os.path.exists(validated_path):
                return f"Файл {validated_path} не найден"
            
            stat = os.stat(validated_path)
            created = datetime.datetime.fromtimestamp(stat.st_ctime)
            modified = datetime.datetime.fromtimestamp(stat.st_mtime)
            
            info = [
                f"📊 Детальная информация о {validated_path}",
                f"Размер: {stat.st_size} байт ({stat.st_size / 1024:.2f} KB)",
                f"Создан: {created.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Изменен: {modified.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Является директорией: {'Да' if os.path.isdir(validated_path) else 'Нет'}",
                f"Является файлом: {'Да' if os.path.isfile(validated_path) else 'Нет'}",
                f"Расширение: {Path(validated_path).suffix}",
                f"Абсолютный путь: {os.path.abspath(validated_path)}"
            ]
            
            # Информация о правах доступа
            try:
                mode = stat.st_mode
                info.append(f"Права доступа: {oct(mode)[-3:]}")
            except:
                pass
            
            return "\n".join(info)
            
        except Exception as e:
            return f"Ошибка при получении информации о файле: {str(e)}"
    
    def analyze_code_file(self, file_path: str) -> str:
        """
        Анализ кода файла с автоматическим определением языка.
        
        Args:
            file_path: Путь к файлу для анализа
            
        Returns:
            str: Результат анализа или сообщение об ошибке
        """
        content_result = self.read_file(file_path)
        
        # Проверяем, есть ли ошибка при чтении файла
        if any(keyword in content_result for keyword in ["Ошибка", "Предупреждение", "не удалось"]):
            return content_result
        
        # Извлекаем содержимое файла из ответа
        if "```" in content_result:
            parts = content_result.split("```")
            if len(parts) >= 3:
                content = parts[1].strip()
            else:
                content = content_result
        else:
            content = content_result
        
        # Определяем язык по расширению файла
        file_ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.html': 'HTML',
            '.css': 'CSS',
            '.md': 'Markdown'
        }
        language = language_map.get(file_ext, 'unknown')
        
        analysis_prompt = f"""
        Проанализируй следующий код на {language} и дай детальные рекомендации:

        Файл: {file_path}
        Язык: {language}

        Код для анализа:
        ```{language}
        {content}
        ```

        Проанализируй:
        1. Синтаксические ошибки
        2. Стиль кода и лучшие практики
        3. Потенциальные баги и уязвимости
        4. Возможности для оптимизации
        5. Качество комментариев и документации

        Предложи конкретные улучшения с примерами кода.
        """
        
        return self.send_to_llama(analysis_prompt)
    
    def search_files(self, pattern: str, search_dir: str = ".") -> str:
        """
        Поиск файлов по шаблону.
        
        Args:
            pattern: Шаблон для поиска (например, "*.py")
            search_dir: Директория для поиска
            
        Returns:
            str: Список найденных файлов
        """
        try:
            validated_path, is_valid = self._validate_path(search_dir)
            if not is_valid:
                return validated_path
            
            if not os.path.exists(validated_path):
                return f"Ошибка: путь {validated_path} не найден"
            
            if not os.path.isdir(validated_path):
                return f"Ошибка: {validated_path} не является директорией"
            
            found_files = []
            for root, dirs, files in os.walk(validated_path):
                for file in files:
                    if pattern in file or pattern == "*" or pattern == "*.*":
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, self.current_directory)
                        found_files.append(relative_path)
            
            if not found_files:
                return f"Файлы по шаблону '{pattern}' не найдены в {validated_path}"
            
            result = f"🔍 Найдено {len(found_files)} файлов по шаблону '{pattern}':\n"
            result += "\n".join(sorted(found_files))
            return result
            
        except Exception as e:
            return f"Ошибка при поиске файлов: {str(e)}"
    
    def process_command(self, user_input: str) -> Tuple[str, bool]:
        """
        Обработка специальных команд с улучшенным парсингом.
        
        Args:
            user_input: Ввод пользователя
            
        Returns:
            Tuple[str, bool]: (результат команды, нужно ли отправлять в AI)
        """
        user_input = user_input.strip()
        if not user_input:
            return "Введите команду или вопрос", True
        
        command_parts = user_input.split()
        cmd = command_parts[0].lower()
        
        if cmd == "!read" and len(command_parts) > 1:
            file_path = ' '.join(command_parts[1:])
            return self.read_file(file_path), False
        
        elif cmd == "!ls" or cmd == "!dir":
            path = ' '.join(command_parts[1:]) if len(command_parts) > 1 else "."
            return self.list_directory(path), False
        
        elif cmd == "!cd" and len(command_parts) > 1:
            new_path = ' '.join(command_parts[1:])
            result, success = self.change_directory(new_path)
            return result, False
        
        elif cmd == "!pwd":
            return f"📁 Текущая директория: {self.current_directory}", False
        
        elif cmd == "!info" and len(command_parts) > 1:
            file_path = ' '.join(command_parts[1:])
            return self.get_file_info(file_path), False
        
        elif cmd == "!analyze" and len(command_parts) > 1:
            file_path = ' '.join(command_parts[1:])
            return self.analyze_code_file(file_path), False
        
        elif cmd == "!search" and len(command_parts) > 1:
            pattern = command_parts[1]
            search_dir = ' '.join(command_parts[2:]) if len(command_parts) > 2 else "."
            return self.search_files(pattern, search_dir), False
        
        elif cmd == "!clear":
            self.conversation_history.clear()
            return "✅ История разговора очищена", False
        
        elif cmd == "!history":
            if not self.conversation_history:
                return "История разговора пуста", False
            result = "📖 История разговора:\n"
            for i, chat in enumerate(self.conversation_history[-5:], 1):  # Последние 5 сообщений
                result += f"{i}. Вы: {chat['user'][:50]}...\n"
            return result, False
        
        elif cmd == "!help":
            return self.get_help(), False
        
        return user_input, True
    
    def get_help(self) -> str:
        """Расширенная справка по командам"""
        return """🆘 Доступные команды:

📁 Файловые операции:
!read <file_path> - прочитать файл
!info <file_path> - информация о файле
!analyze <file_path> - проанализировать код файла
!search <pattern> [dir] - поиск файлов по шаблону

📂 Директории:
!ls [path] - список файлов в директории
!dir [path] - альтернатива !ls
!cd <path> - сменить директорию
!pwd - показать текущую директорию

💬 Система:
!clear - очистить историю разговора
!history - показать историю разговора
!help - показать эту справку

🔧 Примеры:
!read src/main.py
!ls src/components/
!cd ~/projects
!analyze utils.py
!search "*.py" src/
!info config.json
"""
    
    def send_to_llama(self, prompt: str) -> str:
        """
        Улучшенная отправка запросов к Ollama с таймаутами и обработкой ошибок.
        
        Args:
            prompt: Промт для отправки
            
        Returns:
            str: Ответ от AI или сообщение об ошибке
        """
        # Добавляем контекст текущей директории и истории
        context = f"Текущая рабочая директория: {self.current_directory}\n"
        
        # Добавляем последние сообщения из истории для контекста
        if self.conversation_history:
            context += "Предыдущие сообщения:\n"
            for chat in self.conversation_history[-3:]:  # Последние 3 сообщения
                context += f"User: {chat['user']}\nAI: {chat['ai'][:100]}...\n"
        
        full_prompt = f"{self.system_prompt}\n\n{context}\n\nЗапрос: {prompt}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 4096,
                "repeat_penalty": 1.1
            }
        }
        
        try:
            response = self.session.post(self.url, json=payload, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            
            result = response.json()
            ai_response = result.get("response", "Ошибка: ответ не получен")
            
            return ai_response
            
        except requests.exceptions.ConnectionError:
            return "❌ Ошибка: Ollama не запущен. Запустите: `ollama serve`"
        except requests.exceptions.Timeout:
            return "⏰ Ошибка: время ожидания ответа истекло. Попробуйте упростить запрос."
        except requests.exceptions.HTTPError as e:
            return f"🌐 Ошибка HTTP: {str(e)}"
        except json.JSONDecodeError:
            return "❌ Ошибка: неверный ответ от сервера Ollama"
        except Exception as e:
            return f"❌ Неизвестная ошибка: {str(e)}"
    
    def chat(self, user_input: str) -> str:
        """
        Основной метод обработки пользовательского ввода.
        
        Args:
            user_input: Ввод пользователя
            
        Returns:
            str: Ответ системы
        """
        # Обрабатываем команды
        processed_input, send_to_ai = self.process_command(user_input)
        
        if not send_to_ai:
            return processed_input
        
        # Отправляем в AI
        response = self.send_to_llama(processed_input)
        
        # Сохраняем в историю (если не было ошибки соединения)
        if not any(error_keyword in response for error_keyword in ["❌", "⏰", "🌐", "Ошибка: Ollama"]):
            self.conversation_history.append({
                "user": user_input,
                "ai": response
            })
        
        return response

def print_colored(text: str, color: str = 'white') -> None:
    """
    Вывод цветного текста в консоль.
    
    Args:
        text: Текст для вывода
        color: Цвет текста
    """
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m'
    }
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def print_banner() -> None:
    """Вывод красивого баннера при запуске"""
    banner = """
    🤖 CODE ASSISTANT v2.0 🤖
    ==========================
    Локальный AI-помощник для программирования
    Модель: Llama 3.1 8B
    """
    print_colored(banner, "cyan")

def main() -> None:
    """Основная функция запуска помощника"""
    print_banner()
    assistant = CodeAssistant()
    
    print_colored("🚀 Инициализация завершена", "green")
    print_colored(f"📁 Текущая директория: {assistant.current_directory}", "blue")
    print_colored("💡 Введите !help для списка команд", "yellow")
    print_colored("-" * 70, "cyan")
    
    try:
        while True:
            try:
                user_input = input("👤 Вы: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'выход', '!exit']:
                    print_colored("👋 До свидания! Хорошего кодинга!", "cyan")
                    break
                
                if not user_input:
                    continue
                
                response = assistant.chat(user_input)
                print_colored("🤖 AI:", "green")
                print(response)
                print_colored("-" * 70, "cyan")
                
            except KeyboardInterrupt:
                print_colored("\n👋 Прервано пользователем. До свидания!", "cyan")
                break
            except Exception as e:
                print_colored(f"❌ Критическая ошибка: {str(e)}", "red")
                print_colored("Попробуйте перезапустить программу.", "yellow")
                
    finally:
        # Завершаем сессию при выходе
        assistant.session.close()
        print_colored("Сессия завершена.", "blue")

if __name__ == "__main__":
    main()
