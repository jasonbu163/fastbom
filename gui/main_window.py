from __future__ import annotations

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

from config import AppSettings, load_settings
from gui.pages.local_processing_page import LocalProcessingPage
from gui.pages.settings_page import SettingsPage
from utils.platform_capabilities import PlatformCapabilities, detect_platform_capabilities


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: Optional[AppSettings] = None,
        settings_store=None,
        platform_capabilities: Optional[PlatformCapabilities] = None,
    ):
        super().__init__()
        self.settings = settings or load_settings()
        self.settings_store = settings_store
        self.platform_capabilities = platform_capabilities or detect_platform_capabilities()

        self.setWindowTitle("FastBOM智能处理系统 v2.0")
        self.setMinimumSize(1100, 760)

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

        title = QLabel("FastBOM")
        title.setObjectName("sidebarTitle")
        subtitle = QLabel("智能处理系统 v2.0")
        subtitle.setObjectName("sidebarSubtitle")
        sidebar_layout.addWidget(title)
        sidebar_layout.addWidget(subtitle)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("primaryNav")
        self.sidebar.addItem("本地处理")
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
        self.settings_page = SettingsPage(self.settings, store=self.settings_store)
        self.settings_page.settings_saved.connect(self._on_settings_saved)

        self.pages.addWidget(self.local_processing_page)
        self.pages.addWidget(self.settings_page)
        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

    def _on_settings_saved(self, settings: AppSettings) -> None:
        self.settings = settings
        self.local_processing_page.update_settings(settings)
