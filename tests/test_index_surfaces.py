import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


class IndexSurfaceWiringTests(unittest.TestCase):
    def test_chat_adds_exact_status_before_preserving_sync_and_rebuild(self):
        source = _source("atlas_chat.py")
        block = source[source.index("# !indexar"):source.index("# !seguridad")]
        self.assertIn('if sub_idx == "status":', block)
        self.assertIn('elif sub_idx == "sync":', block)
        self.assertIn("construir_indice()", block)
        self.assertLess(
            block.index('if sub_idx == "status":'),
            block.index('elif sub_idx == "sync":'),
        )

    def test_ui_status_is_exact_and_legacy_sync_dispatch_is_preserved(self):
        source = _source("atlas_ui.py")
        start = source.index("# !INDEXAR")
        block = source[start:source.index("# !LIMPIAR", start)]
        self.assertIn("status_exact = len(args) == 1", block)
        self.assertIn('if status_exact:', block)
        self.assertIn('elif sub_idx == "sync":', block)
        self.assertIn("construir_indice()", block)

    def test_ui_index_diagnosis_requires_button_or_status_command(self):
        source = _source("atlas_ui.py")
        state_block = source[
            source.index("# SECCIÓN: Estado"):source.index("# SECCIÓN: Sentidos")
        ]
        self.assertIn("Consultar estado del índice", state_block)
        self.assertIn(
            "consultar_estado_indice_si_solicitado(solicitud_estado_indice)",
            state_block,
        )
        self.assertNotIn("obtener_estadisticas()", state_block)
        self.assertNotIn("consultar_estado_indice(", source)

    def test_existing_system_diagnosis_excludes_index_consistency(self):
        source = _source("atlas_ui.py")
        start = source.index("def _refresh_system_diagnosis")
        block = source[start:source.index("def _render_index_status", start)]
        self.assertIn("include_index_consistency=False", block)

    def test_chat_and_ui_share_busy_presentation(self):
        chat = _source("atlas_chat.py")
        ui = _source("atlas_ui.py")
        self.assertIn("presentar_resultado_sincronizacion(sync)", chat)
        self.assertIn("presentar_resultado_sincronizacion(sync)", ui)

    def test_help_lists_the_new_read_only_command(self):
        self.assertIn("!indexar status", _source("atlas_chat.py"))
        self.assertIn("!indexar status", _source("atlas_ui.py"))

    def test_status_core_has_no_repair_or_writer_entry_points(self):
        source = _source("core/index_status.py")
        for forbidden in (
            "reparar_indice",
            "acquire_index_writer_lock",
            "indexar_archivo",
            "eliminar_documento_indexado",
            "get_or_create_collection",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
