"""
Qt password dialog helpers for encrypted .ecfg files.

This module is intentionally separate from ecfg.py so that the core
secure_config module does not require PySide6.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class PasswordDialog(QDialog):
    """
    Simple password-entry dialog.

    Returns QDialog.Accepted when the user clicks OK.
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
        self._password_edit.setEchoMode(QLineEdit.Password)

        message_label = QLabel(message)
        message_label.setWordWrap(True)

        form_layout = QFormLayout()
        form_layout.addRow("Password:", self._password_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
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

    if dialog.exec() == QDialog.Accepted:
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
