"""Check that a missing dataset cannot damage the reference manifests."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('torch'),
                     'requires the benchmark environment')
class ManifestSafety(unittest.TestCase):
    def test_no_data_preserves_reference_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            artifact = root / 'artifact'
            artifact.mkdir()
            shutil.copy2(ROOT / 'bench_utils.py', root / 'bench_utils.py')
            shutil.copy2(ROOT / 'artifact/gen_manifest.py', artifact / 'gen_manifest.py')
            references = ['instances.csv', 'instances.json', 'mol_data.sha256']
            for name in references:
                (artifact / name).write_text('reference content\n')
            result = subprocess.run([sys.executable, str(artifact / 'gen_manifest.py')],
                                    text=True, capture_output=True, timeout=90)
            self.assertNotEqual(result.returncode, 0)
            for name in references:
                self.assertEqual((artifact / name).read_text(), 'reference content\n', name)
            self.assertIn('No Hamiltonians found', result.stderr)


if __name__ == '__main__':
    unittest.main()
