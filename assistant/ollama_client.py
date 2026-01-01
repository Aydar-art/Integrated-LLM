"""
Клиент для работы с Ollama API.
"""
import requests
import json
import time
from typing import Dict, Any, Generator
import config
import utils

class OllamaClient:
    """Клиент для взаимодействия с Ollama API."""
    
    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.url = config.OLLAMA_URL
        self.stream_url = config.OLLAMA_STREAM_URL
        self.session = requests.Session()
        self.system_prompt = config.SYSTEM_PROMPT
    
    def send_request(self, prompt: str, conversation_history: list = None) -> str:
        """
        Отправка запроса к Ollama API.
        """
        # Если streaming выключен, используем обычный метод
        if not config.STREAMING_ENABLED:
            return self._send_standard_request(prompt, conversation_history)
        
        # Иначе используем streaming
        return self._send_streaming_request(prompt, conversation_history)
    
    def _send_standard_request(self, prompt: str, conversation_history: list = None) -> str:
        """Стандартный запрос без streaming."""
        full_prompt = self._build_prompt(prompt, conversation_history)
        
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
            response = self.session.post(self.url, json=payload, timeout=config.TIMEOUT_SECONDS)
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
    
    def _send_streaming_request(self, prompt: str, conversation_history: list = None) -> str:
        """Streaming запрос с постепенным выводом."""
        full_prompt = self._build_prompt(prompt, conversation_history)
        
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": True,  # Включаем streaming
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 4096,
                "repeat_penalty": 1.1
            }
        }
        
        try:
            utils.print_colored("🤖 AI:", "green")
            print("", end="", flush=True)  # Начало ответа
            
            full_response = ""
            line_buffer = ""
            
            response = self.session.post(self.stream_url, json=payload, timeout=config.TIMEOUT_SECONDS, stream=True)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        # Парсим JSON из каждой строки
                        data = json.loads(line.decode('utf-8'))
                        
                        # Проверяем, есть ли часть ответа
                        if 'response' in data:
                            chunk = data['response']
                            full_response += chunk
                            line_buffer += chunk
                            
                            # Выводим по символам для плавности
                            for char in chunk:
                                print(char, end='', flush=True)
                                time.sleep(config.STREAM_DELAY)
                            
                            # Если накопилась целая строка, выводим перевод строки
                            if '\n' in line_buffer:
                                line_buffer = ""
                        
                        # Если это конец ответа
                        if data.get('done', False):
                            print()  # Завершаем строку
                            break
                            
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"\n❌ Ошибка при обработке streaming: {str(e)}")
                        break
            
            return full_response
            
        except requests.exceptions.ConnectionError:
            return "❌ Ошибка: Ollama не запущен. Запустите: `ollama serve`"
        except requests.exceptions.Timeout:
            return "⏰ Ошибка: время ожидания ответа истекло. Попробуйте упростить запрос."
        except requests.exceptions.HTTPError as e:
            return f"🌐 Ошибка HTTP: {str(e)}"
        except Exception as e:
            return f"❌ Неизвестная ошибка: {str(e)}"
    
    def _build_prompt(self, prompt: str, conversation_history: list = None) -> str:
        """Построение полного промта с контекстом."""
        context = ""
        
        # Добавляем последние сообщения из истории для контекста
        if conversation_history:
            context += "Предыдущие сообщения:\n"
            for chat in conversation_history[-3:]:  # Последние 3 сообщения
                context += f"User: {chat['user']}\nAI: {chat['ai'][:100]}...\n"
        
        return f"{self.system_prompt}\n\n{context}\n\nЗапрос: {prompt}"
    
    def close(self):
        """Закрытие сессии."""
        self.session.close()
