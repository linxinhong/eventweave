"""Encoder registry and pack discovery."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path

from eventweave.encoders.base import Encoder


class EncoderRegistry:
    """Global registry of available encoders."""

    def __init__(self, packs_dir: str | Path | None = None) -> None:
        self._encoders: dict[str, Encoder] = {}
        if packs_dir is None:
            self.packs_dir = Path(__file__).parent.parent.parent / "packs"
        else:
            self.packs_dir = Path(packs_dir)

    def register(self, encoder: Encoder) -> Encoder:
        """Register an encoder instance."""
        self._encoders[encoder.name] = encoder
        return encoder

    def get(self, name: str) -> Encoder:
        """Return an encoder by name, discovering pack encoders if needed."""
        if name not in self._encoders:
            self._load_pack_encoders()
        if name not in self._encoders:
            raise KeyError(f"Unknown encoder: {name}")
        return self._encoders[name]

    def has(self, name: str) -> bool:
        """Return True if the encoder is registered or loadable from packs."""
        if name in self._encoders:
            return True
        self._load_pack_encoders()
        return name in self._encoders

    def list(self) -> list[str]:
        """Return all registered encoder names."""
        self._load_pack_encoders()
        return sorted(self._encoders.keys())

    def _load_pack_encoders(self) -> None:
        """Scan packs for encoder modules and import them once."""
        if not self.packs_dir.exists():
            return
        if getattr(self, "_packs_loaded", False):
            return
        self._packs_loaded = True
        for pack_path in sorted(self.packs_dir.iterdir()):
            if not pack_path.is_dir():
                continue
            encoders_init = pack_path / "encoders" / "__init__.py"
            if not encoders_init.exists():
                continue
            self._import_module(encoders_init)

    def _import_module(self, path: Path) -> None:
        """Import a pack encoder module by file path."""
        module_name = f"eventweave_pack_encoders_{path.parent.parent.name}"
        if module_name in sys.modules:
            return
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)


def encoder(
    name: str, content_type: str = "text/plain"
) -> Callable[[type[Encoder]], type[Encoder]]:
    """Class decorator that registers an encoder under *name*."""

    def decorator(cls: type[Encoder]) -> type[Encoder]:
        instance = cls()
        instance.name = name
        instance.content_type = content_type
        _default_registry.register(instance)
        return cls

    return decorator


# Global default registry used by CLI and runtimes.
_default_registry: EncoderRegistry = EncoderRegistry()


def get_encoder(name: str) -> Encoder:
    """Lookup an encoder in the default registry."""
    return _default_registry.get(name)


def list_encoders() -> list[str]:
    """List all encoders in the default registry."""
    return _default_registry.list()
