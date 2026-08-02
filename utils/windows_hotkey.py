"""Windows system-wide hotkey integration for the Qt event loop."""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes
from typing import Callable, Optional

from PyQt6.QtCore import QAbstractNativeEventFilter
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_NOREPEAT = 0x4000
VK_Q = 0x51
ITINERARY_HOTKEY_ID = 0x4151  # "AQ" (Alt+Q), unique within this application.


class WindowsGlobalHotkey(QAbstractNativeEventFilter):
    """Receive a Windows global hotkey through Qt's native event dispatcher.

    ``QShortcut`` only observes key events delivered to the Qt application.  In
    contrast, Win32 ``RegisterHotKey`` posts ``WM_HOTKEY`` to this process even
    when its windows are minimized or another application has focus.
    """

    def __init__(
        self,
        callback: Callable[[], None],
        hotkey_id: int = ITINERARY_HOTKEY_ID,
        modifiers: int = MOD_ALT | MOD_NOREPEAT,
        virtual_key: int = VK_Q,
    ) -> None:
        super().__init__()
        self._callback = callback
        self._hotkey_id = hotkey_id
        self._modifiers = modifiers
        self._virtual_key = virtual_key
        self._registered = False
        self._application: Optional[QApplication] = None

    def start(self, application: QApplication) -> bool:
        """Register the hotkey and attach this instance to Qt's event loop."""
        if sys.platform != "win32":
            return False
        if self._registered:
            return True

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.RegisterHotKey.argtypes = (
            wintypes.HWND,
            ctypes.c_int,
            wintypes.UINT,
            wintypes.UINT,
        )
        user32.RegisterHotKey.restype = wintypes.BOOL

        # A null HWND makes Windows post WM_HOTKEY to this GUI thread's message
        # queue, which Qt exposes as a windows_dispatcher_MSG native event.
        if not user32.RegisterHotKey(
            None, self._hotkey_id, self._modifiers, self._virtual_key
        ):
            error_code = ctypes.get_last_error()
            logger.warning(
                "Unable to register global Alt+Q hotkey (Win32 error %s); "
                "using the in-app shortcut fallback.",
                error_code,
            )
            return False

        self._application = application
        application.installNativeEventFilter(self)
        self._registered = True
        logger.info("Registered global Alt+Q hotkey.")
        return True

    def stop(self) -> None:
        """Unregister the hotkey and detach from the Qt event loop."""
        if self._application is not None:
            self._application.removeNativeEventFilter(self)
            self._application = None

        if not self._registered:
            return

        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
            user32.UnregisterHotKey.restype = wintypes.BOOL
            if not user32.UnregisterHotKey(None, self._hotkey_id):
                logger.warning(
                    "Unable to unregister global Alt+Q hotkey (Win32 error %s).",
                    ctypes.get_last_error(),
                )
        finally:
            self._registered = False

    def nativeEventFilter(self, event_type, message):
        """Dispatch this hotkey's WM_HOTKEY message to the supplied callback."""
        if event_type not in (b"windows_dispatcher_MSG", b"windows_generic_MSG"):
            return False, 0

        try:
            native_message = wintypes.MSG.from_address(int(message))
        except (TypeError, ValueError):
            return False, 0

        if (
            native_message.message == WM_HOTKEY
            and native_message.wParam == self._hotkey_id
        ):
            self._callback()
            return True, 0
        return False, 0
