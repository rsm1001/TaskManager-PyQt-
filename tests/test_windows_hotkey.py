"""Tests for native global-hotkey message dispatch."""

import ctypes
from ctypes import wintypes

from PyQt6 import sip

from utils.windows_hotkey import ITINERARY_HOTKEY_ID, WM_HOTKEY, WindowsGlobalHotkey


def _message(message_id, hotkey_id):
    message = wintypes.MSG()
    message.message = message_id
    message.wParam = hotkey_id
    return message


def test_windows_global_hotkey_dispatches_matching_wm_hotkey():
    calls = []
    hotkey = WindowsGlobalHotkey(lambda: calls.append("activated"))
    message = _message(WM_HOTKEY, ITINERARY_HOTKEY_ID)

    handled, result = hotkey.nativeEventFilter(
        b"windows_dispatcher_MSG", sip.voidptr(ctypes.addressof(message))
    )

    assert handled is True
    assert result == 0
    assert calls == ["activated"]


def test_windows_global_hotkey_ignores_unrelated_native_messages():
    calls = []
    hotkey = WindowsGlobalHotkey(lambda: calls.append("activated"))
    message = _message(WM_HOTKEY, ITINERARY_HOTKEY_ID + 1)

    handled, result = hotkey.nativeEventFilter(
        b"windows_dispatcher_MSG", sip.voidptr(ctypes.addressof(message))
    )

    assert handled is False
    assert result == 0
    assert calls == []
