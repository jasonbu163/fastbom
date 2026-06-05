# core/__init__.py

__all__ = [
    "BOMClassifier",
    "DXFProcessor",
    "SWConverter",
    "FileExport",
    "SetViews",
    "SetTemplate",
]


def __getattr__(name):
    if name == "BOMClassifier":
        from core.bom_classifier import BOMClassifier

        return BOMClassifier
    if name == "DXFProcessor":
        from core.dxf_processor import DXFProcessor

        return DXFProcessor
    if name == "SWConverter":
        from core.sw_converter import SWConverter

        return SWConverter
    if name == "FileExport":
        from core.file_export import FileExport

        return FileExport
    if name == "SetViews":
        from core.set_views import SetViews

        return SetViews
    if name == "SetTemplate":
        from core.set_template import SetTemplate

        return SetTemplate
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
