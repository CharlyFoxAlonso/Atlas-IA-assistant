"""Validador de Skills Atlas — lint + índice de la biblioteca de skills."""

import re
import yaml
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = PROJECT_ROOT / ".opencode" / "skills"
INDEX_FILE = PROJECT_ROOT / ".opencode" / "_index" / "SKILLS_INDEX.md"

REQUIRED_SECTIONS = {
    "domain": [
        "Propósito", "Cuándo usarla", "Cuándo no usarla",
        "Workflow", "Checklist rápido", "Gotchas / Riesgos",
        "Relaciones", "Archivos relacionados", "Validación",
    ],
    "process": [
        "Propósito", "Cuándo usarla", "Cuándo no usarla",
        "Procedimiento", "Reglas", "Formato de salida",
    ],
}

MAX_LINES = {"domain": 200, "process": 250}


def extract_frontmatter(content):
    """Extrae y parsea el frontmatter YAML de un SKILL.md."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def extract_sections(content):
    """Extrae nombres de secciones (## Título)."""
    return re.findall(r"^\s*##\s+(.+)$", content, re.MULTILINE)


IGNORED_COMMANDS = {"python", "pip", "ruff", "mypy", "pytest", "uvicorn", "streamlit", "ollama", "git", "curl", "certutil"}

def extract_referenced_paths(content):
    """Extrae strings entre backticks que parecen rutas de archivo."""
    backtick_items = re.findall(r"`([^`]+)`", content)
    paths = []
    for item in backtick_items:
        item = item.strip()
        # Debe contener / o \ para ser una ruta
        if "/" not in item and "\\" not in item:
            continue
        # Ignorar flags, comandos, URLs, API endpoints, template vars
        if item.startswith("--") or item.startswith("!") or item.startswith("http"):
            continue
        if item.startswith("python") or item.startswith("pip "):
            continue
        if "{" in item or "}" in item:
            continue
        first_word = item.split()[0] if " " in item else item
        if first_word in IGNORED_COMMANDS:
            continue
        # Ignorar API endpoints (POST /, GET /)
        first_part = item.split("/")[0].strip()
        if first_part in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            continue
        paths.append(item)
    return paths


def extract_internal_links(content):
    """Extrae enlaces Markdown a rutas internas."""
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
    internal = []
    for text, url in links:
        if url.startswith("http") or url.startswith("#") or url.startswith("mailto"):
            continue
        internal.append((text, url))
    return internal


def check_path_exists(path_str, skill_dir=None):
    """Verifica si una ruta existe relativa al project root o al directorio de la skill."""
    # Probar relativo al project root
    full = (PROJECT_ROOT / path_str).resolve()
    if full.exists():
        return True
    # Probar relativo al directorio de la skill
    if skill_dir:
        full2 = (skill_dir / path_str).resolve()
        if full2.exists():
            return True
    # Intentar con / reemplazado por \
    full3 = (PROJECT_ROOT / path_str.replace("/", "\\")).resolve()
    return full3.exists()


def validate_skill(skill_dir):
    """Valida una skill y retorna issues + info."""
    issues = []
    skill_file = skill_dir / "SKILL.md"
    name = skill_dir.name

    if not skill_file.exists():
        return [{"rule": "FILE", "severity": "error", "msg": f"SKILL.md no encontrado en {name}"}], None

    content = skill_file.read_text(encoding="utf-8")
    fm = extract_frontmatter(content)

    # F1: Frontmatter válido
    if fm is None:
        issues.append({"rule": "F1", "severity": "error", "msg": f"Frontmatter YAML inválido o ausente"})

    # F2: name existe
    skill_name = fm.get("name", "") if fm else ""
    if not skill_name:
        issues.append({"rule": "F2", "severity": "error", "msg": f"Campo 'name' ausente o vacío"})

    # F3: type existe y es válido
    skill_type = fm.get("type", "") if fm else ""
    if not skill_type:
        issues.append({"rule": "F3", "severity": "error", "msg": f"Campo 'type' ausente"})
    elif skill_type not in ("domain", "process"):
        issues.append({"rule": "F3", "severity": "error", "msg": f"type '{skill_type}' inválido (debe ser domain o process)"})

    # F4: description existe
    description = fm.get("description", "") if fm else ""
    if not description:
        issues.append({"rule": "F4", "severity": "error", "msg": f"Campo 'description' ausente o vacío"})

    # F5: name coincide con carpeta
    if skill_name and skill_name != name:
        issues.append({"rule": "F5", "severity": "error", "msg": f"name '{skill_name}' no coincide con carpeta '{name}'"})

    # S1: Secciones obligatorias según type
    sections = extract_sections(content)
    required = REQUIRED_SECTIONS.get(skill_type, [])
    for sec in required:
        if sec not in sections:
            issues.append({"rule": "S1", "severity": "error", "msg": f"Sección '{sec}' faltante (type={skill_type})"})

    # R1: references/ existe cuando type=domain
    if skill_type == "domain":
        ref_dir = skill_dir / "references"
        if not ref_dir.is_dir():
            issues.append({"rule": "R1", "severity": "error", "msg": "references/ no existe (requerido para type=domain)"})
        else:
            md_files = list(ref_dir.glob("*.md"))
            if not md_files:
                issues.append({"rule": "R1", "severity": "warning", "msg": "references/ existe pero está vacío"})

    # R2: Rutas a archivos existen
    for path_str in extract_referenced_paths(content):
        if not check_path_exists(path_str, skill_dir):
            issues.append({"rule": "R2", "severity": "warning", "msg": f"Ruta no encontrada: '{path_str}'"})

    # R3: Links internos válidos
    for text, url in extract_internal_links(content):
        if not check_path_exists(url, skill_dir):
            issues.append({"rule": "R3", "severity": "warning", "msg": f"Link interno roto: [{text}]({url})"})

    # S2: Tamaño recomendado
    line_count = len(content.splitlines())
    limit = MAX_LINES.get(skill_type, 200)
    if line_count > limit:
        issues.append({"rule": "S2", "severity": "warning", "msg": f"Demasiadas líneas ({line_count}), máximo recomendado {limit}"})

    info = {
        "name": name,
        "type": skill_type,
        "description": str(description)[:200] if description else "",
        "sections": sections,
        "has_references": (skill_dir / "references").is_dir(),
        "line_count": line_count,
        "valid": len([i for i in issues if i["severity"] == "error"]) == 0,
    }

    return issues, info


def generate_index(skills_info):
    """Genera el índice Markdown como side effect del linter."""
    lines = [
        "# Índice de Skills",
        "",
        "Generado automáticamente por `.opencode/scripts/validate-skills.py`",
        "",
        "| Skill | Tipo | Líneas | References | Estado |",
        "|---|---|---|---|---|",
    ]
    for s in sorted(skills_info, key=lambda x: x["name"]):
        tipo = s["type"]
        estado = "OK" if s["valid"] else "!!"
        refs = "Si" if s["has_references"] else "No"
        lines.append(f"| {s['name']} | {tipo} | {s['line_count']} | {refs} | {estado} |")

    lines.append("")
    lines.append("## Skills detectadas")
    lines.append("")
    for s in sorted(skills_info, key=lambda x: x["name"]):
        lines.append(f"### {s['name']}")
        lines.append("")
        if s["description"]:
            lines.append(f"**Descripción:** {s['description']}")
            lines.append("")
        lines.append(f"- **Archivo:** `skills/{s['name']}/SKILL.md`")
        lines.append(f"- **Tipo:** {s['type']}")
        lines.append(f"- **Líneas:** {s['line_count']}")
        lines.append(f"- **References:** {'Sí' if s['has_references'] else 'No'}")
        if s["sections"]:
            lines.append(f"- **Secciones:** {', '.join(s['sections'])}")
        lines.append("")

    return "\n".join(lines)


def main():
    all_issues = []
    all_info = []
    total_errors = 0
    total_warnings = 0

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue

        issues, info = validate_skill(skill_dir)
        if info:
            all_info.append(info)

        err_count = len([i for i in issues if i["severity"] == "error"])
        warn_count = len([i for i in issues if i["severity"] == "warning"])
        total_errors += err_count
        total_warnings += warn_count

        status = "OK" if err_count == 0 else f"{err_count} error(es)"
        label = f"[{status}]" if err_count == 0 else f"[{status}]"
        print(f"{label} {skill_dir.name}")

        for issue in issues:
            sev = "ERROR" if issue["severity"] == "error" else "WARN"
            print(f"       {sev} [{issue['rule']}] {issue['msg']}")

        all_issues.extend(issues)

    # Generar índice (side effect)
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    markdown = generate_index(all_info)
    INDEX_FILE.write_text(markdown, encoding="utf-8")

    print(f"\nResumen: {len(all_info)} skills, {total_errors} errores, {total_warnings} warnings")
    print(f"Índice: {INDEX_FILE}")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
