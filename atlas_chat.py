"""
Atlas Chat v3.8 - CLI Principal
Con soporte para modelos locales (Ollama) y nube (NVIDIA/Prometeo).
Comandos para gestión de modelos locales.
"""
import sys
import os
from core.brain import pensar_con_streaming, analizar_para_memoria, limpiar_historial, ver_historial, HISTORIAL
from core.router import listar_agentes
from core.memory_manager import guardar_en_memoria, listar_categorias
from core.indexer import construir_indice
from core.vision import analizar_pantalla, limpiar_capturas_antiguas
from core.speech_input import escuchar, probar_microfono
from core.speech_output import hablar, listar_voces_disponibles
from core.security import reporte_seguridad_completo
from core.config import (
    obtener_catalogo_completo,
    verificar_modelo_local,
    descargar_modelo_local,
    eliminar_modelo_local,
    set_modelo_local,
    detectar_hardware,
    MODELO_LOCAL
)

# ============================================
# CONFIGURACIÓN
# ============================================
INTERVALO_ANALISIS = 5
MOTOR_ACTIVO = os.getenv("MOTOR_POR_DEFECTO", "atlas").lower()
MODELO_NUBE_ACTIVO = "meta/llama-3.1-70b-instruct"


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def mostrar_ayuda():
    """Muestra los comandos disponibles."""
    print("""
╔════════════════════════════════════════════════════════════╗
║                    🧠 ATLAS - COMANDOS                      ║
╠════════════════════════════════════════════════════════════╣
║                                                             ║
║  💬 HABLA NORMAL:                                           ║
║     Atlas decide automáticamente qué agente usar            ║
║                                                             ║
║  👁️👂🗣️ SENTIDOS:                                           ║
║     • !mirar               → Captura y analiza pantalla      ║
║     • !escuchar [seg]     → Escucha tu voz (default 5 seg)  ║
║     • !probar_mic         → Prueba el micrófono             ║
║     • !hablar on/off      → Voz automática                  ║
║     • !voces              → Lista voces disponibles         ║
║                                                             ║
║  🧠 AUTO-CONOCIMIENTO:                                      ║
║     • !autoconocer        → Informe completo con código     ║
║     • !autoconocer_corto  → Informe sin código (resumen)    ║
║     • !informe            → Exporta informe a archivo .txt  ║
║     • !reflexionar        → Analiza conversaciones pasadas  ║
║     • !mejorar            → Busca mejoras en la web         ║
║                                                             ║
║  👤 PERFILES:                                               ║
║     • !exportar_perfil [nombre] → Exporta tu config         ║
║     • !importar_perfil [ruta]   → Importa config            ║
║     • !listar_perfiles            → Perfiles exportados     ║
║     • !nuevo_perfil [nombre]      → Crea perfil limpio      ║
║                                                             ║
║  🏠 MODELOS LOCALES:                                        ║
║     • !modelos              → Lista modelos disponibles     ║
║     • !modelo_local [nombre]→ Cambia modelo local activo    ║
║     • !descargar_modelo [nombre] → Descarga modelo          ║
║     • !eliminar_modelo [nombre]  → Elimina modelo           ║
║     • !hardware             → Info de hardware              ║
║                                                             ║
║  🤖 AGENTES DISPONIBLES:                                    ║
║     • 🗣️ General → Conversacional (por defecto)             ║
║     • 📊 Estadística → Si preguntás sobre estadística       ║
║     • 🌐 Researcher → Si necesitás info de la web            ║
║     • 💭 Psicólogo → Si hablás de emociones                 ║
║     • 🏛️ Arquitecto → Si pedís razonamiento profundo        ║
║                                                              ║
║  ⚙️ COMANDOS:                                               ║
║     • !ayuda              → Muestra esta ayuda              ║
║     • !agentes            → Lista agentes disponibles       ║
║     • !categorias         → Categorías de memoria           ║
║     • !historial          → Estado del historial            ║
║     • !limpiar_historial  → Limpia historial                ║
║     • !analizar           → Fuerza análisis de memoria      ║
║     • !indexar            → Reconstruye índice              ║
║     • !seguridad          → Reporte de seguridad            ║
║                                                             ║
║  🚪 SALIR:  "salir", "exit", "quit"                          ║
║                                                             ║
╚════════════════════════════════════════════════════════════╝
    """)


def mostrar_propuestas_memoria(propuestas):
    """Muestra propuestas de guardado con opción de cambiar categoría."""
    if not propuestas:
        return
    categorias = listar_categorias()
    print("\n💾 Atlas detectó información importante:")
    for i, p in enumerate(propuestas, 1):
        print(f"\n{i}. {p['resumen']}")
        print(f"   Sugerencia: [{p['categoria']}]")
        print(f"   Razón: {p['razon']}")
    print("\n¿Guardar? (s/n/cambiar/editar)")
    resp = input("> ").strip().lower()
    if resp in ["s", "si", "sí"]:
        for p in propuestas:
            ok, res = guardar_en_memoria(p["categoria"], p["resumen"])
            print(f"✅ Guardado en {res}" if ok else f"❌ Error: {res}")
    elif resp in ["c", "cambiar"]:
        print("\nElegí categoría:")
        for i, c in enumerate(categorias, 1):
            print(f"  {i}. {c}")
        try:
            sel = int(input("\nNúmero: ").strip())
            if 1 <= sel <= len(categorias):
                cat = categorias[sel - 1]
                for p in propuestas:
                    ok, res = guardar_en_memoria(cat, p["resumen"])
                    print(f"✅ Guardado en {res}" if ok else f"❌ Error: {res}")
        except ValueError:
            print("❌ Inválido.")
    elif resp in ["e", "editar"]:
        for p in propuestas:
            print(f"\nActual: {p['resumen']}")
            nuevo = input("Nuevo (Enter = mantener): ").strip()
            if nuevo:
                p["resumen"] = nuevo
            guardar = input("¿Guardar? (s/n): ").strip().lower()
            if guardar in ["s", "si", "sí"]:
                ok, res = guardar_en_memoria(p["categoria"], p["resumen"])
                print(f"✅ Guardado" if ok else f"❌ Error: {res}")
    else:
        print("🗑️ No guardado.")


def analizar_memoria_pendiente(pregunta, respuesta):
    """Analiza conversación para detectar info importante."""
    if not respuesta or len(respuesta) < 50:
        return False
    print("\n🔍 Analizando conversación...", flush=True)
    try:
        propuestas = analizar_para_memoria(pregunta, respuesta)
        if propuestas:
            print(f"   ✅ {len(propuestas)} propuesta(s)\n", flush=True)
            mostrar_propuestas_memoria(propuestas)
            return True
        else:
            print("   ℹ️ Nada importante\n", flush=True)
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}\n", flush=True)
        return False


# ============================================
# COMANDOS DE MODELOS LOCALES
# ============================================

def comando_modelos():
    """Lista todos los modelos disponibles y su estado."""
    print("\n🏠 MODELOS LOCALES DISPONIBLES")
    print("=" * 70)

    catalogo = obtener_catalogo_completo()

    modelos_oficiales = [
        "qwen3:8b", "qwen3:14b", "qwen3:30b-a3b",
        "gemma3:12b", "deepseek-r1:14b", "mistral-small:22b",
        "llama3.1:8b", "phi4:14b"
    ]

    for modelo_id in modelos_oficiales:
        if modelo_id in catalogo:
            info = catalogo[modelo_id]
            descargado = "✅" if info.get("descargado") else "❌"
            activo = " ⭐ ACTIVO" if info.get("activo") else ""
            destacado = " ⭐MEJOR" if info.get("destacado") else ""

            print(f"\n{descargado} {info['descripcion']}{destacado}{activo}")
            print(f"   Tamaño: {info.get('tamano_gb', 0)} GB | Velocidad: {info.get('velocidad', '?')}")
            print(f"   RAM mín: {info.get('ram_min_gb', 0)} GB | VRAM mín: {info.get('vram_min_gb', 0)} GB")
            print(f"   Uso: {info.get('uso', 'N/A')}")
            if info.get("notas"):
                print(f"   💡 {info['notas']}")

    no_catalogados = [m for m in catalogo if m not in modelos_oficiales and catalogo[m].get("descargado")]
    if no_catalogados:
        print("\n" + "-" * 70)
        print("Otros modelos descargados:")
        for modelo_id in no_catalogados:
            activo = " ⭐ ACTIVO" if catalogo[modelo_id].get("activo") else ""
            print(f"  ✅ {modelo_id}{activo}")

    print("\n" + "=" * 70)
    print(f"\n💡 Usá !modelo_local [nombre] para cambiar el modelo activo")
    print(f"💡 Usá !descargar_modelo [nombre] para descargar un modelo")


def comando_modelo_local(args):
    """Cambia el modelo local activo."""
    if not args:
        print(f"\n🏠 Modelo local actual: {MODELO_LOCAL}")
        print(f"💡 Usá !modelo_local [nombre] para cambiar")
        return

    nuevo_modelo = args[0]

    if not verificar_modelo_local(nuevo_modelo):
        print(f"\n❌ El modelo '{nuevo_modelo}' no está descargado")
        print(f"💡 Descargalo primero con: !descargar_modelo {nuevo_modelo}")
        return

    resultado = set_modelo_local(nuevo_modelo)
    if resultado["exito"]:
        print(f"\n✅ {resultado['mensaje']}")
        print(f"💡 El cambio es temporal. Para cambio permanente, editá .env o core/config.py")
    else:
        print(f"\n❌ Error: {resultado['mensaje']}")


def comando_descargar_modelo(args):
    """Descarga un modelo desde Ollama."""
    if not args:
        print("\n❌ Especificá el modelo a descargar")
        print("💡 Ejemplo: !descargar_modelo qwen3:14b")
        return

    modelo_id = args[0]

    if verificar_modelo_local(modelo_id):
        print(f"\n✅ El modelo '{modelo_id}' ya está descargado")
        return

    print(f"\n📥 Descargando {modelo_id}...")
    print("   Esto puede tardar varios minutos dependiendo de tu conexión.\n")

    def callback_progreso(mensaje):
        print(f"   {mensaje}", flush=True)

    resultado = descargar_modelo_local(modelo_id, callback_progreso)

    if resultado["exito"]:
        print(f"\n✅ {resultado['mensaje']}")
        print(f"💡 Ahora podés usarlo con: !modelo_local {modelo_id}")
    else:
        print(f"\n❌ {resultado['mensaje']}")


def comando_eliminar_modelo(args):
    """Elimina un modelo descargado."""
    if not args:
        print("\n❌ Especificá el modelo a eliminar")
        print("💡 Ejemplo: !eliminar_modelo qwen3:14b")
        return

    modelo_id = args[0]

    if not verificar_modelo_local(modelo_id):
        print(f"\n❌ El modelo '{modelo_id}' no está descargado")
        return

    if modelo_id == MODELO_LOCAL:
        print(f"\n⚠️  No podés eliminar el modelo activo ({modelo_id})")
        print(f"💡 Cambiá a otro modelo primero con: !modelo_local [otro_modelo]")
        return

    confirmar = input(f"¿Eliminar {modelo_id}? (s/n): ").strip().lower()
    if confirmar not in ["s", "si", "sí"]:
        print("❌ Cancelado")
        return

    resultado = eliminar_modelo_local(modelo_id)
    if resultado["exito"]:
        print(f"\n✅ {resultado['mensaje']}")
    else:
        print(f"\n❌ {resultado['mensaje']}")


def comando_hardware():
    """Muestra información del hardware y recomendaciones."""
    print("\n🖥️ INFORMACIÓN DE HARDWARE")
    print("=" * 70)

    hardware = detectar_hardware()

    print(f"\nRAM: {hardware['ram_gb']} GB")
    print(f"GPU: {hardware['gpu']}")
    print(f"VRAM: {hardware['vram_gb']} GB")
    print(f"\nModelo actual: {hardware['modelo_actual']}")
    print(f"\nRecomendación: {hardware['recomendacion']}")
    print(f"\nUpgrade sugerido: {hardware['upgrade_sugerido']}")

    print("\n" + "=" * 70)
    print("\n💡 Para cambiar el modelo local:")
    print("   !modelo_local [nombre_modelo]")
    print("\n💡 Para ver modelos disponibles:")
    print("   !modelos")


# ============================================
# BUCLE PRINCIPAL DEL CHAT
# ============================================

def chat():
    """Bucle principal del chat."""
    print("\n🧠 Atlas Brain activo\n")
    print("Escribe !ayuda para ver comandos\n")
    print("💡 Atlas decide automáticamente qué agente usar según tu pregunta\n")

    if MOTOR_ACTIVO == "atlas":
        print(f"🏠 Motor: Atlas Local ({MODELO_LOCAL})")
    else:
        print(f"☁️ Motor: Prometeo Nube ({MODELO_NUBE_ACTIVO})")

    contador = 0
    pendientes = []
    voz_activa = False

    while True:
        try:
            pregunta = input("\nTú: ").strip()
            if not pregunta:
                continue

            pregunta_lower = pregunta.lower()

            # ============================
            # SALIR
            # ============================
            if pregunta_lower in ["salir", "exit", "quit", "adios", "chau"]:  # ✅ CORREGIDO: sin espacios
                if pendientes:
                    print(f"\n🔍 Analizando {len(pendientes)} pendiente(s)...\n")
                    for p, r in pendientes:
                        analizar_memoria_pendiente(p, r)
                print("\n👋 Hasta luego.\n")
                break

            # ============================
            # !ayuda
            # ============================
            if pregunta_lower == "!ayuda":
                mostrar_ayuda()
                continue

            # ============================
            # !mirar (captura pantalla)
            # ============================
            if pregunta_lower == "!mirar":
                print("\n👁️ Capturando pantalla...")
                ruta, texto = analizar_pantalla()
                if not ruta:
                    print(f"❌ {texto}\n")
                    continue
                print(f"✅ Captura guardada: {ruta}")
                print(f"📝 Texto extraído ({len(texto)} caracteres):\n")
                print(texto[:1000])
                if len(texto) > 1000:
                    print(f"\n... (texto truncado, {len(texto) - 1000} caracteres más)")
                limpiar_capturas_antiguas(max_archivos=10)
                analizar = input("\n¿Querés que analice este texto? (s/n): ").strip().lower()
                if analizar in ["s", "si", "sí"]:
                    pregunta = f"Analizá este texto de mi pantalla:\n\n{texto}"
                else:
                    continue

            # ============================
            # !escuchar (reconocimiento de voz)
            # ============================
            elif pregunta_lower.startswith("!escuchar"):
                partes = pregunta_lower.split()
                duracion = 5
                if len(partes) > 1:
                    try:
                        duracion = int(partes[1])
                    except ValueError:
                        pass
                print(f"\n👂 Preparando micrófono...")
                texto_escuchado = escuchar(duracion)
                if texto_escuchado and not texto_escuchado.startswith("Error") and "No escuché" not in texto_escuchado:
                    print(f"🎤 Dijiste: {texto_escuchado}")
                    usar = input("\n¿Usar esto como pregunta? (s/n): ").strip().lower()
                    if usar in ["s", "si", "sí"]:
                        pregunta = texto_escuchado
                    else:
                        continue
                else:
                    print(f"❌ {texto_escuchado}\n")
                    continue

            # ============================
            # !probar_mic
            # ============================
            elif pregunta_lower in ["!probar_mic", "!test_mic", "!microfono"]:
                probar_microfono()
                continue

            # ============================
            # !hablar (control de voz automática)
            # ============================
            elif pregunta_lower == "!hablar on":
                voz_activa = True
                print("\n🔊 Voz automática activada\n")
                hablar("Voz automática activada")
                continue
            elif pregunta_lower == "!hablar off":
                voz_activa = False
                print("\n🔇 Voz automática desactivada\n")
                hablar("Voz automática desactivada")
                continue

            # ============================
            # !voces (listar voces disponibles)
            # ============================
            elif pregunta_lower == "!voces":
                listar_voces_disponibles()
                continue

            # ============================
            # !agentes
            # ============================
            elif pregunta_lower == "!agentes":
                print("\n🤖 Agentes disponibles:")
                for ag, desc in listar_agentes().items():
                    print(f"  • {ag}: {desc}")
                print("\n💡 No necesitás llamarlos manualmente, Atlas decide solo.\n")
                continue

            # ============================
            # !categorias
            # ============================
            if pregunta_lower == "!categorias":
                print("\n📂 Categorías:")
                for c in listar_categorias():
                    print(f"  • {c}")
                continue

            # ============================
            # !historial
            # ============================
            if pregunta_lower == "!historial":
                info = ver_historial()
                print(f"\n📜 Historial: {info['cantidad']} / {info['maximo']}")
                if info['items']:
                    for i, item in enumerate(info['items'], 1):
                        print(f"  {i}. {item['pregunta'][:60]}...")
                else:
                    print("  (vacío)")
                continue

            # ============================
            # !limpiar_historial
            # ============================
            if pregunta_lower == "!limpiar_historial":
                n = ver_historial()['cantidad']
                if n == 0:
                    print("\nℹ️ Ya está vacío.\n")
                else:
                    limpiar_historial()
                    print(f"\n🗑️ {n} interacciones eliminadas.\n")
                continue

            # ============================
            # !analizar
            # ============================
            if pregunta_lower == "!analizar":
                if pendientes:
                    print(f"\n🔍 Analizando {len(pendientes)} pendiente(s)...\n")
                    for p, r in pendientes:
                        analizar_memoria_pendiente(p, r)
                    pendientes = []
                    contador = 0
                else:
                    print("\nℹ️ Nada pendiente.\n")
                continue

            # ============================
            # !indexar
            # ============================
            if pregunta_lower == "!indexar":
                print("\n🔄 Reconstruyendo índice...")
                try:
                    indice = construir_indice()
                    print(f"✅ {len(indice)} archivos indexados\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # !seguridad
            # ============================
            if pregunta_lower == "!seguridad":
                print("\n🛡️ Reporte de Seguridad Atlas\n")
                print("=" * 60)
                reporte = reporte_seguridad_completo()
                for verificacion, datos in reporte["verificaciones"].items():
                    estado_icono = "✅" if datos["estado"] == "OK" else "⚠️"
                    print(f"\n{estado_icono} {verificacion.replace('_', ' ').title()}")
                    print(f"   Estado: {datos['estado']}")
                    print(f"   {datos['mensaje']}")
                print("\n" + "=" * 60)
                print(f"\n📅 Timestamp: {reporte['timestamp']}")
                print("\n💡 Consejo: Revisá atlas_security.log periódicamente\n")
                continue

            # ============================
            # !autoconocer (informe completo con código)
            # ============================
            if pregunta_lower == "!autoconocer":
                print("\n🪞 Atlas está analizando su propia arquitectura...\n")
                try:
                    from core.self_awareness import generar_reporte_self_awareness
                    print(generar_reporte_self_awareness())
                except ImportError:
                    print("❌ Módulo self_awareness no disponible. Creá core/self_awareness.py\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # !autoconocer_corto (sin código)
            # ============================
            if pregunta_lower == "!autoconocer_corto":
                print("\n🪞 Atlas (resumen sin código)...\n")
                try:
                    from core.self_awareness import generar_reporte_sin_codigo
                    print(generar_reporte_sin_codigo())
                except ImportError:
                    print("❌ Módulo self_awareness no disponible.\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # !informe (exportar informe a archivo)
            # ============================
            if pregunta_lower in ["!informe", "!exportar_informe"]:
                print("\n📄 Generando informe técnico completo...\n")
                try:
                    from core.self_awareness import exportar_reporte_a_archivo
                    ruta = exportar_reporte_a_archivo()
                    print(f"✅ Informe exportado a: {ruta}")
                    print(f"   Podés copiar este archivo y pasarlo a otro modelo.\n")
                except ImportError:
                    print("❌ Módulo self_awareness no disponible.\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # !reflexionar
            # ============================
            if pregunta_lower == "!reflexionar":
                print("\n🧘 Atlas está reflexionando sobre sus conversaciones...\n")
                try:
                    from core.reflection import reflexionar_sobre_conversaciones
                    reflexion = reflexionar_sobre_conversaciones(HISTORIAL)
                    print(reflexion)
                    print("\n" + "-" * 60)
                except ImportError:
                    print("❌ Módulo reflection no disponible. Creá core/reflection.py\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # !mejorar
            # ============================
            if pregunta_lower == "!mejorar":
                print("\n🔍 Atlas está buscando mejores prácticas en la web...\n")
                try:
                    from core.self_improvement import buscar_mejores_practicas
                    from core.self_awareness import generar_reporte_self_awareness
                    contexto = generar_reporte_self_awareness()
                    resultados = buscar_mejores_practicas("RAG local LLM prompt engineering")
                    print(f"📚 Encontré {len(resultados)} recursos relevantes:\n")
                    for i, r in enumerate(resultados[:5], 1):
                        if "error" not in r:
                            print(f"  [{i}] {r.get('titulo', 'Sin título')}")
                            print(f"      {r.get('snippet', '')[:150]}...")
                            print(f"      🔗 {r.get('url', '')}\n")
                    print("\n💡 Para aplicar una mejora específica, pedile a Atlas que analice un área.")
                    print("   Ejemplo: 'mejorá mi sistema de búsqueda de memoria'\n")
                except ImportError:
                    print("❌ Módulo self_improvement no disponible. Creá core/self_improvement.py\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # !exportar_perfil
            # ============================
            if pregunta_lower.startswith("!exportar_perfil"):
                partes = pregunta.split(maxsplit=1)
                nombre = partes[1].strip() if len(partes) > 1 else "charly"
                print(f"\n💾 Exportando perfil '{nombre}'...\n")
                try:
                    from core.profile_manager import exportar_perfil_actual
                    ok, resultado = exportar_perfil_actual(nombre)
                    if ok:
                        print(f"✅ Perfil exportado: {resultado}")
                        print(f"   Podés compartir este archivo con otros usuarios de Atlas.\n")
                    else:
                        print(f"❌ Error: {resultado}\n")
                except ImportError:
                    print("❌ Módulo profile_manager no disponible. Creá core/profile_manager.py\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # !importar_perfil
            # ============================
            if pregunta_lower.startswith("!importar_perfil"):
                partes = pregunta.split(maxsplit=1)
                if len(partes) < 2:
                    print("\n⚠️ Usá: !importar_perfil ruta/al/archivo.zip\n")
                    continue
                ruta = partes[1].strip()
                print(f"\n📥 Importando perfil desde {ruta}...\n")
                print("⚠️  Esto hará backup de tu perfil actual antes de importar.\n")
                confirmar = input("¿Continuar? (s/n): ").strip().lower()
                if confirmar not in ["s", "si", "sí"]:
                    print("❌ Importación cancelada.\n")
                    continue
                try:
                    from core.profile_manager import importar_perfil
                    ok, resultado = importar_perfil(ruta)
                    if ok:
                        print(f"✅ Perfil importado: {resultado}")
                        print("   Reiniciá Atlas para aplicar los cambios.\n")
                    else:
                        print(f"❌ Error: {resultado}\n")
                except ImportError:
                    print("❌ Módulo profile_manager no disponible.\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # !listar_perfiles
            # ============================
            if pregunta_lower == "!listar_perfiles":
                print("\n📋 Perfiles exportados:\n")
                try:
                    from core.profile_manager import listar_perfiles_exportados
                    perfiles = listar_perfiles_exportados()
                    if not perfiles:
                        print("   (no hay perfiles exportados)")
                    else:
                        for p in perfiles:
                            print(f"  • {p['nombre']}")
                            print(f"    Tamaño: {p['tamano_kb']:.2f} KB")
                            print(f"    Fecha: {p['fecha']}")
                            print()
                except ImportError:
                    print("❌ Módulo profile_manager no disponible.\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # !nuevo_perfil
            # ============================
            if pregunta_lower.startswith("!nuevo_perfil"):
                partes = pregunta.split(maxsplit=1)
                if len(partes) < 2:
                    print("\n⚠️ Usá: !nuevo_perfil [nombre_usuario]\n")
                    continue
                nombre = partes[1].strip()
                print(f"\n🆕 Creando perfil nuevo para '{nombre}'...\n")
                print("⚠️  Esto creará una estructura de memoria vacía.")
                print("   Los prompts actuales se mantendrán como base.\n")
                confirmar = input("¿Continuar? (s/n): ").strip().lower()
                if confirmar not in ["s", "si", "sí"]:
                    print("❌ Cancelado.\n")
                    continue
                try:
                    from core.profile_manager import crear_perfil_nuevo
                    ok, resultado = crear_perfil_nuevo(nombre)
                    if ok:
                        print(f"✅ Perfil creado para: {resultado}")
                        print("   Editá los archivos en memory/Atlas_Memory/ para personalizar.\n")
                    else:
                        print(f"❌ Error: {resultado}\n")
                except ImportError:
                    print("❌ Módulo profile_manager no disponible.\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
                continue

            # ============================
            # 🏠 COMANDOS DE MODELOS LOCALES
            # ============================
            if pregunta_lower == "!modelos":
                comando_modelos()
                continue

            if pregunta_lower.startswith("!modelo_local"):
                partes = pregunta.split(maxsplit=1)
                args = partes[1].split() if len(partes) > 1 else []
                comando_modelo_local(args)
                continue

            if pregunta_lower.startswith("!descargar_modelo"):
                partes = pregunta.split(maxsplit=1)
                args = partes[1].split() if len(partes) > 1 else []
                comando_descargar_modelo(args)
                continue

            if pregunta_lower.startswith("!eliminar_modelo"):
                partes = pregunta.split(maxsplit=1)
                args = partes[1].split() if len(partes) > 1 else []
                comando_eliminar_modelo(args)
                continue

            if pregunta_lower == "!hardware":
                comando_hardware()
                continue

            # ============================
            # BRAIN PRINCIPAL
            # ============================
            try:
                respuesta_completa = ""
                agente_mostrado = False
                pensamiento_mostrado = False
                voz_ya_reproducida = False

                for pensamiento, respuesta in pensar_con_streaming(pregunta):
                    if pensamiento and pensamiento.startswith("[Agente:") and not agente_mostrado:
                        print(f"\n{pensamiento}\n", flush=True)
                        agente_mostrado = True
                    elif pensamiento and not pensamiento_mostrado:
                        print(f"\n💭 {pensamiento}\n", flush=True)
                        pensamiento_mostrado = True
                    elif respuesta and respuesta != "🔍 Buscando en la web...":
                        print(f"\n🧠 Atlas:\n{respuesta}\n", flush=True)
                        print("-" * 60, flush=True)
                        respuesta_completa = respuesta
                    elif respuesta == "🔍 Buscando en la web...":
                        print(f"\n{respuesta}\n", flush=True)

                if voz_activa and respuesta_completa:
                    hablar(respuesta_completa)
                    voz_ya_reproducida = True

                if respuesta_completa and len(respuesta_completa) > 50:
                    pendientes.append((pregunta, respuesta_completa))
                    contador += 1

                if contador >= INTERVALO_ANALISIS:
                    print(f"\n🔍 Intervalo alcanzado ({INTERVALO_ANALISIS})...\n")
                    for p, r in pendientes:
                        analizar_memoria_pendiente(p, r)
                    pendientes = []
                    contador = 0

            except KeyboardInterrupt:
                print("\n\n⏹️ Interrumpido.\n")
            except Exception as e:
                print(f"\n❌ Error: {e}\n")

        except KeyboardInterrupt:
            if pendientes:
                print(f"\n\n🔍 Analizando {len(pendientes)} pendiente(s)...\n")
                for p, r in pendientes:
                    analizar_memoria_pendiente(p, r)
            print("\n\n👋 Saliendo...\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":  # ✅ CORREGIDO: __name__ == "__main__"
    try:
        chat()
    except KeyboardInterrupt:
        print("\n\n👋 Hasta luego.\n")
        sys.exit(0)