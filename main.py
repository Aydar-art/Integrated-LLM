import os
import requests
import json
from pathlib import Path

class CodeAssistant:
    def __init__(self, model="llama3.1:8b"):
        self.model = model
        self.url = "http://localhost:11434/api/generate"
        self.conversation_history = []
        self.current_directory = os.getcwd()
    
    def read_file(self, file_path):
        """Чтение содержимого файла"""
        try:
            # Если путь относительный, делаем его абсолютным относительно текущей директории
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.current_directory, file_path)
            
            if not os.path.exists(file_path):
                return f"Ошибка: файл {file_path} не найден"
            
            if os.path.isdir(file_path):
                return f"Ошибка: {file_path} является директорией, а не файлом"
            
            # Проверяем размер файла (не читаем слишком большие файлы)
            file_size = os.path.getsize(file_path)
            if file_size > 1_000_000:  # 1MB лимит
                return f"Ошибка: файл слишком большой ({file_size} байт). Лимит: 1MB"
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            return f"Содержимое файла {file_path}:\n```\n{content}\n```"
            
        except PermissionError:
            return f"Ошибка: нет прав доступа к файлу {file_path}"
        except Exception as e:
            return f"Ошибка при чтении файла: {str(e)}"
    
    def list_directory(self, path="."):
        """Показать содержимое директории"""
        try:
            if not os.path.isabs(path):
                path = os.path.join(self.current_directory, path)
            
            if not os.path.exists(path):
                return f"Ошибка: путь {path} не найден"
            
            items = os.listdir(path)
            files = []
            directories = []
            
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    directories.append(item + "/")
                else:
                    files.append(item)
            
            result = f"Содержимое {path}:\n"
            if directories:
                result += "📁 Директории:\n" + "\n".join(directories) + "\n"
            if files:
                result += "📄 Файлы:\n" + "\n".join(files)
                
            return result
            
        except Exception as e:
            return f"Ошибка при чтении директории: {str(e)}"
    
    def change_directory(self, new_path):
        """Сменить текущую директорию"""
        try:
            if not os.path.isabs(new_path):
                new_path = os.path.join(self.current_directory, new_path)
            
            if not os.path.exists(new_path):
                return f"Ошибка: путь {new_path} не найден", False
            
            if not os.path.isdir(new_path):
                return f"Ошибка: {new_path} не является директорией", False
            
            self.current_directory = os.path.abspath(new_path)
            return f"Текущая директория изменена на: {self.current_directory}", True
            
        except Exception as e:
            return f"Ошибка при смене директории: {str(e)}", False
    
    def get_file_info(self, file_path):
        """Получить информацию о файле"""
        try:
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.current_directory, file_path)
            
            if not os.path.exists(file_path):
                return f"Файл {file_path} не найден"
            
            stat = os.stat(file_path)
            return (
                f"Информация о {file_path}:\n"
                f"Размер: {stat.st_size} байт\n"
                f"Создан: {stat.st_ctime}\n"
                f"Изменен: {stat.st_mtime}\n"
                f"Является директорией: {os.path.isdir(file_path)}"
            )
            
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def process_command(self, user_input):
        """Обработка специальных команд"""
        if user_input.startswith("!read "):
            file_path = user_input[6:].strip()
            return self.read_file(file_path), False
        
        elif user_input.startswith("!ls") or user_input.startswith("!dir"):
            path = user_input[3:].strip() if len(user_input) > 3 else "."
            return self.list_directory(path), False
        
        elif user_input.startswith("!cd "):
            new_path = user_input[4:].strip()
            result, success = self.change_directory(new_path)
            return result, False
        
        elif user_input.startswith("!pwd"):
            return f"Текущая директория: {self.current_directory}", False
        
        elif user_input.startswith("!info "):
            file_path = user_input[6:].strip()
            return self.get_file_info(file_path), False
        
        elif user_input.startswith("!help"):
            return self.get_help(), False
        
        return user_input, True
    
    def get_help(self):
        """Справка по командам"""
        return """Доступные команды:
!read <file_path> - прочитать файл
!ls [path] - список файлов в директории
!cd <path> - сменить директорию
!pwd - показать текущую директорию
!info <file_path> - информация о файле
!help - показать эту справку

Примеры:
!read main.py
!ls src/
!cd projects
!info script.js
"""
    
    def send_to_llama(self, prompt):
        """Отправка запроса к Llama"""
        # Добавляем контекст для код-помощника
        system_prompt = """Ты - опытный помощник по программированию. Ты помогаешь с написанием, анализом и исправлением кода.
        Отвечай подробно и профессионально. Если тебе предоставили код файла, анализируй его и давай конкретные рекомендации.
        
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


        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Более детерминированный для кода
                "top_p": 0.9,
                "num_predict": 2048,  # Больше токенов для кода
                "repeat_penalty": 1.1
            }
        }
        
        try:
            response = requests.post(self.url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "Ошибка: ответ не получен")
            
        except requests.exceptions.ConnectionError:
            return "Ошибка: Ollama не запущен. Запустите: ollama serve"
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def chat(self, user_input):
        """Основной метод чата"""
        # Обрабатываем команды
        processed_input, send_to_ai = self.process_command(user_input)
        
        if not send_to_ai:
            return processed_input
        
        # Отправляем в AI
        response = self.send_to_llama(processed_input)
        
        # Сохраняем в историю
        self.conversation_history.append({
            "user": user_input,
            "ai": response
        })
        
        return response

# Функция для красивого вывода
def print_colored(text, color='white'):
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

# Основной цикл
def main():
    assistant = CodeAssistant()
    
    print_colored("🤖 Code Assistant с Llama 3.1:8b", "cyan")
    print_colored("Введите !help для списка команд", "yellow")
    print_colored("Текущая директория: " + assistant.current_directory, "green")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("👤 Вы: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'выход']:
                print_colored("До свидания!", "cyan")
                break
            
            if not user_input:
                continue
            
            response = assistant.chat(user_input)
            print_colored("🤖 AI:", "blue")
            print(response)
            print("-" * 60)
            
        except KeyboardInterrupt:
            print_colored("\nДо свидания!", "cyan")
            break
        except Exception as e:
            print_colored(f"Ошибка: {str(e)}", "red")

if __name__ == "__main__":
    main()
