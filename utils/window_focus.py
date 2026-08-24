"""Helpers for keeping the main window active after launching external tools."""

import ctypes
import os

from PyQt6.QtCore import QTimer


def restore_window_focus(window, delays=(0, 150, 400, 800)):
    """Force focus back to ``window`` after an external tool is launched.

    On Windows, Qt's ``activateWindow`` can be rejected by the foreground
    window security rules when VS Code was activated by its CLI. The native
    activation path below temporarily attaches the two UI threads so Windows
    accepts the focus transfer. The repeated timers are intentional because
    VS Code may activate its window asynchronously after ``Popen`` returns.
    """
    for delay in delays:
        QTimer.singleShot(delay, lambda target=window: _activate_window(target))


def _activate_window(window):
    if window is None or not window.isVisible():
        return

    window.raise_()
    window.activateWindow()

    if os.name != "nt":
        return

    try:
        hwnd = int(window.winId())
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # SetForegroundWindow is normally restricted when another process is
        # currently foreground. Temporarily sharing the input queues bypasses
        # that restriction for this user-initiated action.
        foreground_hwnd = user32.GetForegroundWindow()
        current_thread = kernel32.GetCurrentThreadId()
        foreground_thread = user32.GetWindowThreadProcessId(
            foreground_hwnd, None,
        ) if foreground_hwnd else 0
        attached = bool(
            foreground_thread
            and foreground_thread != current_thread
            and user32.AttachThreadInput(
                foreground_thread, current_thread, True,
            )
        )
        try:
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.BringWindowToTop(hwnd)
            user32.SetActiveWindow(hwnd)
            user32.SetForegroundWindow(hwnd)
            user32.SetFocus(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(
                    foreground_thread, current_thread, False,
                )
    except (AttributeError, OSError, TypeError, ValueError):
        # Focus restoration is best-effort and must never break the original
        # workspace operation.
        return
