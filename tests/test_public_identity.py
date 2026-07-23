import inspect
import unittest

from core.profile_manager import exportar_perfil_actual


class PublicIdentityTests(unittest.TestCase):
    def test_profile_export_uses_generic_default(self):
        default = inspect.signature(exportar_perfil_actual).parameters["nombre_usuario"].default
        self.assertEqual(default, "usuario")


if __name__ == "__main__":
    unittest.main()
