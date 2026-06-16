from __future__ import annotations

if __name__ == "__main__" and __package__ in {None, ""}:
    raise SystemExit("请从项目入口启动：uv run python main.py")

from pathlib import Path
from typing import Optional

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from auth import AuthSession
from config import AppSettings, load_settings
from config.app_metadata import WINDOW_TITLE, APP_NAME, APP_VERSION, window_title_with_version
from gui.pages.local_processing_page import LocalProcessingPage
from gui.pages.residual_material_page import ResidualMaterialPage
from gui.pages.settings_page import SettingsPage
from gui.pages.user_management_page import UserManagementPage
from services.remote_api import RemoteApiClient, RemoteApiError
from utils.platform_capabilities import PlatformCapabilities, detect_platform_capabilities


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: Optional[AppSettings] = None,
        settings_store=None,
        auth_session: Optional[AuthSession] = None,
        platform_capabilities: Optional[PlatformCapabilities] = None,
        remote_api_client_factory=RemoteApiClient,
    ):
        super().__init__()
        self.settings = settings or load_settings()
        self.settings_store = settings_store
        self.auth_session = auth_session or AuthSession.fallback_admin(self.settings.auth.fallback_admin_username)
        self.platform_capabilities = platform_capabilities or detect_platform_capabilities()
        self.remote_api_client_factory = remote_api_client_factory
        self._logout_attempted = False

        self.setWindowTitle(window_title_with_version())
        self.setMinimumSize(1360, 820)

        icon_path = Path("static/efficacy_researching_settings_icon_152066.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(22, 22, 22, 22)
        root_layout.setSpacing(16)

        self.primary_sidebar = QFrame()
        self.primary_sidebar.setObjectName("primarySidebar")
        self.primary_sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.primary_sidebar)
        sidebar_layout.setContentsMargins(18, 22, 18, 18)
        sidebar_layout.setSpacing(14)

        title = QLabel(WINDOW_TITLE)
        title.setObjectName("sidebarTitle")
        subtitle = QLabel(f"{APP_NAME} {APP_VERSION}")
        subtitle.setObjectName("sidebarSubtitle")
        sidebar_layout.addWidget(title)
        sidebar_layout.addWidget(subtitle)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("primaryNav")
        self.sidebar.addItem("板材物料库存管理")
        self.sidebar.addItem("本地处理")
        self.sidebar.addItem("用户管理")
        self.sidebar.addItem("设置")
        sidebar_layout.addWidget(self.sidebar, 1)
        root_layout.addWidget(self.primary_sidebar)

        self.content_card = QFrame()
        self.content_card.setObjectName("contentCard")
        content_layout = QVBoxLayout(self.content_card)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        self.pages = QStackedWidget()
        self.pages.setObjectName("primaryPages")
        content_layout.addWidget(self.pages)
        root_layout.addWidget(self.content_card, 1)

        self.local_processing_page = LocalProcessingPage(
            settings=self.settings,
            platform_capabilities=self.platform_capabilities,
        )
        self.user_management_page = UserManagementPage(
            settings=self.settings,
            auth_session=self.auth_session,
        )
        self.residual_material_page = ResidualMaterialPage(
            settings=self.settings,
            auth_session=self.auth_session,
        )
        self.settings_page = SettingsPage(self.settings, store=self.settings_store)
        self.settings_page.settings_saved.connect(self._on_settings_saved)

        self.pages.addWidget(self.residual_material_page)
        self.pages.addWidget(self.local_processing_page)
        self.pages.addWidget(self.user_management_page)
        self.pages.addWidget(self.settings_page)
        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

    def _on_settings_saved(self, settings: AppSettings) -> None:
        self.settings = settings
        self.local_processing_page.update_settings(settings)
        self.user_management_page.update_settings(settings)
        self.residual_material_page.update_settings(settings)

    def closeEvent(self, event) -> None:
        self.user_management_page.shutdown()
        self.residual_material_page.shutdown()
        self._logout_backend_session()
        super().closeEvent(event)

    def _logout_backend_session(self) -> None:
        if self._logout_attempted:
            return
        self._logout_attempted = True

        remote_session = self.auth_session.remote_api_session
        if remote_session is None:
            return

        client = self.remote_api_client_factory(self.settings.remote_api)
        client.set_session(remote_session)
        try:
            client.logout()
        except RemoteApiError:
            pass
