import pyautogui
import tempfile
import win32gui
from PIL import ImageGrab
import re


class WindowMgr:
    """Encapsulates some calls to the winapi for window management
    https://stackoverflow.com/questions/2090464/python-window-activation
    """

    def __init__ (self):
        """Constructor"""
        self._handle = None

    def find_window(self, class_name, window_name=None):
        """find a window by its class_name"""
        self._handle = win32gui.FindWindow(class_name, window_name)

    def _window_enum_callback(self, hwnd, wildcard):
        """Pass to win32gui.EnumWindows() to check all the opened windows"""
        if re.match(wildcard, str(win32gui.GetWindowText(hwnd))) is not None:
            print(str(win32gui.GetWindowText(hwnd)))
            self._handle = hwnd

    def find_window_wildcard(self, wildcard):
        """find a window whose title matches the wildcard regex"""
        self._handle = None
        win32gui.EnumWindows(self._window_enum_callback, wildcard)
        print(self._handle)

    def set_foreground(self):
        """put the window in the foreground"""
        win32gui.SetForegroundWindow(self._handle)

    def get_handle(self):
        return self._handle

# open the document...

# find the window
w = WindowMgr()
w.find_window_wildcard(".*Word")

# grab the foreground window...
hwnd = w.get_handle()
if hwnd:
    print(hwnd)
    win32gui.MoveWindow(hwnd, 0,0, 500, 700, True)

    bbox = win32gui.GetWindowRect(hwnd)  # bounding rectangle
    print(bbox)

    # capture screen
    shot = ImageGrab.grab(bbox) # take screenshot, active app
    shot.show()

    shot.save('screenshot.png') # save screenshot

