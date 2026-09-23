"""Lightweight integrity checks; no training dependencies or datasets required."""
import ast
import configparser
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseIntegrity(unittest.TestCase):
    def test_default_configs_exist(self):
        tree = ast.parse((ROOT / 'bench_utils.py').read_text())
        names = {'METHOD_DEFAULT_CONFIGS', 'METHOD_CONFIG_DIR'}
        registry = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in names
        }
        for method, entries in registry['METHOD_DEFAULT_CONFIGS'].items():
            for molecule, filename in entries.items():
                with self.subTest(method=method, molecule=molecule):
                    path = ROOT / 'configs' / registry['METHOD_CONFIG_DIR'][method] / filename
                    self.assertTrue(path.is_file(), str(path.relative_to(ROOT)))

    def test_configs_parse(self):
        for path in (ROOT / 'configs').rglob('*.cfg'):
            with self.subTest(config=str(path.relative_to(ROOT))):
                config = configparser.ConfigParser()
                config.read(path)
                self.assertTrue(config.has_section('env'))
                if config.has_option('env', 'num_qubits'):
                    self.assertGreater(config.getint('env', 'num_qubits'), 0)


if __name__ == '__main__':
    unittest.main()
