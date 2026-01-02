"""
Поддержка различных LLM провайдеров.
"""
import os
import requests
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import config
import utils

class LLMProvider(ABC):
    """Абстрактный класс провайдера LLM."""
    
    @abstractmethod
    def send_request(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        pass

class OllamaProvider(LLMProvider):
    """Провайдер для Ollama."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def send_request(self, prompt: str, model: str = "llama3.1:8b", 
                    temperature: float = 0.3, stream: bool = True, **kwargs) -> str:
        """Отправка запроса к Ollama."""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_predict": 8192,
                "repeat_penalty": 1.1
            }
        }
        
        try:
            if stream:
                return self._stream_request(url, payload)
            else:
                return self._standard_request(url, payload)
                
        except Exception as e:
            return f"❌ Ошибка Ollama: {str(e)}"
    
    def _standard_request(self, url: str, payload: dict) -> str:
        """Стандартный запрос без streaming."""
        response = self.session.post(url, json=payload, timeout=config.TIMEOUT_SECONDS)
        response.raise_for_status()
        result = response.json()
        return result.get("response", "Ошибка: ответ не получен")
    
    def _stream_request(self, url: str, payload: dict) -> str:
        """Streaming запрос."""
        utils.print_colored("🤖 AI:", "green")
        print("", end="", flush=True)
        
        full_response = ""
        response = self.session.post(url, json=payload, timeout=config.TIMEOUT_SECONDS, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    if 'response' in data:
                        chunk = data['response']
                        full_response += chunk
                        print(chunk, end='', flush=True)
                        time.sleep(config.STREAM_DELAY)
                    
                    if data.get('done', False):
                        print()
                        break
                except:
                    continue
        
        return full_response
    
    def get_available_models(self) -> List[str]:
        """Получение списка доступных моделей Ollama."""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
        except:
            pass
        return []

class OpenAIClient(LLMProvider):
    """Клиент для OpenAI API."""
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def send_request(self, prompt: str, model: str = "gpt-3.5-turbo", 
                    temperature: float = 0.3, stream: bool = True, **kwargs) -> str:
        """Отправка запроса к OpenAI."""
        if not self.api_key:
            return "❌ OpenAI API ключ не настроен. Используйте: !set openai <api_key>"
        
        url = f"{self.base_url}/chat/completions"
        
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        try:
            if stream:
                return self._stream_request(url, payload)
            else:
                return self._standard_request(url, payload)
                
        except Exception as e:
            return f"❌ Ошибка OpenAI: {str(e)}"
    
    def _standard_request(self, url: str, payload: dict) -> str:
        """Стандартный запрос."""
        response = self.session.post(url, json=payload, timeout=config.TIMEOUT_SECONDS)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _stream_request(self, url: str, payload: dict) -> str:
        """Streaming запрос."""
        utils.print_colored("🤖 AI:", "green")
        print("", end="", flush=True)
        
        full_response = ""
        response = self.session.post(url, json=payload, timeout=config.TIMEOUT_SECONDS, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    if line.strip() == 'data: [DONE]':
                        print()
                        break
                    
                    try:
                        data = json.loads(line[6:])
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                chunk = delta['content']
                                full_response += chunk
                                print(chunk, end='', flush=True)
                                time.sleep(config.STREAM_DELAY)
                    except:
                        continue
        
        return full_response
    
    def get_available_models(self) -> List[str]:
        """Получение списка доступных моделей OpenAI."""
        if not self.api_key:
            return []
        
        try:
            response = self.session.get(f"{self.base_url}/models", timeout=10)
            if response.status_code == 200:
                models = response.json().get('data', [])
                return [model['id'] for model in models if model['id'].startswith('gpt')]
        except:
            pass
        return []

class DeepSeekClient(LLMProvider):
    """Клиент для DeepSeek API."""
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
    
    def send_request(self, prompt: str, model: str = "deepseek-chat", 
                    temperature: float = 0.3, stream: bool = True, **kwargs) -> str:
        """Отправка запроса к DeepSeek."""
        if not self.api_key:
            return "❌ DeepSeek API ключ не настроен. Используйте: !set deepseek <api_key>"
        
        url = f"{self.base_url}/chat/completions"
        
        messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        try:
            if stream:
                return self._stream_request(url, payload)
            else:
                return self._standard_request(url, payload)
                
        except Exception as e:
            return f"❌ Ошибка DeepSeek: {str(e)}"
    
    def _standard_request(self, url: str, payload: dict) -> str:
        """Стандартный запрос."""
        response = self.session.post(url, json=payload, timeout=config.TIMEOUT_SECONDS)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    
    def _stream_request(self, url: str, payload: dict) -> str:
        """Streaming запрос."""
        utils.print_colored("🤖 AI:", "green")
        print("", end="", flush=True)
        
        full_response = ""
        response = self.session.post(url, json=payload, timeout=config.TIMEOUT_SECONDS, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    if line.strip() == 'data: [DONE]':
                        print()
                        break
                    
                    try:
                        data = json.loads(line[6:])
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            if 'content' in delta:
                                chunk = delta['content']
                                full_response += chunk
                                print(chunk, end='', flush=True)
                                time.sleep(config.STREAM_DELAY)
                    except:
                        continue
        
        return full_response
    
    def get_available_models(self) -> List[str]:
        """Получение списка доступных моделей DeepSeek."""
        if not self.api_key:
            return []
        
        # DeepSeek обычно имеет фиксированный набор моделей
        return ["deepseek-chat", "deepseek-coder"]

class ProviderManager:
    """Менеджер для работы с различными провайдерами."""
    
    def __init__(self):
        self.providers = {
            "ollama": OllamaProvider(),
            "openai": OpenAIClient(),
            "deepseek": DeepSeekClient()
        }
        self.current_provider = "ollama"
        self.current_model = "llama3.1:8b"
    
    def set_provider(self, provider_name: str) -> bool:
        """Установка текущего провайдера."""
        if provider_name in self.providers:
            self.current_provider = provider_name
            return True
        return False
    
    def set_model(self, model_name: str) -> bool:
        """Установка текущей модели."""
        self.current_model = model_name
        return True
    
    def set_api_key(self, provider_name: str, api_key: str) -> bool:
        """Установка API ключа для провайдера."""
        if provider_name == "openai":
            self.providers["openai"] = OpenAIClient(api_key)
            return True
        elif provider_name == "deepseek":
            self.providers["deepseek"] = DeepSeekClient(api_key)
            return True
        return False
    
    def send_request(self, prompt: str, **kwargs) -> str:
        """Отправка запроса через текущий провайдер."""
        provider = self.providers[self.current_provider]
        model = kwargs.get('model', self.current_model)
        
        return provider.send_request(
            prompt=prompt,
            model=model,
            temperature=kwargs.get('temperature', 0.3),
            stream=kwargs.get('stream', True)
        )
    
    def get_available_providers(self) -> List[str]:
        """Получение списка доступных провайдеров."""
        return list(self.providers.keys())
    
    def get_available_models(self, provider_name: str = None) -> List[str]:
        """Получение списка моделей для провайдера."""
        provider_name = provider_name or self.current_provider
        if provider_name in self.providers:
            return self.providers[provider_name].get_available_models()
        return []
    
    def test_connection(self, provider_name: str = None) -> str:
        """Проверка соединения с провайдером."""
        provider_name = provider_name or self.current_provider
        if provider_name in self.providers:
            models = self.get_available_models(provider_name)
            if models:
                return f"✅ {provider_name} доступен. Модели: {', '.join(models[:5])}"
            else:
                return f"❌ {provider_name} не доступен или нет моделей"
        return f"❌ Провайдер {provider_name} не найден"
