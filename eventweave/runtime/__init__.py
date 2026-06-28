"""Python local runtime for EventWeave."""

from eventweave.runtime.local import LocalRuntime
from eventweave.runtime.sink import Sink
from eventweave.runtime.stats import RuntimeStats

__all__ = ["LocalRuntime", "Sink", "RuntimeStats"]
