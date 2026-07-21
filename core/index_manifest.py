"""
core/index_manifest.py
Manifiesto local de indexación incremental (Atlas v4.1).

Registra el estado conocido de cada documento indexado (hash SHA-256,
tamaño, mtime, chunks) para poder decidir qué archivos son nuevos,
cuáles cambiaron, cuáles no se tocaron y cuáles fueron eliminados,
sin releer ni recalcular embeddings de toda la biblioteca.

Propiedades:
- Vive junto a la base vectorial (vector_db/index_manifest.json), es un
  dato local (gitignored) y NO contiene contenido de documentos.
- Escritura atómica: se escribe un .tmp, se hace flush+fsync y se
  reemplaza el original con os.replace().
- Tolerante a fallos: si el manifiesto no existe, empieza vacío; si está
  corrupto, lo respalda antes de reconstruirlo (nunca borra datos).
"""
from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from core import config
from core.security import log_seguridad


def _utc_now_iso() -> str:
    """Timestamp UTC con zona explícita (nunca ingenuo) para persistir."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ManifestEntry:
    """Estado conocido de un documento indexado."""

    relative_path: str
    content_sha256: str
    size_bytes: int
    modified_time_ns: int
    indexed_at: str
    chunk_count: int
    last_operation: str = "indexed"
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManifestEntry":
        """Construye una entrada tolerando claves extra o faltantes menores."""
        return cls(
            relative_path=str(data["relative_path"]),
            content_sha256=str(data.get("content_sha256", "")),
            size_bytes=int(data.get("size_bytes", 0)),
            modified_time_ns=int(data.get("modified_time_ns", 0)),
            indexed_at=str(data.get("indexed_at", "")),
            chunk_count=int(data.get("chunk_count", 0)),
            last_operation=str(data.get("last_operation", "indexed")),
            last_error=data.get("last_error"),
        )


@dataclass
class IndexManifest:
    """Manifiesto de indexación: colección de entradas por ruta relativa."""

    schema_version: int = config.INDEX_SCHEMA_VERSION
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    collection: str = config.COLLECTION_NAME
    documents: Dict[str, ManifestEntry] = field(default_factory=dict)
    # Ruta del respaldo generado al encontrar un manifiesto corrupto (si hubo).
    corrupt_backup_path: Optional[str] = None

    # ----------------------------------------------------------
    # Carga tolerante
    # ----------------------------------------------------------
    @classmethod
    def load(cls, path: Optional[str] = None) -> "IndexManifest":
        """
        Carga el manifiesto desde disco.

        - Si no existe, devuelve uno vacío (caso de adopción inicial).
        - Si está corrupto o es de otro schema, respalda el archivo original
          y devuelve uno vacío. Nunca borra datos ni lanza excepción.
        """
        manifest_path = Path(path or config.INDEX_MANIFEST_PATH)
        manifest = cls()

        if not manifest_path.exists():
            return manifest

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict) or not isinstance(raw.get("documents", {}), dict):
                raise ValueError("estructura de manifiesto inválida")
            if int(raw.get("schema_version", -1)) != config.INDEX_SCHEMA_VERSION:
                raise ValueError(
                    f"schema_version {raw.get('schema_version')} != "
                    f"{config.INDEX_SCHEMA_VERSION}"
                )
        except (OSError, ValueError, json.JSONDecodeError) as e:
            backup = cls._backup_corrupt(manifest_path)
            manifest.corrupt_backup_path = str(backup)
            log_seguridad(
                "INDEX_MANIFEST_CORRUPT",
                f"Manifiesto inválido ({type(e).__name__}: {e}). "
                f"Respaldo: {backup}. Se reconstruye vacío sin tocar ChromaDB.",
            )
            return manifest

        manifest.embedding_model = str(raw.get("embedding_model", manifest.embedding_model))
        manifest.collection = str(raw.get("collection", manifest.collection))
        skipped = 0
        for rel_path, entry_data in raw["documents"].items():
            try:
                entry = ManifestEntry.from_dict(entry_data)
                manifest.documents[entry.relative_path] = entry
            except (KeyError, TypeError, ValueError):
                skipped += 1
        if skipped:
            log_seguridad(
                "INDEX_MANIFEST_ENTRY_SKIPPED",
                f"{skipped} entradas malformadas ignoradas al cargar el manifiesto",
            )
        return manifest

    @staticmethod
    def _backup_corrupt(manifest_path: Path) -> Path:
        """Copia el manifiesto corrupto a un .bak con timestamp UTC."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = manifest_path.with_name(f"{manifest_path.name}.corrupt-{stamp}.bak")
        try:
            shutil.copy2(manifest_path, backup)
        except OSError:
            # Si no se puede copiar, igualmente no se toca el original.
            pass
        return backup

    # ----------------------------------------------------------
    # Guardado atómico
    # ----------------------------------------------------------
    def save(self, path: Optional[str] = None) -> None:
        """
        Escribe el manifiesto de forma atómica:
        manifest.json.tmp -> flush -> fsync -> os.replace().
        Nunca escribe directamente sobre el único archivo válido.
        """
        manifest_path = Path(path or config.INDEX_MANIFEST_PATH)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "schema_version": self.schema_version,
            "embedding_model": self.embedding_model,
            "collection": self.collection,
            "updated_at": _utc_now_iso(),
            "documents": {k: v.to_dict() for k, v in sorted(self.documents.items())},
        }

        tmp_path = manifest_path.with_name(manifest_path.name + ".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, manifest_path)

    # ----------------------------------------------------------
    # Acceso a entradas
    # ----------------------------------------------------------
    def get(self, relative_path: str) -> Optional[ManifestEntry]:
        return self.documents.get(relative_path)

    def upsert(self, entry: ManifestEntry) -> None:
        self.documents[entry.relative_path] = entry

    def remove(self, relative_path: str) -> bool:
        """Elimina la entrada. Idempotente: devuelve True si existía."""
        return self.documents.pop(relative_path, None) is not None
