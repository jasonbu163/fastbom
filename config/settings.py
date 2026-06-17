from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, MutableMapping, Optional, Tuple


@dataclass(frozen=True)
class AppConfig:
    theme: str = "dark_teal.xml"


@dataclass(frozen=True)
class BomConfig:
    part_column: str = "图号"
    material_column: str = "材料"
    material_split_markers: str = "板"
    quantity_column: str = "总数量"


@dataclass(frozen=True)
class OutputConfig:
    result_dir: str = "result"
    classified_dir: str = "1_分类结果"
    processed_dxf_dir: str = "2_DXF处理结果"
    merged_dir: str = "3_合并文件"


@dataclass(frozen=True)
class InventoryConfig:
    export_filename_prefix: str = "板材物料库存"


@dataclass(frozen=True)
class SolidWorksConfig:
    template_dir: str = "template"
    visible: bool = False


@dataclass(frozen=True)
class DxfConfig:
    text_layer: str = "0"
    text_color: int = 2
    text_height: float = 50.0
    spacing: float = 100.0


@dataclass(frozen=True)
class RemoteApiConfig:
    base_url: str = ""
    timeout_seconds: int = 15


@dataclass(frozen=True)
class AuthConfig:
    fallback_admin_username: str = "admin"
    fallback_admin_password: str = "#456@admin"


@dataclass(frozen=True)
class AppSettings:
    app: AppConfig = AppConfig()
    bom: BomConfig = BomConfig()
    output: OutputConfig = OutputConfig()
    inventory: InventoryConfig = InventoryConfig()
    solidworks: SolidWorksConfig = SolidWorksConfig()
    dxf: DxfConfig = DxfConfig()
    remote_api: RemoteApiConfig = RemoteApiConfig()
    auth: AuthConfig = AuthConfig()


SETTING_SPECS: Tuple[Tuple[str, Any], ...] = (
    ("app.theme", str),
    ("bom.part_column", str),
    ("bom.material_column", str),
    ("bom.material_split_markers", str),
    ("bom.quantity_column", str),
    ("output.result_dir", str),
    ("output.classified_dir", str),
    ("output.processed_dxf_dir", str),
    ("output.merged_dir", str),
    ("inventory.export_filename_prefix", str),
    ("solidworks.template_dir", str),
    ("solidworks.visible", bool),
    ("dxf.text_layer", str),
    ("dxf.text_color", int),
    ("dxf.text_height", float),
    ("dxf.spacing", float),
    ("remote_api.base_url", str),
    ("remote_api.timeout_seconds", int),
    ("auth.fallback_admin_username", str),
    ("auth.fallback_admin_password", str),
)


class InMemorySettingsStore:
    def __init__(self, values: Optional[Mapping[str, Any]] = None):
        self._values: MutableMapping[str, Any] = dict(values or {})

    def value(self, key: str) -> Any:
        return self._values.get(key)

    def set_value(self, key: str, value: Any) -> None:
        self._values[key] = value


class QtSettingsStore:
    def __init__(self, organization: str = "FastBOM", application: str = "FastBOM"):
        from PySide6.QtCore import QSettings

        self._settings = QSettings(organization, application)

    def value(self, key: str) -> Any:
        return self._settings.value(key, None)

    def set_value(self, key: str, value: Any) -> None:
        self._settings.setValue(key, value)


def load_settings(store: Optional[Any] = None) -> AppSettings:
    settings = AppSettings()
    if store is not None:
        settings = _apply_values(settings, _values_from_store(store))
    return settings


def save_settings(settings: AppSettings, store: Any) -> None:
    for key, _ in SETTING_SPECS:
        store.set_value(key, _get_nested_value(settings, key))


def can_use_remote_forms(auth_mode: str) -> bool:
    return auth_mode != "fallback_admin"


def _values_from_store(store: Any) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for key, converter in SETTING_SPECS:
        value = store.value(key)
        if key == "auth.fallback_admin_password" and value == "":
            continue
        if value is not None:
            values[key] = _convert_value(value, converter)
    return values


def _apply_values(settings: AppSettings, values: Mapping[str, Any]) -> AppSettings:
    section_values: Dict[str, Dict[str, Any]] = {}
    for key, value in values.items():
        section, field = key.split(".", 1)
        section_values.setdefault(section, {})[field] = value

    for section, values_for_section in section_values.items():
        current_section = getattr(settings, section)
        settings = replace(settings, **{section: replace(current_section, **values_for_section)})

    return settings


def _get_nested_value(settings: AppSettings, key: str) -> Any:
    section, field = key.split(".", 1)
    return getattr(getattr(settings, section), field)


def _convert_value(value: Any, converter: Any) -> Any:
    if converter is bool:
        return _convert_bool(value)
    if converter is int:
        return int(value)
    if converter is float:
        return float(value)
    return str(value)


def _convert_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
