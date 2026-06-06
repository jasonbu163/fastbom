APP_NAME = "PMMS"
APP_VERSION = "3.0"
WINDOW_TITLE = "生产物料管理系统"


def window_title_with_version() -> str:
    return f"{WINDOW_TITLE} {APP_VERSION}"

def login_window_title_with_version() -> str:
    return f"登录 {WINDOW_TITLE} {APP_VERSION}"