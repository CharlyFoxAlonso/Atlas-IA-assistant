"""
tests/test_incremental_indexing.py
Pruebas del corte de indexación incremental (Atlas v4.1).

No requieren Ollama, APIs, Internet ni ChromaDB real: el backend vectorial
se reemplaza por una colección fake en memoria y los archivos viven en
directorios temporales.
"""
import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import core.indexer as indexer
import core.local_ingestion_manager as lim
from core.index_manifest import IndexManifest
from core.indexer import (
    IndexResult,
    construir_indice,
    eliminar_documento_indexado,
    indexar_archivo,
    reconstruir_indice_completo,
    sincronizar_indice,
)

CONTENIDO_BASE = (
    "Texto de prueba suficientemente largo para superar el mínimo de "
    "cincuenta caracteres que exige agregar_documento. " * 3
)


# ============================================
# FAKES Y HELPERS
# ============================================

class FakeCollection:
    """Colección en memoria compatible con lo que usa vector_store."""

    def __init__(self):
        self.store = {}  # id -> {"document": str, "metadata": dict}
        self.add_calls = 0
        self.delete_calls = 0
        self.fallar_add = False  # simular fallo del backend en add()

    def get(self, where=None, ids=None):
        if ids is not None:
            return {"ids": [i for i in ids if i in self.store]}
        matched = []
        for cid, row in self.store.items():
            if all(row["metadata"].get(k) == v for k, v in (where or {}).items()):
                matched.append(cid)
        return {"ids": matched}

    def add(self, documents, ids, metadatas):
        self.add_calls += 1
        if self.fallar_add:
            raise RuntimeError("fallo simulado del backend en add()")
        for doc, cid, md in zip(documents, ids, metadatas):
            self.store[cid] = {"document": doc, "metadata": dict(md)}

    def delete(self, ids):
        self.delete_calls += 1
        for cid in ids:
            self.store.pop(cid, None)

    def count(self):
        return len(self.store)

    def ids_de(self, doc_id):
        return [cid for cid, row in self.store.items()
                if row["metadata"].get("doc_id") == doc_id]


def escribir(base, rel_path, contenido=CONTENIDO_BASE):
    ruta = os.path.join(base, rel_path)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return ruta


def sha256_de(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


class CasoBase(unittest.TestCase):
    """Fixture común: Atlas_Memory temporal + colección fake + manifiesto tmp."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.join(self.tmp.name, "Atlas_Memory")
        os.makedirs(self.base)
        self.manifest_path = os.path.join(self.tmp.name, "vector_db",
                                          "index_manifest.json")
        self.fake = FakeCollection()
        parche = mock.patch("core.vector_store._get_collection",
                            return_value=self.fake)
        parche.start()
        self.addCleanup(parche.stop)

    def sync(self):
        return sincronizar_indice(memoria_base=self.base,
                                  manifest_path=self.manifest_path)

    def rebuild(self):
        return reconstruir_indice_completo(memoria_base=self.base,
                                           manifest_path=self.manifest_path)

    def indexar(self, ruta):
        return indexar_archivo(ruta, memoria_base=self.base,
                               manifest_path=self.manifest_path)


# ============================================
# 18.1 INDEXACIÓN INDIVIDUAL
# ============================================

class IndexacionIndividualTests(CasoBase):

    def test_indexa_un_solo_archivo_sin_tocar_otros(self):
        escribir(self.base, "carpeta_a/doc1.md")
        escribir(self.base, "carpeta_a/doc2.md")
        ruta3 = escribir(self.base, "carpeta_b/doc3.md")

        res = self.indexar(ruta3)

        self.assertEqual(res.status, "indexed")
        self.assertEqual(res.path, "carpeta_b/doc3.md")
        self.assertGreater(res.chunk_count, 0)
        self.assertGreater(res.duration_seconds, 0)
        # Sólo doc3 está en el índice
        self.assertEqual(len(self.fake.store), res.chunk_count)
        self.assertTrue(all(
            md["metadata"]["doc_id"] == "carpeta_b/doc3.md"
            for md in self.fake.store.values()
        ))

    def test_metadata_y_chunk_ids_deterministas(self):
        ruta = escribir(self.base, "carpeta_b/sub/doc.md")
        res = self.indexar(ruta)

        ids_esperados = {f"carpeta_b/sub/doc.md:chunk:{i}"
                         for i in range(res.chunk_count)}
        self.assertEqual(set(self.fake.store.keys()), ids_esperados)
        for row in self.fake.store.values():
            self.assertEqual(row["metadata"]["doc_id"], "carpeta_b/sub/doc.md")
            self.assertEqual(row["metadata"]["ruta"], "carpeta_b/sub/doc.md")
            self.assertEqual(row["metadata"]["nombre"], "doc.md")

    def test_manifiesto_guarda_sha256_y_entrada(self):
        ruta = escribir(self.base, "doc.md")
        res = self.indexar(ruta)

        manifest = IndexManifest.load(self.manifest_path)
        entry = manifest.get("doc.md")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.content_sha256, sha256_de(ruta))
        self.assertEqual(entry.chunk_count, res.chunk_count)
        self.assertEqual(entry.size_bytes, os.stat(ruta).st_size)
        self.assertGreater(entry.modified_time_ns, 0)
        self.assertTrue(entry.indexed_at.endswith("+00:00"))

    def test_reindexar_no_duplica_chunks(self):
        ruta = escribir(self.base, "doc.md")
        res1 = self.indexar(ruta)
        total_tras_primera = self.fake.count()
        res2 = self.indexar(ruta)

        self.assertEqual(res2.status, "indexed")
        self.assertEqual(self.fake.count(), total_tras_primera)
        self.assertEqual(res1.chunk_count, res2.chunk_count)

    def test_archivo_inexistente_falla_sin_excepcion(self):
        res = self.indexar(os.path.join(self.base, "no_existe.md"))
        self.assertEqual(res.status, "failed")
        self.assertIn("no encontrado", res.error)

    def test_extension_no_soportada(self):
        ruta = escribir(self.base, "doc.xyz")
        res = self.indexar(ruta)
        self.assertEqual(res.status, "failed")
        self.assertIn("no soportada", res.error)


# ============================================
# AUD-01 CONTENCIÓN DE RUTAS
# ============================================

class ContencionRutasTests(CasoBase):
    """indexar_archivo() no debe aceptar archivos fuera de memoria_base."""

    def _verificar_rechazo_sin_side_effects(self, ruta, fuente_externa):
        espia_loader = mock.Mock()
        espia_agregar = mock.Mock()
        with mock.patch.object(indexer, "leer_archivo_con_info", espia_loader), \
             mock.patch.object(indexer, "agregar_documento", espia_agregar):
            res = self.indexar(ruta)

        self.assertEqual(res.status, "failed")
        self.assertIn("fuera de la base", res.error)
        espia_loader.assert_not_called()
        espia_agregar.assert_not_called()
        # Manifiesto no creado ni alterado
        self.assertFalse(os.path.exists(self.manifest_path))
        # Fuente externa intacta
        self.assertTrue(os.path.exists(fuente_externa))
        with open(fuente_externa, encoding="utf-8") as f:
            self.assertIn("Texto de prueba", f.read())
        return res

    def test_ruta_relativa_con_dotdot_rechazada(self):
        fuera = escribir(self.tmp.name, "fuera.md")
        ruta_escape = os.path.join(self.base, "..", "fuera.md")
        self._verificar_rechazo_sin_side_effects(ruta_escape, fuera)

    def test_ruta_absoluta_externa_rechazada(self):
        hermano = os.path.join(self.tmp.name, "otro_lugar")
        os.makedirs(hermano)
        fuera = escribir(hermano, "documento.md")
        self._verificar_rechazo_sin_side_effects(fuera, fuera)

    def test_prefijo_similar_rechazado(self):
        # Atlas_Memory_Evil NO es descendiente de Atlas_Memory
        evil = self.base + "_Evil"
        fuera = escribir(evil, "documento.md")
        self._verificar_rechazo_sin_side_effects(fuera, fuera)

    def test_ruta_valida_interna_sigue_indexando(self):
        ruta = escribir(self.base, "carpeta/doc_valido.md")
        res = self.indexar(ruta)
        self.assertEqual(res.status, "indexed")
        self.assertEqual(res.path, "carpeta/doc_valido.md")
        self.assertGreater(self.fake.count(), 0)

    def test_symlink_externo_rechazado(self):
        fuera = escribir(self.tmp.name, "objetivo_externo.md")
        enlace = os.path.join(self.base, "enlace.md")
        try:
            os.symlink(fuera, enlace)
        except (OSError, NotImplementedError) as e:
            self.skipTest(f"el entorno no permite crear symlinks: {e}")
        self._verificar_rechazo_sin_side_effects(enlace, fuera)


# ============================================
# 18.2 ARCHIVO SIN CAMBIOS
# ============================================

class SinCambiosTests(CasoBase):

    def test_segunda_sync_omite_todo_sin_releer(self):
        for i in range(5):
            escribir(self.base, f"docs/doc{i}.md")

        r1 = self.sync()
        self.assertEqual(r1.indexed_new, 5)
        self.assertEqual(r1.failed, 0)

        # Espía del loader en la segunda pasada
        with mock.patch.object(indexer, "leer_archivo_con_info",
                               wraps=indexer.leer_archivo_con_info) as espia:
            adds_antes = self.fake.add_calls
            r2 = self.sync()

        self.assertEqual(r2.scanned, 5)
        self.assertEqual(r2.skipped_unchanged, 5)
        self.assertEqual(r2.indexed_new, 0)
        self.assertEqual(r2.reindexed_modified, 0)
        self.assertEqual(espia.call_count, 0, "no debería releer archivos intactos")
        self.assertEqual(self.fake.add_calls, adds_antes,
                         "no debería recalcular embeddings")

    def test_touch_sin_cambio_de_contenido_no_reindexa(self):
        ruta = escribir(self.base, "doc.md")
        self.sync()

        # Cambia sólo el mtime, no el contenido
        stat = os.stat(ruta)
        os.utime(ruta, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

        r2 = self.sync()
        self.assertEqual(r2.skipped_unchanged, 1)
        self.assertEqual(r2.reindexed_modified, 0)


# ============================================
# 18.3 ARCHIVO MODIFICADO
# ============================================

class ModificadoTests(CasoBase):

    def test_modificar_reindexa_solo_ese_documento(self):
        ruta_a = escribir(self.base, "a/doc_a.md")
        escribir(self.base, "b/doc_b.md")
        self.sync()
        adds_tras_primera = self.fake.add_calls

        nuevo_contenido = CONTENIDO_BASE + "\n\nCapítulo 9: contenido nuevo y distinto."
        escribir(self.base, "a/doc_a.md", nuevo_contenido)
        stat = os.stat(ruta_a)
        os.utime(ruta_a, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

        r2 = self.sync()

        self.assertEqual(r2.reindexed_modified, 1)
        self.assertEqual(r2.skipped_unchanged, 1)
        self.assertEqual(r2.indexed_new, 0)
        self.assertEqual(self.fake.add_calls, adds_tras_primera + 1,
                         "sólo doc_a debió reindexarse")
        self.assertGreater(self.fake.delete_calls, 0,
                           "los chunks viejos de doc_a debieron eliminarse")

        # El manifiesto refleja el nuevo hash
        entry = IndexManifest.load(self.manifest_path).get("a/doc_a.md")
        self.assertEqual(entry.content_sha256, sha256_de(ruta_a))

        # El contenido indexado de doc_a es el nuevo
        textos_a = [row["document"] for row in self.fake.store.values()
                    if row["metadata"]["doc_id"] == "a/doc_a.md"]
        self.assertTrue(any("contenido nuevo y distinto" in t for t in textos_a))

    def test_manifest_no_duplica_entrada_tras_reindexar(self):
        ruta = escribir(self.base, "doc.md")
        self.indexar(ruta)
        escribir(self.base, "doc.md", CONTENIDO_BASE + " variación de contenido.")
        self.sync()
        manifest = IndexManifest.load(self.manifest_path)
        self.assertEqual(len(manifest.documents), 1)


# ============================================
# 18.4 ARCHIVO ELIMINADO
# ============================================

class EliminadoTests(CasoBase):

    def test_sync_detecta_eliminado_y_retira_solo_ese(self):
        escribir(self.base, "a/doc_a.md")
        ruta_b = escribir(self.base, "b/doc_b.md")
        self.sync()
        total_antes = self.fake.count()
        chunks_b = len(self.fake.ids_de("b/doc_b.md"))
        self.assertGreater(chunks_b, 0)

        os.remove(ruta_b)
        r2 = self.sync()

        self.assertEqual(r2.removed_deleted, 1)
        self.assertEqual(r2.skipped_unchanged, 1)
        self.assertEqual(self.fake.ids_de("b/doc_b.md"), [])
        self.assertEqual(self.fake.count(), total_antes - chunks_b)
        self.assertIsNone(IndexManifest.load(self.manifest_path).get("b/doc_b.md"))
        self.assertIsNotNone(IndexManifest.load(self.manifest_path).get("a/doc_a.md"))

    def test_eliminar_documento_indexado_es_idempotente(self):
        ruta = escribir(self.base, "doc.md")
        self.indexar(ruta)
        os.remove(ruta)

        r1 = eliminar_documento_indexado("doc.md", manifest_path=self.manifest_path)
        self.assertEqual(r1.status, "deleted")
        self.assertGreater(r1.chunks_removed, 0)

        r2 = eliminar_documento_indexado("doc.md", manifest_path=self.manifest_path)
        self.assertEqual(r2.status, "not_found")
        self.assertEqual(r2.chunks_removed, 0)


# ============================================
# 18.5 MISMO NOMBRE EN CARPETAS DISTINTAS
# ============================================

class MismoNombreTests(CasoBase):

    def test_no_colisionan_y_se_eliminan_independiente(self):
        escribir(self.base, "Derecho/clase_1.md", CONTENIDO_BASE + " derecho.")
        escribir(self.base, "Estadistica/clase_1.md", CONTENIDO_BASE + " estadística.")
        self.sync()

        ids_derecho = self.fake.ids_de("Derecho/clase_1.md")
        ids_estadistica = self.fake.ids_de("Estadistica/clase_1.md")
        self.assertGreater(len(ids_derecho), 0)
        self.assertGreater(len(ids_estadistica), 0)
        self.assertEqual(set(ids_derecho) & set(ids_estadistica), set())

        # Eliminar uno no afecta al otro
        res = eliminar_documento_indexado("Derecho/clase_1.md",
                                          manifest_path=self.manifest_path)
        self.assertEqual(res.status, "deleted")
        self.assertEqual(self.fake.ids_de("Derecho/clase_1.md"), [])
        self.assertEqual(len(self.fake.ids_de("Estadistica/clase_1.md")),
                         len(ids_estadistica))

    def test_actualizar_uno_no_reindexa_el_otro(self):
        ruta_d = escribir(self.base, "Derecho/clase_1.md")
        escribir(self.base, "Estadistica/clase_1.md")
        self.sync()
        adds = self.fake.add_calls

        escribir(self.base, "Derecho/clase_1.md", CONTENIDO_BASE + " cambio.")
        stat = os.stat(ruta_d)
        os.utime(ruta_d, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
        r2 = self.sync()

        self.assertEqual(r2.reindexed_modified, 1)
        self.assertEqual(self.fake.add_calls, adds + 1)


# ============================================
# 18.6 MANIFIESTO INEXISTENTE
# ============================================

class ManifestInexistenteTests(CasoBase):

    def test_se_crea_correctamente_sin_borrar_la_base(self):
        escribir(self.base, "doc.md")
        self.assertFalse(os.path.exists(self.manifest_path))

        r = self.sync()

        self.assertEqual(r.failed, 0)
        self.assertTrue(os.path.exists(self.manifest_path))
        with open(self.manifest_path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["schema_version"], 1)
        self.assertIn("doc.md", data["documents"])
        self.assertGreater(self.fake.count(), 0, "la base fake no se tocó")

    def test_save_es_atomico_sin_tmp_residual(self):
        escribir(self.base, "doc.md")
        self.sync()
        carpeta = os.path.dirname(self.manifest_path)
        residuos = [f for f in os.listdir(carpeta) if f.endswith(".tmp")]
        self.assertEqual(residuos, [])


# ============================================
# 18.7 MANIFIESTO CORRUPTO
# ============================================

class ManifestCorruptoTests(CasoBase):

    def test_corrupto_se_respalda_y_recupera_sin_perder_datos(self):
        escribir(self.base, "doc.md")
        self.sync()
        chunks_antes = self.fake.count()

        # Corromper el manifiesto
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            f.write("{ json roto ,,,")

        r2 = self.sync()

        # Se creó un respaldo del corrupto
        carpeta = os.path.dirname(self.manifest_path)
        backups = [f for f in os.listdir(carpeta) if ".corrupt-" in f]
        self.assertEqual(len(backups), 1, "debe existir un respaldo del corrupto")

        # La base vectorial NO se tocó y el manifiesto se reconstruyó
        self.assertEqual(self.fake.count(), chunks_antes)
        manifest = IndexManifest.load(self.manifest_path)
        self.assertIn("doc.md", manifest.documents)
        self.assertEqual(r2.failed, 0)

    def test_load_corrupto_no_lanza_excepcion(self):
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            f.write("no es json")
        manifest = IndexManifest.load(self.manifest_path)
        self.assertEqual(manifest.documents, {})
        self.assertIsNotNone(manifest.corrupt_backup_path)


# ============================================
# 18.8 ERROR DEL LOADER
# ============================================

class ErrorLoaderTests(CasoBase):

    def test_archivo_fallido_no_registra_exito_y_sync_continua(self):
        escribir(self.base, "ok1.md")
        escribir(self.base, "ok2.md")
        escribir(self.base, "roto.md")

        real_loader = indexer.leer_archivo_con_info

        def loader_fallando(ruta):
            if ruta.endswith("roto.md"):
                return {"ok": False, "error": "loader simulado roto"}
            return real_loader(ruta)

        with mock.patch.object(indexer, "leer_archivo_con_info", loader_fallando):
            r = self.sync()

        self.assertEqual(r.failed, 1)
        self.assertEqual(r.indexed_new, 2)
        manifest = IndexManifest.load(self.manifest_path)
        self.assertIsNone(manifest.get("roto.md"),
                          "un fallo no debe figurar como éxito en el manifiesto")

        # Reintento sin el fallo: se indexa
        r2 = self.sync()
        self.assertEqual(r2.indexed_new, 1)
        self.assertIsNotNone(IndexManifest.load(self.manifest_path).get("roto.md"))


# ============================================
# 18.9 ERROR DEL ÍNDICE (backend vectorial)
# ============================================

class ErrorIndiceTests(CasoBase):

    def test_fallo_backend_no_borra_fuente_y_permite_reintento(self):
        ruta = escribir(self.base, "doc.md")

        with mock.patch.object(indexer, "agregar_documento",
                               side_effect=RuntimeError("Chroma caído")):
            res = self.indexar(ruta)

        self.assertEqual(res.status, "failed")
        self.assertIn("Chroma caído", res.error)
        self.assertTrue(os.path.exists(ruta), "el archivo fuente NO se borra")
        self.assertIsNone(IndexManifest.load(self.manifest_path).get("doc.md"))

        # Reintento con el backend sano
        res2 = self.indexar(ruta)
        self.assertEqual(res2.status, "indexed")
        self.assertGreater(self.fake.count(), 0)


# ============================================
# AUD-02 FALLOS PARCIALES: delete OK → add falla
# ============================================

class FalloParcialDeleteAddTests(CasoBase):
    """
    Reproducción del escenario: v1 indexada → archivo cambia a v2 →
    la reindexación elimina los chunks de v1 → col.add de v2 falla →
    el manifiesto sigue describiendo v1 → la sync posterior debe recuperar.
    """

    def test_delete_ok_add_falla_y_sync_posterior_recupera(self):
        # 1-3. v1 escrita, indexada, confirmada en chunks y manifiesto
        ruta = escribir(self.base, "doc.md", CONTENIDO_BASE)
        r1 = self.sync()
        self.assertEqual(r1.indexed_new, 1)
        self.assertGreater(self.fake.count(), 0)
        hash_v1 = IndexManifest.load(self.manifest_path).get("doc.md").content_sha256

        # 4-5. v2: contenido, hash y tamaño distintos; mtime confiable
        contenido_v2 = CONTENIDO_BASE + "\n\nCapítulo 7: versión dos con más texto."
        escribir(self.base, "doc.md", contenido_v2)
        stat = os.stat(ruta)
        os.utime(ruta, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
        self.assertNotEqual(hash_v1, sha256_de(ruta))

        # 6-7. delete permitido, siguiente add falla
        self.fake.fallar_add = True
        deletes_antes = self.fake.delete_calls
        r2 = self.sync()

        # 8-10. Resultado failed; chunks v1 eliminados; manifiesto sigue en v1
        self.assertEqual(r2.failed, 1)
        self.assertGreater(self.fake.delete_calls, deletes_antes,
                           "el delete de v1 ocurrió antes del fallo")
        self.assertEqual(self.fake.count(), 0,
                         "v1 eliminada y v2 nunca agregada: índice vacío")
        entry = IndexManifest.load(self.manifest_path).get("doc.md")
        self.assertEqual(entry.content_sha256, hash_v1,
                         "el manifiesto conserva la última versión buena (v1)")
        self.assertEqual(entry.last_operation, "failed")
        self.assertIsNotNone(entry.last_error)

        # 11-16. Backend sano: la sync posterior reintenta v2 y reconcilia
        self.fake.fallar_add = False
        r3 = self.sync()

        self.assertEqual(r3.failed, 0)
        self.assertEqual(r3.reindexed_modified, 1,
                         "reintenta v2 porque el archivo ya no coincide con v1")
        entry3 = IndexManifest.load(self.manifest_path).get("doc.md")
        self.assertEqual(entry3.content_sha256, sha256_de(ruta))
        self.assertEqual(entry3.last_operation, "indexed")
        # Chroma y manifiesto alineados, sin duplicación
        self.assertEqual(self.fake.count(), entry3.chunk_count)
        ids_doc = self.fake.ids_de("doc.md")
        self.assertEqual(len(ids_doc), len(set(ids_doc)))
        textos = [row["document"] for row in self.fake.store.values()]
        self.assertTrue(any("versión dos" in t for t in textos))


# ============================================
# AUD-02b FALLO PARCIAL: add OK → manifest.save falla
# ============================================

class FalloManifestSaveTests(CasoBase):
    """
    Escenario: v1 indexada → v2 modificada → reindexación OK en Chroma →
    manifest.save falla → el manifiesto en disco sigue en v1 →
    la sync posterior debe reconciliar sin duplicación permanente.
    """

    def test_add_ok_save_falla_y_sync_reconcilia(self):
        ruta = escribir(self.base, "doc.md", CONTENIDO_BASE)
        self.sync()
        hash_v1 = IndexManifest.load(self.manifest_path).get("doc.md").content_sha256

        contenido_v2 = CONTENIDO_BASE + "\n\nSegunda versión con contenido adicional."
        escribir(self.base, "doc.md", contenido_v2)
        stat = os.stat(ruta)
        os.utime(ruta, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

        # add ocurre; el guardado del manifiesto falla
        with mock.patch.object(IndexManifest, "save",
                               side_effect=OSError("disco lleno simulado")):
            r2 = self.sync()

        self.assertGreaterEqual(r2.failed, 1,
                                "el fallo del manifiesto se reporta, no se oculta")
        # Chroma ya tiene v2; el manifiesto EN DISCO sigue describiendo v1
        entry_disco = IndexManifest.load(self.manifest_path).get("doc.md")
        self.assertEqual(entry_disco.content_sha256, hash_v1)

        # Sync posterior: detecta el desfasaje (stat/hash != v1), reindexa
        # con deduplicación y guarda el manifiesto
        r3 = self.sync()
        self.assertEqual(r3.failed, 0)
        self.assertEqual(r3.reindexed_modified, 1)
        entry3 = IndexManifest.load(self.manifest_path).get("doc.md")
        self.assertEqual(entry3.content_sha256, sha256_de(ruta))
        self.assertEqual(self.fake.count(), entry3.chunk_count)
        ids_doc = self.fake.ids_de("doc.md")
        self.assertEqual(len(ids_doc), len(set(ids_doc)),
                         "sin duplicación permanente")


# ============================================
# 18.10 INTEGRACIÓN CON INGESTIÓN LOCAL
# ============================================

class IngestionLocalTests(unittest.TestCase):

    def test_ingesta_indexa_solo_el_documento_nuevo(self):
        with tempfile.TemporaryDirectory() as tmp:
            rag_base = os.path.join(tmp, "Atlas_Memory")
            temp_dir = os.path.join(tmp, "temp_local_ingestion")
            os.makedirs(rag_base)
            # Documento preexistente en la biblioteca
            escribir(rag_base, "03_Conocimiento/General/viejo.md")

            class FakeUpload:
                name = "apunte.txt"

                def getbuffer(self):
                    return (CONTENIDO_BASE * 2).encode("utf-8")

            def fake_digerir(**kwargs):
                yield {"estado": "procesando", "mensaje": "fake"}
                yield {"estado": "completado",
                       "texto": "# Digerido\n\n" + CONTENIDO_BASE}

            indexado = IndexResult("x", "indexed", chunk_count=3)

            with mock.patch.object(lim, "RAG_BASE_PATH", rag_base), \
                 mock.patch.object(lim, "TEMP_DIR", temp_dir), \
                 mock.patch.object(lim, "digerir_documento_con_progreso",
                                   side_effect=lambda **kw: fake_digerir(**kw)), \
                 mock.patch("core.indexer.indexar_archivo",
                            return_value=indexado) as espia_indexar, \
                 mock.patch("core.indexer.construir_indice") as espia_rebuild:
                pasos = list(lim.procesar_archivo_local(FakeUpload()))

            espia_indexar.assert_called_once()
            ruta_indexada = espia_indexar.call_args[0][0]
            self.assertTrue(ruta_indexada.endswith(".md"))
            self.assertTrue(os.path.exists(ruta_indexada),
                            "el Markdown quedó guardado en disco")
            self.assertNotIn("viejo.md", ruta_indexada)
            espia_rebuild.assert_not_called()

            estados = [p["estado"] for p in pasos]
            self.assertIn("indexando", estados)
            self.assertEqual(estados[-1], "completado")
            mensajes = " ".join(p["mensaje"] for p in pasos)
            self.assertNotIn("Reconstruyendo", mensajes)

    def test_ingesta_con_indexacion_fallida_conserva_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            rag_base = os.path.join(tmp, "Atlas_Memory")
            temp_dir = os.path.join(tmp, "temp_local_ingestion")
            os.makedirs(rag_base)

            class FakeUpload:
                name = "apunte.txt"

                def getbuffer(self):
                    return (CONTENIDO_BASE * 2).encode("utf-8")

            def fake_digerir(**kwargs):
                yield {"estado": "completado", "texto": "# Digerido\n\n" + CONTENIDO_BASE}

            fallo = IndexResult("x", "failed", error="Chroma caído")

            with mock.patch.object(lim, "RAG_BASE_PATH", rag_base), \
                 mock.patch.object(lim, "TEMP_DIR", temp_dir), \
                 mock.patch.object(lim, "digerir_documento_con_progreso",
                                   side_effect=lambda **kw: fake_digerir(**kw)), \
                 mock.patch("core.indexer.indexar_archivo", return_value=fallo):
                pasos = list(lim.procesar_archivo_local(FakeUpload()))

            estados = [p["estado"] for p in pasos]
            self.assertIn("advertencia", estados)
            self.assertEqual(estados[-1], "completado")
            self.assertIn("pendiente de indexación", pasos[-1]["mensaje"])
            # El Markdown NO se borró
            guardados = list(Path(rag_base).rglob("Local_*.md"))
            self.assertEqual(len(guardados), 1)


# ============================================
# 18.11 RECONSTRUCCIÓN COMPLETA
# ============================================

class ReconstruccionTests(CasoBase):

    def test_rebuild_procesa_todo_y_lo_indica_explicitamente(self):
        for i in range(4):
            escribir(self.base, f"docs/doc{i}.md")
        self.sync()

        r = self.rebuild()

        self.assertEqual(r.mode, "rebuild")
        self.assertEqual(r.scanned, 4)
        self.assertEqual(r.reindexed_modified, 4)
        self.assertEqual(r.skipped_unchanged, 0,
                         "una reconstrucción NO omite documentos")

    def test_construir_indice_alias_compatible(self):
        for i in range(3):
            escribir(self.base, f"doc{i}.md")
        with contextlib.redirect_stdout(io.StringIO()):
            archivos = construir_indice(memoria_base=self.base,
                                        manifest_path=self.manifest_path)
        # Contrato histórico: devuelve la lista de archivos indexados.
        self.assertIsInstance(archivos, list)
        self.assertEqual(len(archivos), 3)
        manifest = IndexManifest.load(self.manifest_path)
        total_chunks = sum(e.chunk_count for e in manifest.documents.values())
        self.assertEqual(self.fake.count(), total_chunks)

    def test_sync_y_rebuild_no_se_confunden(self):
        escribir(self.base, "doc.md")
        r_sync = self.sync()
        r_rebuild = self.rebuild()
        self.assertEqual(r_sync.mode, "sync")
        self.assertEqual(r_rebuild.mode, "rebuild")


if __name__ == "__main__":
    unittest.main()
