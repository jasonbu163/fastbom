from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from auth import AuthSession
from config import AppSettings
from config.settings import save_settings
from config.app_metadata import APP_NAME, window_title_with_version
from services.auth_service import AuthError, AuthService


class LoginWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, login_call):
        super().__init__()
        self.login_call = login_call

    def run(self) -> None:
        try:
            self.finished.emit(self.login_call())
        except AuthError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"登录失败：{exc}")
        finally:
            self.done.emit()


class LoginDialog(QDialog):
    def __init__(self, auth_service: AuthService, settings: AppSettings, settings_store):
        super().__init__()
        self.auth_service = auth_service
        self.settings = settings
        self.settings_store = settings_store
        self.auth_session: AuthSession | None = None
        self._login_thread: QThread | None = None
        self._login_worker: LoginWorker | None = None

        self.setWindowTitle(window_title_with_version())
        self.setFixedWidth(560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 24)
        layout.setSpacing(18)

        title = QLabel(f"{window_title_with_version()} ({APP_NAME})")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        subtitle = QLabel("服务器账号可解锁远程物料库；离线 admin 仅用于服务器不可用时进入软件。")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        api_row = QHBoxLayout()
        self.api_state_label = QLabel()
        self._refresh_api_state_label()
        api_settings_btn = QPushButton("服务器设置")
        api_settings_btn.clicked.connect(self._show_settings_dialog)
        api_row.addWidget(self.api_state_label, 1)
        api_row.addWidget(api_settings_btn)
        layout.addLayout(api_row)

        form = QFormLayout()
        form.setSpacing(12)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("服务器账号或 admin")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("账号", self.username_edit)
        form.addRow("密码", self.password_edit)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.backend_login_btn = QPushButton("登录")
        self.backend_login_btn.clicked.connect(self._login_backend)
        self.fallback_login_btn = QPushButton("离线登录")
        self.fallback_login_btn.clicked.connect(self._login_fallback)
        cancel_btn = QPushButton("取消")
        self.cancel_btn = cancel_btn
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(self.backend_login_btn)
        actions.addWidget(self.fallback_login_btn)
        actions.addWidget(cancel_btn)
        layout.addLayout(actions)

    def _login_backend(self) -> None:
        self._login_async(
            lambda: self.auth_service.login_backend_user(
                self.username_edit.text().strip(),
                self.password_edit.text(),
            )
        )

    def _login_fallback(self) -> None:
        self._login(
            lambda: self.auth_service.login_fallback_admin(
                self.username_edit.text().strip(),
                self.password_edit.text(),
            )
        )

    def _login(self, login_call) -> None:
        try:
            self.auth_session = login_call()
        except AuthError as exc:
            QMessageBox.warning(self, "登录失败", str(exc))
            return
        self.accept()

    def _login_async(self, login_call) -> None:
        if self._login_thread is not None:
            return

        self._set_login_pending(True)
        thread = QThread(self)
        worker = LoginWorker(login_call)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_login_success)
        worker.failed.connect(self._on_login_failed)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(self._cleanup_login_worker)
        thread.finished.connect(thread.deleteLater)
        self._login_thread = thread
        self._login_worker = worker
        thread.start()

    def _on_login_success(self, auth_session: AuthSession) -> None:
        self.auth_session = auth_session
        self.accept()

    def _on_login_failed(self, message: str) -> None:
        QMessageBox.warning(self, "登录失败", message)

    def _cleanup_login_worker(self) -> None:
        self._login_thread = None
        self._login_worker = None
        self._set_login_pending(False)

    def _set_login_pending(self, pending: bool) -> None:
        self.backend_login_btn.setEnabled(not pending)
        self.fallback_login_btn.setEnabled(not pending)
        self.cancel_btn.setEnabled(not pending)
        self.username_edit.setEnabled(not pending)
        self.password_edit.setEnabled(not pending)
        self.backend_login_btn.setText("正在登录..." if pending else "登录")

    def _show_settings_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("服务器设置")
        form = QFormLayout(dialog)
        api_url_edit = QLineEdit(self.settings.remote_api.base_url)
        api_url_edit.setPlaceholderText("例如 http://192.168.1.10:18080")
        timeout_spin = QSpinBox()
        timeout_spin.setRange(1, 300)
        timeout_spin.setValue(self.settings.remote_api.timeout_seconds)
        form.addRow("服务器", api_url_edit)
        form.addRow("请求超时秒数", timeout_spin)

        actions = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        save_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        actions.addStretch()
        actions.addWidget(save_btn)
        actions.addWidget(cancel_btn)
        form.addRow(actions)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.save_backend_settings(api_url_edit.text().strip(), timeout_spin.value())
        self._refresh_api_state_label()
        QMessageBox.information(self, "服务器设置", "服务器设置已保存。")

    def save_backend_settings(self, base_url: str, timeout_seconds: int) -> AppSettings:
        normalized_base_url = self._normalize_base_url(base_url)
        self.settings = AppSettings(
            app=self.settings.app,
            bom=self.settings.bom,
            output=self.settings.output,
            inventory=self.settings.inventory,
            solidworks=self.settings.solidworks,
            dxf=self.settings.dxf,
            remote_api=type(self.settings.remote_api)(
                base_url=normalized_base_url,
                timeout_seconds=timeout_seconds,
            ),
            auth=self.settings.auth,
        )
        save_settings(self.settings, self.settings_store)
        self.auth_service.settings = self.settings
        return self.settings

    def _refresh_api_state_label(self) -> None:
        api_url = self.settings.remote_api.base_url.strip()
        if api_url:
            self.api_state_label.setText(f"服务器：{api_url}")
        else:
            self.api_state_label.setText("服务器：未配置，可先使用离线登录")

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        value = base_url.strip()
        if value and "://" not in value:
            return f"http://{value}"
        return value
