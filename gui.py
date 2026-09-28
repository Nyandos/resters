"""
gui.py - れすたーず メインGUI＆タイマー制御
フルスクリーンゲームのエスケープ（意図しない最小化）を確実に防ぎながら、
20-20-20休憩を可愛くリマインドするTkinterアプリケーション。
"""

import math
import time
import tkinter as tk
from tkinter import ttk
from config_manager import ConfigManager
from sound_generator import SoundManager
from window_utils import (
    apply_no_activate,
    enable_dark_title_bar,
    make_topmost_without_activating,
    remove_topmost,
)

# --- テーマカラー定数（目に優しいナイト・パステル） ---
COLOR_BG = "#161622"            # メイン背景
COLOR_CARD = "#212130"          # カード背景
COLOR_TEXT_MAIN = "#f3f4f6"     # メインテキスト
COLOR_TEXT_SUB = "#9ca3af"      # サブテキスト
COLOR_ACCENT = "#5eead4"        # 通常時アクセント（ミントシアン）
COLOR_ALERT = "#f59e0b"         # 警告時アクセント（アンバーオレンジ）
COLOR_REST = "#60a5fa"          # 休憩中アクセント（ソフトブルー）
COLOR_BTN_BG = "#2e2e42"        # 通常ボタン背景
COLOR_BTN_HOVER = "#3c3c54"     # ホバー背景
COLOR_SWITCH_BG = "#f59e0b"     # よくみてすいっちボタン色
COLOR_SWITCH_ACTIVE = "#d97706"


class RestarsApp:
    def __init__(self, root):
        self.root = root
        self.config_mgr = ConfigManager()
        self.sound_mgr = SoundManager()

        # タイマー状態
        # "WORKING": 作業中（20分カウント）
        # "WAITING_CONFIRM": 20分経過、よくみてすいっち押下待ち（音ループ中）
        # "RESTING": 承諾後、20秒休憩中
        self.state = "WORKING"
        self.remaining_seconds = self.config_mgr.work_minutes * 60
        self.total_target_seconds = self.remaining_seconds
        self.timer_running = True
        self.show_settings = False

        # ウィンドウ初期設定
        self.root.title("れすたーず ( ˘ω˘ ) - 20-20-20")
        self.root.configure(bg=COLOR_BG)
        self.root.resizable(False, False)

        # ウィンドウサイズと前回の保存座標の復元
        w, h = 360, 240
        x, y = self.config_mgr.window_pos
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        # Windows 10/11 のダークタイトルバーを適用
        enable_dark_title_bar(self.root)

        # 終了イベントのハンドリング
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # UIの構築
        self._setup_ui()

        # モードに応じたウィンドウ設定（つきそい / おとだけ）
        self.apply_mode_window_settings()

        # 毎秒タイマーループ開始
        self.root.after(1000, self._timer_tick)

    def _setup_ui(self):
        # メインコンテナ
        self.container = tk.Frame(self.root, bg=COLOR_BG)
        self.container.pack(fill="both", expand=True, padx=8, pady=8)

        # 1. --- 通常 / 休憩中 パネル (timer_view) ---
        self.timer_view = tk.Frame(self.container, bg=COLOR_CARD, bd=1, relief="solid")
        self.timer_view.configure(highlightbackground="#333348", highlightthickness=1)
        self.timer_view.pack(fill="both", expand=True)

        # 上部情報バー（モード表示 ＆ 設定ボタン）
        top_bar = tk.Frame(self.timer_view, bg=COLOR_CARD)
        top_bar.pack(fill="x", padx=10, pady=(6, 0))

        self.status_badge = tk.Label(
            top_bar,
            text="つきそいもーど稼働中",
            bg=COLOR_CARD,
            fg=COLOR_ACCENT,
            font=("Meiryo", 8, "bold")
        )
        self.status_badge.pack(side="left")

        self.setting_btn = tk.Button(
            top_bar,
            text="⚙ 設定",
            bg=COLOR_BTN_BG,
            fg=COLOR_TEXT_SUB,
            activebackground=COLOR_BTN_HOVER,
            activeforeground=COLOR_TEXT_MAIN,
            bd=0,
            font=("Meiryo", 8),
            cursor="hand2",
            command=self.toggle_settings
        )
        self.setting_btn.pack(side="right")

        # 残り時間カウントダウン
        self.time_label = tk.Label(
            self.timer_view,
            text="20:00",
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            font=("Segoe UI", 28, "bold")
        )
        self.time_label.pack(pady=(0, 0))

        # 進捗プログレスキャンバス
        self.progress_canvas = tk.Canvas(self.timer_view, width=310, height=7, bg="#15151f", bd=0, highlightthickness=0)
        self.progress_canvas.pack(pady=3)
        self.progress_bar = self.progress_canvas.create_rectangle(0, 0, 0, 7, fill=COLOR_ACCENT, width=0)

        # メッセージ案内ラベル
        self.msg_label = tk.Label(
            self.timer_view,
            text="おめめをいたわりながらゲームを楽しもう！",
            bg=COLOR_CARD,
            fg=COLOR_TEXT_SUB,
            font=("Meiryo", 8)
        )
        self.msg_label.pack(pady=(2, 6))

        # 下部ボタングループ
        btn_box = tk.Frame(self.timer_view, bg=COLOR_CARD)
        btn_box.pack(fill="x", padx=12, pady=(0, 8))

        self.pause_btn = tk.Button(
            btn_box,
            text="一時停止",
            bg=COLOR_BTN_BG,
            fg=COLOR_TEXT_MAIN,
            activebackground=COLOR_BTN_HOVER,
            bd=0,
            font=("Meiryo", 8),
            cursor="hand2",
            command=self.toggle_pause
        )
        self.pause_btn.pack(side="left", padx=2, expand=True, fill="x")

        self.test_alert_btn = tk.Button(
            btn_box,
            text="休憩テスト(10s)",
            bg=COLOR_BTN_BG,
            fg=COLOR_TEXT_SUB,
            activebackground=COLOR_BTN_HOVER,
            bd=0,
            font=("Meiryo", 8),
            cursor="hand2",
            command=self.trigger_test_alert
        )
        self.test_alert_btn.pack(side="left", padx=2, expand=True, fill="x")

        # 2. --- ★「よくみてすいっち」アラートパネル (alert_view) ★ ---
        self.alert_view = tk.Frame(self.container, bg=COLOR_CARD, bd=1, relief="solid")
        self.alert_view.configure(highlightbackground=COLOR_ALERT, highlightthickness=2)

        self.alert_badge = tk.Label(
            self.alert_view,
            text="✦ 20-20-20 おめめおやすみタイム！ ✦",
            bg=COLOR_CARD,
            fg=COLOR_ALERT,
            font=("Meiryo", 9, "bold")
        )
        self.alert_badge.pack(pady=(8, 2))

        self.alert_desc = tk.Label(
            self.alert_view,
            text="20分経ちました！\n20秒間、約6メートル（遠く）を\nぼーっと眺めて目を休めよう！",
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            font=("Meiryo", 8),
            justify="center"
        )
        self.alert_desc.pack(pady=(0, 6))

        # ★ よくみてすいっち（承諾ボタン） ★
        self.switch_btn = tk.Button(
            self.alert_view,
            text="◎ よくみてすいっち（音を止めて20秒休む）",
            bg=COLOR_SWITCH_BG,
            fg="#1a1a24",
            activebackground=COLOR_SWITCH_ACTIVE,
            activeforeground="#000000",
            bd=0,
            font=("Meiryo", 9, "bold"),
            cursor="hand2",
            command=self.on_switch_pressed
        )
        self.switch_btn.pack(fill="x", padx=16, pady=(0, 4), ipady=3)

        self.alert_note = tk.Label(
            self.alert_view,
            text="※すいっちを押すまでリマインダー音が鳴り続けます",
            bg=COLOR_CARD,
            fg=COLOR_TEXT_SUB,
            font=("Meiryo", 7)
        )
        self.alert_note.pack(pady=(0, 4))

        # 3. --- 設定パネル (settings_view) ---
        self.settings_view = tk.Frame(self.container, bg=COLOR_CARD, bd=1, relief="solid")
        self.settings_view.configure(highlightbackground="#44445c", highlightthickness=1)
        self._setup_settings_ui()

    def _setup_settings_ui(self):
        """設定パネルのUI構築"""
        title = tk.Label(
            self.settings_view,
            text="⚙ せってい (config.cfg)",
            bg=COLOR_CARD,
            fg=COLOR_TEXT_MAIN,
            font=("Meiryo", 9, "bold")
        )
        title.pack(pady=(6, 4))

        # モード選択
        mode_box = tk.Frame(self.settings_view, bg=COLOR_CARD)
        mode_box.pack(fill="x", padx=10, pady=2)
        tk.Label(mode_box, text="モード:", bg=COLOR_CARD, fg=COLOR_TEXT_SUB, font=("Meiryo", 8)).pack(side="left")

        self.mode_var = tk.StringVar(value=self.config_mgr.mode)
        rb1 = tk.Radiobutton(
            mode_box, text="つきそい(サブ画面最前面)", variable=self.mode_var, value="tsukisoi",
            bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, selectcolor=COLOR_BG, activebackground=COLOR_CARD,
            font=("Meiryo", 7), command=self._on_mode_changed
        )
        rb1.pack(side="left", padx=2)

        rb2 = tk.Radiobutton(
            mode_box, text="おとだけ(裏画面)", variable=self.mode_var, value="otodake",
            bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, selectcolor=COLOR_BG, activebackground=COLOR_CARD,
            font=("Meiryo", 7), command=self._on_mode_changed
        )
        rb2.pack(side="left", padx=2)

        # 音量スライダー
        vol_box = tk.Frame(self.settings_view, bg=COLOR_CARD)
        vol_box.pack(fill="x", padx=10, pady=2)
        tk.Label(vol_box, text="音量:", bg=COLOR_CARD, fg=COLOR_TEXT_SUB, font=("Meiryo", 8)).pack(side="left")

        self.vol_scale = tk.Scale(
            vol_box, from_=0, to=100, orient="horizontal",
            bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, highlightthickness=0,
            bd=0, activebackground=COLOR_ACCENT, font=("Segoe UI", 7),
            command=self._on_volume_changed
        )
        self.vol_scale.set(self.config_mgr.volume)
        self.vol_scale.pack(side="left", fill="x", expand=True, padx=4)

        self.test_sound_btn = tk.Button(
            vol_box, text="試聴", bg=COLOR_BTN_BG, fg=COLOR_TEXT_MAIN,
            bd=0, font=("Meiryo", 7), cursor="hand2", command=self._preview_sound
        )
        self.test_sound_btn.pack(side="right", padx=2)

        # 音色選択
        tone_box = tk.Frame(self.settings_view, bg=COLOR_CARD)
        tone_box.pack(fill="x", padx=10, pady=2)
        tk.Label(tone_box, text="音色:", bg=COLOR_CARD, fg=COLOR_TEXT_SUB, font=("Meiryo", 8)).pack(side="left")

        self.tone_var = tk.StringVar(value=self.config_mgr.sound_tone)
        for tone_id, tone_name in [("gentle", "ベル"), ("chime", "チャイム"), ("warm", "マリンバ")]:
            rb = tk.Radiobutton(
                tone_box, text=tone_name, variable=self.tone_var, value=tone_id,
                bg=COLOR_CARD, fg=COLOR_TEXT_MAIN, selectcolor=COLOR_BG, activebackground=COLOR_CARD,
                font=("Meiryo", 8), command=self._on_tone_changed
            )
            rb.pack(side="left", padx=4)

        # 設定パネルを閉じるボタン
        close_set_btn = tk.Button(
            self.settings_view, text="完了して戻る", bg=COLOR_BTN_BG, fg=COLOR_TEXT_MAIN,
            activebackground=COLOR_BTN_HOVER, bd=0, font=("Meiryo", 8), cursor="hand2", command=self.toggle_settings
        )
        close_set_btn.pack(pady=4)

    # --- モード切替 & フルスクリーンエスケープ防止制御 ---

    def apply_mode_window_settings(self):
        """
        現在のモード（つきそい / おとだけ）に応じてウィンドウ特性を切り替える
        ★ フォーカス奪取防止: WS_EX_NOACTIVATE を適用し、ゲームウィンドウが最小化されるのを防ぐ ★
        """
        mode = self.config_mgr.mode
        if mode == "tsukisoi":
            # サブモニター用「つきそいもーど」:
            # 最前面にしつつ、WS_EX_NOACTIVATE を適用してゲームからフォーカスを奪わない
            make_topmost_without_activating(self.root)
            apply_no_activate(self.root)
            self.status_badge.configure(text="つきそいもーど (サブ画面最前面)", fg=COLOR_ACCENT)
        else:
            # シングルモニター用「おとだけもーど」:
            # 最前面表示を解除し、ゲームの背後に置かれる
            remove_topmost(self.root)
            self.status_badge.configure(text="おとだけもーど (裏画面常駐)", fg="#a78bfa")

    def _on_mode_changed(self):
        new_mode = self.mode_var.get()
        self.config_mgr.mode = new_mode
        self.apply_mode_window_settings()

    def _on_volume_changed(self, val):
        self.config_mgr.volume = int(val)

    def _on_tone_changed(self):
        self.config_mgr.sound_tone = self.tone_var.get()

    def _preview_sound(self):
        """現在の音量・音色でテスト再生"""
        self.sound_mgr.play_once(self.config_mgr.volume, self.config_mgr.sound_tone)

    # --- タイマーロジック ---

    def _timer_tick(self):
        """1秒ごとのタイマー更新処理"""
        if self.timer_running and self.state in ("WORKING", "RESTING"):
            self.remaining_seconds -= 1

            if self.remaining_seconds <= 0:
                if self.state == "WORKING":
                    # 20分作業終了 -> よくみてすいっち待ち状態へ移行！
                    self._trigger_switch_alert()
                elif self.state == "RESTING":
                    # 20秒休憩終了 -> 作業状態へ復帰！
                    self._complete_rest()
            else:
                self._update_display()

        # 次の1秒後
        self.root.after(1000, self._timer_tick)

    def _update_display(self):
        """残り時間やプログレスバーの更新"""
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        self.time_label.configure(text=f"{mins:02d}:{secs:02d}")

        # プログレスバーの計算
        if self.total_target_seconds > 0:
            progress = 1.0 - (self.remaining_seconds / self.total_target_seconds)
            bar_w = int(310 * max(0.0, min(1.0, progress)))
            self.progress_canvas.coords(self.progress_bar, 0, 0, bar_w, 7)

    def _trigger_switch_alert(self):
        """
        作業時間（20分）終了時：
        ★ フルスクリーンゲームのエスケープ（最小化）を絶対に起こさない ★
        フォーカスを奪う新規ウィンドウや deiconify/lift は一切行わず、
        既存ウィンドウ内のパネルを切り替え、音をループ再生する。
        """
        self.state = "WAITING_CONFIRM"
        self.sound_mgr.play_loop(self.config_mgr.volume, self.config_mgr.sound_tone)

        # パネルの切り替え
        self.timer_view.pack_forget()
        if self.settings_view.winfo_ismapped():
            self.settings_view.pack_forget()
            self.show_settings = False
        self.alert_view.pack(fill="both", expand=True)

        self.root.title("れすたーず ( ◉ ω ◉ ) - よくみてすいっち！")

    def on_switch_pressed(self):
        """
        「よくみてすいっち」が押されたときの処理：
        1. 即座にリマインダー音を停止！
        2. 20-20-20ルールに基づき、20秒の遠くを見つめる休憩カウントを開始！
        """
        self.sound_mgr.stop()

        self.state = "RESTING"
        self.remaining_seconds = self.config_mgr.rest_seconds
        self.total_target_seconds = self.remaining_seconds

        # アラートビューを隠し、タイマービューを休憩モードとして表示
        self.alert_view.pack_forget()
        self.timer_view.pack(fill="both", expand=True)

        self.root.title("れすたーず ( ˘ω˘ ) - 20秒遠くを見てね…")
        self.status_badge.configure(text="✦ 20秒遠くを見つめる休憩タイム ✦", fg=COLOR_REST)
        self.msg_label.configure(text="約6メートル（20フィート）先をぼーっと眺めてね", fg=COLOR_TEXT_MAIN)
        self.time_label.configure(fg=COLOR_REST)
        self.progress_canvas.itemconfig(self.progress_bar, fill=COLOR_REST)
        self.pause_btn.configure(state="disabled")
        self.test_alert_btn.configure(state="disabled")

        self._update_display()

    def _complete_rest(self):
        """20秒の休憩が完了したときの処理"""
        # 完了音（ポロン♪）を1回再生
        self.sound_mgr.play_completion(self.config_mgr.volume)

        # 作業モードへ復帰
        self.state = "WORKING"
        self.remaining_seconds = self.config_mgr.work_minutes * 60
        self.total_target_seconds = self.remaining_seconds

        self.root.title("れすたーず ( ˘ω˘ ) - 20-20-20")
        self.apply_mode_window_settings()
        self.msg_label.configure(text="おめめリフレッシュ完了！おつかれさま！", fg=COLOR_ACCENT)
        self.time_label.configure(fg=COLOR_TEXT_MAIN)
        self.progress_canvas.itemconfig(self.progress_bar, fill=COLOR_ACCENT)
        self.pause_btn.configure(state="normal", text="一時停止")
        self.test_alert_btn.configure(state="normal")

        self._update_display()

    def trigger_test_alert(self):
        """テスト用：10秒後にリマインドを発火させる"""
        self.remaining_seconds = 10
        self.total_target_seconds = 10
        self.state = "WORKING"
        self.timer_running = True
        self.pause_btn.configure(text="一時停止")
        self.msg_label.configure(text="テスト中: 10秒後にすいっちが出ます！", fg=COLOR_ALERT)
        self._update_display()

    def toggle_pause(self):
        """タイマーの一時停止・再開"""
        if self.state in ("WORKING", "RESTING"):
            self.timer_running = not self.timer_running
            if self.timer_running:
                self.pause_btn.configure(text="一時停止", bg=COLOR_BTN_BG)
                self.msg_label.configure(text="タイマー再開しました")
            else:
                self.pause_btn.configure(text="再開", bg=COLOR_ACCENT, fg="#000000")
                self.msg_label.configure(text="一時停止中")

    def toggle_settings(self):
        """設定パネルの開閉"""
        self.show_settings = not self.show_settings
        if self.show_settings:
            self.timer_view.pack_forget()
            if self.alert_view.winfo_ismapped():
                self.alert_view.pack_forget()
            self.settings_view.pack(fill="both", expand=True)
            self.setting_btn.configure(text="✕ 戻る", fg=COLOR_ACCENT)
        else:
            self.settings_view.pack_forget()
            self.setting_btn.configure(text="⚙ 設定", fg=COLOR_TEXT_SUB)
            if self.state == "WAITING_CONFIRM":
                self.alert_view.pack(fill="both", expand=True)
            else:
                self.timer_view.pack(fill="both", expand=True)

    def on_close(self):
        """終了処理（ウィンドウ座標の保存、音声の停止）"""
        self.sound_mgr.stop()
        # 現在のウィンドウ位置（サブモニター上など）を config.cfg に保存
        try:
            cur_x = self.root.winfo_x()
            cur_y = self.root.winfo_y()
            self.config_mgr.set_window_pos(cur_x, cur_y)
        except Exception:
            pass
        self.root.destroy()
