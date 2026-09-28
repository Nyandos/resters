"""
sound_generator.py - れすたーず用 音声生成・再生モジュール
外部ライブラリを一切使わず、Python標準ライブラリ（wave, struct, math, winsound）のみで
音量調整可能なWAVをインメモリ（RAM上）で動的に合成し、非同期ループ再生・停止を行います。
一時ファイルを作成しないため、ファイルのロックやアクセス権の問題が一切発生しません。
"""

import io
import math
import struct
import threading
import wave
import winsound


class SoundManager:
    def __init__(self):
        self._is_playing = False
        self._play_thread = None
        self._lock = threading.Lock()

    def _create_sine_wave(self, freq, duration, sample_rate, volume_ratio, decay=True):
        """指定周波数の減衰サイン波サンプル（16bit signed int）リストを生成"""
        num_samples = int(duration * sample_rate)
        samples = []
        max_amplitude = 32767 * volume_ratio

        for i in range(num_samples):
            t = i / sample_rate
            # 指数関数的減衰（ベルやチャイムのやわらかな響き）
            env = math.exp(-3.5 * t / duration) if decay else 1.0
            val = math.sin(2.0 * math.pi * freq * t) * max_amplitude * env
            samples.append(int(max(-32768, min(32767, val))))
        return samples

    def generate_wav_bytes(self, volume_percent=70, tone_type="gentle"):
        """心地よいリマインダー音のWAVバイナリ（bytes）をインメモリで生成"""
        sample_rate = 44100
        vol_ratio = max(0.0, min(1.0, volume_percent / 100.0))

        total_samples = []

        if tone_type == "gentle":
            # やさしいベル和音: E5(659Hz) -> G#5(830Hz) -> B5(987Hz) -> E6(1318Hz)
            notes = [(659.25, 0.28), (830.61, 0.28), (987.77, 0.32), (1318.51, 1.0)]
            for freq, dur in notes:
                total_samples.extend(self._create_sine_wave(freq, dur, sample_rate, vol_ratio))
        elif tone_type == "chime":
            # 涼やかなチャイム: C5(523Hz) -> G5(783Hz) -> E5(659Hz) -> C6(1046Hz)
            notes = [(523.25, 0.3), (783.99, 0.3), (659.25, 0.3), (1046.50, 1.0)]
            for freq, dur in notes:
                total_samples.extend(self._create_sine_wave(freq, dur, sample_rate, vol_ratio))
        else:  # "warm"
            # 落ち着いたマリンバ風: A4(440Hz) -> C#5(554Hz) -> E5(659Hz) -> A5(880Hz)
            notes = [(440.0, 0.25), (554.37, 0.25), (659.25, 0.3), (880.0, 0.9)]
            for freq, dur in notes:
                total_samples.extend(self._create_sine_wave(freq, dur, sample_rate, vol_ratio))

        # ループ時に耳障りにならないよう、1.5秒の無音ポーズを末尾に挿入
        pause_samples = int(1.5 * sample_rate)
        total_samples.extend([0] * pause_samples)

        # メモリ上でWAVフォーマットにパック
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)  # モノラル
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            raw_data = bytearray()
            for s in total_samples:
                raw_data.extend(struct.pack('<h', s))
            wf.writeframes(raw_data)

        return buf.getvalue()

    def generate_completion_sound(self, volume_percent=70):
        """休憩完了（20秒経過）時の「おつかれさま」サイン音を生成"""
        sample_rate = 44100
        vol_ratio = max(0.0, min(1.0, volume_percent / 100.0))
        total_samples = []

        # ポロン♪（C5 -> G5）
        notes = [(523.25, 0.2), (783.99, 0.5)]
        for freq, dur in notes:
            total_samples.extend(self._create_sine_wave(freq, dur, sample_rate, vol_ratio))

        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            raw_data = bytearray()
            for s in total_samples:
                raw_data.extend(struct.pack('<h', s))
            wf.writeframes(raw_data)

        return buf.getvalue()

    def play_loop(self, volume_percent=70, tone_type="gentle", max_repeats=None):
        """
        指定の音量・音色で非同期ループ再生を開始。
        max_repeats が指定されている場合（例: 4）、その回数再生後に自動ミュート。
        None の場合はストップされるまで無限ループ（はやくはやくもーど）。
        """
        with self._lock:
            # 既に再生中なら一旦停止
            self._stop_internal()

            if volume_percent <= 0:
                return

            wav_bytes = self.generate_wav_bytes(volume_percent, tone_type)
            self._is_playing = True

            def loop_worker():
                played_count = 0
                while self._is_playing:
                    try:
                        winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
                        played_count += 1
                        if max_repeats is not None and played_count >= max_repeats:
                            # 指定回数（4回）鳴り終えたら自動ミュート
                            break
                    except Exception:
                        break
                self._is_playing = False

            self._play_thread = threading.Thread(target=loop_worker, daemon=True)
            self._play_thread.start()

    def play_once(self, volume_percent=70, tone_type="gentle"):
        """テストやワンショット通知用に1回だけ非同期再生"""
        with self._lock:
            self._stop_internal()

            if volume_percent <= 0:
                return

            wav_bytes = self.generate_wav_bytes(volume_percent, tone_type)
            self._is_playing = True

            def once_worker():
                try:
                    winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
                except Exception:
                    pass
                finally:
                    self._is_playing = False

            self._play_thread = threading.Thread(target=once_worker, daemon=True)
            self._play_thread.start()

    def play_completion(self, volume_percent=70):
        """休憩完了音を再生"""
        with self._lock:
            self._stop_internal()

            if volume_percent <= 0:
                return

            wav_bytes = self.generate_completion_sound(volume_percent)
            self._is_playing = True

            def comp_worker():
                try:
                    winsound.PlaySound(wav_bytes, winsound.SND_MEMORY)
                except Exception:
                    pass
                finally:
                    self._is_playing = False

            self._play_thread = threading.Thread(target=comp_worker, daemon=True)
            self._play_thread.start()

    def _stop_internal(self):
        """ロック保持中に呼ばれる停止処理"""
        self._is_playing = False
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

    def stop(self):
        """再生を即座に停止"""
        with self._lock:
            self._stop_internal()

    def is_playing(self):
        return self._is_playing
