from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformCapabilities:
    platform_name: str
    solidworks_local_processing_available: bool
    solidworks_local_processing_reason: str = ""


def detect_platform_capabilities(platform_name: str | None = None) -> PlatformCapabilities:
    current_platform = platform_name or sys.platform
    if current_platform != "win32":
        return PlatformCapabilities(
            platform_name=current_platform,
            solidworks_local_processing_available=False,
            solidworks_local_processing_reason="此功能需要 Windows + SolidWorks + pywin32 环境。",
        )

    if importlib.util.find_spec("pythoncom") is None or importlib.util.find_spec("win32com.client") is None:
        return PlatformCapabilities(
            platform_name=current_platform,
            solidworks_local_processing_available=False,
            solidworks_local_processing_reason="此功能需要 pywin32/pythoncom 依赖。",
        )

    return PlatformCapabilities(
        platform_name=current_platform,
        solidworks_local_processing_available=True,
    )
