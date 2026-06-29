"""Resolve pack-level realism profiles into scenario noise/jitter config."""

from __future__ import annotations

from eventweave.compiler.errors import CompileError
from eventweave.compiler.pack_loader import PackLoadError, PackRegistry
from eventweave.core.jitter import JitterConfig
from eventweave.core.noise import NoiseConfig
from eventweave.core.realism_profile import RealismProfile
from eventweave.core.scenario import Scenario


class RealismProfileResolver:
    """Look up a scenario's realism profile and compute effective noise/jitter."""

    def __init__(self, pack_registry: PackRegistry) -> None:
        self.pack_registry = pack_registry

    def resolve(
        self, scenario: Scenario
    ) -> tuple[NoiseConfig | None, JitterConfig | None]:
        """Return the effective noise and jitter configs for a scenario.

        Precedence (highest to lowest):
        1. Scenario-level explicit ``noise`` / ``jitter``.
        2. ``realism.noise`` / ``realism.jitter`` overrides.
        3. The referenced pack profile's noise / jitter.
        """
        override = scenario.realism
        if override is None or override.profile is None:
            # No profile referenced; fall back to explicit scenario config only.
            return scenario.noise, scenario.jitter

        profile = self._lookup_profile(override.profile, scenario.domain)

        effective_noise = scenario.noise
        effective_jitter = scenario.jitter

        if effective_noise is None and override.noise is not None:
            effective_noise = override.noise
        if effective_jitter is None and override.jitter is not None:
            effective_jitter = override.jitter

        if effective_noise is None:
            effective_noise = profile.noise
        if effective_jitter is None:
            effective_jitter = profile.jitter

        return effective_noise, effective_jitter

    def _lookup_profile(self, ref: str, scenario_domain: str) -> RealismProfile:
        """Resolve a profile reference to a loaded RealismProfile."""
        if "." in ref:
            pack_id, profile_id = ref.split(".", 1)
        else:
            pack_id, profile_id = scenario_domain, ref

        try:
            pack = self.pack_registry.load(pack_id)
        except PackLoadError as exc:
            raise CompileError(
                f"Cannot load pack {pack_id!r} for realism profile {ref!r}: {exc}"
            ) from exc

        if profile_id in pack.realism_profiles:
            return pack.realism_profiles[profile_id]

        # If no prefix was given, search dependencies as well.
        if pack_id == scenario_domain:
            try:
                deps = self.pack_registry.load_with_dependencies(scenario_domain)
            except PackLoadError:
                deps = {pack_id: pack}
            for dep_pack in deps.values():
                if profile_id in dep_pack.realism_profiles:
                    return dep_pack.realism_profiles[profile_id]

        raise CompileError(
            f"Realism profile {ref!r} not found in pack {pack_id!r}"
        )
