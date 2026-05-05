"""
Qt password dialog helpers for encrypted .ecfg files.

This module is intentionally separate from ecfg.py so that the core
secure_config module does not require PySide6.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class PasswordDialog(QDialog):
    """
    Simple password-entry dialog.

    Returns QDialog.DialogCode.Accepted when the user clicks OK.
    Returns QDialog.Rejected when the user clicks Cancel or closes the dialog.
    """

    def __init__(
        self,
        parent=None,
        *,
        title: str = "Enter Password",
        message: str = "Enter password:",
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        message_label = QLabel(message)
        message_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Password:", self._password_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(message_label)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(buttons)

        self._password_edit.setFocus()

    def password(self) -> str:
        """Return the password currently entered by the user."""
        return self._password_edit.text()


class EcfgOpenPasswordDialog(QDialog):
    """
    Dialog for selecting an .ecfg file and entering its password.

    Returns QDialog.DialogCode.Accepted when the user clicks OK.
    Returns QDialog.Rejected when the user clicks Cancel or closes the dialog.
    """

    def __init__(
        self,
        parent=None,
        *,
        title: str = "Open Encrypted Config",
        message: str = "Select an .ecfg file and enter its password:",
        initial_dir: str | Path | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(600, 150)

        self._initial_dir = Path(initial_dir) if initial_dir is not None else Path.cwd()

        message_label = QLabel(message)
        message_label.setWordWrap(True)

        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_for_file)

        path_row = QHBoxLayout()
        path_row.addWidget(self._path_edit, stretch=1)
        path_row.addWidget(browse_button)

        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form_layout = QFormLayout()
        form_layout.addRow("File:", path_row)
        form_layout.addRow("Password:", self._password_edit)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(message_label)
        main_layout.addLayout(form_layout)
        main_layout.addWidget(self._buttons)

        self._update_ok_enabled()

        self._path_edit.textChanged.connect(self._update_ok_enabled)
        self._password_edit.textChanged.connect(self._update_ok_enabled)

    def _browse_for_file(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Select .ecfg File",
            str(self._initial_dir),
            "Encrypted Config Files (*.ecfg);;All Files (*)",
        )

        if path:
            self._path_edit.setText(path)
            self._password_edit.setFocus()

    def _update_ok_enabled(self) -> None:
        ok_button = self._buttons.button(QDialogButtonBox.StandardButton.Ok)

        if ok_button is None:
            return

        has_path = bool(self._path_edit.text().strip())
        has_password = bool(self._password_edit.text())

        ok_button.setEnabled(has_path and has_password)

    def path(self) -> Path:
        """Return the selected .ecfg path."""
        return Path(self._path_edit.text())

    def password(self) -> str:
        """Return the password currently entered by the user."""
        return self._password_edit.text()


def get_password(
    parent=None,
    *,
    title: str = "Enter Password",
    message: str = "Enter password:",
) -> str | None:
    """
    Show a password dialog and return the entered password.

    Returns None if the user cancels.
    """
    dialog = PasswordDialog(parent, title=title, message=message)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.password()

    return None


def get_password_standalone(
    *,
    title: str = "Enter Password",
    message: str = "Enter password:",
) -> str | None:
    """
    Convenience function for scripts that do not already have a QApplication.

    If a QApplication already exists, it is reused.
    """
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return get_password(title=title, message=message)


def get_ecfg_path_and_password(
    parent=None,
    *,
    title: str = "Open Encrypted Config",
    message: str = "Select an .ecfg file and enter its password:",
    initial_dir: str | Path | None = None,
) -> tuple[Path, str] | None:
    """
    Show a dialog that asks for both an .ecfg file and a password.

    Returns
    -------
    tuple[Path, str] | None
        Returns ``(path, password)`` if the user accepts.
        Returns ``None`` if the user cancels.
    """
    dialog = EcfgOpenPasswordDialog(
        parent,
        title=title,
        message=message,
        initial_dir=initial_dir,
    )

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.path(), dialog.password()

    return None


def get_ecfg_path_and_password_standalone(
    *,
    title: str = "Open Encrypted Config",
    message: str = "Select an .ecfg file and enter its password:",
    initial_dir: str | Path | None = None,
) -> tuple[Path, str] | None:
    """
    Standalone convenience function for selecting an .ecfg file and password.

    If a QApplication already exists, it is reused.
    """
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return get_ecfg_path_and_password(
        title=title,
        message=message,
        initial_dir=initial_dir,
    )