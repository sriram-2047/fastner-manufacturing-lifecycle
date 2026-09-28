import os
import time
import socket
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip('/')
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "15"))

_last_check_time = 0
_is_ollama_available = False
_cached_models = []

def _is_port_open(host='127.0.0.1', port=11434, timeout=0.2):
    """Fast socket-level ping to check if local port is actively listening."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def check_ollama_status():
    """
    Check if local Ollama server is responsive and return model information.
    Uses 5-second caching for high performance.
    """
    global _last_check_time, _is_ollama_available, _cached_models
    now = time.time()

    if now - _last_check_time < 5.0:
        return {
            'available': _is_ollama_available,
            'url': OLLAMA_BASE_URL,
            'configured_model': OLLAMA_MODEL,
            'available_models': _cached_models,
            'model_found': any(OLLAMA_MODEL in m for m in _cached_models)
        }

    # Extract host and port from URL
    host = '127.0.0.1'
    port = 11434
    if '://' in OLLAMA_BASE_URL:
        parts = OLLAMA_BASE_URL.split('://')[1].split(':')
        host = parts[0]
        if len(parts) > 1:
            try:
                port = int(parts[1].split('/')[0])
            except ValueError:
                port = 11434

    if not _is_port_open(host, port, timeout=0.2):
        _last_check_time = now
        _is_ollama_available = False
        _cached_models = []
        return {
            'available': False,
            'url': OLLAMA_BASE_URL,
            'configured_model': OLLAMA_MODEL,
            'available_models': [],
            'model_found': False
        }

    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1.5)
        if response.status_code == 200:
            data = response.json()
            models = [m.get('name') for m in data.get('models', [])]
            _last_check_time = now
            _is_ollama_available = True
            _cached_models = models
            return {
                'available': True,
                'url': OLLAMA_BASE_URL,
                'configured_model': OLLAMA_MODEL,
                'available_models': models,
                'model_found': any(OLLAMA_MODEL in m for m in models)
            }
    except requests.exceptions.RequestException:
        pass

    _last_check_time = now
    _is_ollama_available = False
    _cached_models = []
    return {
        'available': False,
        'url': OLLAMA_BASE_URL,
        'configured_model': OLLAMA_MODEL,
        'available_models': [],
        'model_found': False
    }

def query_ollama(prompt, system_prompt=None, temperature=0.1):
    """
    Send a generation request to the local Ollama instance.
    Returns (response_text, error_message).
    Fast failover if server is not reachable.
    """
    status = check_ollama_status()
    if not status['available']:
        return None, "AI service is currently unavailable. Please check the Ollama service."

    # Check if configured model exists if models were fetched
    if status.get('available_models') and not status.get('model_found'):
        return None, f"Configured Ollama model '{OLLAMA_MODEL}' is not available. Please pull the model with 'ollama pull {OLLAMA_MODEL}'."

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": 0.9
        }
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        url = f"{OLLAMA_BASE_URL}/api/generate"
        response = requests.post(
            url,
            json=payload,
            timeout=(3.0, OLLAMA_TIMEOUT)
        )
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get('response', '').strip()
            return generated_text, None
        elif response.status_code == 404:
            return None, f"Configured Ollama model '{OLLAMA_MODEL}' is not available. Please pull the model with Ollama."
        else:
            return None, f"Ollama HTTP error {response.status_code}: {response.text}"
    except requests.exceptions.Timeout:
        return None, "Ollama request timed out. Please check if the model is loaded."
    except requests.exceptions.ConnectionError:
        return None, "AI service is currently unavailable. Please check the Ollama service."
    except Exception as e:
        return None, f"Ollama communication error: {str(e)}"

