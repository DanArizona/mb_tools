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

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QPushButton,
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
)

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

        self._update_window_title()

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

        self._exit_action = QAction("Exit", self)
        self._exit_action.triggered.connect(self.close)

        self._add_row_action = QAction("Add Row", self)
        self._add_row_action.triggered.connect(self.add_row)

        self._delete_row_action = QAction("Delete Row", self)
        self._delete_row_action.triggered.connect(self.delete_selected_rows)

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction(self._new_action)
        file_menu.addAction(self._open_action)
        file_menu.addSeparator()
        file_menu.addAction(self._save_action)
        file_menu.addAction(self._save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self._exit_action)

        edit_menu = self.menuBar().addMenu("Edit")
        edit_menu.addAction(self._add_row_action)
        edit_menu.addAction(self._delete_row_action)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        toolbar.addAction(self._new_action)
        toolbar.addAction(self._open_action)
        toolbar.addAction(self._save_action)
        toolbar.addSeparator()
        toolbar.addAction(self._add_row_action)
        toolbar.addAction(self._delete_row_action)

    def _build_central_widget(self) -> None:
        add_button = QPushButton("Add Row")
        add_button.clicked.connect(self.add_row)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_selected_rows)

        button_row = QHBoxLayout()
        button_row.addWidget(add_button)
        button_row.addWidget(delete_button)
        button_row.addStretch(1)

        layout = QVBoxLayout()
        layout.addWidget(self._table)
        layout.addLayout(button_row)

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

        self._path = path
        self._password = password
        self._set_table_data(data)
        self._set_dirty(False)

    def save_file(self) -> None:
        if self._path is None:
            self.save_file_as()
            return

        if self._password is None:
            QMessageBox.warning(
                self,
                "No Password",
                "No password is available for this file. Use Save As instead.",
            )
            return

        self._save_to_path(self._path, self._password)

    # def save_file_as(self) -> None:
    #     path, _selected_filter = QFileDialog.getSaveFileName(
    #         self,
    #         "Save Encrypted Config As",
    #         str(self._path or Path.cwd() / "config.ecfg"),
    #         "Encrypted Config Files (*.ecfg);;All Files (*)",
    #     )

    #     if not path:
    #         return

    #     save_path = Path(path)

    #     if save_path.suffix.lower() != ".ecfg":
    #         save_path = save_path.with_suffix(".ecfg")

    #     # For this first version, reuse the current password if present.
    #     # If this is a new file with no password, ask the user by using
    #     # the same file+password dialog pattern later. For now, simple warning.
    #     if self._password is None:
    #         QMessageBox.warning(
    #             self,
    #             "Password Required",
    #             "This first editor version can save existing decrypted files.\n\n"
    #             "Open an existing .ecfg file first, then use Save or Save As.",
    #         )
    #         return

    #     if self._save_to_path(save_path, self._password):
    #         self._path = save_path
    #         self._set_dirty(False)

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
        return True

    # ------------------------------------------------------------------
    # Table actions
    # ------------------------------------------------------------------

    def add_row(self) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        key_item = QTableWidgetItem("")
        value_item = QTableWidgetItem("")

        self._table.setItem(row, 0, key_item)
        self._table.setItem(row, 1, value_item)

        self._table.setCurrentItem(key_item)
        self._table.editItem(key_item)

        self._set_dirty(True)

    def delete_selected_rows(self) -> None:
        selected_rows = sorted(
            {index.row() for index in self._table.selectedIndexes()},
            reverse=True,
        )

        if not selected_rows:
            return

        for row in selected_rows:
            self._table.removeRow(row)

        self._set_dirty(True)

    # ------------------------------------------------------------------
    # Data conversion
    # ------------------------------------------------------------------

    def _set_table_data(self, data: dict[str, Any]) -> None:
        self._loading_table = True

        try:
            self._table.setRowCount(0)

            for key, value in data.items():
                row = self._table.rowCount()
                self._table.insertRow(row)

                key_item = QTableWidgetItem(str(key))
                value_item = QTableWidgetItem(self._value_to_text(value))

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
        """
        Convert table text back to a Python value.

        This keeps ordinary strings as strings, but allows JSON literals
        for numbers, booleans, lists, dicts, and null.

        Examples
        --------
        hello        -> "hello"
        42           -> 42
        true         -> True
        ["a", "b"]   -> ["a", "b"]
        {"x": 1}     -> {"x": 1}
        """
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
            self._set_dirty(True)

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
