import tempfile
import unittest
from pathlib import Path
from scripts.verify_workflows import EXPECTED, verify

class WorkflowInventoryTests(unittest.TestCase):
    def test_repository_inventory(self):
        verify()

    def test_reject_legacy_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / ".github" / "workflows"
            folder.mkdir(parents=True)
            for filename, name in EXPECTED.items():
                (folder / filename).write_text(f"name: {name}\n")
            (folder / "legacy.yml").write_text("name: Old repair\n")
            with self.assertRaisesRegex(RuntimeError, "extra"):
                verify(Path(tmp))

if __name__ == "__main__": unittest.main()
