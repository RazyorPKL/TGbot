# lang: Python 3, file: tgbot_windows.py
# target: Windows 10/11 Cloud PC
# kontrol Windows via Telegram bot + persistence + restart/shutdown tanpa konfirmasi
# deps: pip install pyTelegramBotAPI psutil

import telebot
import subprocess
import os
import sys
import psutil
import platform
import time
import shutil
import winreg
from datetime import datetime

# ══════════════════════════════════════════
# CONFIG — isi ini dulu
# ══════════════════════════════════════════
BOT_TOKEN   = "7393330327:AAHBHUeUl8OtE00_xyxLINPjWu2-wNh4el0"   # dari @BotFather
ALLOWED_IDS = [5412978370]                       # Telegram user ID kamu — cek di @userinfobot

# ══════════════════════════════════════════
# PERSISTENCE — pasang saat pertama jalan
# ══════════════════════════════════════════
def install_persistence():
    try:
        script_src = os.path.abspath(__file__)
        persist_dir = os.path.join(os.environ.get("APPDATA", "C:\\"), "TGBot")
        persist_dst = os.path.join(persist_dir, "tgbot_windows.py")

        os.makedirs(persist_dir, exist_ok=True)
        if script_src != persist_dst:
            shutil.copy2(script_src, persist_dst)

        python   = sys.executable
        pythonw  = os.path.join(os.path.dirname(python), "pythonw.exe")
        if os.path.exists(pythonw):
            python = pythonw

        run_val = f'"{python}" "{persist_dst}"'

        # Registry Run key — HKCU (tidak butuh admin)
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "TGBotWindows", 0, winreg.REG_SZ, run_val)
        winreg.CloseKey(key)

        # Startup folder fallback
        startup = os.path.join(
            os.environ.get("APPDATA", ""),
            r"Microsoft\Windows\Start Menu\Programs\Startup\tgbot.bat"
        )
        with open(startup, "w") as f:
            f.write(f'@echo off\nstart "" /B "{python}" "{persist_dst}"\n')

        print(f"[+] Persistence terpasang: {persist_dst}")
    except Exception as e:
        print(f"[!] Persistence gagal: {e}")

# ══════════════════════════════════════════
# INIT
# ══════════════════════════════════════════
bot = telebot.TeleBot(BOT_TOKEN)

def is_allowed(message):
    return message.from_user.id in ALLOWED_IDS

# ══════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════
def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        out = result.stdout.strip() or result.stderr.strip()
        return out[:4000] if out else "(tidak ada output)"
    except subprocess.TimeoutExpired:
        return "[!] Timeout 30 detik"
    except Exception as e:
        return f"[!] Error: {e}"

def get_sysinfo():
    cpu    = psutil.cpu_percent(interval=1)
    mem    = psutil.virtual_memory()
    disk   = psutil.disk_usage("C:\\")
    uptime = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"💻 *System Info*\n"
        f"OS      : {platform.system()} {platform.release()}\n"
        f"CPU     : {cpu}%\n"
        f"RAM     : {mem.percent}% ({mem.used // 1024**2} MB / {mem.total // 1024**2} MB)\n"
        f"Disk C  : {disk.percent}% ({disk.used // 1024**3} GB / {disk.total // 1024**3} GB)\n"
        f"Boot    : {uptime}"
    )

def get_proclist():
    procs = []
    for p in psutil.process_iter(['pid', 'name']):
        try: procs.append(f"{p.info['pid']:6} | {p.info['name']}")
        except: pass
    out = "\n".join(procs[:50])
    return f"```\n{'PID':>6} | Name\n{'-'*30}\n{out}\n```"

# ══════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════
@bot.message_handler(commands=['start', 'help'])
def cmd_help(msg):
    if not is_allowed(msg): return
    bot.reply_to(msg,
        "🤖 *Windows Bot*\n\n"
        "/info — system info\n"
        "/ps — list proses (50 teratas)\n"
        "/kill `<nama/PID>` — kill proses\n"
        "/run `<command>` — jalankan CMD\n"
        "/ps1 `<script>` — jalankan PowerShell\n"
        "/ls `<path>` — list folder\n"
        "/download `<path>` — kirim file ke Telegram\n"
        "/screenshot — screenshot layar\n"
        "/restart\\_explorer — restart Explorer\n"
        "/reboot — restart PC langsung\n"
        "/shutdown — shutdown PC langsung\n",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['info'])
def cmd_info(msg):
    if not is_allowed(msg): return
    bot.reply_to(msg, get_sysinfo(), parse_mode="Markdown")

@bot.message_handler(commands=['ps'])
def cmd_ps(msg):
    if not is_allowed(msg): return
    bot.reply_to(msg, get_proclist(), parse_mode="Markdown")

@bot.message_handler(commands=['kill'])
def cmd_kill(msg):
    if not is_allowed(msg): return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: /kill <nama.exe atau PID>")
        return
    target = parts[1].strip()
    out = run_cmd(f"taskkill /f /pid {target}") if target.isdigit() else run_cmd(f"taskkill /f /im {target}")
    bot.reply_to(msg, f"```\n{out}\n```", parse_mode="Markdown")

@bot.message_handler(commands=['run'])
def cmd_run(msg):
    if not is_allowed(msg): return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: /run <command>")
        return
    out = run_cmd(parts[1])
    bot.reply_to(msg, f"```\n{out}\n```", parse_mode="Markdown")

@bot.message_handler(commands=['ps1'])
def cmd_ps1(msg):
    if not is_allowed(msg): return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: /ps1 <powershell script>")
        return
    out = run_cmd(f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{parts[1]}"')
    bot.reply_to(msg, f"```\n{out}\n```", parse_mode="Markdown")

@bot.message_handler(commands=['ls'])
def cmd_ls(msg):
    if not is_allowed(msg): return
    parts = msg.text.split(maxsplit=1)
    path  = parts[1].strip() if len(parts) > 1 else "C:\\"
    out   = run_cmd(f'dir "{path}"')
    bot.reply_to(msg, f"```\n{out}\n```", parse_mode="Markdown")

@bot.message_handler(commands=['download'])
def cmd_download(msg):
    if not is_allowed(msg): return
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: /download <path file>")
        return
    path = parts[1].strip()
    if not os.path.isfile(path):
        bot.reply_to(msg, f"File tidak ditemukan: {path}")
        return
    with open(path, 'rb') as f:
        bot.send_document(msg.chat.id, f)

@bot.message_handler(commands=['screenshot'])
def cmd_screenshot(msg):
    if not is_allowed(msg): return
    try:
        import tempfile
        tmp = tempfile.mktemp(suffix=".png")
        run_cmd(
            f'powershell -Command "'
            f'Add-Type -AssemblyName System.Windows.Forms;'
            f'$b = [System.Drawing.Bitmap]::new([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,'
            f'[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height);'
            f'$g = [System.Drawing.Graphics]::FromImage($b);'
            f'$g.CopyFromScreen(0,0,0,0,$b.Size);'
            f'$b.Save(\'{tmp}\');"'
        )
        if os.path.isfile(tmp):
            with open(tmp, 'rb') as f:
                bot.send_photo(msg.chat.id, f)
            os.remove(tmp)
        else:
            bot.reply_to(msg, "Screenshot gagal.")
    except Exception as e:
        bot.reply_to(msg, f"Error: {e}")

@bot.message_handler(commands=['restart_explorer'])
def cmd_restart_explorer(msg):
    if not is_allowed(msg): return
    run_cmd("taskkill /f /im explorer.exe")
    time.sleep(2)
    subprocess.Popen("explorer.exe")
    bot.reply_to(msg, "✅ Explorer direstart.")

@bot.message_handler(commands=['reboot'])
def cmd_reboot(msg):
    if not is_allowed(msg): return
    bot.reply_to(msg, "🔄 Reboot dijalankan...")
    run_cmd("shutdown /r /t 3 /f")

@bot.message_handler(commands=['shutdown'])
def cmd_shutdown(msg):
    if not is_allowed(msg): return
    bot.reply_to(msg, "⚠️ Shutdown dijalankan...")
    run_cmd("shutdown /s /t 3 /f")

# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════
if __name__ == "__main__":
    # ── single-instance lock via Windows mutex ──
    import ctypes
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "TGBotWindows_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("[!] Instance lain sudah jalan. Keluar.")
        sys.exit(0)

    install_persistence()
    print("[*] Bot jalan...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
