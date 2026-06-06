from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from auth import AuthSession
from config import AppSettings
from services import RemoteApiClient, RemoteApiError, RemoteApiResponseError


ROLE_LABELS = {
    "admin": "管理员",
    "operator": "操作员",
    "viewer": "查看员",
}

STATUS_LABELS = {
    "active": "启用",
    "disabled": "禁用",
}


class ApiCallWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, call: Callable[[], Any]):
        super().__init__()
        self.call = call

    def run(self) -> None:
        try:
            self.finished.emit(self.call())
        except RemoteApiResponseError as exc:
            suffix = f"（{exc.error_code}）" if exc.error_code else ""
            self.failed.emit(f"{exc}{suffix}")
        except RemoteApiError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"远程请求失败：{exc}")
        finally:
            self.done.emit()


class UserManagementPage(QWidget):
    def __init__(
        self,
        settings: AppSettings,
        auth_session: AuthSession,
        client: Optional[RemoteApiClient] = None,
    ):
        super().__init__()
        self.settings = settings
        self.auth_session = auth_session
        self.client = client or RemoteApiClient(settings.remote_api)
        self.client.set_session(auth_session.remote_api_session)
        self.current_user: Optional[Mapping[str, Any]] = None
        self.users: list[Mapping[str, Any]] = []
        self.current_page = 1
        self.page_size = 20
        self.total_items = 0
        self._threads: list[QThread] = []
        self._workers: list[ApiCallWorker] = []
        self._closing = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(14)

        title = QLabel("账号管理")
        title.setObjectName("pageTitle")
        root_layout.addWidget(title)
        self._create_toolbar_group(root_layout)
        self._create_table_group(root_layout)
        self._refresh_action_state()

    def update_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.client.update_config(settings.remote_api)
        self._refresh_action_state()

    def shutdown(self) -> None:
        self._closing = True
        for thread in list(self._threads):
            thread.quit()
            if not thread.wait(max(1000, (self.settings.remote_api.timeout_seconds + 1) * 1000)):
                thread.wait()
        self._threads.clear()
        self._workers.clear()

    def _create_toolbar_group(self, layout: QVBoxLayout) -> None:
        group_layout = QVBoxLayout()
        status_row = QHBoxLayout()
        self.api_url_label = QLabel()
        self.login_state_label = QLabel()
        self.user_label = QLabel()
        self.request_state_label = QLabel("尚未请求")
        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.clicked.connect(self.refresh_all)
        status_row.addWidget(QLabel("服务器"))
        status_row.addWidget(self.api_url_label, 1)
        status_row.addWidget(QLabel("会话"))
        status_row.addWidget(self.login_state_label)
        status_row.addWidget(QLabel("当前用户"))
        status_row.addWidget(self.user_label)
        status_row.addStretch()
        status_row.addWidget(self.refresh_btn)
        group_layout.addLayout(status_row)

        request_row = QHBoxLayout()
        request_row.addWidget(QLabel("最近请求"))
        request_row.addWidget(self.request_state_label, 1)
        group_layout.addLayout(request_row)
        layout.addWidget(self._group("连接状态", group_layout))

    def _create_table_group(self, layout: QVBoxLayout) -> None:
        group_layout = QVBoxLayout()
        actions = QHBoxLayout()
        self.add_user_btn = QPushButton("新增用户")
        self.add_user_btn.clicked.connect(lambda: self._show_user_dialog())
        self.edit_user_btn = QPushButton("编辑选中")
        self.edit_user_btn.clicked.connect(self._edit_selected_user)
        self.reset_password_btn = QPushButton("重置密码")
        self.reset_password_btn.clicked.connect(self._reset_selected_password)
        self.change_own_password_btn = QPushButton("修改自己密码")
        self.change_own_password_btn.clicked.connect(self._change_own_password)
        self.delete_user_btn = QPushButton("禁用选中")
        self.delete_user_btn.clicked.connect(self._delete_selected_user)
        actions.addWidget(self.add_user_btn)
        actions.addWidget(self.edit_user_btn)
        actions.addWidget(self.reset_password_btn)
        actions.addWidget(self.delete_user_btn)
        actions.addStretch()
        actions.addWidget(self.change_own_password_btn)
        group_layout.addLayout(actions)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["账号", "显示名", "角色", "状态"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_selected_user)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 120)
        self.table.verticalHeader().setVisible(False)
        group_layout.addWidget(self.table, 1)

        self.empty_label = QLabel("没有可管理的账号。")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)
        group_layout.addWidget(self.empty_label)

        pagination = QHBoxLayout()
        self.total_label = QLabel("共 0 条")
        self.page_label = QLabel("第 1 / 1 页")
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.clicked.connect(self.previous_page)
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.clicked.connect(self.next_page)
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(1, 200)
        self.page_size_spin.setValue(self.page_size)
        self.page_size_spin.valueChanged.connect(self.change_page_size)
        pagination.addWidget(self.total_label)
        pagination.addStretch()
        pagination.addWidget(QLabel("每页"))
        pagination.addWidget(self.page_size_spin)
        pagination.addWidget(self.prev_page_btn)
        pagination.addWidget(self.page_label)
        pagination.addWidget(self.next_page_btn)
        group_layout.addLayout(pagination)

        table_group = self._group("账号列表", group_layout)
        table_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(table_group, 1)

    def refresh_all(self) -> None:
        self._run_api(
            "正在刷新账号...",
            lambda: {
                "current_user": self.client.get_current_user(),
                "user_page": self.client.page_users(self.current_page, self.page_size),
            },
            self._on_refresh_all_loaded,
        )

    def previous_page(self) -> None:
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self.refresh_all()

    def next_page(self) -> None:
        if self.current_page >= self._total_pages():
            return
        self.current_page += 1
        self.refresh_all()

    def change_page_size(self, page_size: int) -> None:
        self.page_size = page_size
        self.current_page = 1
        self.refresh_all()

    def _show_user_dialog(self, user: Optional[Mapping[str, Any]] = None) -> None:
        if not self._can_manage_users():
            QMessageBox.information(self, "账号管理", "当前账号没有用户管理权限。")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑用户" if user else "新增用户")
        form = QFormLayout(dialog)
        username_edit = QLineEdit(str(user.get("username") or "") if user else "")
        username_edit.setReadOnly(user is not None)
        display_name_edit = QLineEdit(str(user.get("displayName") or "") if user else "")
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        password_edit.setPlaceholderText("新增用户必填")
        role_combo = QComboBox()
        for role in self._allowed_roles():
            role_combo.addItem(ROLE_LABELS.get(role, role), role)
        status_combo = QComboBox()
        for status, label in STATUS_LABELS.items():
            status_combo.addItem(label, status)
        if user:
            role_combo.setCurrentIndex(max(0, role_combo.findData(user.get("role"))))
            status_combo.setCurrentIndex(max(0, status_combo.findData(user.get("status"))))
        form.addRow("账号", username_edit)
        form.addRow("显示名", display_name_edit)
        if not user:
            form.addRow("初始密码", password_edit)
        form.addRow("角色", role_combo)
        form.addRow("状态", status_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            password_edit.clear()
            return

        username = username_edit.text().strip()
        if not username:
            QMessageBox.warning(self, "账号管理", "请输入账号。")
            return
        if not user and not password_edit.text():
            QMessageBox.warning(self, "账号管理", "请输入初始密码。")
            return

        payload = {
            "displayName": display_name_edit.text().strip() or username,
            "role": role_combo.currentData(),
            "status": status_combo.currentData(),
        }
        if user:
            self._run_api(
                "正在更新用户...",
                lambda: self.client.update_user(username, payload),
                self._after_user_changed,
            )
        else:
            payload.update({"username": username, "password": password_edit.text()})
            self._run_api(
                "正在创建用户...",
                lambda: self.client.create_user(payload),
                self._after_user_changed,
            )
        password_edit.clear()

    def _edit_selected_user(self) -> None:
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "编辑用户", "请先选择一个用户。")
            return
        self._show_user_dialog(user)

    def _reset_selected_password(self) -> None:
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "重置密码", "请先选择一个用户。")
            return
        username = str(user.get("username") or "")
        self._show_password_dialog(username, require_old=username == self.auth_session.username)

    def _change_own_password(self) -> None:
        self._show_password_dialog(self.auth_session.username, require_old=True)

    def _show_password_dialog(self, username: str, require_old: bool) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("修改密码" if require_old else "重置密码")
        form = QFormLayout(dialog)
        old_password_edit = QLineEdit()
        old_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        new_password_edit = QLineEdit()
        new_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        if require_old:
            form.addRow("旧密码", old_password_edit)
        form.addRow("新密码", new_password_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            old_password_edit.clear()
            new_password_edit.clear()
            return
        if not new_password_edit.text():
            QMessageBox.warning(self, "密码", "请输入新密码。")
            return
        payload = {"newPassword": new_password_edit.text()}
        if require_old:
            if not old_password_edit.text():
                QMessageBox.warning(self, "密码", "请输入旧密码。")
                return
            payload["oldPassword"] = old_password_edit.text()
        self._run_api(
            "正在更新密码...",
            lambda: self.client.update_user_password(username, payload),
            self._after_password_changed,
        )
        old_password_edit.clear()
        new_password_edit.clear()

    def _delete_selected_user(self) -> None:
        user = self._selected_user()
        if user is None:
            QMessageBox.information(self, "禁用账号", "请先选择一个用户。")
            return
        username = str(user.get("username") or "")
        if QMessageBox.question(self, "禁用账号", f"确认禁用账号 {username}？这不会删除历史记录。") != QMessageBox.StandardButton.Yes:
            return
        self._run_api(
            "正在禁用账号...",
            lambda: self.client.delete_user(username),
            self._after_user_changed,
        )

    def _on_refresh_all_loaded(self, result: Mapping[str, Any]) -> None:
        self.current_user = dict(result.get("current_user") or {})
        self._on_user_page_loaded(dict(result.get("user_page") or {}))
        self._refresh_action_state()

    def _on_user_page_loaded(self, page_data: Mapping[str, Any]) -> None:
        meta = dict(page_data.get("meta") or {})
        self.current_page = int(meta.get("page") or self.current_page)
        self.page_size = int(meta.get("pageSize") or self.page_size)
        self.total_items = int(meta.get("total") or 0)
        if self.page_size_spin.value() != self.page_size:
            self.page_size_spin.blockSignals(True)
            self.page_size_spin.setValue(self.page_size)
            self.page_size_spin.blockSignals(False)
        self._on_users_loaded(list(page_data.get("items") or []))
        self._refresh_pagination_labels()

    def _on_users_loaded(self, users: list[Mapping[str, Any]]) -> None:
        self.users = users
        self.table.setRowCount(len(users))
        if not users:
            self.empty_label.setVisible(True)
            self.request_state_label.setText("账号列表为空")
            return
        self.empty_label.setVisible(False)
        for row, user in enumerate(users):
            values = [
                user.get("username"),
                user.get("displayName"),
                ROLE_LABELS.get(str(user.get("role")), user.get("role")),
                STATUS_LABELS.get(str(user.get("status")), user.get("status")),
            ]
            for col, value in enumerate(values):
                table_item = QTableWidgetItem("" if value is None else str(value))
                table_item.setData(Qt.ItemDataRole.UserRole, str(user.get("username") or ""))
                self.table.setItem(row, col, table_item)
        self.request_state_label.setText(f"已加载 {len(users)} 个账号")

    def _after_user_changed(self, _user: Mapping[str, Any]) -> None:
        self.request_state_label.setText("账号已更新")
        self.refresh_all()

    def _after_password_changed(self, _result: Mapping[str, Any]) -> None:
        self.request_state_label.setText("密码已更新")
        QMessageBox.information(self, "密码", "密码已更新。")

    def _refresh_pagination_labels(self) -> None:
        total_pages = self._total_pages()
        self.total_label.setText(f"共 {self.total_items} 条")
        self.page_label.setText(f"第 {self.current_page} / {total_pages} 页")
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < total_pages)

    def _total_pages(self) -> int:
        if self.total_items <= 0:
            return 1
        return max(1, (self.total_items + self.page_size - 1) // self.page_size)

    def _run_api(self, status: str, call: Callable[[], Any], on_success: Callable[[Any], None]) -> None:
        if self._closing:
            return
        if not self.auth_session.can_use_remote_features:
            message = "当前为离线登录，无法使用远程账号管理功能。"
            self.request_state_label.setText(message)
            QMessageBox.information(self, "远程功能不可用", message)
            return
        self.request_state_label.setText(status)
        thread = QThread(self)
        worker = ApiCallWorker(call)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result: self._handle_api_success(result, on_success))
        worker.failed.connect(self._on_api_failed)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._cleanup_worker(thread, worker))
        thread.finished.connect(thread.deleteLater)
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()

    def _handle_api_success(self, result: Any, on_success: Callable[[Any], None]) -> None:
        if self._closing:
            return
        on_success(result)

    def _cleanup_worker(self, thread: QThread, worker: ApiCallWorker) -> None:
        if thread in self._threads:
            self._threads.remove(thread)
        if worker in self._workers:
            self._workers.remove(worker)

    def _on_api_failed(self, message: str) -> None:
        if self._closing:
            return
        self.request_state_label.setText(message)
        self._refresh_action_state()
        QMessageBox.warning(self, "远程请求失败", message)

    def _selected_user(self) -> Optional[Mapping[str, Any]]:
        row = self.table.currentRow()
        if row < 0:
            return None
        table_item = self.table.item(row, 0)
        if table_item is None:
            return None
        username = table_item.data(Qt.ItemDataRole.UserRole)
        return self._user_by_username(str(username or ""))

    def _user_by_username(self, username: str) -> Optional[Mapping[str, Any]]:
        for user in self.users:
            if str(user.get("username") or "") == username:
                return user
        return None

    def _refresh_action_state(self) -> None:
        self.api_url_label.setText(self.settings.remote_api.base_url or "未配置")
        can_use_remote = self.auth_session.can_use_remote_features and self.client.session is not None
        if self.auth_session.can_use_remote_features and self.client.session is None:
            self.login_state_label.setText("登录失效")
        else:
            self.login_state_label.setText("服务器账号已登录" if can_use_remote else "离线登录，远程功能禁用")
        display_name = self.auth_session.display_name or self.auth_session.username
        if self.current_user:
            display_name = str(self.current_user.get("displayName") or self.current_user.get("username") or display_name)
        self.user_label.setText(display_name)
        can_manage = can_use_remote and self._can_manage_users()
        self.refresh_btn.setEnabled(can_use_remote)
        self.add_user_btn.setEnabled(can_manage)
        self.edit_user_btn.setEnabled(can_manage)
        self.reset_password_btn.setEnabled(can_manage)
        self.delete_user_btn.setEnabled(can_manage)
        self.change_own_password_btn.setEnabled(can_use_remote)

    def _can_manage_users(self) -> bool:
        if not self.current_user:
            return self.auth_session.can_use_remote_features
        return str(self.current_user.get("role") or "") == "admin"

    def _allowed_roles(self) -> list[str]:
        if self._can_manage_admin_users():
            return ["admin", "operator", "viewer"]
        return ["operator", "viewer"]

    def _can_manage_admin_users(self) -> bool:
        current_username = str((self.current_user or {}).get("username") or self.auth_session.username)
        if current_username == "root":
            return True
        for user in self.users:
            if str(user.get("role") or "") == "admin" and str(user.get("username") or "") != current_username:
                return True
        return False

    @staticmethod
    def _group(title: str, layout: QFormLayout | QVBoxLayout) -> QGroupBox:
        group = QGroupBox(title)
        group.setLayout(layout)
        return group
