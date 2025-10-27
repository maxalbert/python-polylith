"""Factory functions to create package manager instances from enums."""

from typing import Union
from polylith.workspace.package_managers import (
    PackageManagerEnum,
    PackageManager,
    UvPackageManager,
    HatchPackageManager,
    PoetryPackageManager,
    PdmPackageManager,
)


def get_package_manager(package_manager: Union[str, PackageManagerEnum]) -> PackageManager:
    """Factory function to get PackageManager instance from string or enum.

    Args:
        package_manager: PackageManagerEnum value or string identifier

    Returns:
        Concrete PackageManager implementation

    Raises:
        ValueError: If package manager is not supported
    """
    # Convert string to enum if needed
    if isinstance(package_manager, str):
        try:
            pm_enum = PackageManagerEnum(package_manager)
        except ValueError:
            valid_options = [pm.value for pm in PackageManagerEnum]
            raise ValueError(f"Unsupported package manager '{package_manager}'. Valid options: {valid_options}")
    else:
        pm_enum = package_manager

    mapping = {
        PackageManagerEnum.UV: UvPackageManager(),
        PackageManagerEnum.HATCH: HatchPackageManager(),
        PackageManagerEnum.POETRY: PoetryPackageManager(),
        PackageManagerEnum.PDM: PdmPackageManager(),
    }

    if pm_enum not in mapping:
        raise ValueError(f"Unsupported package manager: {pm_enum}")

    return mapping[pm_enum]


def get_supported_package_managers() -> list[PackageManager]:
    """Get all supported package managers.

    Returns:
        List of all concrete PackageManager implementations
    """
    return [get_package_manager(pm) for pm in PackageManagerEnum]