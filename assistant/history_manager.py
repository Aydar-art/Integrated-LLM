"""
Модуль для управления историей сообщений.
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any
import datetime
import config
import utils

class HistoryManager:
    """Менеджер для работы с историей чата."""
    
    def __init__(self, current_directory: str):
        self.current_directory = current_directory
        self.history_file = os.path.join(current_directory, config.HISTORY_FILE)
        self.conversation_history: List[Dict[str, str]] = []
    
    def load_history(self) -> bool:
        """
        Загрузка истории сообщений из файла.
        """
        try:
            if not os.path.exists(self.history_file):
                utils.print_colored("ℹ️ Файл истории не найден, начнем с чистого листа", "yellow")
                return True
            
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # Проверяем структуру данных
            if isinstance(history_data, list):
                self.conversation_history = history_data
                utils.print_colored(f"✅ Загружено {len(self.conversation_history)} сообщений из истории", "green")
                return True
            else:
                utils.print_colored("❌ Неверный формат файла истории", "red")
                return False
                
        except json.JSONDecodeError:
            utils.print_colored("❌ Ошибка чтения JSON в файле истории", "red")
            return False
        except Exception as e:
            utils.print_colored(f"❌ Ошибка загрузки истории: {str(e)}", "red")
            return False
    
    def save_history(self) -> bool:
        """
        Сохранение истории сообщений в файл.
        """
        try:
            # Ограничиваем размер истории
            if len(self.conversation_history) > config.MAX_HISTORY_ENTRIES:
                self.conversation_history = self.conversation_history[-config.MAX_HISTORY_ENTRIES:]
                utils.print_colored(f"ℹ️ История ограничена до {config.MAX_HISTORY_ENTRIES} сообщений", "yellow")
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            utils.print_colored(f"❌ Ошибка сохранения истории: {str(e)}", "red")
            return False
    
    def export_history(self, file_path: str = None) -> str:
        """
        Экспорт истории в указанный файл.
        """
        try:
            if file_path is None:
                file_path = f"chat_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Используем FileManager для валидации пути
            from .file_manager import FileManager
            fm = FileManager(self.current_directory)
            validated_path, is_valid = fm.validate_path(file_path)
            if not is_valid:
                return validated_path
            
            export_data = {
                "export_date": datetime.datetime.now().isoformat(),
                "total_messages": len(self.conversation_history),
                "history": self.conversation_history
            }
            
            with open(validated_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return f"✅ История экспортирована в: {validated_path} ({len(self.conversation_history)} сообщений)"
            
        except Exception as e:
            return f"❌ Ошибка экспорта истории: {str(e)}"
    
    def import_history(self, file_path: str) -> str:
        """
        Импорт истории из файла.
        """
        try:
            # Используем FileManager для валидации пути
            from .file_manager import FileManager
            fm = FileManager(self.current_directory)
            validated_path, is_valid = fm.validate_path(file_path)
            if not is_valid:
                return validated_path
            
            if not os.path.exists(validated_path):
                return f"❌ Файл {validated_path} не найден"
            
            with open(validated_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Поддерживаем два формата: простой список и структурированный экспорт
            if isinstance(import_data, list):
                new_history = import_data
            elif isinstance(import_data, dict) and "history" in import_data:
                new_history = import_data["history"]
            else:
                return "❌ Неподдерживаемый формат файла истории"
            
            if not isinstance(new_history, list):
                return "❌ Неверный формат данных истории"
            
            # Добавляем импортированную историю к текущей
            self.conversation_history.extend(new_history)
            
            # Сохраняем объединенную историю
            self.save_history()
            
            return f"✅ Импортировано {len(new_history)} сообщений. Всего сообщений: {len(self.conversation_history)}"
            
        except json.JSONDecodeError:
            return "❌ Ошибка чтения JSON в файле импорта"
        except Exception as e:
            return f"❌ Ошибка импорта истории: {str(e)}"
    
    def clear_history(self, confirm: bool = False) -> str:
        """
        Очистка истории сообщений.
        """
        if not confirm:
            return "⚠️ Для очистки истории используйте !clear confirm"
        
        message_count = len(self.conversation_history)
        self.conversation_history.clear()
        
        # Также удаляем файл истории
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
        except:
            pass  # Игнорируем ошибки удаления файла
        
        return f"✅ История очищена ({message_count} сообщений удалено)"
    
    def show_history_stats(self) -> str:
        """
        Показ статистики истории.
        """
        if not self.conversation_history:
            return "📊 История пуста"
        
        total_messages = len(self.conversation_history)
        today = datetime.datetime.now().date()
        today_messages = len([msg for msg in self.conversation_history 
                             if datetime.datetime.fromisoformat(msg.get('timestamp', '')).date() == today])
        
        # Анализ тематики сообщений
        code_related = sum(1 for msg in self.conversation_history 
                          if any(keyword in msg.get('user', '').lower() 
                                for keyword in ['код', 'функци', 'класс', 'def ', 'function', 'code']))
        
        stats = [
            f"📊 Статистика истории:",
            f"Всего сообщений: {total_messages}",
            f"Сообщений сегодня: {today_messages}",
            f"Запросов о коде: {code_related} ({code_related/total_messages*100:.1f}%)",
            f"Файл истории: {self.history_file}",
            f"Размер файла: {os.path.getsize(self.history_file) if os.path.exists(self.history_file) else 0} байт"
        ]
        
        return "\n".join(stats)
    
    def show_recent_history(self) -> str:
        """Показ последних сообщений из истории"""
        if not self.conversation_history:
            return "📖 История разговора пуста"
        
        result = "📖 Последние сообщения:\n"
        for i, chat in enumerate(self.conversation_history[-10:], 1):  # Последние 10 сообщений
            timestamp = chat.get('timestamp', '')
            user_msg = chat['user'][:80] + "..." if len(chat['user']) > 80 else chat['user']
            result += f"{i}. [{timestamp}] Вы: {user_msg}\n"
        
        result += f"\nВсего сообщений: {len(self.conversation_history)}"
        return result
    
    def add_message(self, user_input: str, ai_response: str) -> None:
        """
        Добавление сообщения в историю.
        """
        self.conversation_history.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "user": user_input,
            "ai": ai_response
        })
        
        # Автосохранение истории каждые 10 сообщений
        if len(self.conversation_history) % 10 == 0:
            self.save_history()
