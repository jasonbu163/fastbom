from __future__ import annotations
from typing import Any
import pythoncom
from win32com.client import VARIANT  # 让调用方少敲一次 pythoncom.XXX

# 下面这两行把 IDE 的“未解析”警告一次性掐掉
VT_BYREF = pythoncom.VT_BYREF  # type: ignore[attr-defined]
VT_I4 = pythoncom.VT_I4        # type: ignore[attr-defined]

# --------------------------------------------------
# 公用的“引用型整型 VARIANT”构造器
# --------------------------------------------------
def ref_int(initial: int = 0) -> VARIANT:
    """
    返回一个 VT_BYREF | VT_I4 的 VARIANT，专用于 SolidWorks API 里
    需要传出 errors/warnings 这类整型引用参数的场景。
    """
    return VARIANT(VT_BYREF | VT_I4, initial)

# --------------------------------------------------
# 以后需要别的类型就继续加，例如：
# def ref_double(initial: float = 0.0) -> VARIANT:
#     return VARIANT(VT_BYREF | VT_R8, initial)
# --------------------------------------------------