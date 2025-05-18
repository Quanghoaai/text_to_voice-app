# client.py
import tkinter as tk
from tkinter import messagebox, ttk
import time
import datetime
import json
import os
import hashlib
import platform
from gtts import gTTS
import pygame
import sys
import logging
from cryptography.fernet import Fernet
import base64
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading
import uuid
from functools import wraps

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('client.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- License Key Configuration ---
# Replace this with the key from server.py (printed in server console or in .env file)
KEY = b'V0429G-GlyXHD2a6NfRCiRcAcFFbn7JvP9oe35kz6Sc='  # Example: b'gXjB4Z3X9y7zK2mPqWvL8tR5nF0hJ6uYxC1dE2aB3cI='
try:
    cipher = Fernet(KEY)
except Exception as e:
    logger.error(f"Failed to initialize Fernet cipher: {e}")
    messagebox.showerror("Cấu hình lỗi", "Không thể khởi tạo mã hóa.\n1. Chạy server.py để lấy KEY.\n2. Copy KEY từ console server hoặc file .env.\n3. Thay thế KEY trong client.py.")
    sys.exit(1)

# --- Pygame Mixer Management ---
class MixerManager:
    def __init__(self):
        self.initialized = False

    def init(self):
        if not self.initialized:
            try:
                import os
                import sys
                # Suppress Pygame welcome message
                with open(os.devnull, 'w') as f:
                    sys.stdout = f
                    pygame.mixer.init()
                    sys.stdout = sys.__stdout__
                self.initialized = True
                logger.info("Pygame mixer initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize pygame mixer: {e}")

    def cleanup(self):
        if self.initialized:
            try:
                pygame.mixer.quit()
                self.initialized = False
                logger.info("Pygame mixer cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up pygame mixer: {e}")

mixer_manager = MixerManager()

# --- Subscription Packages ---
PACKAGES = {
    "1M": {"price": 10.0, "duration_days": 30},
    "3M": {"price": 25.0, "duration_days": 90},
    "6M": {"price": 45.0, "duration_days": 180},
    "PERM": {"price": 100.0, "duration_days": None}
}

# --- Server Configuration ---
SERVER_URL = "http://127.0.0.1:5000"
REQUEST_TIMEOUT = 5
MAX_RETRIES = 3

# --- HTTP Session with Retry ---
session = requests.Session()
retries = Retry(total=MAX_RETRIES, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))

# --- Utility Functions ---
def generate_machine_id():
    """Generates a stable machine ID."""
    try:
        components = [
            platform.node(),
            platform.system(),
            platform.processor(),
            str(uuid.getnode())
        ]
        unique_string = ':'.join(filter(None, components))
        return hashlib.sha256(unique_string.encode('utf-8')).hexdigest()
    except Exception as e:
        logger.error(f"Error generating machine ID: {e}")
        return hashlib.sha256(platform.node().encode('utf-8')).hexdigest()

def require_active_license(func):
    """Decorator to ensure an active license."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_license_active():
            messagebox.showwarning("Cảnh báo", "License đã hết hạn. Vui lòng gia hạn.")
            return
        return func(self, *args, **kwargs)
    return wrapper

class SmartHomeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ứng dụng điều khiển nhà thông minh")
        self.configure(bg="#2E2E2E")
        self.geometry("600x400")
        self._lock = threading.Lock()
        # --- State Variables ---
        self.total_seconds = 0
        self.current_start_time = None
        self.license_data = None
        self.selected_package = "1M"
        self.is_generating = False
        # --- Initialize License ---
        self.initialize_license()
        # --- Setup GUI ---
        self.setup_gui()
        # --- Update Status ---
        self.update_status()
        self.update_license_tab()
        # --- Bind Events ---
        self.bind('<q>', self.exit_on_q)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_license(self):
        """Loads and decrypts license data."""
        with self._lock:
            try:
                if not os.path.exists("license.json"):
                    logger.info("License file not found")
                    return None
                with open("license.json", "rb") as f:
                    encrypted_data = f.read()
                if not encrypted_data:
                    logger.warning("License file is empty")
                    return None
                decrypted_data = cipher.decrypt(encrypted_data)
                license_data = json.loads(decrypted_data.decode('utf-8'))
                required_fields = ['username', 'voice_id', 'registration_date', 'status', 'expiration_date', 'package', 'machine_id']
                if not all(field in license_data for field in required_fields):
                    logger.error("Invalid license data structure")
                    return None
                if license_data['machine_id'] != generate_machine_id():
                    logger.warning("Machine ID mismatch in license")
                    return None
                return license_data
            except Exception as e:
                logger.error(f"Error loading license: {e}")
                messagebox.showwarning("Lỗi License", "Không thể đọc hoặc giải mã file license.")
                return None

    def save_license(self, license_data):
        """Encrypts and saves license data."""
        with self._lock:
            try:
                encrypted_data = cipher.encrypt(json.dumps(license_data).encode('utf-8'))
                with open("license.json", "wb") as f:
                    f.write(encrypted_data)
                logger.info("License saved successfully")
            except Exception as e:
                logger.error(f"Error saving license: {e}")
                messagebox.showerror("Lỗi Lưu License", "Không thể lưu file license.")

    def is_license_active(self):
        """Checks if the license is active."""
        if not self.license_data or not self.license_data.get("expiration_date"):
            return False
        expiry_date_str = self.license_data["expiration_date"]
        if expiry_date_str == "Vĩnh viễn":
            return True
        try:
            current_date = datetime.datetime.now()
            expiry_date = datetime.datetime.strptime(expiry_date_str, "%d/%m/%Y %H:%M:%S")
            return current_date < expiry_date
        except Exception as e:
            logger.error(f"Error checking license: {e}")
            return False

    def initialize_license(self):
        """Initializes license or sets up trial."""
        self.license_data = self.load_license()
        if self.license_data and self.is_license_active():
            logger.info("Active license loaded")
            self.selected_package = self.license_data.get("package", "1M")
            if hasattr(self, 'package_var'):
                self.package_var.set(self.selected_package)
        else:
            logger.info("Initializing trial license")
            machine_id = generate_machine_id()
            start_date = datetime.datetime.now()
            trial_end = start_date + datetime.timedelta(minutes=3)
            self.license_data = {
                "username": "trial_user",
                "voice_id": "Free",
                "registration_date": start_date.strftime("%d/%m/%Y %H:%M:%S"),
                "status": "Dùng thử",
                "expiration_date": trial_end.strftime("%d/%m/%Y %H:%M:%S"),
                "package": "TRIAL",
                "machine_id": machine_id
            }
            self.save_license(self.license_data)
            self.selected_package = "TRIAL"
            messagebox.showinfo("Thông báo", f"Bạn đang ở chế độ dùng thử 3 phút.\nMã máy: {machine_id}")

    def setup_gui(self):
        """Sets up the GUI."""
        notebook = ttk.Notebook(self)
        notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Main Tab
        main_tab = tk.Frame(notebook, bg="#2E2E2E")
        notebook.add(main_tab, text="Main")
        tk.Label(main_tab, text="Chọn gói để sử dụng.\nNhấn phím 'q' để thoát.", bg="#2E2E2E", fg="white", font=("Arial", 12)).pack(pady=10)
        package_frame = tk.Frame(main_tab, bg="#2E2E2E")
        package_frame.pack(pady=10)
        self.package_var = tk.StringVar(value=self.selected_package)
        package_label = tk.Label(package_frame, text="Gói:", bg="#2E2E2E", fg="white", font=("Arial", 10))
        package_label.pack(side="left", padx=5)
        self.package_menu = ttk.OptionMenu(package_frame, self.package_var, self.selected_package, *PACKAGES.keys())
        self.package_menu.pack(side="left")
        tk.Button(main_tab, text="Đăng ký/Gia hạn", command=lambda: self.renew_license(self.package_var.get()),
                  bg="#4CAF50", fg="white", font=("Arial", 10)).pack(pady=10)
        language_frame = tk.Frame(main_tab, bg="#2E2E2E")
        language_frame.pack(pady=10)
        self.language_var = tk.StringVar(value="vi")
        tk.Label(language_frame, text="Ngôn ngữ:", bg="#2E2E2E", fg="white", font=("Arial", 10)).pack(side="left", padx=5)
        self.language_menu = ttk.OptionMenu(language_frame, self.language_var, "vi", "en", "vi")
        self.language_menu.pack(side="left")
        self.text_area = tk.Text(main_tab, height=5, bg="#333333", fg="white", insertbackground="white", font=("Arial", 12))
        self.text_area.pack(expand=True, fill='both', padx=20, pady=10)
        self.text_area.config(state=tk.DISABLED)
        button_frame = tk.Frame(main_tab, bg="#2E2E2E")
        button_frame.pack(pady=10)
        self.generate_button = tk.Button(button_frame, text="Tạo giọng nói", command=self.start_generate_voice,
                                        state=tk.DISABLED, bg="#00B8D4", fg="white", font=("Arial", 10))
        self.generate_button.pack(side="left", padx=10)
        self.service_button = tk.Button(button_frame, text="Bắt đầu dịch vụ", command=self.toggle_service,
                                       bg="#008000", fg="white", font=("Arial", 10))
        self.service_button.pack(side="left")
        self.status_label = tk.Label(main_tab, text="Trạng thái: Đang kiểm tra", bg="#2E2E2E", fg="yellow", font=("Arial", 12, "bold"))
        self.status_label.pack(pady=15)

        # License Tab
        license_tab = tk.Frame(notebook, bg="#2E2E2E")
        notebook.add(license_tab, text="License")
        tk.Label(license_tab, text="Thông tin License", bg="#2E2E2E", fg="white", font=("Arial", 14, "bold")).pack(pady=10)
        license_info_frame = tk.Frame(license_tab, bg="#2E2E2E")
        license_info_frame.pack(fill='x', padx=20, pady=5)
        self.license_status_label = tk.Label(license_info_frame, text="Trạng thái: Đang kiểm tra", bg="#2E2E2E", fg="yellow", anchor="w", font=("Arial", 12, "bold"))
        self.license_status_label.pack(fill='x')
        self.user_label = tk.Label(license_info_frame, text="Người dùng: N/A", bg="#2E2E2E", fg="white", anchor="w", font=("Arial", 10))
        self.user_label.pack(fill='x')
        self.voice_id_label = tk.Label(license_info_frame, text="ID giọng: N/A", bg="#2E2E2E", fg="white", anchor="w", font=("Arial", 10))
        self.voice_id_label.pack(fill='x')
        self.registration_label = tk.Label(license_info_frame, text="Ngày đăng ký: N/A", bg="#2E2E2E", fg="white", anchor="w", font=("Arial", 10))
        self.registration_label.pack(fill='x')
        self.expiration_label = tk.Label(license_info_frame, text="Ngày hết hạn: N/A", bg="#2E2E2E", fg="white", anchor="w", font=("Arial", 10))
        self.expiration_label.pack(fill='x')
        host_frame = tk.Frame(license_tab, bg="#2E2E2E")
        host_frame.pack(fill='x', padx=20, pady=5)
        self.machine_id_label = tk.Label(host_frame, text=f"Mã máy: {generate_machine_id()}", bg="#2E2E2E", fg="white", anchor="w", font=("Arial", 10))
        self.machine_id_label.pack(side="left", fill='x', expand=True)
        tk.Button(host_frame, text="Copy", command=lambda: self.clipboard_append(self.machine_id_label.cget("text").replace("Mã máy: ", "")),
                  bg="#42A5F5", fg="white", font=("Arial", 9)).pack(side="right")
        contact_frame = tk.Frame(license_tab, bg="#2E2E2E")
        contact_frame.pack(fill='x', padx=20, pady=5)
        tk.Label(contact_frame, text="Liên Hệ", bg="#2E2E2E", fg="white", font=("Arial", 12, "bold"), anchor="w").pack(fill='x')
        tk.Label(contact_frame, text="Zalo: Liên hệ Admin", bg="#2E2E2E", fg="white", anchor="w", font=("Arial", 10)).pack(fill='x')
        tk.Label(contact_frame, text="Telegram: @SmartHomeBot (sắp ra mắt)", bg="#2E2E2E", fg="white", anchor="w", font=("Arial", 10)).pack(fill='x')

    def update_status(self):
        """Updates status labels."""
        self.license_data = self.load_license()
        if self.license_data and self.is_license_active():
            expiry_date = self.license_data['expiration_date']
            self.status_label.config(text=f"Trạng thái: Đã đăng ký, hết hạn vào {expiry_date}", fg="green")
            self.service_button.config(state=tk.NORMAL)
        else:
            if self.license_data and self.license_data.get("package") == "TRIAL":
                expiry_date = self.license_data['expiration_date']
                if self.is_license_active():
                    self.status_label.config(text=f"Trạng thái: Dùng thử, hết hạn vào {expiry_date}", fg="yellow")
                    self.service_button.config(state=tk.NORMAL)
                else:
                    self.status_label.config(text="Trạng thái: Dùng thử đã hết hạn", fg="red")
                    self.service_button.config(state=tk.DISABLED)
            else:
                self.status_label.config(text="Trạng thái: License đã hết hạn", fg="red")
                self.service_button.config(state=tk.DISABLED)
            self.text_area.config(state=tk.DISABLED)
            self.generate_button.config(state=tk.DISABLED)
            if self.current_start_time is not None:
                self.toggle_service()

    def update_license_tab(self):
        """Updates License tab labels."""
        self.license_data = self.load_license()
        if self.license_data:
            status_text = "Đã đăng ký" if self.is_license_active() else "Hết hạn"
            status_color = "green" if self.is_license_active() else "red"
            if self.license_data.get("package") == "TRIAL":
                try:
                    expiry_date = datetime.datetime.strptime(self.license_data["expiration_date"], "%d/%m/%Y %H:%M:%S")
                    status_text = "Dùng thử" if datetime.datetime.now() < expiry_date else "Hết hạn dùng thử"
                    status_color = "yellow" if datetime.datetime.now() < expiry_date else "red"
                except ValueError:
                    status_text = "Hết hạn (Lỗi ngày)"
                    status_color = "red"
            self.license_status_label.config(text=f"Trạng thái: {status_text}", fg=status_color)
            self.user_label.config(text=f"Người dùng: {self.license_data.get('username', 'N/A')}")
            self.voice_id_label.config(text=f"ID giọng: {self.license_data.get('voice_id', 'N/A')}")
            self.registration_label.config(text=f"Ngày đăng ký: {self.license_data.get('registration_date', 'N/A')}")
            self.expiration_label.config(text=f"Ngày hết hạn: {self.license_data.get('expiration_date', 'N/A')}")
            self.machine_id_label.config(text=f"Mã máy: {self.license_data.get('machine_id', generate_machine_id())}")
        else:
            self.license_status_label.config(text="Trạng thái: Chưa có License", fg="red")
            self.user_label.config(text="Người dùng: N/A")
            self.voice_id_label.config(text="ID giọng: N/A")
            self.registration_label.config(text="Ngày đăng ký: N/A")
            self.expiration_label.config(text="Ngày hết hạn: N/A")
            self.machine_id_label.config(text=f"Mã máy: {generate_machine_id()}")

    def renew_license(self, package):
        """Renews license via server."""
        if package not in PACKAGES:
            messagebox.showerror("Lỗi", "Gói không hợp lệ.")
            return
        if not self.license_data:
            messagebox.showerror("Lỗi", "Không tìm thấy thông tin license.")
            return

        # ✅ Sửa lỗi "machine_id might be referenced before assignment"
        machine_id = self.license_data.get("machine_id", generate_machine_id())  # Đảm bảo luôn gán giá trị
        logger.info(f"Renewing license for machine ID: {machine_id}, package: {package}")

        try:
            response = session.post(
                f"{SERVER_URL}/activate",
                json={"machine_id": machine_id, "package": package},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            if "license" not in result:
                messagebox.showerror("Lỗi Gia hạn", "Phản hồi server không hợp lệ.")
                return
            encrypted_license = base64.b64decode(result["license"])
            decrypted_license_data = cipher.decrypt(encrypted_license).decode('utf-8')
            new_license_data = json.loads(decrypted_license_data)
            if new_license_data.get("machine_id") != machine_id:
                messagebox.showerror("Lỗi", "Mã máy không khớp.")
                return
            self.license_data = new_license_data
            self.save_license(self.license_data)
            self.selected_package = self.license_data.get("package", "1M")
            self.package_var.set(self.selected_package)
            self.update_status()
            self.update_license_tab()
            messagebox.showinfo("Thông báo", f"Đã gia hạn gói {package.replace('M', ' tháng')} thành công!")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during license renewal: {e}")
            messagebox.showerror("Lỗi Kết nối", f"Không thể kết nối đến server: {e}")
        except Exception as e:
            logger.error(f"Error processing license renewal: {e}")
            messagebox.showerror("Lỗi", f"Lỗi khi gia hạn: {e}")

    @require_active_license
    def start_generate_voice(self):
        """Starts voice generation in a thread."""
        if self.is_generating:
            return
        text = self.text_area.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập văn bản.")
            return
        self.is_generating = True
        self.generate_button.config(state=tk.DISABLED, text="Đang tạo...")
        threading.Thread(target=self.generate_voice, args=(text,), daemon=True).start()

    def generate_voice(self, text):
        """Generates and plays voice."""
        lang = self.language_var.get()
        audio_file = f"output_{int(time.time())}.mp3"
        try:
            mixer_manager.init()
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(audio_file)
            if mixer_manager.initialized:
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    self.update_idletasks()
                    time.sleep(0.1)
            else:
                messagebox.showwarning("Cảnh báo", "Không thể phát âm thanh.")
        except Exception as e:
            logger.error(f"Error generating voice: {e}")
            messagebox.showerror("Lỗi", f"Không thể tạo giọng nói: {e}")
        finally:
            self.is_generating = False
            self.generate_button.config(state=tk.NORMAL, text="Tạo giọng nói")
            if os.path.exists(audio_file):
                try:
                    pygame.mixer.music.unload()
                    os.remove(audio_file)
                except Exception as e:
                    logger.error(f"Error cleaning up audio file: {e}")

    @require_active_license
    def toggle_service(self):
        """Toggles service state."""
        if self.current_start_time is None:
            self.current_start_time = time.time()
            self.service_button.config(text="Dừng dịch vụ", bg="#FF0000")
            self.text_area.config(state=tk.NORMAL)
            self.generate_button.config(state=tk.NORMAL)
            logger.info("Service started")
        else:
            end_time = time.time()
            session_seconds = end_time - self.current_start_time
            self.total_seconds += session_seconds
            self.current_start_time = None
            self.service_button.config(text="Bắt đầu dịch vụ", bg="#008000")
            self.text_area.config(state=tk.DISABLED)
            self.generate_button.config(state=tk.DISABLED)
            logger.info(f"Service stopped, session duration: {session_seconds:.2f} seconds")

    def on_closing(self):
        """Handles application shutdown."""
        if self.current_start_time is not None:
            end_time = time.time()
            self.total_seconds += end_time - self.current_start_time
            self.current_start_time = None
        total_minutes = self.total_seconds / 60
        message = f"Tổng thời gian sử dụng: {total_minutes:.2f} phút"
        current_license = self.load_license()
        if current_license:
            package = current_license.get('package', 'N/A')
            package_display = package.replace('M', ' tháng') if package != 'PERM' else 'Vĩnh viễn'
            price = PACKAGES.get(package, {}).get('price', 'N/A')
            message += f"\nGói: {package_display} ({price}$)"
        logger.info(message)
        try:
            messagebox.showinfo("Tóm tắt sử dụng", message)
            with open("usage_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now()}: {message}\n")
        except Exception as e:
            logger.error(f"Error logging usage: {e}")
        mixer_manager.cleanup()
        self.destroy()

    def exit_on_q(self, event):
        """Handles 'q' key press."""
        self.on_closing()

if __name__ == "__main__":
    if KEY == b'PUT_YOUR_SERVER_KEY_HERE':
        logger.error("Fernet KEY not set. Run server.py, copy the KEY from console or .env, and update client.py.")
        sys.exit(1)
    app = SmartHomeApp()
    try:
        app.mainloop()
    except Exception as e:
        logger.error(f"Main loop error: {e}")
        sys.exit(1)