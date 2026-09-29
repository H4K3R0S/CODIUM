"""F5 — regresija deljenog sloja (`core/cell/executor.py` + `approvals.py`)
u CODIUM-u. Isti kod kao u KALIMA (v. `tests/security/test_approval_gate_executor.py`
u ~/ai/domains/kalima), ovde samo dokazuje da se generalizovani obrazac
podjednako ponasa van KALIMA konteksta (bez scope-brane, jer CODIUM alati ne
ciljaju "metu" u pentest smislu).

Pokrece se direktno: `.venv/bin/python3 tests/security/test_cell_security_layer.py -v`
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_DOMAIN_ROOT = Path(__file__).resolve().parents[2]
if str(_DOMAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_DOMAIN_ROOT))

from core.cell.approvals import PENDING, Approvals
from core.cell.executor import (
    EXECUTED,
    REJECTED,
    Executor,
)

_ALLOWLIST = {
    "domain": "codium",
    "tools": {
        "echo": {"binary": "/bin/echo", "risk": "LOW", "targets_network": False,
                  "timeout_s": 10, "action": "codium.echo"},
    },
}


class CellSecurityLayerTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        tmp_path = Path(self._tmp.name)
        self.allow_path = tmp_path / "tools.allow.json"
        self.allow_path.write_text(json.dumps(_ALLOWLIST), encoding="utf-8")
        self.approvals = Approvals(database_path=tmp_path / "approvals.db")
        self.executor = Executor(
            domain="codium", allow_path=self.allow_path,
            logs_dir=tmp_path / "logs", approvals=self.approvals,
            emit=lambda evt: None,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_low_risk_izvrsava_se_i_pise_audit(self) -> None:
        rezultat = self.executor.run("echo", args={"argv": ["codium-test"]})
        self.assertEqual(rezultat.status, EXECUTED)
        self.assertIn("codium-test", rezultat.stdout)
        self.assertTrue(Path(rezultat.audit_path).exists())

    def test_non_allowlist_alat_ne_izvrsava_se(self) -> None:
        with patch("core.cell.executor.subprocess.run") as run_mock:
            rezultat = self.executor.run("rm", args={"argv": ["-rf", "/"]})
            run_mock.assert_not_called()
        self.assertEqual(rezultat.status, REJECTED)

    def test_high_gate_pa_izvrsenje_bezopasnom_komandom(self) -> None:
        gate, token = self.approvals.create_gate(
            tool="echo", args={"argv": ["odobreno-codium"]}, risk="HIGH",
            reason="simulirana HIGH akcija (npr. `git push` bi bio ovde)",
        )
        self.assertEqual(gate.status, PENDING)
        self.assertIsNone(self.approvals.approve(gate.id, "pogresan-token"))
        odobren = self.approvals.approve(gate.id, token)
        self.assertIsNotNone(odobren)
        rezultat = self.executor.execute_approved(odobren)
        self.assertEqual(rezultat.status, EXECUTED)
        self.assertIn("odobreno-codium", rezultat.stdout)


class RegressionImportTest(unittest.TestCase):
    def test_uvoz_ne_puca(self) -> None:
        import core.cell.approvals
        import core.cell.executor  # noqa: F401


if __name__ == "__main__":
    unittest.main(verbosity=2)
