# ========== RUNTIME: dozvole i dnevnik CODIUM-a ==========
# Rute traze gate i dnevnik kroz `Depends`, pa im ovde stoji jedan primerak.
# Testovi ga menjaju kroz `app.dependency_overrides`, ne kroz ovaj modul.
from __future__ import annotations

from pathlib import Path

from core.ai.usage import UsageRecorder
from core.domains.codium.audit import (
    ActivityFeed,
    ApprovalRepository,
    AuditRepository,
    ScopeRuleRepository,
)
from core.domains.codium.runtime import (
    codium_database_path,
    codium_ops_database_path,
)
from core.security.scope_gate import ScopeGate

_rules: ScopeRuleRepository | None = None
_audit: AuditRepository | None = None
_gate: ScopeGate | None = None
_feed: ActivityFeed | None = None
_approvals: ApprovalRepository | None = None


def _database_path() -> Path:
    """Poslovna baza (pravila). Izdvojeno da test moze da je zameni."""
    return codium_database_path()


def _ops_database_path() -> Path:
    """Operativna baza (dnevnik)."""
    return codium_ops_database_path()


def get_scope_rules() -> ScopeRuleRepository:
    global _rules
    if _rules is None:
        _rules = ScopeRuleRepository(_database_path())
    return _rules


def get_audit() -> AuditRepository:
    global _audit
    if _audit is None:
        _audit = AuditRepository(_ops_database_path())
    return _audit


def get_scope_gate() -> ScopeGate:
    global _gate
    if _gate is None:
        # Pravila se citaju u trenutku provere, ne sada: pravilo dodato u toku
        # rada mora da vazi odmah, bez restarta.
        _gate = ScopeGate(lambda: get_scope_rules().list())
    return _gate


def get_activity_feed() -> ActivityFeed:
    global _feed
    if _feed is None:
        # Feed spaja dnevnik i evidenciju poziva — obe zive u ops bazi.
        _feed = ActivityFeed(get_audit(), UsageRecorder(_ops_database_path()))
    return _feed


def get_approvals() -> ApprovalRepository:
    global _approvals
    if _approvals is None:
        # Molbe su poslovni podatak — poslovna baza, ne ops.
        _approvals = ApprovalRepository(_database_path())
    return _approvals


def reset() -> None:
    """Zaboravi napravljene primerke (koristi se u testovima)."""
    global _rules, _audit, _gate, _feed, _approvals
    _rules = None
    _audit = None
    _gate = None
    _feed = None
    _approvals = None
