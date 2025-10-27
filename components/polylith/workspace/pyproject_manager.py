"""PyProject.toml file management with immutable operations."""

import copy
from pathlib import Path
from typing import Dict, Any
import tomlkit

from polylith.workspace.build_backends import BuildBackend
from polylith.workspace.build_backend_factory import get_build_backend


def _deep_merge_dict(target: dict, source: dict) -> None:
    """Deep merge source dict into target dict."""
    for key, value in source.items():
        if key not in target:
            target[key] = value
        elif isinstance(value, dict) and isinstance(target[key], dict):
            _deep_merge_dict(target[key], value)
        else:
            target[key] = value


class PyProjectTOMLManager:
    """Immutable manager for pyproject.toml file operations."""

    def __init__(self, content: Dict[str, Any]):
        """Initialize with parsed TOML content."""
        self._content = content

    @classmethod
    def from_file(cls, pyproject_toml_path: Path) -> 'PyProjectTOMLManager':
        """Create manager from pyproject.toml file."""
        if not pyproject_toml_path.exists():
            # Return manager with empty content for missing files
            return cls({})

        try:
            content = tomlkit.loads(pyproject_toml_path.read_text())
            return cls(dict(content))  # Convert to regular dict for easier manipulation
        except tomlkit.exceptions.ParseError as e:
            raise ValueError(f"Invalid TOML syntax in {pyproject_toml_path}: {e}") from e

    def detect_build_backend(self) -> BuildBackend:
        """Detect build backend from TOML content."""
        # Check if build-system section exists
        build_system = self._content.get("build-system")
        if not build_system:
            return get_build_backend("")

        # Check if build-backend is specified
        build_backend = build_system.get("build-backend", "")
        return get_build_backend(build_backend)

    def merge_config(self, new_config: Dict[str, Any]) -> 'PyProjectTOMLManager':
        """Return new manager with merged configuration."""
        # Create deep copy of current content
        merged_content = copy.deepcopy(self._content)

        # Deep merge new config into copy
        _deep_merge_dict(merged_content, new_config)

        return PyProjectTOMLManager(merged_content)

    def merge_backend_if_compatible(self, new_backend: BuildBackend) -> 'PyProjectTOMLManager':
        """Return new manager with merged backend config if compatible with existing backend."""
        existing_backend = self.detect_build_backend()

        if not existing_backend.is_compatible_with(new_backend) and existing_backend.get_identifier() != "none":
            raise ValueError(f"Incompatible backends: existing {existing_backend.get_identifier()}, new {new_backend.get_identifier()}")

        new_config = new_backend.generate_config()
        return self.merge_config(new_config)

    def write_content(self, output_path: Path) -> None:
        """Write content to pyproject.toml file."""
        with output_path.open("w", encoding="utf-8") as f:
            f.write(tomlkit.dumps(self._content))

    def has_complete_build_system(self) -> bool:
        """Check if build-system section is complete."""
        build_system = self._content.get("build-system", {})
        hatch_config = self._content.get("tool", {}).get("hatch", {}).get("build", {})

        return bool(
            build_system.get("build-backend") and
            hatch_config.get("dev-mode-dirs")
        )

    def has_polylith_config(self) -> bool:
        """Check for Polylith-specific configuration."""
        return "tool" in self._content and "polylith" in self._content["tool"]

    def is_empty(self) -> bool:
        """Check if the content is empty (file didn't exist or was empty)."""
        return not self._content