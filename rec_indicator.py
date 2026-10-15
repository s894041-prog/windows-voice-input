# -*- coding: utf-8 -*-
"""錄音指示窗：錄音時顯示麥克風音量條，停止後隱藏。

重要：tkinter 只能由主執行緒操作，所以本類別沒有自己的執行緒。
主程式在錄音迴圈裡定期呼叫 pump() 更新畫面；錄音 callback 只准呼叫
push_level() 存數字（callback 跑在音效執行緒，不能碰 tkinter）。
"""
import tkinter as tk


class RecIndicator:
    """小浮窗指示器，全部呼叫都必須來自發起錄音的那條執行緒（主執行緒）。"""

    def __init__(self):
        self._level = 0.0
        self._bar_width = 180
        root = tk.Tk()
        self._root = root
        root.title("錄音中")
        root.overrideredirect(True)  # 無邊框浮窗
        root.attributes("-topmost", True)  # 永遠最上層
        root.configure(bg="#222222")
        # 固定在螢幕右上角
        x = root.winfo_screenwidth() - 280
        root.geometry(f"+{x}+40")

        label = tk.Label(root, text="● 錄音中…再按 Caps Lock 停止",
                         font=("Microsoft JhengHei", 11),
                         fg="#ff5555", bg="#222222")
        label.pack(padx=14, pady=(10, 4))

        canvas = tk.Canvas(root, width=self._bar_width, height=16,
                           bg="#444444", highlightthickness=0)
        canvas.pack(padx=14, pady=(0, 12))
        self._canvas = canvas
        self._bar = canvas.create_rectangle(0, 0, 0, 16, fill="#4caf50", width=0)
        root.withdraw()  # 先藏起來，show() 才顯示

    def show(self):
        """顯示浮窗（錄音開始時呼叫，主執行緒）。"""
        self._level = 0.0
        self._root.deiconify()
        self._root.lift()
        self.pump()

    def push_level(self, level):
        """存入最新音量 0~1（錄音 callback 呼叫，只存數字不碰畫面）。"""
        self._level = level

    def pump(self):
        """重畫音量條並處理視窗事件（錄音迴圈每圈呼叫，主執行緒）。"""
        width = int(self._bar_width * max(0.0, min(1.0, self._level)))
        self._canvas.coords(self._bar, 0, 0, width, 16)
        color = "#4caf50" if width < self._bar_width * 0.8 else "#ff5555"
        self._canvas.itemconfig(self._bar, fill=color)
        self._root.update()

    def hide(self):
        """隱藏浮窗（錄音結束時呼叫，主執行緒）。"""
        try:
            self._root.withdraw()
        except Exception:
            pass
