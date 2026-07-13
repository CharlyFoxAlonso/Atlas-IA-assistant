"""Safe technical CLI for the Atlas system subsystem."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import json
import sys
from typing import Any, Optional, Sequence, TextIO

from core.system.doctor import diagnosticar_sistema
from core.system.healer import ALL_COMPONENTS, Healer, SAFE_COMPONENTS
from core.system.launcher import LAUNCH_TARGETS, Launcher

EXIT_OK = 0
EXIT_NOT_READY = 1
EXIT_ARGUMENT_ERROR = 2
EXIT_OPERATION_FAILED = 3


class AtlasArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(EXIT_ARGUMENT_ERROR, f"{self.prog}: error: {message}\n")


def _parser() -> AtlasArgumentParser:
    examples = """COMANDOS DISPONIBLES:
  help [doctor|heal|launch]       Mostrar ayuda general o de un comando
  doctor [--profile PERFIL]      Diagnosticar sin modificar el sistema
  heal [COMPONENTE]              Simular o aplicar reparaciones explícitas
  launch [--target ui|cli]       Simular o iniciar Atlas

COMPONENTES DE HEALER:
  folders            Preparar carpetas administradas
  config             Crear configuración mínima solamente si falta
  venv               Verificar el runtime privado
  ollama_service     Verificar o iniciar Ollama instalado
  python_packages    Instalar requirements (pesado)
  ollama_model       Descargar el modelo configurado (pesado)

EJEMPLOS:
  python -m core.system doctor
  python -m core.system doctor --profile cli --deep
  python -m core.system doctor --json
  python -m core.system heal
  python -m core.system heal folders
  python -m core.system heal folders --apply
  python -m core.system heal python_packages --apply --allow-heavy
  python -m core.system launch
  python -m core.system launch --target ui --port 8401 --apply
  python -m core.system launch --repair folders --repair config --apply

SEGURIDAD:
  heal and launch are dry-run unless --apply is explicitly provided.
  Heavy repairs additionally require --allow-heavy and are never delegated
  automatically by launch.
"""
    parser = AtlasArgumentParser(
        prog="python -m core.system",
        description="Diagnóstico, reparación segura y arranque técnico de Atlas.",
        epilog=examples,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    help_parser = subparsers.add_parser("help", help="Mostrar ayuda general o de un comando")
    help_parser.add_argument("topic", nargs="?", choices=("doctor", "heal", "launch"))

    doctor = subparsers.add_parser("doctor", help="Inspeccionar Atlas sin modificar el sistema")
    doctor.add_argument("--profile", choices=("ui", "cli", "api"), default="ui", help="Perfil de preparación")
    doctor.add_argument("--deep", action="store_true", help="Probar imports requeridos en procesos aislados")
    doctor.add_argument("--json", action="store_true", help="Emitir únicamente JSON")

    heal = subparsers.add_parser("heal", help="Simular o aplicar una reparación explícita")
    heal.add_argument(
        "component",
        nargs="?",
        default="all",
        choices=("all",) + ALL_COMPONENTS,
        help="Componente a reparar (por defecto: all, solo reparaciones seguras)",
    )
    heal.add_argument("--apply", action="store_true", help="Aplicar cambios reales")
    heal.add_argument(
        "--allow-heavy",
        action="store_true",
        help="Consentir una instalación o descarga pesada; requiere también --apply",
    )
    heal.add_argument("--json", action="store_true", help="Emitir únicamente JSON")

    launch = subparsers.add_parser("launch", help="Simular o iniciar Atlas")
    launch.add_argument("--target", choices=LAUNCH_TARGETS, default="ui", help="Punto de entrada")
    launch.add_argument("--port", type=int, default=8401, help="Puerto de la UI (1-65535)")
    launch.add_argument(
        "--repair",
        action="append",
        choices=SAFE_COMPONENTS,
        default=[],
        help="Reparación segura autorizada antes de iniciar; puede repetirse",
    )
    launch.add_argument("--apply", action="store_true", help="Aplicar reparaciones e iniciar realmente")
    launch.add_argument("--json", action="store_true", help="Emitir únicamente JSON")
    return parser


def _print_command_help(parser: AtlasArgumentParser, topic: Optional[str], stream: TextIO) -> None:
    if topic is None:
        parser.print_help(stream)
        return
    subparser_action = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    subparser_action.choices[topic].print_help(stream)


def _write_json(value: Any, stream: TextIO) -> None:
    stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _runtime_line(diagnosis: dict) -> str:
    python = diagnosis.get("python", {})
    if python.get("in_venv"):
        return f"Runtime: entorno privado activo ({python.get('executable', 'Python')})"
    if diagnosis.get("execution_mode") == "packaged":
        return f"Runtime: aplicación empaquetada ({python.get('executable', 'runtime privado')})"
    return (
        f"Runtime: Python global {python.get('version', 'desconocido')}. "
        "Atlas debería ejecutarse dentro de .venv; no se instalarán paquetes en este runtime."
    )


def _human_doctor(report: dict, stream: TextIO) -> None:
    state = "LISTO" if report.get("ready_to_start") else "NO LISTO"
    stream.write(f"Atlas Doctor — {state}\n")
    stream.write(f"Salud: {report.get('health_score', 0)}/100\n")
    stream.write(_runtime_line(report) + "\n")
    stream.write(f"Datos: {report.get('data_location', 'desconocido')}\n")
    critical = report.get("critical_issues", [])
    warnings = report.get("warnings", [])
    if critical:
        stream.write("Problemas críticos:\n")
        for item in critical:
            stream.write(f"  - {item}\n")
    if warnings:
        stream.write("Advertencias:\n")
        for item in warnings:
            stream.write(f"  - {item}\n")
    enabled = [name for name, value in report.get("capabilities", {}).items() if value]
    stream.write("Capacidades disponibles: " + (", ".join(enabled) if enabled else "ninguna") + "\n")


def _human_repair(report: dict, stream: TextIO) -> None:
    mode = "APLICACIÓN REAL" if not report.get("dry_run", True) else "SIMULACIÓN"
    stream.write(f"Atlas Healer — {mode}\n")
    results = report.get("results", [report])
    for result in results:
        status = "OK" if result.get("success") else "FALLO/ADVERTENCIA"
        stream.write(f"  [{status}] {result.get('component')}: {result.get('message', '')}\n")
    if report.get("dry_run", True):
        stream.write("No se realizó ningún cambio. Usá --apply para aplicar esta operación.\n")


def _human_launch(report: dict, stream: TextIO) -> None:
    if report.get("dry_run", True):
        stream.write("Atlas Launcher — SIMULACIÓN\n")
    else:
        stream.write("Atlas Launcher — EJECUCIÓN REAL\n")
    stream.write(report.get("message", "") + "\n")
    diagnosis = report.get("diagnosis") or {}
    if diagnosis:
        stream.write(_runtime_line(diagnosis) + "\n")
    if report.get("dry_run", True):
        stream.write("No se inició ningún proceso. Usá --apply para iniciar Atlas.\n")


def _doctor_exit(report: dict) -> int:
    if not report.get("ready_to_start", False) or report.get("warnings"):
        return EXIT_NOT_READY
    return EXIT_OK


def _doctor(args: argparse.Namespace, stdout: TextIO) -> int:
    report = diagnosticar_sistema(profile=args.profile, deep_packages=args.deep)
    if args.json:
        _write_json(report, stdout)
    else:
        _human_doctor(report, stdout)
    return _doctor_exit(report)


def _heal(args: argparse.Namespace, stdout: TextIO) -> int:
    if args.allow_heavy and not args.apply:
        raise ValueError("--allow-heavy requiere --apply")
    if args.component in ("python_packages", "ollama_model") and args.apply and not args.allow_heavy:
        raise ValueError("las reparaciones pesadas requieren --apply y --allow-heavy")

    healer = Healer(dry_run=not args.apply, allow_heavy=args.allow_heavy)
    if args.component == "all":
        report = healer.fix_all(include_heavy=args.allow_heavy)
    else:
        result = healer.fix(args.component)
        report = {
            "success": result.success,
            "dry_run": result.dry_run,
            "results": [result.to_dict()],
        }
    if args.json:
        _write_json(report, stdout)
    else:
        _human_repair(report, stdout)
    if report.get("success"):
        return EXIT_OK
    return EXIT_OPERATION_FAILED if args.apply else EXIT_NOT_READY


def _launch(args: argparse.Namespace, stdout: TextIO) -> int:
    result = Launcher(dry_run=not args.apply).launch(
        target=args.target,
        port=args.port,
        authorized_repairs=args.repair,
    )
    report = result.to_dict()
    if args.json:
        _write_json(report, stdout)
    else:
        _human_launch(report, stdout)
    return EXIT_OK if result.success else EXIT_OPERATION_FAILED


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = _parser()
    arguments = list(argv) if argv is not None else None
    try:
        with redirect_stdout(out), redirect_stderr(err):
            args = parser.parse_args(arguments)
        if args.command is None:
            parser.print_help(out)
            return EXIT_OK
        if args.command == "help":
            _print_command_help(parser, args.topic, out)
            return EXIT_OK
        if args.command == "doctor":
            return _doctor(args, out)
        if args.command == "heal":
            return _heal(args, out)
        if args.command == "launch":
            return _launch(args, out)
    except ValueError as exc:
        err.write(f"Error de argumentos: {exc}\n")
        return EXIT_ARGUMENT_ERROR
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else EXIT_ARGUMENT_ERROR
    except KeyboardInterrupt:
        err.write("Operación cancelada por el usuario.\n")
        return EXIT_OPERATION_FAILED
    except Exception as exc:
        err.write(f"La operación falló: {type(exc).__name__}: {exc}\n")
        return EXIT_OPERATION_FAILED
    return EXIT_ARGUMENT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
