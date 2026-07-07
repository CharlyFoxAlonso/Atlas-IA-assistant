"""
Test NVIDIA API - Verifica qué modelos están disponibles
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY") or os.getenv("NVIDIA_API_KEY")

if not api_key:
    print("ERROR: No se encontró API Key en .env")
    exit(1)

print(f"API Key detectada: {api_key[:10]}...{api_key[-4:]}")
print(f"Longitud: {len(api_key)} caracteres")
print("-" * 50)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=api_key
)

# ============================================
# 1. LISTAR MODELOS DISPONIBLES
# ============================================
print("\n1. MODELOS DISPONIBLES EN TU CUENTA:\n")
try:
    models = client.models.list()
    modelos = []
    for model in models:
        modelos.append(model.id)
    
    print(f"Total: {len(modelos)} modelos\n")
    
    # Mostrar primeros 30
    for i, nombre in enumerate(sorted(modelos)[:30], 1):
        print(f"  {i:2d}. {nombre}")
    
    if len(modelos) > 30:
        print(f"\n  ... y {len(modelos) - 30} más")
    
    # Guardar lista completa en archivo
    with open("modelos_nvidia_disponibles.txt", "w", encoding="utf-8") as f:
        f.write("MODELOS DISPONIBLES EN NVIDIA API\n")
        f.write(f"Total: {len(modelos)}\n\n")
        for nombre in sorted(modelos):
            f.write(f"{nombre}\n")
    
    print(f"\n  Lista completa guardada en: modelos_nvidia_disponibles.txt")
    
except Exception as e:
    print(f"  ERROR listando modelos: {e}")
    print("\n  Posibles causas:")
    print("  - API Key incorrecta o expirada")
    print("  - No estás suscrito a ningún modelo en NVIDIA NIM")
    print("  - Ir a https://build.nvidia.com y hacer click en 'Get API Key'")

# ============================================
# 2. PROBAR MODELOS POPULARES (uno por uno)
# ============================================
print("\n2. PROBANDO MODELOS POPULARES:\n")

modelos_a_probar = [
    "meta/llama3-8b-instruct",
    "meta/llama3-70b-instruct",
    "meta/llama-3.1-8b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.3-70b-instruct",
    "mistralai/mixtral-8x7b-instruct-v0.1",
    "mistralai/mixtral-8x22b-instruct-v0.1",
    "mistralai/mistral-large",
    "nvidia/nemotron-4-340b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "deepseek-ai/deepseek-r1",
    "deepseek-ai/deepseek-v3",
    "qwen/qwen2.5-72b-instruct",
    "google/deplot",
]

for modelo in modelos_a_probar:
    try:
        response = client.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": "Decí 'Hola' en una sola palabra."}],
            max_tokens=10,
            temperature=0.1
        )
        respuesta = response.choices[0].message.content.strip()
        print(f"  OK  {modelo}")
        print(f"       Respuesta: {respuesta}")
    except Exception as e:
        error_msg = str(e)[:80]
        print(f"  ERR {modelo}")
        print(f"       {error_msg}")

print("\n  Los modelos marcados con OK son los que podés usar en Atlas Prometeo.")