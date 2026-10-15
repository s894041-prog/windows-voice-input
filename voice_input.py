# -*- coding: utf-8 -*-
"""Windows 語音輸入小工具：按住熱鍵說話 → Groq 辨識 → Groq 潤飾 → 自動貼上."""
import argparse
import os
import sys
import tempfile
import time
import wave

from dotenv import load_dotenv
from rec_indicator import RecIndicator

# 載入 .env（API Key 放這裡，不要進版控）
load_dotenv()

# 從環境變數讀取設定（全部只用 Groq 一把 Key）
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
POLISH_MODEL = os.getenv("POLISH_MODEL", "openai/gpt-oss-20b")
HOTKEY = os.getenv("VOICE_HOTKEY", "caps lock")
VOICE_MODE = os.getenv("VOICE_MODE", "tap")  # tap：點一下開始、再點一下停止；hold：按住說話、放開停止
SAMPLE_RATE = int(os.getenv("VOICE_SAMPLE_RATE", "16000"))
MAX_SECONDS = int(os.getenv("VOICE_MAX_SECONDS", "120"))


def _parse_device(value):
    """解析 VOICE_DEVICE（空白＝系統預設，數字＝裝置編號）。"""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        print(f"VOICE_DEVICE 設定無效（{value}），改用系統預設。可跑 --mics 查看編號。")
        return None


DEVICE = _parse_device(os.getenv("VOICE_DEVICE", ""))

# 潤飾用的系統提示詞（要求只輸出潤飾後文字）
POLISH_PROMPT = (
    "你是繁體中文語音輸入助手。把使用者的逐字稿轉成自然、通順的繁體中文書面語："
    "補標點符號、修正語病與同音錯字、數字與單位保持原意、人名地名若不確定就保留原文不亂改。"
    "只輸出潤飾後的正文，不要加任何解釋、前言或引號。"
)


def check_keys():
    """檢查 GROQ_API_KEY 是否存在，缺了就印出提示並回傳 False。"""
    if not GROQ_API_KEY:
        print("缺少設定：GROQ_API_KEY")
        print("請複製 .env.example 為 .env 並填入你的免費 Key。")
        return False
    return True


def record_while_hotkey_held():
    """按住熱鍵期間錄音，放開即停止，回傳 wav 暫存檔路徑。"""
    try:
        import keyboard
        import sounddevice as sd
        import numpy as np
    except ImportError as exc:
        print(f"缺少錄音套件：{exc}，請先 pip install -r requirements.txt")
        return None

    print(f"請按住 [{HOTKEY}] 開始說話，放開即辨識（最長 {MAX_SECONDS} 秒）…")
    # 等待熱鍵被按住
    while not keyboard.is_pressed(HOTKEY):
        time.sleep(0.05)

    print("錄音中…（放開按鍵結束）")
    indicator = RecIndicator()
    indicator.show()
    frames = []
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            device=DEVICE) as stream:
            start = time.time()
            while keyboard.is_pressed(HOTKEY):
                data, _ = stream.read(int(SAMPLE_RATE * 0.1))
                frames.append(data.copy())
                rms = float(np.sqrt(np.mean(data.astype(np.float64) ** 2)))
                indicator.push_level(min(1.0, rms * 5.0))
                indicator.pump()
                if time.time() - start > MAX_SECONDS:
                    print("已達最長錄音時間，自動停止。")
                    break
    finally:
        indicator.hide()

    if not frames:
        print("沒有錄到聲音，請重試。")
        return None

    import numpy as np  # 錄音資料轉檔用
    audio = np.concatenate(frames, axis=0)
    pcm = (audio * 32767).astype(np.int16)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    with wave.open(tmp.name, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())
    print(f"錄音完成：{len(pcm) / SAMPLE_RATE:.1f} 秒")
    return tmp.name


def record_toggle_caps():
    """單鍵模式：點一下 Caps Lock 開始，再點一下停止。

    按鍵事件會被攔截（suppress），所以 Caps Lock 只會觸發錄音，
    不會切換大小寫、不會影響打字；錄音時跳出音量指示窗。
    """
    try:
        import keyboard
        import sounddevice as sd
        import numpy as np
        import threading
    except ImportError as exc:
        print(f"缺少錄音套件：{exc}，請先 pip install -r requirements.txt")
        return None

    started = threading.Event()
    hook_start = keyboard.add_hotkey("caps lock", lambda: started.set(),
                                     suppress=True)
    try:
        print("點一下 [Caps Lock] 開始說話…")
        started.wait()
    finally:
        keyboard.remove_hotkey(hook_start)
    # 等使用者放開，避免按住的連發直接觸發停止
    while keyboard.is_pressed("caps lock"):
        time.sleep(0.02)

    print(f"錄音中…再點一下 [Caps Lock] 停止（最長 {MAX_SECONDS} 秒）。")
    indicator = RecIndicator()
    indicator.show()
    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())
        # 即時音量推給指示窗（靜音約 0，正常說話約 0.1~0.5）
        rms = float(np.sqrt(np.mean(indata.astype(np.float64) ** 2)))
        indicator.push_level(min(1.0, rms * 5.0))

    stopped = threading.Event()
    hook_stop = keyboard.add_hotkey("caps lock", lambda: stopped.set(),
                                    suppress=True)
    start = time.time()
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            device=DEVICE, callback=callback):
            while not stopped.is_set() and time.time() - start < MAX_SECONDS:
                indicator.pump()
                time.sleep(0.05)
    finally:
        keyboard.remove_hotkey(hook_stop)
        indicator.hide()
    if not stopped.is_set() and time.time() - start >= MAX_SECONDS:
        print("已達最長錄音時間，自動停止。")

    if not frames:
        print("沒有錄到聲音，請重試。")
        return None
    audio = np.concatenate(frames, axis=0)
    pcm = (audio * 32767).astype(np.int16)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    with wave.open(tmp.name, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())
    print(f"錄音完成：{len(pcm) / SAMPLE_RATE:.1f} 秒")
    return tmp.name


def record_press_enter_to_stop():
    """備用錄音模式：按 Enter 開始，再按 Enter 停止（熱鍵無權限時用）。"""
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError as exc:
        print(f"缺少錄音套件：{exc}，請先 pip install -r requirements.txt")
        return None

    input("按 Enter 開始錄音…")
    print(f"錄音中…再按 Enter 停止（最長 {MAX_SECONDS} 秒）。")
    indicator = RecIndicator()
    indicator.show()
    frames = []
    stop_flag = {"stop": False}

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())
        rms = float(np.sqrt(np.mean(indata.astype(np.float64) ** 2)))
        indicator.push_level(min(1.0, rms * 5.0))
        if len(frames) * 0.1 >= MAX_SECONDS:
            stop_flag["stop"] = True

    import threading

    def wait_enter():
        input()
        stop_flag["stop"] = True

    threading.Thread(target=wait_enter, daemon=True).start()
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            device=DEVICE, callback=callback):
            while not stop_flag["stop"]:
                indicator.pump()
                time.sleep(0.05)
    finally:
        indicator.hide()

    if not frames:
        print("沒有錄到聲音，請重試。")
        return None
    audio = np.concatenate(frames, axis=0)
    pcm = (audio * 32767).astype(np.int16)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    with wave.open(tmp.name, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm.tobytes())
    print(f"錄音完成：{len(pcm) / SAMPLE_RATE:.1f} 秒")
    return tmp.name


def transcribe_groq(wav_path):
    """送 Groq Whisper 轉寫，回傳辨識文字。"""
    from groq import Groq
    from pathlib import Path

    client = Groq(api_key=GROQ_API_KEY)
    with open(wav_path, "rb") as audio_file:
        result = client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=(Path(wav_path).name, audio_file.read()),
            language="zh",
            response_format="text",
            temperature=0.0,
        )
    # groq 回傳可能是字串或物件，兩種都相容
    if isinstance(result, str):
        return result.strip()
    return str(getattr(result, "text", result)).strip()


def polish_with_groq(raw_text):
    """用 Groq 上的 LLM 把逐字稿潤飾成通順繁中，只回傳正文。"""
    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=POLISH_MODEL,
        messages=[
            {"role": "system", "content": POLISH_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    return (resp.choices[0].message.content or "").strip()


def paste_text(text):
    """把文字送到剪貼簿並自動 Ctrl+V 貼到目前游標處。"""
    import pyperclip

    pyperclip.copy(text)
    time.sleep(0.15)
    try:
        import pyautogui

        pyautogui.hotkey("ctrl", "v")
    except Exception:
        # pyautogui 失敗時改用 keyboard 送鍵
        import keyboard

        keyboard.send("ctrl+v")
    print("已貼上到目前游標位置。")


def process_once(wav_path=None, use_enter_mode=False, no_polish=False, no_paste=False):
    """跑一次完整流程：錄音 → 辨識 → 潤飾 → 貼上。"""
    if wav_path is None:
        if use_enter_mode:
            wav_path = record_press_enter_to_stop()
        elif VOICE_MODE == "hold":
            wav_path = record_while_hotkey_held()
        else:
            wav_path = record_toggle_caps()
    if not wav_path:
        return False
    try:
        print("辨識中（Groq Whisper）…")
        raw_text = transcribe_groq(wav_path)
        print(f"逐字稿：{raw_text}")
        if not raw_text:
            print("辨識結果為空，請重試。")
            return False
        final_text = raw_text
        if not no_polish:
            print("潤飾中（Groq）…")
            try:
                final_text = polish_with_groq(raw_text)
            except Exception as exc:
                print(f"潤飾失敗，改用原文：{exc}")
        print(f"結果：{final_text}")
        if not no_paste:
            paste_text(final_text)
        return True
    finally:
        # 只有程式產生的暫存檔才刪除，外部傳入的測試檔保留
        if wav_path is None or True:
            try:
                if os.path.exists(wav_path) and tempfile.gettempdir() in wav_path:
                    os.remove(wav_path)
            except OSError:
                pass


def main():
    """主程式：常駐等待熱鍵，Ctrl+C 結束。"""
    parser = argparse.ArgumentParser(description="語音輸入法：熱鍵錄音→辨識→潤飾→貼上")
    parser.add_argument("--once", action="store_true", help="只跑一次就結束")
    parser.add_argument("--enter-mode", action="store_true", help="用 Enter 取代熱鍵錄音")
    parser.add_argument("--wav", default=None, help="直接辨識指定 wav 檔（測試用）")
    parser.add_argument("--no-polish", action="store_true", help="跳過 Groq 潤飾")
    parser.add_argument("--no-paste", action="store_true", help="只印出文字不自動貼上")
    parser.add_argument("--mics", action="store_true", help="列出麥克風裝置編號後離開")
    args = parser.parse_args()

    if args.mics:
        import sounddevice as sd
        print(sd.query_devices())
        return

    if not check_keys():
        sys.exit(1)

    if args.wav or args.once:
        process_once(wav_path=args.wav, use_enter_mode=args.enter_mode,
                     no_polish=args.no_polish, no_paste=args.no_paste)
        return

    if VOICE_MODE == "hold":
        print(f"語音輸入常駐中：按住 [{HOTKEY}] 說話，放開自動貼上。Ctrl+C 結束。")
    else:
        print("語音輸入常駐中：點一下 [Caps Lock] 開始，再點一下停止貼上。Ctrl+C 結束。")
        print("錄音時右上角會跳出麥克風音量窗，有綠色音量條＝有收到聲音。")
    print("若熱鍵沒反應，請改用：python voice_input.py --once --enter-mode")
    while True:
        try:
            process_once(use_enter_mode=args.enter_mode, no_polish=args.no_polish,
                         no_paste=args.no_paste)
        except KeyboardInterrupt:
            print("\n已結束。")
            break
        except Exception as exc:
            print(f"發生錯誤：{exc}，繼續等待下一次。")


if __name__ == "__main__":
    main()
