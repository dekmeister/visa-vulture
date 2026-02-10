"""Startup safety disclaimer dialog."""

import tkinter as tk
from tkinter import ttk

_DISCLAIMER_TEXT = """\
WARNING: This software controls physical test equipment capable of outputting \
voltage, current, and signals. Improper use may result in damage to equipment, \
connected devices, or personal injury.

SAFETY PRECAUTIONS:

  - Verify all connections before energising any equipment.
  - Set appropriate voltage and current limits for your device under test.
  - Never leave energised equipment unattended.
  - Ensure you have appropriate training before operating test equipment.
  - Review your test plan carefully before execution.

NO WARRANTY:

This software is provided "as-is" without warranty of any kind, express or \
implied. The developers accept no responsibility or liability for any damage, \
loss, or injury resulting from the use of this software. You use this software \
entirely at your own risk.

By clicking "I Accept the Risk" you acknowledge that you have read, understood, \
and agree to the above terms.\
"""


class DisclaimerDialog:
    """
    Modal safety disclaimer shown at application startup.

    Users must accept the disclaimer to proceed. Declining or closing
    the dialog causes the application to exit.
    """

    def __init__(self, parent: tk.Tk):
        self._parent = parent
        self._accepted = False
        self._create_dialog()

    def _create_dialog(self) -> None:
        """Create the dialog window and widgets."""
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("VISA Vulture - Safety Disclaimer")
        self._dialog.geometry("520x440")
        self._dialog.resizable(False, False)

        # Make dialog modal. Only set transient if the parent is visible,
        # otherwise the dialog inherits the withdrawn state on some WMs.
        if self._parent.winfo_viewable():
            self._dialog.transient(self._parent)
        self._dialog.grab_set()

        # Closing the window is treated as declining
        self._dialog.protocol("WM_DELETE_WINDOW", self._handle_decline)

        # Configure grid
        self._dialog.columnconfigure(0, weight=1)
        self._dialog.rowconfigure(1, weight=1)

        # Header
        header = ttk.Label(
            self._dialog,
            text="WARNING - Safety Disclaimer",
            font=("TkDefaultFont", 12, "bold"),
            foreground="red",
        )
        header.grid(row=0, column=0, padx=15, pady=(15, 5))

        # Disclaimer text in a read-only Text widget
        text_frame = ttk.Frame(self._dialog)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL)
        self._text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=10,
            state=tk.NORMAL,
        )
        scrollbar.config(command=self._text.yview)

        self._text.insert("1.0", _DISCLAIMER_TEXT)
        self._text.config(state=tk.DISABLED)

        self._text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Buttons
        btn_frame = ttk.Frame(self._dialog)
        btn_frame.grid(row=2, column=0, pady=(10, 15))

        self._accept_btn = ttk.Button(
            btn_frame, text="I Accept the Risk", command=self._handle_accept
        )
        self._accept_btn.pack(side=tk.LEFT, padx=10)

        self._decline_btn = ttk.Button(
            btn_frame, text="Decline", command=self._handle_decline
        )
        self._decline_btn.pack(side=tk.LEFT, padx=10)

        # Center on parent
        self._center_on_parent()

    def _center_on_parent(self) -> None:
        """Center dialog on parent window."""
        self._dialog.update_idletasks()
        parent_x = self._parent.winfo_rootx()
        parent_y = self._parent.winfo_rooty()
        parent_w = self._parent.winfo_width()
        parent_h = self._parent.winfo_height()
        dialog_w = self._dialog.winfo_width()
        dialog_h = self._dialog.winfo_height()

        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2

        self._dialog.geometry(f"+{x}+{y}")

    def _handle_accept(self) -> None:
        """Handle Accept button click."""
        self._accepted = True
        self._dialog.destroy()

    def _handle_decline(self) -> None:
        """Handle Decline button or window close."""
        self._accepted = False
        self._dialog.destroy()

    def show(self) -> bool:
        """
        Show dialog modally and wait for user response.

        Returns:
            True if the user accepted, False if declined or closed.
        """
        self._dialog.wait_window()
        return self._accepted
