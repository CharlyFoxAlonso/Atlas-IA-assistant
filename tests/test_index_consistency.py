"""
tests/test_index_consistency.py
Pruebas del verificador de consistencia de solo lectura (IDX-C1).

No requieren Ollama, APIs, Internet ni ChromaDB real: el adaptador Chroma
se reemplaza por fakes y los archivos viven en directorios temporales.
Verifican el contrato de solo lectura (SDD §7): cero escritura, cero
creación, cero embeddings, cero proveedores.
"""
import hashlib
import json
import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest import mock

from core.index_consistency import (
    ConsistencyIssue,
    ConsistencyReport,
    ConsistencyState,
    DivergenceCategory,
    ORPHAN_SAMPLE_LIMIT,
    VERIFICATION_LIMITATION,
    _agregar_issue,
    _crear_issue,
    _render_issue,
    verificar_consistencia,
)
from core.system.paths import LegacyVectorStoreError
from core.vector_store import (
    ChromaReadStatus,
    IDX_PUBLIC_ERROR_MESSAGES,
    _ChromaReadAccess,
)

SECRET = "SYNTHETIC_SECRET_TOKEN"
PRIVATE_MARKERS = (
    SECRET,
    r"C:\Users\delfa",
    "C:/Users/delfa",
    r"\\server\share",
    "//server/share",
    "/home/delfa",
    "/tmp",
    "/var/log/app.log",
    "https://example.org/private/path",
    "http://localhost:8000/api",
    "Documents/private.txt",
    "private.txt",
    "RAW_BACKEND_MESSAGE",
)
LEGACY_ISSUE = (
    "legacy_vector_store_detected: Legacy vector store detected; configured "
    "vector storage is unavailable until storage is moved or ATLAS_DATA_DIR "
    "is restored. [LegacyVectorStoreError]"
)
CHROMA_BACKEND_ISSUE = (
    "chroma_backend_unavailable: Chroma backend unavailable while opening "
    "existing collection. [RuntimeError]"
)
CHROMA_COLLECTION_ISSUE = (
    "chroma_collection_read_failed: Chroma collection could not be read. "
    "[RuntimeError]"
)
RAW_CHROMA_ISSUE = (
    "raw_chroma_error_rejected: Chroma read access reported an unsafe "
    "external error. [Exception]"
)

CONTENIDO = (
    "Texto de prueba suficientemente largo para superar el mínimo de "
    "cincuenta caracteres que exige agregar_documento. " * 3
)


def sha256_de(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def escribir(base, rel_path, contenido=CONTENIDO):
    ruta = os.path.join(base, rel_path)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return ruta


def escribir_manifest(path, documents=None, schema_version=1, corrupt=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if corrupt:
        with open(path, "w", encoding="utf-8") as f:
            f.write("{ json roto ,,,")
        return
    payload = {
        "schema_version": schema_version,
        "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
        "collection": "atlas_rag",
        "documents": documents or {},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def entrada_para(ruta, rel, chunk_count=3):
    stat = os.stat(ruta)
    return {
        "relative_path": rel,
        "content_sha256": sha256_de(ruta),
        "size_bytes": stat.st_size,
        "modified_time_ns": stat.st_mtime_ns,
        "indexed_at": "2026-08-01T00:00:00+00:00",
        "chunk_count": chunk_count,
        "last_operation": "indexed",
        "last_error": None,
    }


def cadenas_publicas(valor):
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for k, v in valor.items():
            yield from cadenas_publicas(k)
            yield from cadenas_publicas(v)
    elif isinstance(valor, (list, tuple, set)):
        for item in valor:
            yield from cadenas_publicas(item)


def assert_sin_datos_privados(testcase, valor):
    texto = "\n".join(cadenas_publicas(valor))
    for marcador in PRIVATE_MARKERS:
        testcase.assertNotIn(marcador, texto)


class FakeCollection:
    """Colección en memoria compatible con el acceso de solo lectura."""

    def __init__(self, chunks=None):
        # chunks: dict id -> metadata (dict) o None
        self.chunks = chunks or {}

    def get(self, include=None):
        ids = list(self.chunks.keys())
        metadatas = [self.chunks[cid] for cid in ids]
        return {"ids": ids, "metadatas": metadatas}


class CasoBase(unittest.TestCase):
    """Fixture común: base temporal + manifiesto + adaptador Chroma fake."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.join(self.tmp.name, "Atlas_Memory")
        os.makedirs(self.base)
        self.vector_dir = os.path.join(self.tmp.name, "vector_db")
        os.makedirs(self.vector_dir)
        self.manifest_path = os.path.join(self.vector_dir, "index_manifest.json")
        self.chroma_path = self.vector_dir

    def _parchear_chroma(self, acceso):
        # Un FakeCollection se envuelve en el acceso interno para que el
        # verificador lea metadata pública y use el handle solo internamente.
        if isinstance(acceso, FakeCollection):
            acceso = _ChromaReadAccess(
                ChromaReadStatus(
                    root_present=True,
                    collection_present=True,
                ),
                collection=acceso,
            )
        elif isinstance(acceso, ChromaReadStatus):
            acceso = _ChromaReadAccess(acceso)
        parche = mock.patch(
            "core.index_consistency._abrir_coleccion_existente",
            return_value=acceso,
        )
        parche.start()
        self.addCleanup(parche.stop)
        return parche

    def _verificar(self, **kwargs):
        return verificar_consistencia(
            memoria_base=self.base,
            manifest_path=self.manifest_path,
            chroma_path=self.chroma_path,
            collection_name="atlas_rag",
            **kwargs,
        )


class EstadosNominalesTests(CasoBase):

    def test_healthy_observado_y_publicado_degraded(self):
        ruta = escribir(self.base, "doc.md")
        rel = "doc.md"
        escribir_manifest(self.manifest_path, {rel: entrada_para(ruta, rel)})
        self._parchear_chroma(FakeCollection({f"{rel}:chunk:0": {"doc_id": rel}}))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.HEALTHY.value)
        self.assertEqual(reporte.published_state, ConsistencyState.DEGRADED.value)
        self.assertEqual(reporte.sources_count, 1)
        self.assertEqual(reporte.manifest_entries_count, 1)
        self.assertEqual(reporte.chunk_count, 1)
        self.assertEqual(reporte.divergences, {})
        self.assertEqual(reporte.orphan_count, 0)
        self.assertFalse(reporte.writer_state_known)
        self.assertFalse(reporte.writer_active)
        self.assertTrue(reporte.possibly_transient)
        self.assertTrue(reporte.checked_at.endswith("+00:00"))

    def test_healthy_empty_observado_y_publicado_degraded(self):
        # Sin fuentes, sin manifiesto, sin Chroma.
        self._parchear_chroma(ChromaReadStatus(root_present=False))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.HEALTHY_EMPTY.value)
        self.assertEqual(reporte.published_state, ConsistencyState.DEGRADED.value)
        self.assertEqual(reporte.sources_count, 0)
        self.assertEqual(reporte.manifest_entries_count, 0)
        self.assertEqual(reporte.chunk_count, 0)
        self.assertEqual(reporte.divergences, {})


class CategoriasInconsistentTests(CasoBase):

    def test_source_and_manifest_present_chroma_absent(self):
        ruta = escribir(self.base, "doc.md")
        rel = "doc.md"
        escribir_manifest(self.manifest_path, {rel: entrada_para(ruta, rel)})
        self._parchear_chroma(
            ChromaReadStatus(root_present=True, collection_present=True)
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(
                DivergenceCategory.SOURCE_AND_MANIFEST_PRESENT_CHROMA_ABSENT.value
            ),
            1,
        )

    def test_source_present_manifest_stale_chroma_present(self):
        ruta = escribir(self.base, "doc.md")
        rel = "doc.md"
        stat = os.stat(ruta)
        # Entrada con huella vieja (contenido distinto).
        escribir_manifest(self.manifest_path, {
            rel: {
                "relative_path": rel,
                "content_sha256": "0" * 64,
                "size_bytes": stat.st_size + 1,
                "modified_time_ns": stat.st_mtime_ns + 1,
                "indexed_at": "2026-08-01T00:00:00+00:00",
                "chunk_count": 1,
                "last_operation": "indexed",
                "last_error": None,
            }
        })
        self._parchear_chroma(FakeCollection({rel: {"doc_id": rel}}))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(
                DivergenceCategory.SOURCE_PRESENT_MANIFEST_STALE_CHROMA_PRESENT.value
            ),
            1,
        )

    def test_source_present_manifest_metadata_stale_content_same(self):
        ruta = escribir(self.base, "doc.md")
        rel = "doc.md"
        stat = os.stat(ruta)
        # Entrada con el MISMO sha pero size/mtime viejos.
        escribir_manifest(self.manifest_path, {
            rel: {
                "relative_path": rel,
                "content_sha256": sha256_de(ruta),
                "size_bytes": stat.st_size + 1,
                "modified_time_ns": stat.st_mtime_ns + 1,
                "indexed_at": "2026-08-01T00:00:00+00:00",
                "chunk_count": 1,
                "last_operation": "indexed",
                "last_error": None,
            }
        })
        self._parchear_chroma(FakeCollection({rel: {"doc_id": rel}}))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(
                DivergenceCategory.SOURCE_PRESENT_MANIFEST_METADATA_STALE_CONTENT_SAME.value
            ),
            1,
        )

    def test_source_present_manifest_absent_chroma_present(self):
        rel = "doc.md"
        escribir(self.base, rel)
        self._parchear_chroma(FakeCollection({rel: {"doc_id": rel}}))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(
                DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_PRESENT.value
            ),
            1,
        )

    def test_source_present_manifest_absent_chroma_absent(self):
        escribir(self.base, "doc.md")
        self._parchear_chroma(
            ChromaReadStatus(root_present=True, collection_present=True)
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(
                DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_ABSENT.value
            ),
            1,
        )

    def test_source_absent_manifest_present(self):
        rel = "doc.md"
        escribir_manifest(self.manifest_path, {
            rel: {
                "relative_path": rel,
                "content_sha256": "0" * 64,
                "size_bytes": 1,
                "modified_time_ns": 1,
                "indexed_at": "2026-08-01T00:00:00+00:00",
                "chunk_count": 1,
                "last_operation": "indexed",
                "last_error": None,
            }
        })
        self._parchear_chroma(
            ChromaReadStatus(root_present=True, collection_present=True)
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(
                DivergenceCategory.SOURCE_ABSENT_MANIFEST_PRESENT.value
            ),
            1,
        )

    def test_source_absent_chroma_present_orphans(self):
        rel = "doc.md"
        self._parchear_chroma(FakeCollection({rel: {"doc_id": rel}}))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(
                DivergenceCategory.SOURCE_ABSENT_CHROMA_PRESENT.value
            ),
            1,
        )
        self.assertEqual(reporte.orphan_count, 1)
        self.assertEqual(reporte.orphan_sample, (rel,))

    def test_orphan_sample_limited(self):
        chunks = {}
        for i in range(ORPHAN_SAMPLE_LIMIT + 5):
            cid = f"orphan:{i}"
            chunks[cid] = {"doc_id": f"fantasma/{i}.md"}
        self._parchear_chroma(FakeCollection(chunks))

        reporte = self._verificar()

        self.assertEqual(reporte.orphan_count, ORPHAN_SAMPLE_LIMIT + 5)
        self.assertEqual(len(reporte.orphan_sample), ORPHAN_SAMPLE_LIMIT)

    def test_manifest_absent_with_sources(self):
        escribir(self.base, "doc.md")
        # Chroma con chunks: la capa de manifiesto es la única ausente.
        self._parchear_chroma(FakeCollection({"doc.md": {"doc_id": "doc.md"}}))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(DivergenceCategory.MANIFEST_ABSENT.value),
            1,
        )

    def test_chroma_absent_with_sources(self):
        ruta = escribir(self.base, "doc.md")
        rel = "doc.md"
        escribir_manifest(self.manifest_path, {rel: entrada_para(ruta, rel)})
        self._parchear_chroma(ChromaReadStatus(root_present=False))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(DivergenceCategory.CHROMA_ABSENT.value),
            1,
        )

    def test_chroma_collection_absent_with_sources(self):
        ruta = escribir(self.base, "doc.md")
        rel = "doc.md"
        escribir_manifest(self.manifest_path, {rel: entrada_para(ruta, rel)})
        self._parchear_chroma(
            ChromaReadStatus(root_present=True, collection_present=False)
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(DivergenceCategory.CHROMA_COLLECTION_ABSENT.value),
            1,
        )

    def test_manifest_and_chroma_empty_sources_present(self):
        escribir(self.base, "doc.md")
        self._parchear_chroma(ChromaReadStatus(root_present=False))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.INCONSISTENT.value)
        self.assertEqual(
            reporte.divergences.get(
                DivergenceCategory.MANIFEST_AND_CHROMA_EMPTY_SOURCES_PRESENT.value
            ),
            1,
        )


class EstadosUnavailableTests(CasoBase):

    def test_manifest_corrupt_sin_backup(self):
        escribir(self.base, "doc.md")
        escribir_manifest(self.manifest_path, corrupt=True)
        self._parchear_chroma(
            ChromaReadStatus(root_present=True, collection_present=True)
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.UNAVAILABLE.value)
        self.assertEqual(reporte.published_state, ConsistencyState.UNAVAILABLE.value)
        self.assertTrue(reporte.manifest_present)
        self.assertTrue(reporte.manifest_corrupt)
        self.assertEqual(
            reporte.divergences.get(DivergenceCategory.MANIFEST_CORRUPT.value),
            1,
        )
        # No se creó ningún respaldo .bak (SDD §7.2).
        backups = [f for f in os.listdir(self.vector_dir) if ".corrupt-" in f]
        self.assertEqual(backups, [])

    def test_manifest_schema_incompatible(self):
        escribir(self.base, "doc.md")
        escribir_manifest(self.manifest_path, schema_version=99)
        self._parchear_chroma(
            ChromaReadStatus(root_present=True, collection_present=True)
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.UNAVAILABLE.value)
        self.assertTrue(reporte.manifest_schema_incompatible)
        self.assertEqual(
            reporte.divergences.get(
                DivergenceCategory.MANIFEST_SCHEMA_INCOMPATIBLE.value
            ),
            1,
        )

    def test_chroma_unavailable(self):
        escribir(self.base, "doc.md")
        self._parchear_chroma(
            ChromaReadStatus(
                root_present=True,
                collection_present=True,
                unavailable=True,
                error_code="chroma_backend_unavailable",
                error_type="RuntimeError",
            )
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.UNAVAILABLE.value)
        self.assertTrue(reporte.chroma_unavailable)
        self.assertEqual(
            reporte.divergences.get(DivergenceCategory.CHROMA_UNAVAILABLE.value),
            1,
        )
        self.assertEqual(reporte.issues, (CHROMA_BACKEND_ISSUE,))


class EstadosDegradedTests(CasoBase):

    def test_entradas_malformadas_aislables(self):
        ruta = escribir(self.base, "doc.md")
        rel = "doc.md"
        escribir_manifest(self.manifest_path, {
            rel: entrada_para(ruta, rel),
            "malformada.md": {"sin_campos": True},
        })
        self._parchear_chroma(FakeCollection({rel: {"doc_id": rel}}))

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.DEGRADED.value)
        self.assertEqual(reporte.manifest_entries_count, 1)

    def test_verification_limitation_por_sha_ilegible(self):
        ruta = escribir(self.base, "doc.md")
        rel = "doc.md"
        stat = os.stat(ruta)
        escribir_manifest(self.manifest_path, {
            rel: {
                "relative_path": rel,
                "content_sha256": "0" * 64,
                "size_bytes": stat.st_size + 1,
                "modified_time_ns": stat.st_mtime_ns + 1,
                "indexed_at": "2026-08-01T00:00:00+00:00",
                "chunk_count": 1,
                "last_operation": "indexed",
                "last_error": None,
            }
        })
        self._parchear_chroma(FakeCollection({rel: {"doc_id": rel}}))

        with mock.patch(
            "core.index_consistency._sha256_archivo",
            side_effect=OSError("permiso denegado"),
        ):
            reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.DEGRADED.value)
        self.assertEqual(reporte.divergences.get(VERIFICATION_LIMITATION), 1)

    def test_path_error_por_legacy_vector_store(self):
        # Sin fuentes ni manifiesto: sin divergencias accionables, por lo
        # que el único factor es el path_error → DEGRADED (SDD §5).
        with mock.patch(
            "core.index_consistency.validate_vector_store_path",
            side_effect=LegacyVectorStoreError(
                "Possible legacy vector store detected"
            ),
        ):
            reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.DEGRADED.value)
        self.assertEqual(reporte.path_error, LEGACY_ISSUE)
        self.assertEqual(reporte.issues, (LEGACY_ISSUE,))


class ContratoSoloLecturaTests(CasoBase):

    def test_no_escribe_ni_crea_ni_embebe(self):
        ruta = escribir(self.base, "doc.md")
        rel = "doc.md"
        escribir_manifest(self.manifest_path, {rel: entrada_para(ruta, rel)})
        self._parchear_chroma(FakeCollection({rel: {"doc_id": rel}}))

        with mock.patch("core.index_manifest.IndexManifest.load") as espia_load, \
             mock.patch("core.security.log_seguridad") as espia_log, \
             mock.patch("core.vector_store.agregar_documento") as espia_agregar, \
             mock.patch("core.vector_store.eliminar_documento") as espia_eliminar, \
             mock.patch("core.vector_store._get_collection") as espia_get_collection:
            reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.HEALTHY.value)
        espia_load.assert_not_called()
        espia_log.assert_not_called()
        espia_agregar.assert_not_called()
        espia_eliminar.assert_not_called()
        espia_get_collection.assert_not_called()

    def test_nunca_lanza_ante_errores_de_coleccion(self):
        class ColeccionRota:
            def get(self, include=None):
                raise RuntimeError("backend caído")

        self._parchear_chroma(
            _ChromaReadAccess(
                ChromaReadStatus(
                    root_present=True,
                    collection_present=True,
                ),
                collection=ColeccionRota(),
            )
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.UNAVAILABLE.value)
        self.assertTrue(reporte.chroma_unavailable)

    def test_ignora_carpetas_y_extensiones_no_soportadas(self):
        os.makedirs(os.path.join(self.base, "__pycache__"), exist_ok=True)
        os.makedirs(os.path.join(self.base, "temp_ingestion"), exist_ok=True)
        escribir(self.base, "__pycache__/cache.md")
        escribir(self.base, "temp_ingestion/tmp.md")
        escribir(self.base, "nota.xyz")
        self._parchear_chroma(
            ChromaReadStatus(root_present=True, collection_present=True)
        )

        reporte = self._verificar()

        self.assertEqual(reporte.sources_count, 0)
        self.assertEqual(reporte.observed_state, ConsistencyState.HEALTHY_EMPTY.value)

    def test_identidad_legacy_ruta_normalizada(self):
        # Chunk con metadata 'ruta' con separador de Windows: se normaliza.
        rel = "carpeta/doc.md"
        ruta = escribir(self.base, rel)
        escribir_manifest(self.manifest_path, {rel: entrada_para(ruta, rel)})
        self._parchear_chroma(
            FakeCollection({rel: {"ruta": "carpeta\\doc.md"}})
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.HEALTHY.value)
        self.assertEqual(reporte.chunk_count, 1)


class RemediacionObsTests(CasoBase):
    """Cierre de OBS-02 (sanitización de errores) y OBS-04 (orden de huérfanos)."""

    class ColeccionConRutaWindows:
        def get(self, include=None):
            raise RuntimeError(
                "no se pudo abrir 'C:\\Users\\delfa\\AppData\\Local\\Temp\\"
                f"vector_db\\chroma.sqlite3' {SECRET}"
            )

    class ColeccionConRutaPosix:
        def get(self, include=None):
            raise RuntimeError(
                f"no se pudo abrir '/home/delfa/My Documents/private.txt' {SECRET}"
            )

    def test_issues_sanitize_windows_path(self):
        self._parchear_chroma(
            _ChromaReadAccess(
                ChromaReadStatus(
                    root_present=True,
                    collection_present=True,
                ),
                collection=self.ColeccionConRutaWindows(),
            )
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.UNAVAILABLE.value)
        self.assertTrue(reporte.chroma_unavailable)
        self.assertEqual(reporte.issues, (CHROMA_COLLECTION_ISSUE,))
        assert_sin_datos_privados(self, asdict(reporte))

    def test_issues_sanitize_posix_path(self):
        self._parchear_chroma(
            _ChromaReadAccess(
                ChromaReadStatus(
                    root_present=True,
                    collection_present=True,
                ),
                collection=self.ColeccionConRutaPosix(),
            )
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.UNAVAILABLE.value)
        self.assertTrue(reporte.chroma_unavailable)
        self.assertEqual(reporte.issues, (CHROMA_COLLECTION_ISSUE,))
        assert_sin_datos_privados(self, asdict(reporte))

    def test_path_error_sanitized(self):
        with mock.patch(
            "core.index_consistency.validate_vector_store_path",
            side_effect=LegacyVectorStoreError(
                f"legacy store detectado en 'C:\\Users\\delfa\\legacy\\vector_db' {SECRET}"
            ),
        ):
            reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.DEGRADED.value)
        self.assertEqual(reporte.path_error, LEGACY_ISSUE)
        self.assertEqual(reporte.issues, (LEGACY_ISSUE,))
        assert_sin_datos_privados(self, asdict(reporte))

    def test_error_crudo_del_adaptador_se_sanitiza_y_no_duplica_issues(self):
        error = (
            r"RuntimeError: C:\Users\delfa\private.txt "
            f"{SECRET}"
        )
        self._parchear_chroma(
            ChromaReadStatus(
                root_present=True,
                collection_present=True,
                unavailable=True,
                error=error,
            )
        )

        reporte = self._verificar()

        self.assertEqual(reporte.issues, (RAW_CHROMA_ISSUE,))
        assert_sin_datos_privados(self, asdict(reporte))
        self.assertEqual(len(reporte.issues), len(set(reporte.issues)))

    def test_allowlist_cubre_las_ramas_idx_c1(self):
        self.assertEqual(
            set(IDX_PUBLIC_ERROR_MESSAGES),
            {
                "legacy_vector_store_detected",
                "chroma_backend_unavailable",
                "chroma_collection_read_failed",
                "consistency_verification_failed",
                "raw_chroma_error_rejected",
            },
        )
        self.assertEqual(
            _render_issue(
                _crear_issue(
                    "legacy_vector_store_detected",
                    LegacyVectorStoreError(f"C:\\Users\\delfa\\legacy {SECRET}"),
                )
            ),
            LEGACY_ISSUE,
        )
        self.assertEqual(
            _render_issue(_crear_issue("chroma_backend_unavailable", RuntimeError())),
            CHROMA_BACKEND_ISSUE,
        )
        self.assertEqual(
            _render_issue(_crear_issue("chroma_collection_read_failed", RuntimeError())),
            CHROMA_COLLECTION_ISSUE,
        )
        self.assertEqual(
            _render_issue(_crear_issue("raw_chroma_error_rejected", "SecretError")),
            RAW_CHROMA_ISSUE,
        )
        self.assertEqual(
            _render_issue(
                _crear_issue("consistency_verification_failed", RuntimeError())
            ),
            "consistency_verification_failed: Consistency verification "
            "encountered an internal error. [RuntimeError]",
        )

    def test_deduplica_por_codigo_componente_y_tipo_seguro(self):
        issues = []
        primero = ConsistencyIssue(
            code="raw_chroma_error_rejected",
            component="chroma",
            public_message="mensaje publico uno",
            error_type="Exception",
        )
        segundo = ConsistencyIssue(
            code="raw_chroma_error_rejected",
            component="chroma",
            public_message="otro mensaje",
            error_type="Exception",
        )

        _agregar_issue(issues, primero)
        _agregar_issue(issues, segundo)

        self.assertEqual(issues, [primero])

    def test_tipo_de_error_desconocido_se_publica_como_exception(self):
        class ErrorPrivadoDelBackend(Exception):
            pass

        class ColeccionConTipoDesconocido:
            def get(self, include=None):
                raise ErrorPrivadoDelBackend(
                    f"/var/log/app.log C:/Users/delfa/private.txt {SECRET}"
                )

        self._parchear_chroma(
            _ChromaReadAccess(
                ChromaReadStatus(
                    root_present=True,
                    collection_present=True,
                ),
                collection=ColeccionConTipoDesconocido(),
            )
        )

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.UNAVAILABLE.value)
        self.assertEqual(
            reporte.issues,
            (
                "chroma_collection_read_failed: Chroma collection could not be read. "
                "[Exception]",
            ),
        )
        assert_sin_datos_privados(self, asdict(reporte))

    def test_handle_interno_no_se_serializa_en_reporte_ni_status(self):
        class ColeccionConSecretoInterno:
            def __init__(self):
                self.secret = (
                    r"C:\Users\delfa\private.txt "
                    f"{SECRET} RAW_BACKEND_MESSAGE"
                )

            def get(self, include=None):
                return {"ids": [], "metadatas": []}

        status = ChromaReadStatus(root_present=True, collection_present=True)
        acceso = _ChromaReadAccess(status, collection=ColeccionConSecretoInterno())
        self._parchear_chroma(acceso)

        reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.HEALTHY_EMPTY.value)
        self.assertNotIn("collection", asdict(status))
        assert_sin_datos_privados(self, asdict(status))
        assert_sin_datos_privados(self, asdict(reporte))
        self.assertEqual(reporte.issues, ())
        self.assertIsNone(reporte.path_error)

    def test_invariante_recursiva_rechaza_texto_crudo_en_campos_publicos(self):
        entradas = (
            (
                ChromaReadStatus(
                    root_present=True,
                    collection_present=True,
                    unavailable=True,
                    error=(
                        r"C:\Users\delfa\private.txt "
                        f"{SECRET} \\\\server\\share\\private.txt "
                        "//server/share/private.txt "
                        "/home/delfa/My Documents/private.txt /tmp "
                        "https://example.org/private/path "
                        "http://localhost:8000/api docs/file.md core/module.py"
                    ),
                ),
                (),
            ),
            (
                _ChromaReadAccess(
                    ChromaReadStatus(
                        root_present=True,
                        collection_present=True,
                    ),
                    collection=self.ColeccionConRutaWindows(),
                ),
                (),
            ),
        )
        for acceso, parches in entradas:
            self._parchear_chroma(acceso)
            reporte = self._verificar()
            assert_sin_datos_privados(self, asdict(reporte))
            for parche in parches:
                parche.stop()

        with mock.patch(
            "core.index_consistency.validate_vector_store_path",
            side_effect=LegacyVectorStoreError(
                f"//server/share/private.txt {SECRET}"
            ),
        ):
            reporte = self._verificar()
        assert_sin_datos_privados(self, asdict(reporte))

        with mock.patch(
            "core.index_consistency._inventariar_fuentes",
            side_effect=RuntimeError(
                f"/tmp {SECRET} https://example.org/private/path"
            ),
        ):
            reporte = self._verificar()
        assert_sin_datos_privados(self, asdict(reporte))

    def test_orphan_sample_orden_determinista(self):
        chunks_a = {
            "orphan:z": {"doc_id": "f/z.md"},
            "orphan:a": {"doc_id": "f/a.md"},
            "orphan:m": {"doc_id": "f/m.md"},
        }
        chunks_b = {
            "orphan:m": {"doc_id": "f/m.md"},
            "orphan:z": {"doc_id": "f/z.md"},
            "orphan:a": {"doc_id": "f/a.md"},
        }
        self._parchear_chroma(FakeCollection(chunks_a))
        reporte_a = self._verificar()
        self._parchear_chroma(FakeCollection(chunks_b))
        reporte_b = self._verificar()

        self.assertEqual(
            reporte_a.orphan_sample, ("orphan:a", "orphan:m", "orphan:z")
        )
        self.assertEqual(reporte_a.orphan_sample, reporte_b.orphan_sample)
        self.assertEqual(reporte_a.orphan_count, 3)
        self.assertEqual(reporte_b.orphan_count, 3)

    def test_orphan_sample_limite_sigue_siendo_10(self):
        self.assertEqual(ORPHAN_SAMPLE_LIMIT, 10)
        chunks = {}
        for i in range(ORPHAN_SAMPLE_LIMIT + 5):
            chunks[f"orphan:{i:02d}"] = {"doc_id": f"fantasma/{i}.md"}
        self._parchear_chroma(FakeCollection(chunks))

        reporte = self._verificar()

        self.assertEqual(reporte.orphan_count, ORPHAN_SAMPLE_LIMIT + 5)
        self.assertEqual(len(reporte.orphan_sample), ORPHAN_SAMPLE_LIMIT)
        # Orden lexicográfico determinista de los chunk ids.
        self.assertEqual(
            reporte.orphan_sample,
            tuple(sorted(chunks))[:ORPHAN_SAMPLE_LIMIT],
        )

    def test_error_de_backend_no_genera_escrituras(self):
        self._parchear_chroma(
            _ChromaReadAccess(
                ChromaReadStatus(
                    root_present=True,
                    collection_present=True,
                ),
                collection=self.ColeccionConRutaWindows(),
            )
        )

        with mock.patch("core.index_manifest.IndexManifest.load") as espia_load, \
             mock.patch("core.security.log_seguridad") as espia_log, \
             mock.patch("core.vector_store.agregar_documento") as espia_agregar, \
             mock.patch("core.vector_store.eliminar_documento") as espia_eliminar, \
             mock.patch("core.vector_store._get_collection") as espia_get_collection:
            reporte = self._verificar()

        self.assertEqual(reporte.observed_state, ConsistencyState.UNAVAILABLE.value)
        self.assertEqual(reporte.issues, (CHROMA_COLLECTION_ISSUE,))
        assert_sin_datos_privados(self, asdict(reporte))
        espia_load.assert_not_called()
        espia_log.assert_not_called()
        espia_agregar.assert_not_called()
        espia_eliminar.assert_not_called()
        espia_get_collection.assert_not_called()


if __name__ == "__main__":
    unittest.main()
