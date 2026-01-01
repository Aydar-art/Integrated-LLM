"""
Основной файл запуска AI-помощника.
"""
from assistant.core import CodeAssistant
import utils
import config

def main():
    """Основная функция запуска помощника."""
    utils.print_banner()
    assistant = CodeAssistant()
    
    utils.print_colored("🚀 Инициализация завершена", "green")
    utils.print_colored(f"📁 Текущая директория: {assistant.current_directory}", "blue")
    utils.print_colored(f"🔧 Текущий провайдер: {assistant.provider_manager.current_provider}", "yellow")
    utils.print_colored(f"🤖 Текущая модель: {assistant.provider_manager.current_model}", "yellow")
    utils.print_colored(f"🎯 Потоковый вывод: {'включен' if config.STREAMING_ENABLED else 'выключен'}", "cyan")
    utils.print_colored(f"⚡ Скорость вывода: {config.STREAM_DELAY} сек/символ", "cyan")
    utils.print_colored("💡 Введите !help для списка команд", "yellow")
    utils.print_colored("-" * 70, "cyan")
    
    try:
        while True:
            try:
                user_input = input("👤 Вы: ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'выход', '!exit']:
                    assistant.history_manager.save_history()
                    utils.print_colored("👋 До свидания! Хорошего кодинга!", "cyan")
                    break
                
                if not user_input:
                    continue
                
                # Определяем тип команды для правильного отображения
                is_file_command = user_input.split()[0].lower() in [
                    '!read', '!ls', '!dir', '!pwd', '!info', '!search', 
                    '!history', '!export', '!import', '!clear', '!save', 
                    '!stream', '!speed', '!provider', '!model', '!models', 
                    '!set', '!test', '!help'
                ]
                
                response = assistant.chat(user_input)
                
                # Для файловых команд и команд настройки показываем ответ сразу
                if is_file_command or not config.STREAMING_ENABLED:
                    if not response.startswith("❌"):
                        utils.print_colored("🤖 AI:", "green")
                        print(response)
                
                utils.print_colored("-" * 70, "cyan")
                
            except KeyboardInterrupt:
                assistant.history_manager.save_history()
                utils.print_colored("\n👋 Прервано пользователем. До свидания!", "cyan")
                break
            except Exception as e:
                utils.print_colored(f"❌ Критическая ошибка: {str(e)}", "red")
                utils.print_colored("Попробуйте перезапустить программу.", "yellow")
                
    finally:
        assistant.close()
        utils.print_colored("Сессия завершена.", "blue")

if __name__ == "__main__":
    main()
