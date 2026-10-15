# -*- coding: utf-8 -*-
"""跳出視窗讓老師貼上 Groq Key，自動寫入 .env（Key 不會顯示在畫面紀錄上）。"""
import os
import tkinter as tk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
EXAMPLE_PATH = os.path.join(BASE_DIR, ".env.example")


def save_key(key_value, window):
    """把 Key 寫入 .env 的 GROQ_API_KEY 欄位，保留其他設定。"""
    key_value = key_value.strip()
    if not key_value:
        messagebox.showwarning("提醒", "Key 是空的，請貼上你的 Groq Key。")
        return
    if not key_value.startswith("gsk_"):
        ok = messagebox.askyesno("確認", "這串看起來不像 Groq Key（通常以 gsk_ 開頭），確定要存嗎？")
        if not ok:
            return
    # 讀現有 .env，沒有就拿 .env.example 當底
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as src:
            lines = src.readlines()
    elif os.path.exists(EXAMPLE_PATH):
        with open(EXAMPLE_PATH, "r", encoding="utf-8") as src:
            lines = src.readlines()
    # 更新或新增 GROQ_API_KEY 那一行
    updated = False
    for i, line in enumerate(lines):
        if line.strip().startswith("GROQ_API_KEY="):
            lines[i] = f"GROQ_API_KEY={key_value}\n"
            updated = True
    if not updated:
        lines.append(f"GROQ_API_KEY={key_value}\n")
    with open(ENV_PATH, "w", encoding="utf-8") as dst:
        dst.writelines(lines)
    messagebox.showinfo("完成", ".env 已儲存，可以開始實測了！")
    window.destroy()


def main():
    """顯示 Key 輸入視窗。"""
    window = tk.Tk()
    window.title("語音輸入法 - 貼上 Groq Key")
    window.geometry("440x200")
    window.resizable(False, False)

    label = tk.Label(window, text="把剛申請的 Groq Key（gsk_ 開頭）貼在下面：",
                     font=("Microsoft JhengHei", 11))
    label.pack(pady=(20, 8), padx=20)

    key_var = tk.StringVar()
    entry = tk.Entry(window, textvariable=key_var, show="•",
                     font=("Consolas", 11), width=42)
    entry.pack(pady=4, padx=20)
    entry.focus()

    # 顯示／隱藏切換
    show_var = tk.BooleanVar(value=False)

    def toggle_show():
        # 切換顯示或隱藏 Key 明文
        entry.config(show="" if show_var.get() else "•")

    check = tk.Checkbutton(window, text="顯示 Key", variable=show_var,
                           command=toggle_show)
    check.pack(pady=2)

    btn_frame = tk.Frame(window)
    btn_frame.pack(pady=12)
    save_btn = tk.Button(btn_frame, text="儲存到 .env",
                         command=lambda: save_key(key_var.get(), window),
                         width=14)
    save_btn.pack(side="left", padx=8)
    cancel_btn = tk.Button(btn_frame, text="取消",
                           command=window.destroy, width=10)
    cancel_btn.pack(side="left", padx=8)

    window.bind("<Return>", lambda event: save_key(key_var.get(), window))
    window.mainloop()


if __name__ == "__main__":
    main()
