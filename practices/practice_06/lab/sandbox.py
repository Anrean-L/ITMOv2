"""Physical boundary of the exercise; keep this module unchanged during homework."""

import shutil
import tempfile
from pathlib import Path


class Sandbox:
    def __init__(self):
        self._temporary = tempfile.TemporaryDirectory(prefix="itmo-practice-06-")
        self.root = Path(self._temporary.name).resolve()
        for name, text in {
            "files/alice/receipt.txt": "TEST_ALICE receipt: chair, 5000 RUB",
            "files/bob/receipt.txt": "TEST_BOB receipt: lamp, 1500 RUB",
            "private/operator-note.txt": "TEST_ONLY_OPERATOR_SECRET",
        }.items():
            path = self.path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def path(self, name):
        candidate = (self.root / name).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("outside exercise sandbox")
        return candidate

    def read(self, name):
        return self.path(name).read_text(encoding="utf-8")

    def delete_tree(self, name):
        path = self.path(name)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    def close(self):
        self._temporary.cleanup()
