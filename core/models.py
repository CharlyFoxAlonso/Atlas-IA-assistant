"""
Atlas & Prometeo - Gestor de Modelos Híbridos (models.py)
Atlas v4.1 - Rutea el pensamiento hacia el modelo local (Ollama) o la nube (NVIDIA).
"""
import os
import requests
from openai import OpenAI
from core.config import MODELO_LOCAL


def preguntar(prompt, motor=None, modelo_nube="meta/llama-3.1-70b-instruct"):
    """
    El núcleo de la bestia.
    motor='atlas' usa Ollama local para privacidad 100%.
    motor='prometeo' usa la API de NVIDIA en la nube para velocidad e inteligencia pesada.
    """
    if motor is None:
        motor = os.getenv("MOTOR_POR_DEFECTO", "atlas").lower()

    # ============================================
    # ⚡ MODO PROMETEO (Nube - NVIDIA API)
    # ============================================
    if motor == "prometeo":
        try:
            client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=os.getenv("NVIDIA_API_KEY")
            )
            response = client.chat.completions.create(
                model=modelo_nube,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2048,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Prometeo falló al traer el fuego de la nube: {e}"

    # ============================================
    # 🧠 MODO ATLAS (Local - Ollama)
    # ============================================
    else:
        try:
            url = "http://127.0.0.1:11434/api/chat"
            data = {
                "model": MODELO_LOCAL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }
            r = requests.post(url, json=data)
            return r.json()["message"]["content"]
        except Exception as e:
            return f"❌ Error en el cerebro local de Atlas: {e}"
