"""
config_manager.py - れすたーず用 設定管理モジュール
config.cfg の読み込み・保存を行います。
ファイルが存在しない場合はデフォルト値を書き込んだ config.cfg を自動生成します。
"""

import configparser
import os

DEFAULT_CONFIG = {
    "SETTINGS": {
        "mode": "tsukisoi",          # "tsukisoi" (つきそいもーど) or "otodake" (おとだけもーど)
        "volume": "70",              # 音量: 0 ～ 100
        "work_minutes": "20",        # 20-20-20の作業時間（分）
        "rest_seconds": "20",        # 20-20-20の休憩時間（秒）
        "sound_tone": "gentle",      # "gentle", "chime", "warm"
        "window_x": "120",           # ウィンドウ位置X（サブモニター等の位置記憶用）
        "window_y": "120",           # ウィンドウ位置Y
        "auto_resume": "true",       # 20秒休憩終了後に自動で作業タイマーを再開するか
        "hayaku_mode": "false",      # はやくはやくもーど: true=承諾まで無限ループ, false=4回で自動ミュート
    }
}

import sys

class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is None:
            if getattr(sys, 'frozen', False):
                # PyInstaller で exe 化された場合：exe と同じフォルダ
                base_dir = os.path.dirname(sys.executable)
            else:
                # 通常の Python 実行時：スクリプトと同じフォルダ
                base_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_path = os.path.join(base_dir, "config.cfg")
        else:
            self.config_path = config_path
            
        self.config = configparser.ConfigParser()
        self.load()

    def load(self):
        """config.cfg を読み込む。存在しない場合はデフォルトを作成"""
        if not os.path.exists(self.config_path):
            self.reset_defaults()
            return

        try:
            self.config.read(self.config_path, encoding="utf-8")
            if "SETTINGS" not in self.config:
                self.config["SETTINGS"] = DEFAULT_CONFIG["SETTINGS"]
                self.save()
        except Exception as e:
            print(f"Error loading config.cfg, using defaults: {e}")
            self.reset_defaults()

    def save(self):
        """現在の設定を config.cfg に保存"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                self.config.write(f)
        except Exception as e:
            print(f"Error saving config.cfg: {e}")

    def reset_defaults(self):
        """デフォルト設定で config.cfg を初期化・保存"""
        self.config.read_dict(DEFAULT_CONFIG)
        self.save()

    # --- ゲッター & セッター ---

    @property
    def mode(self):
        return self.config.get("SETTINGS", "mode", fallback="tsukisoi")

    @mode.setter
    def mode(self, val):
        self.config.set("SETTINGS", "mode", str(val))
        self.save()

    @property
    def volume(self):
        return self.config.getint("SETTINGS", "volume", fallback=70)

    @volume.setter
    def volume(self, val):
        val = max(0, min(100, int(val)))
        self.config.set("SETTINGS", "volume", str(val))
        self.save()

    @property
    def work_minutes(self):
        return self.config.getint("SETTINGS", "work_minutes", fallback=20)

    @work_minutes.setter
    def work_minutes(self, val):
        self.config.set("SETTINGS", "work_minutes", str(max(1, int(val))))
        self.save()

    @property
    def rest_seconds(self):
        return self.config.getint("SETTINGS", "rest_seconds", fallback=20)

    @rest_seconds.setter
    def rest_seconds(self, val):
        self.config.set("SETTINGS", "rest_seconds", str(max(5, int(val))))
        self.save()

    @property
    def sound_tone(self):
        return self.config.get("SETTINGS", "sound_tone", fallback="gentle")

    @sound_tone.setter
    def sound_tone(self, val):
        self.config.set("SETTINGS", "sound_tone", str(val))
        self.save()

    @property
    def window_pos(self):
        x = self.config.getint("SETTINGS", "window_x", fallback=120)
        y = self.config.getint("SETTINGS", "window_y", fallback=120)
        return x, y

    def set_window_pos(self, x, y):
        self.config.set("SETTINGS", "window_x", str(int(x)))
        self.config.set("SETTINGS", "window_y", str(int(y)))
        self.save()

    @property
    def auto_resume(self):
        return self.config.getboolean("SETTINGS", "auto_resume", fallback=True)

    @auto_resume.setter
    def auto_resume(self, val):
        self.config.set("SETTINGS", "auto_resume", "true" if val else "false")
        self.save()

    @property
    def hayaku_mode(self):
        return self.config.getboolean("SETTINGS", "hayaku_mode", fallback=False)

    @hayaku_mode.setter
    def hayaku_mode(self, val):
        self.config.set("SETTINGS", "hayaku_mode", "true" if val else "false")
        self.save()
