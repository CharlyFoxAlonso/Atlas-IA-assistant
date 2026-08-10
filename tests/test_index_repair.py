"""Pruebas sintéticas de IDX-C3 sin Chroma, Ollama ni datos de usuario."""
import hashlib
import os
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest import mock

from core.index_consistency import (
    ConsistencyReport,
    ConsistencyState,
    DivergenceCategory,
    _ConsistencySnapshot,
    _capturar_snapshot_consistencia,
    verificar_consistencia,
)
from core.index_manifest import IndexManifest, ManifestEntry
from core.index_repair import (
    RepairItem,
    RepairReport,
    _confirmar_items_por_identidad,
    _repair_missing_sources,
    _repair_sources,
    _report_orphans,
    _reparar_metadata_stale,
    reparar_indice,
)
from core.index_writer_lock import (
    IndexWriterBusyError,
    acquire_index_writer_lock,
    derive_lock_path_for_manifest,
)
from core.indexer import IndexResult, STATUS_INDEXED
from core.vector_store import ChromaReadStatus, _ChromaReadAccess


class _SyntheticWriterLock:
    """Lock temporal para probar el orden sin tocar la persistencia real."""

    def __init__(self, path):
        self.lock_path = Path(path)

    def __enter__(self):
        self.lock_path.write_text("synthetic-lock", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.lock_path.exists():
            self.lock_path.unlink()
        return False


class _FakeCollection:
    def __init__(self, chunks):
        self._chunks = dict(chunks)

    def get(self, include=None):
        return {
            "ids": list(self._chunks),
            "metadatas": list(self._chunks.values()),
        }


class IndexRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.join(self.tmp.name, "Atlas_Memory")
        self.vector = os.path.join(self.tmp.name, "vector_db")
        os.makedirs(self.base)
        os.makedirs(self.vector)
        self.manifest_path = os.path.join(self.vector, "index_manifest.json")
        self.lock_path = os.path.join(self.vector, "index_writer.lock")

    def _entry(self, identity="doc.txt", sha="0" * 64):
        return ManifestEntry(
            relative_path=identity,
            content_sha256=sha,
            size_bytes=1,
            modified_time_ns=1,
            indexed_at="2026-08-01T00:00:00+00:00",
            chunk_count=1,
        )

    def _snapshot(
        self,
        *,
        state=ConsistencyState.HEALTHY.value,
        published=None,
        sources=(),
        entries=None,
        chunks=None,
        categories=None,
        corrupt=False,
        schema=False,
        unavailable=False,
        path_error=None,
        malformed=0,
        orphans=(),
        writer_known=True,
        writer_active=False,
        issues=(),
    ):
        entries = dict(entries or {})
        chunks = dict(chunks or {})
        categories = dict(categories or {})
        published = published or state
        report = ConsistencyReport(
            observed_state=state,
            published_state=published,
            divergences=(
                {"verification_limitation": 1}
                if state == ConsistencyState.DEGRADED.value
                else {}
            ),
            orphan_sample=tuple(sorted(orphans)[:10]),
            orphan_count=len(orphans),
            sources_count=len(sources),
            manifest_entries_count=len(entries),
            chunk_count=sum(len(ids) for ids in chunks.values()),
            manifest_present=bool(entries) or corrupt or schema,
            manifest_corrupt=corrupt,
            manifest_schema_incompatible=schema,
            chroma_root_present=bool(chunks),
            chroma_collection_present=bool(chunks),
            chroma_unavailable=unavailable,
            path_error=path_error,
            issues=tuple(issues),
            writer_state_known=writer_known,
            writer_active=writer_active,
            possibly_transient=writer_active or not writer_known,
        )
        return _ConsistencySnapshot(
            base=self.base,
            manifest_path=self.manifest_path,
            chroma_path=self.vector,
            collection_name="atlas_rag",
            report=report,
            sources=tuple(sorted(sources)),
            manifest_entries=entries,
            manifest_malformed_entries=malformed,
            chunks_by_identity={key: tuple(value) for key, value in chunks.items()},
            orphan_ids=tuple(orphans),
            categories_by_identity=categories,
        )

    def test_identidad_sin_fuente_ni_manifest_con_chunks_queda_inconsistente(self):
        item = RepairItem(
            "doc.txt",
            DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_PRESENT.value,
            "reindex",
            "attempted",
        )
        snapshot = self._snapshot(chunks={"doc.txt": ("doc.txt:chunk:0",)})
        confirmed = _confirmar_items_por_identidad([item], snapshot)[0]
        self.assertEqual(confirmed.status, "still_inconsistent")
        self.assertEqual(
            confirmed.category,
            DivergenceCategory.SOURCE_ABSENT_CHROMA_PRESENT.value,
        )

    def test_identidad_sin_fuente_ni_manifest_ni_chunks_es_repaired(self):
        item = RepairItem(
            "doc.txt",
            DivergenceCategory.SOURCE_ABSENT_MANIFEST_PRESENT.value,
            "remove_manifest_entry",
            "attempted",
        )
        snapshot = self._snapshot()
        confirmed = _confirmar_items_por_identidad([item], snapshot)[0]
        self.assertEqual(confirmed.status, "repaired")

    def test_metadata_stale_mismo_sha_actualiza_solo_metadata(self):
        ruta = os.path.join(self.base, "doc.txt")
        Path(ruta).write_text("contenido estable", encoding="utf-8")
        digest = hashlib.sha256(Path(ruta).read_bytes()).hexdigest()
        entry = self._entry(sha=digest)
        manifest = IndexManifest(documents={"doc.txt": entry})
        manifest.save(self.manifest_path)

        with mock.patch("core.index_repair.indexar_archivo") as indexar:
            item = _reparar_metadata_stale(
                identity="doc.txt",
                ruta_abs=ruta,
                entry=entry,
                base=self.base,
                manifest_path=self.manifest_path,
                lock_path=self.lock_path,
            )

        self.assertEqual(item.status, "attempted")
        self.assertEqual(item.action, "metadata_update")
        indexar.assert_not_called()
        actualizado = IndexManifest.load(self.manifest_path).get("doc.txt")
        self.assertEqual(actualizado.content_sha256, digest)
        self.assertEqual(actualizado.size_bytes, os.stat(ruta).st_size)
        self.assertEqual(actualizado.modified_time_ns, os.stat(ruta).st_mtime_ns)

    def test_metadata_stale_cambio_durante_carga_reindexa_sin_guardar(self):
        ruta = os.path.join(self.base, "doc.txt")
        Path(ruta).write_text("contenido estable", encoding="utf-8")
        digest = hashlib.sha256(Path(ruta).read_bytes()).hexdigest()
        entry = self._entry(sha=digest)
        IndexManifest(documents={"doc.txt": entry}).save(self.manifest_path)
        resultado = IndexResult("doc.txt", STATUS_INDEXED, 2)
        original_load = IndexManifest.load

        def cargar_y_mutar(path=None):
            manifest = original_load(path)
            Path(ruta).write_text(
                "contenido cambiado durante la reparación",
                encoding="utf-8",
            )
            return manifest

        with mock.patch(
            "core.index_repair.IndexManifest.load",
            side_effect=cargar_y_mutar,
        ):
            with mock.patch(
                "core.index_repair.IndexManifest.save",
            ) as guardar_manifest:
                with mock.patch(
                    "core.index_repair.indexar_archivo",
                    return_value=resultado,
                ) as indexar:
                    item = _reparar_metadata_stale(
                        identity="doc.txt",
                        ruta_abs=ruta,
                        entry=entry,
                        base=self.base,
                        manifest_path=self.manifest_path,
                        lock_path=self.lock_path,
                    )

        guardar_manifest.assert_not_called()
        indexar.assert_called_once()
        self.assertEqual(item.action, "reindex")
        self.assertEqual(item.status, "attempted")
        self.assertEqual(
            item.category,
            DivergenceCategory.SOURCE_PRESENT_MANIFEST_STALE_CHROMA_PRESENT.value,
        )

    def test_metadata_stale_sha_cambiado_reindexa(self):
        ruta = os.path.join(self.base, "doc.txt")
        Path(ruta).write_text("contenido nuevo", encoding="utf-8")
        entry = self._entry(sha="0" * 64)
        resultado = IndexResult("doc.txt", STATUS_INDEXED, 2)
        with mock.patch("core.index_repair.indexar_archivo", return_value=resultado) as indexar:
            item = _reparar_metadata_stale(
                identity="doc.txt",
                ruta_abs=ruta,
                entry=entry,
                base=self.base,
                manifest_path=self.manifest_path,
                lock_path=self.lock_path,
            )
        self.assertEqual(item.action, "reindex")
        self.assertEqual(item.status, "attempted")
        self.assertEqual(
            item.category,
            DivergenceCategory.SOURCE_PRESENT_MANIFEST_STALE_CHROMA_PRESENT.value,
        )
        indexar.assert_called_once()

    def test_todas_las_categorias_reindexables_usan_indexar_archivo(self):
        categories = (
            DivergenceCategory.SOURCE_AND_MANIFEST_PRESENT_CHROMA_ABSENT.value,
            DivergenceCategory.SOURCE_PRESENT_MANIFEST_STALE_CHROMA_PRESENT.value,
            DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_PRESENT.value,
            DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_ABSENT.value,
            DivergenceCategory.MANIFEST_ABSENT.value,
            DivergenceCategory.CHROMA_ABSENT.value,
            DivergenceCategory.CHROMA_COLLECTION_ABSENT.value,
            DivergenceCategory.MANIFEST_AND_CHROMA_EMPTY_SOURCES_PRESENT.value,
        )
        for category in categories:
            with self.subTest(category=category):
                snapshot = self._snapshot(
                    sources=("doc.txt",),
                    categories={"doc.txt": category},
                )
                resultado = IndexResult("doc.txt", STATUS_INDEXED, 1)
                with mock.patch(
                    "core.index_repair.indexar_archivo",
                    return_value=resultado,
                ) as indexar:
                    items = _repair_sources(snapshot, lock_path=self.lock_path)
                self.assertEqual(items[0].action, "reindex")
                self.assertEqual(items[0].status, "attempted")
                indexar.assert_called_once()

    def test_fallo_de_un_documento_no_detiene_los_demas(self):
        snapshot = self._snapshot(
            sources=("a.txt", "b.txt"),
            categories={
                "a.txt": DivergenceCategory.CHROMA_ABSENT.value,
                "b.txt": DivergenceCategory.CHROMA_ABSENT.value,
            },
        )
        with mock.patch(
            "core.index_repair.indexar_archivo",
            side_effect=[RuntimeError("private path"), IndexResult("b.txt", STATUS_INDEXED, 1)],
        ) as indexar:
            items = _repair_sources(snapshot, lock_path=self.lock_path)
        self.assertEqual([item.status for item in items], ["failed", "attempted"])
        self.assertEqual(items[0].error_type, "RuntimeError")
        self.assertEqual(indexar.call_count, 2)

    def test_source_absent_sin_chroma_solo_retirar_manifest(self):
        IndexManifest(documents={"gone.txt": self._entry("gone.txt")}).save(
            self.manifest_path
        )
        snapshot = self._snapshot(entries={"gone.txt": self._entry("gone.txt")})
        with mock.patch("core.index_repair.eliminar_documento_indexado") as eliminar:
            items = _repair_missing_sources(snapshot, lock_path=self.lock_path)
        eliminar.assert_not_called()
        self.assertEqual(items[0].action, "remove_manifest_entry")
        self.assertIsNone(IndexManifest.load(self.manifest_path).get("gone.txt"))

    def test_source_absent_con_chroma_reutiliza_delete(self):
        entry = self._entry("gone.txt")
        snapshot = self._snapshot(
            entries={"gone.txt": entry},
            chunks={"gone.txt": ("gone.txt:chunk:0",)},
        )
        resultado = mock.Mock(status="deleted", error=None)
        with mock.patch(
            "core.index_repair.eliminar_documento_indexado",
            return_value=resultado,
        ) as eliminar:
            items = _repair_missing_sources(snapshot, lock_path=self.lock_path)
        eliminar.assert_called_once_with(
            "gone.txt",
            manifest_path=self.manifest_path,
            lock_path=self.lock_path,
        )
        self.assertEqual(items[0].action, "remove")
        self.assertEqual(items[0].status, "attempted")

    def test_diagnosticos_inseguros_tienen_reason_allowlisted(self):
        from core.index_repair import _blocked_reason

        snapshots = (
            (self._snapshot(corrupt=True), "manifest_corrupt"),
            (self._snapshot(schema=True), "manifest_schema_incompatible"),
            (self._snapshot(state=ConsistencyState.UNAVAILABLE.value, unavailable=True), "chroma_unavailable"),
            (self._snapshot(malformed=1), "malformed_manifest_entries"),
            (self._snapshot(path_error="path_error"), "path_error"),
        )
        for snapshot, expected in snapshots:
            with self.subTest(expected=expected):
                self.assertEqual(_blocked_reason(snapshot), expected)

    def test_precheck_no_bloquea_el_degraded_publicado_por_lock_propio(self):
        from core.index_repair import _blocked_reason

        snapshot = self._snapshot(
            state=ConsistencyState.HEALTHY.value,
            published=ConsistencyState.DEGRADED.value,
            writer_known=True,
            writer_active=True,
        )
        self.assertIsNone(_blocked_reason(snapshot))

    def test_precheck_bloquea_writer_desconocido(self):
        from core.index_repair import _blocked_reason

        snapshot = self._snapshot(
            state=ConsistencyState.HEALTHY.value,
            published=ConsistencyState.DEGRADED.value,
            writer_known=False,
            writer_active=False,
        )
        self.assertEqual(_blocked_reason(snapshot), "degraded_diagnosis")

    def test_huerfanos_se_reportan_y_no_se_purgan(self):
        snapshot = self._snapshot(
            chunks={"unknown.txt": ("chunk-1",)},
            orphans=("chunk-1",),
        )
        with mock.patch("core.index_repair.eliminar_documento_indexado") as eliminar:
            items = _report_orphans(snapshot)
        eliminar.assert_not_called()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].status, "skipped")
        self.assertEqual(items[0].action, "skip")
        self.assertNotEqual(items[0].category, "orphan")

    def test_reparacion_reindexa_y_confirma_fuera_del_lock(self):
        ruta = os.path.join(self.base, "doc.txt")
        Path(ruta).write_text("contenido largo", encoding="utf-8")
        categoria = DivergenceCategory.SOURCE_AND_MANIFEST_PRESENT_CHROMA_ABSENT.value
        pre = self._snapshot(
            sources=("doc.txt",),
            categories={"doc.txt": categoria},
        )
        post = self._snapshot(
            sources=("doc.txt",),
            categories={"doc.txt": None},
        )
        resultado = IndexResult("doc.txt", STATUS_INDEXED, 1)
        estados_lock_snapshot = []

        def capturar(**kwargs):
            estados_lock_snapshot.append(Path(self.lock_path).exists())
            return pre if len(estados_lock_snapshot) == 1 else post

        def confirmar(items, snapshot):
            self.assertTrue(all(item.status == "attempted" for item in items))
            return _confirmar_items_por_identidad(items, snapshot)

        with mock.patch(
            "core.index_repair._capturar_snapshot_consistencia",
            side_effect=capturar,
        ):
            with mock.patch("core.index_repair.indexar_archivo", return_value=resultado):
                with mock.patch(
                    "core.index_repair.acquire_index_writer_lock",
                    return_value=_SyntheticWriterLock(self.lock_path),
                ):
                    with mock.patch(
                        "core.index_repair._confirmar_items_por_identidad",
                        side_effect=confirmar,
                    ):
                        report = reparar_indice(memoria_base=self.base)

        self.assertEqual(estados_lock_snapshot, [True, False])
        self.assertTrue(report.post_check_performed)
        self.assertTrue(report.success)
        self.assertEqual(report.items[0].status, "repaired")

    def test_diagnostico_bloqueado_deja_cero_items_y_hace_post_check(self):
        pre = self._snapshot(
            state=ConsistencyState.UNAVAILABLE.value,
            corrupt=True,
        )
        post = self._snapshot(
            state=ConsistencyState.UNAVAILABLE.value,
            corrupt=True,
        )
        estados_lock_snapshot = []

        def capturar(**kwargs):
            estados_lock_snapshot.append(Path(self.lock_path).exists())
            return pre if len(estados_lock_snapshot) == 1 else post

        with mock.patch(
            "core.index_repair._capturar_snapshot_consistencia",
            side_effect=capturar,
        ) as capturar:
            with mock.patch("core.index_repair.indexar_archivo") as indexar:
                with mock.patch(
                    "core.index_repair.acquire_index_writer_lock",
                    return_value=_SyntheticWriterLock(self.lock_path),
                ):
                    report = reparar_indice(memoria_base=self.base)
        self.assertEqual(capturar.call_count, 2)
        self.assertEqual(estados_lock_snapshot, [True, False])
        indexar.assert_not_called()
        self.assertTrue(report.blocked)
        self.assertEqual(report.blocked_reason, "manifest_corrupt")
        self.assertEqual(report.items, ())
        self.assertFalse(report.success)

    def test_fallo_global_de_precheck_bloquea_sin_items_inventados(self):
        post = self._snapshot()
        estados_lock_snapshot = []

        def capturar(**kwargs):
            estados_lock_snapshot.append(Path(self.lock_path).exists())
            if len(estados_lock_snapshot) == 1:
                raise RuntimeError("C:/private/precheck")
            return post

        with mock.patch(
            "core.index_repair._capturar_snapshot_consistencia",
            side_effect=capturar,
        ) as capturar:
            with mock.patch(
                "core.index_repair.acquire_index_writer_lock",
                return_value=_SyntheticWriterLock(self.lock_path),
            ):
                report = reparar_indice(memoria_base=self.base)

        self.assertEqual(capturar.call_count, 2)
        self.assertEqual(estados_lock_snapshot, [True, False])
        self.assertTrue(report.blocked)
        self.assertEqual(report.blocked_reason, "degraded_diagnosis")
        self.assertEqual(report.items, ())
        self.assertTrue(report.post_check_performed)
        self.assertFalse(report.success)

    def test_target_de_escritura_incoherente_bloquea_sin_escrituras(self):
        pre = self._snapshot()
        post = self._snapshot()
        with mock.patch(
            "core.index_repair._capturar_snapshot_consistencia",
            side_effect=[pre, post],
        ) as capturar:
            with mock.patch(
                "core.index_repair.acquire_index_writer_lock",
                return_value=_SyntheticWriterLock(self.lock_path),
            ) as acquire:
                with mock.patch("core.index_repair.indexar_archivo") as indexar:
                    with mock.patch(
                        "core.index_repair.eliminar_documento_indexado"
                    ) as eliminar:
                        report = reparar_indice(
                            memoria_base=self.base,
                            manifest_path=self.manifest_path,
                            chroma_path=self.vector,
                            collection_name="atlas_rag",
                            lock_path=self.lock_path,
                        )

        self.assertEqual(capturar.call_count, 2)
        acquire.assert_called_once()
        indexar.assert_not_called()
        eliminar.assert_not_called()
        self.assertTrue(report.blocked)
        self.assertEqual(report.blocked_reason, "writer_target_mismatch")
        self.assertEqual(report.items, ())
        self.assertTrue(report.post_check_performed)
        self.assertFalse(report.success)

    def test_busy_es_unico_camino_sin_post_check(self):
        with mock.patch(
            "core.index_repair.acquire_index_writer_lock",
            side_effect=IndexWriterBusyError("index_writer_busy"),
        ):
            with mock.patch("core.index_repair._capturar_snapshot_consistencia") as capturar:
                report = reparar_indice(
                    memoria_base=self.base,
                )
        capturar.assert_not_called()
        self.assertTrue(report.busy)
        self.assertFalse(report.post_check_performed)
        self.assertFalse(report.success)

    def test_writer_activo_en_post_publica_degraded_y_falla(self):
        item = RepairItem(
            "doc.txt",
            DivergenceCategory.SOURCE_PRESENT_MANIFEST_ABSENT_CHROMA_ABSENT.value,
            "reindex",
            "attempted",
        )
        snapshot = self._snapshot(
            state=ConsistencyState.HEALTHY.value,
            published=ConsistencyState.DEGRADED.value,
            writer_known=True,
            writer_active=True,
        )
        confirmed = _confirmar_items_por_identidad([item], snapshot)[0]
        self.assertEqual(confirmed.status, "still_inconsistent")
        report = RepairReport(
            pre_state=ConsistencyState.INCONSISTENT.value,
            post_state=snapshot.report.published_state,
            post_observed=snapshot.report.observed_state,
            post_check_performed=True,
            success=True,
            blocked=False,
            blocked_reason=None,
            busy=False,
            busy_message=None,
            items=(confirmed,),
        )
        self.assertFalse(report.success)

    def test_otro_writer_en_snapshot_final_fuerza_success_false(self):
        categoria = DivergenceCategory.CHROMA_ABSENT.value
        pre = self._snapshot(
            sources=("doc.txt",),
            categories={"doc.txt": categoria},
        )
        post = self._snapshot(
            state=ConsistencyState.HEALTHY.value,
            published=ConsistencyState.DEGRADED.value,
            sources=("doc.txt",),
            categories={"doc.txt": None},
            writer_known=True,
            writer_active=True,
        )
        with mock.patch(
            "core.index_repair._capturar_snapshot_consistencia",
            side_effect=[pre, post],
        ):
            with mock.patch(
                "core.index_repair.indexar_archivo",
                return_value=IndexResult("doc.txt", STATUS_INDEXED, 1),
            ):
                with mock.patch(
                    "core.index_repair.acquire_index_writer_lock",
                    return_value=_SyntheticWriterLock(self.lock_path),
                ):
                    report = reparar_indice(memoria_base=self.base)
        self.assertEqual(report.post_state, ConsistencyState.DEGRADED.value)
        self.assertFalse(report.success)
        self.assertEqual(report.items[0].status, "still_inconsistent")

    def test_reparacion_idempotente_en_estado_nominal(self):
        nominal = self._snapshot()
        estados_lock_snapshot = []

        def capturar(**kwargs):
            estados_lock_snapshot.append(Path(self.lock_path).exists())
            return nominal

        with mock.patch(
            "core.index_repair._capturar_snapshot_consistencia",
            side_effect=capturar,
        ):
            with mock.patch(
                "core.index_repair.acquire_index_writer_lock",
                side_effect=lambda **kwargs: _SyntheticWriterLock(self.lock_path),
            ):
                first = reparar_indice(memoria_base=self.base)
                second = reparar_indice(memoria_base=self.base)
        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertEqual(first.items, ())
        self.assertEqual(second.items, ())
        self.assertEqual(estados_lock_snapshot, [True, False, True, False])
        self.assertFalse(Path(self.lock_path).exists())

    def test_todos_los_diagnosticos_inseguros_bloquean_sin_escritura(self):
        pre_posts = (
            (self._snapshot(corrupt=True), self._snapshot(corrupt=True)),
            (self._snapshot(schema=True), self._snapshot(schema=True)),
            (
                self._snapshot(
                    state=ConsistencyState.UNAVAILABLE.value,
                    unavailable=True,
                ),
                self._snapshot(
                    state=ConsistencyState.UNAVAILABLE.value,
                    unavailable=True,
                ),
            ),
            (self._snapshot(malformed=1), self._snapshot(malformed=1)),
            (
                self._snapshot(state=ConsistencyState.DEGRADED.value),
                self._snapshot(state=ConsistencyState.DEGRADED.value),
            ),
            (
                self._snapshot(
                    state=ConsistencyState.UNAVAILABLE.value,
                    unavailable=True,
                    issues=("chroma_collection_read_failed: Chroma unavailable",),
                ),
                self._snapshot(
                    state=ConsistencyState.UNAVAILABLE.value,
                    unavailable=True,
                    issues=("chroma_collection_read_failed: Chroma unavailable",),
                ),
            ),
            (
                self._snapshot(path_error="legacy_vector_store_detected"),
                self._snapshot(path_error="legacy_vector_store_detected"),
            ),
        )
        for pre, post in pre_posts:
            with self.subTest(reason=pre.report.path_error or pre.report.observed_state):
                with mock.patch(
                    "core.index_repair._capturar_snapshot_consistencia",
                    side_effect=[pre, post],
                ):
                    with mock.patch("core.index_repair.indexar_archivo") as indexar:
                        with mock.patch(
                            "core.index_repair.acquire_index_writer_lock",
                            return_value=_SyntheticWriterLock(self.lock_path),
                        ):
                            report = reparar_indice(memoria_base=self.base)
                indexar.assert_not_called()
                self.assertTrue(report.blocked)
                self.assertTrue(report.post_check_performed)
                self.assertEqual(report.items, ())
                self.assertFalse(report.success)

    def test_snapshot_compartido_conserva_la_semantica_publica(self):
        ruta = os.path.join(self.base, "index_manifest.json")
        acceso = _ChromaReadAccess()
        with mock.patch(
            "core.index_consistency._abrir_coleccion_existente",
            return_value=acceso,
        ):
            reporte = verificar_consistencia(
                memoria_base=self.base,
                manifest_path=ruta,
                chroma_path=self.vector,
                collection_name="atlas_rag",
            )
            snapshot = _capturar_snapshot_consistencia(
                memoria_base=self.base,
                manifest_path=ruta,
                chroma_path=self.vector,
                collection_name="atlas_rag",
            )
        first = asdict(reporte)
        second = asdict(snapshot.report)
        first.pop("checked_at")
        second.pop("checked_at")
        self.assertEqual(first, second)

    def test_precheck_read_only_preserva_lock_existente_y_semantica_publica(self):
        ruta = Path(self.base, "doc.txt")
        ruta.write_text("contenido estable", encoding="utf-8")
        stat = ruta.stat()
        entry = ManifestEntry(
            relative_path="doc.txt",
            content_sha256=hashlib.sha256(ruta.read_bytes()).hexdigest(),
            size_bytes=stat.st_size,
            modified_time_ns=stat.st_mtime_ns,
            indexed_at="2026-08-01T00:00:00+00:00",
            chunk_count=1,
        )
        IndexManifest(documents={"doc.txt": entry}).save(self.manifest_path)
        manifest_before = Path(self.manifest_path).read_bytes()
        source_before = ruta.read_bytes()
        lock_path = derive_lock_path_for_manifest(self.manifest_path)
        acceso = _ChromaReadAccess(
            ChromaReadStatus(
                root_present=True,
                collection_present=True,
            ),
            collection=_FakeCollection(
                {"doc.txt:chunk:0": {"doc_id": "doc.txt"}}
            ),
        )

        with mock.patch(
            "core.index_consistency._abrir_coleccion_existente",
            return_value=acceso,
        ):
            with acquire_index_writer_lock(lock_path=lock_path):
                lock_before = lock_path.read_bytes()
                public = verificar_consistencia(
                    memoria_base=self.base,
                    manifest_path=self.manifest_path,
                    chroma_path=self.vector,
                    collection_name="atlas_rag",
                    lock_path=str(lock_path),
                )
                snapshot = _capturar_snapshot_consistencia(
                    memoria_base=self.base,
                    manifest_path=self.manifest_path,
                    chroma_path=self.vector,
                    collection_name="atlas_rag",
                    lock_path=str(lock_path),
                )
                self.assertTrue(lock_path.exists())
                self.assertEqual(lock_path.read_bytes(), lock_before)

        self.assertEqual(Path(self.manifest_path).read_bytes(), manifest_before)
        self.assertEqual(ruta.read_bytes(), source_before)
        self.assertEqual(public.observed_state, ConsistencyState.HEALTHY.value)
        self.assertEqual(public.published_state, ConsistencyState.DEGRADED.value)
        self.assertTrue(public.writer_active)
        public_dict = asdict(public)
        snapshot_dict = asdict(snapshot.report)
        public_dict.pop("checked_at")
        snapshot_dict.pop("checked_at")
        self.assertEqual(public_dict, snapshot_dict)

    def test_error_publico_solo_expone_tipo_seguro(self):
        item = RepairItem(
            "doc.txt",
            "unknown-category",
            "reindex",
            "failed",
            error_type="C:/private/document.txt: RuntimeError",
        )
        self.assertEqual(item.category, "unknown")
        self.assertEqual(item.error_type, "Exception")

if __name__ == "__main__":
    unittest.main()
