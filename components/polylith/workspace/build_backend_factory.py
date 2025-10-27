"""Factory functions to create build backend instances."""

from typing import Union
from polylith.workspace.build_backends import (
    BuildBackendEnum,
    BuildBackend,
    HatchlingBackend,
    PoetryCoreBackend,
    PdmBackend,
    UnsupportedBuildBackend,
    NoBuildBackend,
)


def get_build_backend(backend: Union[str, BuildBackendEnum]) -> BuildBackend:
    """Factory function to get BuildBackend instance from enum or string identifier.

    Args:
        backend: BuildBackendEnum value or string identifier from pyproject.toml

    Returns:
        Concrete BuildBackend implementation (including special backends for unsupported/missing cases)
    """
    # Convert string identifier to enum if needed
    if isinstance(backend, str):
        if not backend:
            return NoBuildBackend()

        if "poetry" in backend:
            backend_enum = BuildBackendEnum.POETRY_CORE
        elif "hatchling" in backend:
            backend_enum = BuildBackendEnum.HATCHLING
        elif "pdm" in backend:
            backend_enum = BuildBackendEnum.PDM_BACKEND
        else:
            # Unknown/unsupported backend
            return UnsupportedBuildBackend(backend)
    else:
        backend_enum = backend

    # Handle special enum cases
    if backend_enum == BuildBackendEnum.NONE:
        return NoBuildBackend()
    elif backend_enum == BuildBackendEnum.UNSUPPORTED:
        return UnsupportedBuildBackend("unsupported")

    # Standard mapping
    mapping = {
        BuildBackendEnum.HATCHLING: HatchlingBackend(),
        BuildBackendEnum.POETRY_CORE: PoetryCoreBackend(),
        BuildBackendEnum.PDM_BACKEND: PdmBackend(),
    }

    if backend_enum not in mapping:
        # This should not happen with current enum values, but be defensive
        return UnsupportedBuildBackend(str(backend_enum))

    return mapping[backend_enum]