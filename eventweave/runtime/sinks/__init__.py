"""Built-in event sinks."""

from eventweave.runtime.sinks.file import FileSink
from eventweave.runtime.sinks.http import HTTPSink
from eventweave.runtime.sinks.null import NullSink
from eventweave.runtime.sinks.stdout import StdoutSink

__all__ = ["FileSink", "HTTPSink", "NullSink", "StdoutSink"]
