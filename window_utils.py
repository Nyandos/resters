"""
window_utils.py - れすたーず用 フルスクリーンエスケープ防止＆ウィンドウ制御ユーティリティ
フルスクリーンゲームプレイ中にゲームが意図せず最小化（エスケープ）されるのを
確実に防ぐための Windows API (user32, dwmapi) ラッパーです。
"""

import ctypes
from ctypes import wintypes
import sys

# Windows API 定数
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000       # クリックされてもフォアグラウンドを奪わない
WS_EX_TOPMOST = 0x00000008

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010             # アクティブ化（フォーカス奪取）せずに位置・Z順序を変更
SWP_SHOWWINDOW = 0x0040

DWMWA_USE_IMMERSIVE_DARK_MODE = 20  # Windows 10/11 ダークタイトルバー属性

user32 = ctypes.windll.user32 if sys.platform == "win32" else None
dwmapi = ctypes.windll.dwmapi if sys.platform == "win32" else None


def get_real_hwnd(tk_window):
    """Tkinterウィンドウの真のトップレベルHWNDを取得"""
    if not user32:
        return None
    tk_window.update_idletasks()
    hwnd = tk_window.winfo_id()
    parent = user32.GetParent(hwnd)
    return parent if parent else hwnd


def enable_dark_title_bar(tk_window):
    """Windows 10/11 でタイトルバーを洗練されたダークモードに変更"""
    if not dwmapi:
        return
    try:
        hwnd = get_real_hwnd(tk_window)
        if hwnd:
            value = ctypes.c_int(2)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
    except Exception as e:
        print(f"Failed to set dark title bar: {e}")


def apply_no_activate(tk_window):
    """
    ウィンドウに WS_EX_NOACTIVATE を適用。
    これにより、ユーザーがサブモニターのボタンをクリックした際にも
    ゲームからフォーカスが奪われず、フルスクリーンゲームが最小化（エスケープ）されません。
    """
    if not user32:
        return False
    try:
        hwnd = get_real_hwnd(tk_window)
        if not hwnd:
            return False
        
        current_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        new_style = current_style | WS_EX_NOACTIVATE
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        return True
    except Exception as e:
        print(f"Failed to apply WS_EX_NOACTIVATE: {e}")
        return False


def make_topmost_without_activating(tk_window):
    """フォーカスを一切奪わずに、最前面（HWND_TOPMOST）へ配置"""
    if not user32:
        return
    try:
        hwnd = get_real_hwnd(tk_window)
        if hwnd:
            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
    except Exception as e:
        print(f"Failed to SetWindowPos TOPMOST: {e}")


def remove_topmost(tk_window):
    """最前面表示を解除（おとだけモード時など）"""
    if not user32:
        return
    try:
        hwnd = get_real_hwnd(tk_window)
        if hwnd:
            user32.SetWindowPos(
                hwnd,
                HWND_NOTOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
    except Exception as e:
        print(f"Failed to remove TOPMOST: {e}")
