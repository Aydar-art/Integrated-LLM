"""
Модуль для работы с файлами и директориями.
"""
import os
import re
from pathlib import Path
from typing import Tuple, List, Dict, Any
import datetime
import config
import utils

class FileManager:
    """Менеджер для работы с файловой системой."""
    
    def __init__(self, current_directory: str):
        self.current_directory = current_directory
    
    def validate_path(self, path: str) -> Tuple[str, bool]:
        """
        Валидация и нормализация пути с защитой от traversal атак.
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
        Безопасное чтение содержимого файла.
        """
        try:
            validated_path, is_valid = self.validate_path(file_path)
            if not is_valid:
                return validated_path
            
            if not os.path.exists(validated_path):
                return f"Ошибка: файл {validated_path} не найден"
            
            if os.path.isdir(validated_path):
                return f"Ошибка: {validated_path} является директорией, а не файлом"
            
            # Проверка размера файла
            file_size = os.path.getsize(validated_path)
            if file_size > config.MAX_FILE_SIZE:
                return f"Ошибка: файл слишком большой ({file_size} байт). Лимит: {config.MAX_FILE_SIZE}"
            
            # Определяем язык для лучшего форматирования
            language = utils.detect_language_from_extension(validated_path)
            
            # Попытка чтения с разными кодировками
            encodings = ['utf-8', 'cp1251', 'iso-8859-1', 'latin-1']
            for encoding in encodings:
                try:
                    with open(validated_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    
                    file_info = self._get_file_stats(validated_path)
                    return f"{file_info}\nЯзык: {language}\nСодержимое файла {validated_path}:\n```{language.split()[0].lower()}\n{content}\n```"
                    
                except UnicodeDecodeError:
                    continue
            
            # Если ни одна кодировка не подошла, читаем как бинарный
            try:
                with open(validated_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='replace')
                return f"Файл прочитан с заменой нечитаемых символов:\n```{language.split()[0].lower()}\n{content}\n```"
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
            created = utils.format_timestamp(stat.st_ctime)
            modified = utils.format_timestamp(stat.st_mtime)
            
            return (
                f"📊 Информация о файле:\n"
                f"Размер: {stat.st_size} байт\n"
                f"Создан: {created}\n"
                f"Изменен: {modified}\n"
                f"Расширение: {Path(file_path).suffix}"
            )
        except:
            return "📊 Информация о файле: недоступна"
    
    def read_multiple_files(self, file_paths: List[str]) -> str:
        """
        Чтение нескольких файлов с автоматическим определением языков.
        """
        if len(file_paths) > config.MAX_FILES_PER_QUERY:
            return f"❌ Слишком много файлов. Максимум: {config.MAX_FILES_PER_QUERY}"
        
        file_contents = []
        group_info = self.get_file_group_info(file_paths)
        
        # Заголовок с информацией о файлах
        header = f"📚 Анализ {len(file_paths)} файлов:\n"
        header += f"Размер: {utils.format_file_size(group_info['total_size'])}\n"
        header += f"Языки: {', '.join(group_info['languages'])}\n\n"
        file_contents.append(header)
        
        for file_info in group_info['files']:
            try:
                content_result = self.read_file(file_info['path'])
                
                # Извлекаем чистое содержимое файла
                if "```" in content_result:
                    parts = content_result.split("```")
                    if len(parts) >= 3:
                        content = parts[1].strip()
                        file_contents.append(
                            f"📄 Файл: {file_info['path']} ({file_info['language']})\n"
                            f"```{file_info['language'].split()[0].lower()}\n"
                            f"{content}\n"
                            f"```\n"
                        )
                else:
                    file_contents.append(
                        f"📄 Файл: {file_info['path']} ({file_info['language']})\n"
                        f"{content_result}\n"
                    )
                    
            except Exception as e:
                file_contents.append(f"❌ Ошибка чтения {file_info['path']}: {str(e)}")
        
        return "\n".join(file_contents)
    
    def get_file_group_info(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Получение информации о группе файлов.
        """
        total_size = 0
        languages = set()
        file_info = []
        
        for file_path in file_paths:
            try:
                validated_path, is_valid = self.validate_path(file_path)
                if not is_valid:
                    continue
                    
                stat = os.stat(validated_path)
                total_size += stat.st_size
                language = utils.detect_language_from_extension(file_path)
                languages.add(language)
                
                file_info.append({
                    'path': validated_path,
                    'size': stat.st_size,
                    'language': language,
                    'extension': Path(file_path).suffix,
                    'modified': datetime.datetime.fromtimestamp(stat.st_mtime)
                })
            except:
                continue
        
        return {
            'total_files': len(file_paths),
            'total_size': total_size,
            'languages': list(languages),
            'files': file_info
        }
    
    def find_files_by_pattern(self, pattern: str, directory: str = ".") -> List[str]:
        """
        Поиск файлов по шаблону с поддержкой расширений.
        """
        try:
            validated_path, is_valid = self.validate_path(directory)
            if not is_valid:
                return []
            
            found_files = []
            
            # Если это шаблон типа *.py
            if pattern.startswith('*.'):
                extension = pattern[1:]  # убираем звездочку
                for root, dirs, files in os.walk(validated_path):
                    for file in files:
                        if file.lower().endswith(extension.lower()):
                            found_files.append(os.path.join(root, file))
            else:
                # Поиск по имени файла (без пути)
                for root, dirs, files in os.walk(validated_path):
                    for file in files:
                        if pattern.lower() in file.lower():
                            found_files.append(os.path.join(root, file))
            
            return found_files[:config.MAX_FILES_PER_QUERY]
            
        except Exception as e:
            return []
    
    def list_directory(self, path: str = ".") -> str:
        """
        Безопасное отображение содержимого директории.
        """
        try:
            validated_path, is_valid = self.validate_path(path)
            if not is_valid:
                return validated_path
            
            if not os.path.exists(validated_path):
                return f"Ошибка: путь {validated_path} не найден"
            
            if not os.path.isdir(validated_path):
                return f"Ошибка: {validated_path} не является директорией"
            
            items = utils.safe_list_directory(validated_path)
            files = []
            directories = []
            
            for item in items:
                item_path = os.path.join(validated_path, item)
                try:
                    if os.path.isdir(item_path):
                        # Подсчет содержимого директории
                        dir_items = len(utils.safe_list_directory(item_path))
                        directories.append(f"📁 {item}/ ({dir_items} items)")
                    else:
                        file_ext = Path(item).suffix.lower()
                        language = utils.detect_language_from_extension(item)
                        icon = "📄" if file_ext in config.SUPPORTED_EXTENSIONS else "📎"
                        size = os.path.getsize(item_path)
                        size_str = utils.format_file_size(size)
                        files.append(f"{icon} {item} ({language}, {size_str})")
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
    
    def get_file_info(self, file_path: str) -> str:
        """
        Получение детальной информации о файле.
        """
        try:
            validated_path, is_valid = self.validate_path(file_path)
            if not is_valid:
                return validated_path
            
            if not os.path.exists(validated_path):
                return f"Файл {validated_path} не найден"
            
            stat = os.stat(validated_path)
            created = datetime.datetime.fromtimestamp(stat.st_ctime)
            modified = datetime.datetime.fromtimestamp(stat.st_mtime)
            language = utils.detect_language_from_extension(validated_path)
            
            info = [
                f"📊 Детальная информация о {validated_path}",
                f"Язык: {language}",
                f"Размер: {stat.st_size} байт ({utils.format_file_size(stat.st_size)})",
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
