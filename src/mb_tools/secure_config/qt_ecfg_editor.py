"""
Qt editor for password-encrypted .ecfg dictionary files.

This module depends on PySide6 and is intentionally kept separate from
the core ecfg.py module so that mb_tools.secure_config can be used
without requiring Qt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from mb_tools.secure_config import (
    EcfgDecryptError,
    EcfgError,
    load_ecfg,
    save_ecfg,
)
from mb_tools.secure_config.qt_password import (
    get_ecfg_path_and_password,
    get_new_password,
    get_password,
)


MAX_RECENT_FILES = 8


TableSnapshot = list[tuple[str, str]]


class EcfgEditorWindow(QMainWindow):
    """
    Main window for editing encrypted dictionary-style .ecfg files.
    """

    def __init__(self) -> None:
        super().__init__()

        self._path: Path | None = None
        self._password: str | None = None
        self._dirty = False
        self._loading_table = False

        self._undo_stack: list[TableSnapshot] = []
        self._redo_stack: list[TableSnapshot] = []

        self._settings = QSettings("MBTools", "EcfgEditor")
        self._recent_files = self._load_recent_files()

        self.setWindowTitle("ECFG Editor")
        self.resize(800, 500)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Key", "Value"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.itemChanged.connect(self._on_item_changed)

        self._build_actions()
        self._build_menu()
        self._build_toolbar()
        self._build_central_widget()

        self._reset_undo_history()
        self._update_window_title()
        self._update_undo_redo_enabled()
        self._update_recent_files_menu()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_actions(self) -> None:
        self._new_action = QAction("New", self)
        self._new_action.triggered.connect(self.new_file)

        self._open_action = QAction("Open...", self)
        self._open_action.triggered.connect(self.open_file)

        self._save_action = QAction("Save", self)
        self._save_action.triggered.connect(self.save_file)

        self._save_as_action = QAction("Save As...", self)
        self._save_as_action.triggered.connect(self.save_file_as)

        self._change_password_action = QAction("Change Password...", self)
        self._change_password_action.triggered.connect(self.change_password)

        self._exit_action = QAction("Exit", self)
        self._exit_action.triggered.connect(self.close)

        self._undo_action = QAction("Undo", self)
        self._undo_action.setShortcut("Ctrl+Z")
        self._undo_action.triggered.connect(self.undo)

        self._redo_action = QAction("Redo", self)
        self._redo_action.setShortcut("Ctrl+Y")
        self._redo_action.triggered.connect(self.redo)

        self._add_row_before_action = QAction("Add Row Before", self)
        self._add_row_before_action.triggered.connect(self.add_row_before)

        self._add_row_after_action = QAction("Add Row After", self)
        self._add_row_after_action.triggered.connect(self.add_row_after)

        self._delete_row_action = QAction("Delete Row", self)
        self._delete_row_action.triggered.connect(self.delete_selected_rows)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self._new_action)
        file_menu.addAction(self._open_action)

        self._recent_menu = QMenu("Recent Files", self)
        file_menu.addMenu(self._recent_menu)

        file_menu.addSeparator()
        file_menu.addAction(self._save_action)
        file_menu.addAction(self._save_as_action)
        file_menu.addAction(self._change_password_action)
        file_menu.addSeparator()
        file_menu.addAction(self._exit_action)

        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction(self._undo_action)
        edit_menu.addAction(self._redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self._add_row_before_action)
        edit_menu.addAction(self._add_row_after_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self._delete_row_action)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        toolbar.addAction(self._new_action)
        toolbar.addAction(self._open_action)
        toolbar.addAction(self._save_action)
        toolbar.addSeparator()
        toolbar.addAction(self._undo_action)
        toolbar.addAction(self._redo_action)
        toolbar.addSeparator()
        toolbar.addAction(self._add_row_before_action)
        toolbar.addAction(self._add_row_after_action)
        toolbar.addAction(self._delete_row_action)

    def _build_central_widget(self) -> None:
        layout = QVBoxLayout()
        layout.addWidget(self._table)

        central = QWidget()
        central.setLayout(layout)

        self.setCentralWidget(central)

    # ------------------------------------------------------------------
    # File actions
    # ------------------------------------------------------------------

    def new_file(self) -> None:
        if not self._confirm_discard_changes():
            return

        self._path = None
        self._password = None
        self._set_table_data({})
        self._set_dirty(False)
        self._reset_undo_history()

    def open_file(self) -> None:
        if not self._confirm_discard_changes():
            return

        result = get_ecfg_path_and_password(
            self,
            title="Open Encrypted Config",
            message="Select an encrypted .ecfg file and enter its password.",
        )

        if result is None:
            return

        path, password = result
        self._open_path_with_password(path, password)

    def open_recent_file(self, path: Path) -> None:
        if not self._confirm_discard_changes():
            return

        if not path.exists():
            QMessageBox.warning(
                self,
                "Recent File Not Found",
                f"The recent file no longer exists:\n\n{path}",
            )
            self._remove_recent_file(path)
            return

        password = get_password(
            self,
            title="Decrypt Recent .ecfg File",
            message=f"Enter password for:\n{path}",
        )

        if password is None:
            return

        self._open_path_with_password(path, password)

    def _open_path_with_password(self, path: Path, password: str) -> None:
        try:
            data = load_ecfg(path, password)
        except EcfgDecryptError as exc:
            QMessageBox.critical(
                self,
                "Decrypt Failed",
                str(exc),
            )
            return
        except EcfgError as exc:
            QMessageBox.critical(
                self,
                "Open Failed",
                str(exc),
            )
            return
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Open Failed",
                f"Could not open file:\n{path}\n\n{exc}",
            )
            return

        self._path = Path(path)
        self._password = password
        self._set_table_data(data)
        self._set_dirty(False)
        self._reset_undo_history()
        self._add_recent_file(self._path)

    def save_file(self) -> None:
        if self._path is None:
            self.save_file_as()
            return

        if self._password is None:
            password = get_new_password(
                self,
                title="Set .ecfg Password",
                message=(
                    "Enter and confirm the password that will be used "
                    "to encrypt this .ecfg file."
                ),
            )

            if password is None:
                return

            self._password = password

        self._save_to_path(self._path, self._password)

    def save_file_as(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Encrypted Config As",
            str(self._path or Path.cwd() / "config.ecfg"),
            "Encrypted Config Files (*.ecfg);;All Files (*)",
        )

        if not path:
            return

        save_path = Path(path)

        if save_path.suffix.lower() != ".ecfg":
            save_path = save_path.with_suffix(".ecfg")

        password = self._password

        if password is None:
            password = get_new_password(
                self,
                title="Set .ecfg Password",
                message=(
                    "Enter and confirm the password that will be used "
                    "to encrypt this .ecfg file."
                ),
            )

            if password is None:
                return

        if self._save_to_path(save_path, password):
            self._path = save_path
            self._password = password
            self._set_dirty(False)

    def change_password(self) -> None:
        password = get_new_password(
            self,
            title="Change .ecfg Password",
            message=(
                "Enter and confirm the new password for this .ecfg file.\n\n"
                "The file will use the new password the next time it is saved."
            ),
        )

        if password is None:
            return

        self._password = password
        self._set_dirty(True)

        QMessageBox.information(
            self,
            "Password Changed",
            "The password has been changed in memory.\n\n"
            "Save the file to write the change to disk.",
        )

    def _save_to_path(self, path: Path, password: str) -> bool:
        try:
            data = self._table_data()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Invalid Data",
                str(exc),
            )
            return False

        try:
            save_ecfg(path, data, password)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Could not save file:\n{path}\n\n{exc}",
            )
            return False
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Unexpected error while saving:\n{exc}",
            )
            return False

        self.statusBar().showMessage(f"Saved {path}", 4000)
        self._set_dirty(False)
        self._add_recent_file(path)
        return True

    # ------------------------------------------------------------------
    # Table actions
    # ------------------------------------------------------------------

    def _current_or_last_row(self) -> int:
        current_row = self._table.currentRow()

        if current_row >= 0:
            return current_row

        row_count = self._table.rowCount()

        if row_count == 0:
            return 0

        return row_count - 1

    def _insert_empty_row(self, row: int) -> None:
        row = max(0, min(row, self._table.rowCount()))

        self._loading_table = True
        try:
            self._table.insertRow(row)

            key_item = QTableWidgetItem("")
            value_item = QTableWidgetItem("")

            self._table.setItem(row, 0, key_item)
            self._table.setItem(row, 1, value_item)
        finally:
            self._loading_table = False

        self._table.setCurrentItem(self._table.item(row, 0))
        self._table.editItem(self._table.item(row, 0))

        self._record_table_change()

    def add_row_before(self) -> None:
        if self._table.rowCount() == 0:
            self._insert_empty_row(0)
            return

        row = self._current_or_last_row()
        self._insert_empty_row(row)

    def add_row_after(self) -> None:
        if self._table.rowCount() == 0:
            self._insert_empty_row(0)
            return

        row = self._current_or_last_row()
        self._insert_empty_row(row + 1)

    def delete_selected_rows(self) -> None:
        selected_rows = sorted(
            {index.row() for index in self._table.selectedIndexes()},
            reverse=True,
        )

        if not selected_rows:
            return

        self._loading_table = True
        try:
            for row in selected_rows:
                self._table.removeRow(row)
        finally:
            self._loading_table = False

        self._record_table_change()

    # ------------------------------------------------------------------
    # Undo / redo
    # ------------------------------------------------------------------

    def undo(self) -> None:
        if len(self._undo_stack) <= 1:
            return

        current = self._snapshot_table()
        self._redo_stack.append(current)

        self._undo_stack.pop()
        previous = self._undo_stack[-1]

        self._apply_snapshot(previous)
        self._set_dirty(True)
        self._update_undo_redo_enabled()

    def redo(self) -> None:
        if not self._redo_stack:
            return

        snapshot = self._redo_stack.pop()
        self._undo_stack.append(snapshot)

        self._apply_snapshot(snapshot)
        self._set_dirty(True)
        self._update_undo_redo_enabled()

    def _record_table_change(self) -> None:
        if self._loading_table:
            return

        snapshot = self._snapshot_table()

        if not self._undo_stack or self._undo_stack[-1] != snapshot:
            self._undo_stack.append(snapshot)
            self._redo_stack.clear()

        self._set_dirty(True)
        self._update_undo_redo_enabled()

    def _reset_undo_history(self) -> None:
        self._undo_stack = [self._snapshot_table()]
        self._redo_stack = []
        self._update_undo_redo_enabled()

    def _update_undo_redo_enabled(self) -> None:
        self._undo_action.setEnabled(len(self._undo_stack) > 1)
        self._redo_action.setEnabled(bool(self._redo_stack))

    # ------------------------------------------------------------------
    # Recent files
    # ------------------------------------------------------------------

    def _load_recent_files(self) -> list[Path]:
        raw = self._settings.value("recent_files", "[]")

        if not isinstance(raw, str):
            return []

        try:
            values = json.loads(raw)
        except json.JSONDecodeError:
            return []

        recent_files: list[Path] = []

        if isinstance(values, list):
            for value in values:
                if isinstance(value, str):
                    recent_files.append(Path(value))

        return recent_files[:MAX_RECENT_FILES]

    def _save_recent_files(self) -> None:
        values = [str(path) for path in self._recent_files]
        self._settings.setValue("recent_files", json.dumps(values))

    def _add_recent_file(self, path: Path) -> None:
        path = Path(path)

        self._recent_files = [
            recent_path
            for recent_path in self._recent_files
            if recent_path != path
        ]

        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:MAX_RECENT_FILES]

        self._save_recent_files()
        self._update_recent_files_menu()

    def _remove_recent_file(self, path: Path) -> None:
        path = Path(path)

        self._recent_files = [
            recent_path
            for recent_path in self._recent_files
            if recent_path != path
        ]

        self._save_recent_files()
        self._update_recent_files_menu()

    def _clear_recent_files(self) -> None:
        self._recent_files = []
        self._save_recent_files()
        self._update_recent_files_menu()

    def _update_recent_files_menu(self) -> None:
        self._recent_menu.clear()

        if not self._recent_files:
            empty_action = QAction("(No recent files)", self)
            empty_action.setEnabled(False)
            self._recent_menu.addAction(empty_action)
            return

        for path in self._recent_files:
            action = QAction(str(path), self)
            action.triggered.connect(
                lambda _checked=False, p=path: self.open_recent_file(p)
            )
            self._recent_menu.addAction(action)

        self._recent_menu.addSeparator()

        clear_action = QAction("Clear Recent Files", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self._recent_menu.addAction(clear_action)

    # ------------------------------------------------------------------
    # Data conversion
    # ------------------------------------------------------------------

    def _set_table_data(self, data: dict[str, Any]) -> None:
        snapshot: TableSnapshot = [
            (str(key), self._value_to_text(value))
            for key, value in data.items()
        ]

        self._apply_snapshot(snapshot)

    def _snapshot_table(self) -> TableSnapshot:
        snapshot: TableSnapshot = []

        for row in range(self._table.rowCount()):
            key_item = self._table.item(row, 0)
            value_item = self._table.item(row, 1)

            key = key_item.text() if key_item is not None else ""
            value = value_item.text() if value_item is not None else ""

            snapshot.append((key, value))

        return snapshot

    def _apply_snapshot(self, snapshot: TableSnapshot) -> None:
        self._loading_table = True

        try:
            self._table.setRowCount(0)

            for key, value in snapshot:
                row = self._table.rowCount()
                self._table.insertRow(row)

                key_item = QTableWidgetItem(key)
                value_item = QTableWidgetItem(value)

                self._table.setItem(row, 0, key_item)
                self._table.setItem(row, 1, value_item)
        finally:
            self._loading_table = False

    def _table_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        seen_keys: set[str] = set()

        for row in range(self._table.rowCount()):
            key_item = self._table.item(row, 0)
            value_item = self._table.item(row, 1)

            key = key_item.text().strip() if key_item is not None else ""
            value_text = value_item.text() if value_item is not None else ""

            if not key:
                raise ValueError(f"Row {row + 1} has an empty key.")

            if key in seen_keys:
                raise ValueError(f"Duplicate key: {key!r}")

            seen_keys.add(key)
            data[key] = self._text_to_value(value_text)

        return data

    @staticmethod
    def _value_to_text(value: Any) -> str:
        if isinstance(value, str):
            return value

        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _text_to_value(text: str) -> Any:
        stripped = text.strip()

        if stripped == "":
            return ""

        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return text

    # ------------------------------------------------------------------
    # Dirty-state handling
    # ------------------------------------------------------------------

    def _on_item_changed(self, _item: QTableWidgetItem) -> None:
        if not self._loading_table:
            self._record_table_change()

    def _set_dirty(self, dirty: bool) -> None:
        self._dirty = dirty
        self._update_window_title()

    def _update_window_title(self) -> None:
        name = str(self._path) if self._path is not None else "Untitled"
        marker = "*" if self._dirty else ""
        self.setWindowTitle(f"{marker}ECFG Editor - {name}")

    def _confirm_discard_changes(self) -> bool:
        if not self._dirty:
            return True

        result = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        return result == QMessageBox.StandardButton.Yes

    # ------------------------------------------------------------------
    # Close handling
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard_changes():
            event.accept()
        else:
            event.ignore()


def run_ecfg_editor() -> int:
    """
    Run the ECFG editor as a standalone Qt application.
    """
    app = QApplication.instance()

    owns_app = app is None

    if app is None:
        app = QApplication(sys.argv)

    window = EcfgEditorWindow()
    window.show()

    if owns_app:
        return app.exec()

    return 0


if __name__ == "__main__":
    raise SystemExit(run_ecfg_editor())
