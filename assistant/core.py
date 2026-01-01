"""
Основной класс CodeAssistant.
"""
import os
import re
from pathlib import Path
from typing import Tuple, List, Dict, Any
from .file_manager import FileManager
from .history_manager import HistoryManager
from .ollama_client import OllamaClient
import config
import utils

class CodeAssistant:
    """Основной класс помощника для программирования."""
    
    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.current_directory = os.getcwd()
        
        # Инициализация компонентов
        self.file_manager = FileManager(self.current_directory)
        self.history_manager = HistoryManager(self.current_directory)
        self.ollama_client = OllamaClient(model)
        
        # Загружаем историю при запуске
        self.history_manager.load_history()
    
    def process_combined_query(self, user_input: str) -> Tuple[str, bool]:
        """
        Обработка комбинированных запросов с чтением файлов.
        """
        # Паттерны для обнаружения файлов в запросе
        file_patterns = [
            r'!read\s+([^\s]+(?:\s+[^\s]+)*)',  # !read file1.py file2.js
            r'прочитай\s+([^\s]+(?:\s+[^\s]+)*)',  # прочитай file1.py file2.js
            r'анализ\s+(?:кода\s+)?в\s+([^\s]+(?:\s+[^\s]+)*)',  # анализ кода в file1.py file2.js
            r'([a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)(?:\s+[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+)*',  # file1.py file2.js
            r'файл[а-я]*\s+([^\s]+(?:\s+[^\s]+)*)',  # файлы file1.py file2.js
            r'\*\.([a-zA-Z0-9]+)',  # *.py *.js
        ]
        
        found_files = []
        clean_query = user_input
        search_pattern = None
        
        # Поиск паттернов типа *.py
        pattern_match = re.search(r'\*\.([a-zA-Z0-9]+)', user_input)
        if pattern_match:
            search_pattern = f"*.{pattern_match.group(1)}"
            found_files = self.file_manager.find_files_by_pattern(search_pattern)
            clean_query = clean_query.replace(pattern_match.group(0), '').strip()
        
        # Поиск конкретных файлов
        if not found_files:
            for pattern in file_patterns:
                matches = re.finditer(pattern, user_input, re.IGNORECASE)
                for match in matches:
                    file_candidates = match.group(1).split()
                    
                    for file_candidate in file_candidates:
                        # Проверяем, существует ли файл
                        validated_path, is_valid = self.file_manager.validate_path(file_candidate)
                        if is_valid and os.path.exists(validated_path) and os.path.isfile(validated_path):
                            found_files.append(validated_path)
                            # Убираем имя файла из запроса чтобы не мешало AI
                            clean_query = clean_query.replace(file_candidate, '').strip()
        
        # Удаляем лишние пробелы
        clean_query = re.sub(r'\s+', ' ', clean_query).strip()
        
        if found_files:
            if search_pattern:
                info_msg = f"🔍 Найдено файлов по шаблону '{search_pattern}': {len(found_files)}\n\n"
            else:
                info_msg = f"📚 Обрабатываю {len(found_files)} файлов:\n" + "\n".join([f"  • {os.path.basename(f)}" for f in found_files]) + "\n\n"
            
            # Читаем все найденные файлы
            files_content = self.file_manager.read_multiple_files(found_files)
            
            # Комбинируем содержимое файлов с запросом пользователя
            combined_prompt = f"{info_msg}{files_content}\n\n💬 Запрос пользователя: {clean_query}"
            return combined_prompt, True
        
        return user_input, True
    
    def analyze_code_file(self, file_path: str) -> str:
        """
        Анализ кода файла с автоматическим определением языка.
        """
        content_result = self.file_manager.read_file(file_path)
        
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
        language = utils.detect_language_from_extension(file_path)
        
        analysis_prompt = f"""
        Проанализируй следующий код на {language} и дай детальные рекомендации:

        Файл: {file_path}
        Язык: {language}

        Код для анализа:
        ```{language.split()[0].lower()}
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
        
        return self.ollama_client.send_request(analysis_prompt, self.history_manager.conversation_history)
    
    def analyze_multiple_files(self, file_paths: List[str]) -> str:
        """
        Анализ нескольких файлов одновременно.
        """
        if len(file_paths) > config.MAX_FILES_PER_QUERY:
            return f"❌ Слишком много файлов для анализа. Максимум: {config.MAX_FILES_PER_QUERY}"
        
        files_content = self.file_manager.read_multiple_files(file_paths)
        
        analysis_prompt = f"""
        Проанализируй следующие файлы и дай комплексные рекомендации:

        {files_content}

        Проанализируй:
        1. Связи между файлами
        2. Общую архитектуру проекта
        3. Стиль кода и консистентность
        4. Потенциальные проблемы интеграции
        5. Возможности для рефакторинга

        Дай общие рекомендации по проекту и конкретные советы для каждого файла.
        """
        
        return self.ollama_client.send_request(analysis_prompt, self.history_manager.conversation_history)
    
    def search_files(self, pattern: str, search_dir: str = ".") -> str:
        """
        Поиск файлов по шаблону.
        """
        try:
            validated_path, is_valid = self.file_manager.validate_path(search_dir)
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
            
            # Группируем по языкам
            languages = {}
            for file_path in found_files:
                language = utils.detect_language_from_extension(file_path)
                if language not in languages:
                    languages[language] = []
                languages[language].append(file_path)
            
            result = f"🔍 Найдено {len(found_files)} файлов по шаблону '{pattern}':\n"
            for language, files in languages.items():
                result += f"\n{language} ({len(files)} файлов):\n"
                result += "\n".join([f"  • {file}" for file in sorted(files)])
            
            return result
            
        except Exception as e:
            return f"Ошибка при поиске файлов: {str(e)}"
    
    def change_directory(self, new_path: str) -> Tuple[str, bool]:
        """
        Смена текущей рабочей директории.
        """
        try:
            validated_path, is_valid = self.file_manager.validate_path(new_path)
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
            
            # Обновляем file_manager с новой директорией
            self.file_manager = FileManager(self.current_directory)
            
            return f"✅ Текущая директория изменена:\n{old_directory} → {self.current_directory}", True
            
        except Exception as e:
            return f"Ошибка при смене директории: {str(e)}", False
    
    def process_command(self, user_input: str) -> Tuple[str, bool]:
        """
        Обработка команд пользователя.
        """
        user_input = user_input.strip()
        if not user_input:
            return "Введите команду или вопрос", True
        
        command_parts = user_input.split()
        cmd = command_parts[0].lower()
        
        # Обработка специальных команд
        if cmd == "!read" and len(command_parts) > 1:
            file_paths = command_parts[1:]
            if len(file_paths) == 1:
                return self.file_manager.read_file(file_paths[0]), False
            else:
                return self.file_manager.read_multiple_files(file_paths), False
        
        elif cmd == "!ls" or cmd == "!dir":
            path = ' '.join(command_parts[1:]) if len(command_parts) > 1 else "."
            return self.file_manager.list_directory(path), False
        
        elif cmd == "!cd" and len(command_parts) > 1:
            new_path = ' '.join(command_parts[1:])
            result, success = self.change_directory(new_path)
            return result, False
        
        elif cmd == "!pwd":
            return f"📁 Текущая директория: {self.current_directory}", False
        
        elif cmd == "!info" and len(command_parts) > 1:
            file_path = ' '.join(command_parts[1:])
            return self.file_manager.get_file_info(file_path), False
        
        elif cmd == "!analyze" and len(command_parts) > 1:
            file_paths = command_parts[1:]
            if len(file_paths) == 1:
                return self.analyze_code_file(file_paths[0]), False
            else:
                return self.analyze_multiple_files(file_paths), False
        
        elif cmd == "!search" and len(command_parts) > 1:
            pattern = command_parts[1]
            search_dir = ' '.join(command_parts[2:]) if len(command_parts) > 2 else "."
            return self.search_files(pattern, search_dir), False
        
        elif cmd == "!clear":
            confirm = len(command_parts) > 1 and command_parts[1].lower() == "confirm"
            return self.history_manager.clear_history(confirm), False
        
        elif cmd == "!history":
            if len(command_parts) > 1 and command_parts[1].lower() == "stats":
                return self.history_manager.show_history_stats(), False
            return self.history_manager.show_recent_history(), False
        
        elif cmd == "!export" and len(command_parts) > 1:
            file_path = ' '.join(command_parts[1:])
            return self.history_manager.export_history(file_path), False
        
        elif cmd == "!import" and len(command_parts) > 1:
            file_path = ' '.join(command_parts[1:])
            return self.history_manager.import_history(file_path), False
        
        elif cmd == "!save":
            success = self.history_manager.save_history()
            return "✅ История сохранена" if success else "❌ Ошибка сохранения истории", False
        
        elif cmd == "!stream":
            if len(command_parts) > 1:
                mode = command_parts[1].lower()
                if mode in ['on', 'true', '1', 'enable']:
                    config.STREAMING_ENABLED = True
                    return "✅ Потоковый вывод включен", False
                elif mode in ['off', 'false', '0', 'disable']:
                    config.STREAMING_ENABLED = False
                    return "✅ Потоковый вывод выключен", False
            return f"📊 Текущий режим: {'включен' if config.STREAMING_ENABLED else 'выключен'}\nИспользуйте: !stream on/off", False
        
        elif cmd == "!speed":
            if len(command_parts) > 1:
                try:
                    speed = float(command_parts[1])
                    if 0.001 <= speed <= 0.1:
                        config.STREAM_DELAY = speed
                        return f"✅ Скорость вывода установлена: {speed} сек/символ", False
                    else:
                        return "❌ Скорость должна быть между 0.001 и 0.1 секунд", False
                except ValueError:
                    return "❌ Введите число для скорости (например: 0.02)", False
            return f"📊 Текущая скорость: {config.STREAM_DELAY} сек/символ\nИспользуйте: !speed <значение>", False
        
        elif cmd == "!help":
            return self.get_help(), False
        
        # Комбинированные запросы с несколькими файлами
        else:
            return self.process_combined_query(user_input)
    
    def get_help(self) -> str:
        """Справка по командам."""
        return """🆘 Доступные команды и форматы:

📁 Файловые операции:
!read <file1> [file2] ... - прочитать один или несколько файлов
!analyze <file1> [file2] ... - проанализировать один или несколько файлов
!info <file> - информация о файле

💬 Комбинированные запросы:
прочитай <file1> <file2> и <запрос> - прочитать несколько файлов и выполнить запрос
анализ кода в <file1> <file2> - прочитать и проанализировать несколько файлов
*.py <запрос> - найти все Python файлы и выполнить запрос

🔍 Поиск и анализ:
!search <pattern> [dir] - поиск файлов по шаблону
!ls [path] - список файлов в директории
!cd <path> - сменить директорию

💾 История сообщений:
!history - показать последние сообщения
!history stats - статистика истории
!save - сохранить историю в файл
!export [file_path] - экспорт истории в файл
!import <file_path> - импорт истории из файла
!clear confirm - очистить историю (с подтверждением)

🎯 Настройки streaming:
!stream on/off - включить/выключить потоковый вывод
!speed <значение> - установить скорость вывода (сек/символ)

🔧 Примеры:
!read main.py utils.py
!analyze service.js model.py
прочитай config.json package.json и объясни настройки
*.js: найди общие паттерны
!stream on  # Включить потоковый вывод
!speed 0.02 # Установить скорость
"""
    
    def chat(self, user_input: str) -> str:
        """
        Основной метод обработки пользовательского ввода.
        """
        # Обрабатываем команды
        processed_input, send_to_ai = self.process_command(user_input)
        
        if not send_to_ai:
            return processed_input
        
        # Отправляем в AI
        response = self.ollama_client.send_request(processed_input, self.history_manager.conversation_history)
        
        # Сохраняем в историю (если не было ошибки соединения)
        if not any(error_keyword in response for error_keyword in ["❌", "⏰", "🌐", "Ошибка: Ollama"]):
            self.history_manager.add_message(user_input, response)
        
        return response
    
    def close(self):
        """Закрытие ресурсов."""
        self.ollama_client.close()
        self.history_manager.save_history()
