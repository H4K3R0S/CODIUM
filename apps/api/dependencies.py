from core.foundation.lifecycle import RuntimeLifecycle, runtime_lifecycle

# ==========          FOUNDATION DEPENDENCIES          ==========

def get_runtime_lifecycle() -> RuntimeLifecycle:
    """Vraca CORE runtime lifecycle (stanje sistema)."""

    return runtime_lifecycle
