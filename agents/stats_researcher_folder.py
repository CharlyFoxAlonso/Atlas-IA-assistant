import os
from core.file_loader import leer_archivo_estudio
from core.models import preguntar
from core.cache import esta_en_cache, guardar_en_cache, obtener_del_cache


def limpiar_texto(texto):
    """Limpieza básica de texto extraído de PDFs."""
    if not texto:
        return ""
    
    # Quitar caracteres nulos
    texto = texto.replace("\x00", " ")
    
    # Quitar saltos de línea excesivos
    texto = texto.replace("\n\n\n", "\n\n")
    
    return texto.strip()


def investigar_carpeta_v2(ruta_carpeta):
    """
    Investiga todos los archivos de una carpeta y genera apuntes de estudio.
    Usa cache para no reprocesar archivos que no cambiaron.
    
    Devuelve:
        Texto concatenado con los apuntes de todos los archivos procesados.
    """
    resultados_finales = []
    archivos_procesados = 0
    archivos_cache = 0
    archivos_omitidos = 0
    
    # Recorrer la carpeta
    for root, _, files in os.walk(ruta_carpeta):
        for f in files:
            path = os.path.join(root, f)
            
            # Verificar cache primero
            if esta_en_cache(path):
                resultado = obtener_del_cache(path)
                resultados_finales.append(
                    f"\n\n{'=' * 60}\n📘 {f} (desde cache)\n{'=' * 60}\n"
                    + resultado
                )
                archivos_cache += 1
                continue
            
            # Leer el archivo
            contenido = leer_archivo_estudio(path)
            contenido = limpiar_texto(contenido)
            
            # Si no hay suficiente texto, omitir
            if not contenido or len(contenido) < 50:
                archivos_omitidos += 1
                continue
            
            # Construir el prompt (contexto reducido a 5000)
            prompt = f"""
Eres un profesor universitario experto en estadística.
Convierte este material en apuntes de examen estructurados.

ARCHIVO: {f}

CONTENIDO:
{contenido[:5000]}

FORMATO OBLIGATORIO:

## RESUMEN
Máximo 40 palabras

## CONCEPTOS CLAVE
Lista de 5-10 conceptos

## FÓRMULAS IMPORTANTES
Si existen, listarlas

## EJERCICIOS RESUELTOS
Si aplica, mostrar paso a paso

## ERRORES TÍPICOS
Errores comunes de estudiantes

## PREGUNTAS DE EXAMEN
3-5 preguntas posibles

Reglas:
- Usa principalmente el material proporcionado
- Si falta información crítica, puedes complementar con conocimiento general de estadística
- Indica con [MATERIAL] lo que viene del PDF y con [COMPLEMENTO] lo que agregas tú
- Si no hay ejercicios, escribe "No aplica"
- Sé claro y directo
- Usa formato Markdown
"""
            
            # Consultar al modelo
            try:
                respuesta = preguntar(prompt)
                
                # Guardar en cache
                guardar_en_cache(path, respuesta)
                
                resultados_finales.append(
                    f"\n\n{'=' * 60}\n📘 {f}\n{'=' * 60}\n"
                    + respuesta
                )
                
                archivos_procesados += 1
                
            except Exception as e:
                resultados_finales.append(
                    f"\n\n{'=' * 60}\n❌ ERROR en {f}\n{'=' * 60}\n{str(e)}"
                )
    
    # Resumen final
    resumen = f"\n\n{'=' * 60}\n📊 RESUMEN DE PROCESAMIENTO\n{'=' * 60}\n"
    resumen += f"✅ Archivos procesados nuevos: {archivos_procesados}\n"
    resumen += f"📦 Archivos cargados del cache: {archivos_cache}\n"
    resumen += f"⚠️ Archivos omitidos (vacíos o muy cortos): {archivos_omitidos}\n"
    resumen += f"{'=' * 60}\n"
    
    return "\n".join(resultados_finales) + resumen