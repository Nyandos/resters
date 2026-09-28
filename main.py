"""
main.py - おめめおやすみタイマー「れすたーず」 (Restars)
エントリーポイントスクリプト
"""

import sys
import os
import tkinter as tk

# スクリプトの親ディレクトリを検索パスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui import RestarsApp

def main():
    root = tk.Tk()
    app = RestarsApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
