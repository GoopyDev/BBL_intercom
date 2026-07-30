import ctypes
import os
from typing import Optional


SINGLE_INSTANCE_MUTEX_NAME = r"Global\BBL_Chat_SingleInstance"
SINGLE_INSTANCE_WINDOW_PROP = "BBL_Chat_SingleInstanceWindow"


class SingleInstanceController:
    """Gestiona un mutex de Windows para garantizar una sola instancia de la app."""

    def __init__(self, mutex_name: str = SINGLE_INSTANCE_MUTEX_NAME, window_property: str = SINGLE_INSTANCE_WINDOW_PROP):
        self.mutex_name = mutex_name
        self.window_property = window_property
        self._mutex_handle = None
        self._acquired = False

    def acquire(self) -> bool:
        if os.name != "nt":
            return True

        if self._acquired:
            return True

        self._mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, self.mutex_name)
        if not self._mutex_handle:
            return False

        last_error = ctypes.windll.kernel32.GetLastError()
        if last_error == 183:  # ERROR_ALREADY_EXISTS
            ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
            self._mutex_handle = None
            return False

        self._acquired = True
        return True

    def release(self) -> None:
        if self._mutex_handle and self._acquired:
            try:
                ctypes.windll.kernel32.ReleaseMutex(self._mutex_handle)
            except Exception:
                pass
            try:
                ctypes.windll.kernel32.CloseHandle(self._mutex_handle)
            except Exception:
                pass

        self._mutex_handle = None
        self._acquired = False

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass

    def register_window(self, hwnd: Optional[int]) -> None:
        if os.name != "nt" or not hwnd:
            return

        ctypes.windll.user32.SetPropW(hwnd, self.window_property, 1)

    def unregister_window(self, hwnd: Optional[int]) -> None:
        if os.name != "nt" or not hwnd:
            return

        ctypes.windll.user32.RemovePropW(hwnd, self.window_property)

    def find_existing_window(self) -> Optional[int]:
        if os.name != "nt":
            return None

        found = []

        def enum_callback(hwnd, _lparam):
            if self._window_has_property(hwnd):
                found.append(hwnd)
                return False
            return True

        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
        ctypes.windll.user32.EnumWindows(enum_proc(enum_callback), None)
        return found[0] if found else None

    def activate_existing_window(self) -> Optional[int]:
        hwnd = self.find_existing_window()
        if not hwnd:
            return None

        try:
            if ctypes.windll.user32.IsIconic(hwnd):
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        except Exception:
            pass

        try:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.BringWindowToTop(hwnd)
        except Exception:
            pass

        return hwnd

    def _window_has_property(self, hwnd: int) -> bool:
        if os.name != "nt":
            return False

        try:
            return bool(ctypes.windll.user32.GetPropW(hwnd, self.window_property))
        except Exception:
            return False
