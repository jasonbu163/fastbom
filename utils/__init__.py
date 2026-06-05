# utils/__init__.py

from utils.show import Show
from utils.log import logger

try:
    from utils.variant_helper import ref_int
except ModuleNotFoundError as exc:
    if exc.name != "pythoncom":
        raise

    def ref_int(value=0):
        raise RuntimeError("ref_int requires pywin32/pythoncom and is only available on Windows.")

__all__ = [
    'Show',
    'logger',
    'ref_int'
]
