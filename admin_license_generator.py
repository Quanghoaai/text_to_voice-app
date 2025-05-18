import tkinter as tk
from tkinter import ttk, filedialog  # Đã thêm filedialog ở đây
from tkinter import messagebox
import datetime
import json
import base64
from cryptography.fernet import Fernet

# Khóa bí mật dùng chung giữa admin và client
KEY = Fernet.generate_key()  # Chỉ sinh một lần duy nhất trong thực tế
cipher = Fernet(KEY)

# Các gói đăng ký
PACKAGES = {
    "1M": {"duration_days": 30},
    "3M": {"duration_days": 90},
    "6M": {"duration_days": 180},
    "PERM": {"duration_days": None}  # Vĩnh viễn
}

# Hàm tạo license
def generate_license(machine_id, package):
    start_date = datetime.datetime.now()
    if package == "PERM":
        expiry_date = "Vĩnh viễn"
    else:
        expiry_date = (start_date + datetime.timedelta(days=PACKAGES[package]["duration_days"])).strftime("%d/%m/%Y %H:%M:%S")
    
    license_data = {
        "username": "hoanq",
        "voice_id": "Free",
        "registration_date": start_date.strftime("%d/%m/%Y %H:%M:%S"),
        "status": "Đã đăng ký",
        "expiration_date": expiry_date,
        "package": package,
        "machine_id": machine_id
    }
    return license_data

# Hàm mã hóa license
def encrypt_license(license_data):
    try:
        encrypted_data = cipher.encrypt(json.dumps(license_data).encode())
        return base64.b64encode(encrypted_data).decode()
    except Exception as e:
        messagebox.showerror("Lỗi", f"Lỗi mã hóa license: {e}")
        return None

# Hàm lưu license vào file json
def save_license_to_file(encrypted_license):
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
        title="Lưu License"
    )
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump({"license": encrypted_license}, f, indent=4)
            messagebox.showinfo("Thông báo", "Lưu file thành công!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi lưu file: {e}")

# Khi nhấn nút Generate
def on_generate():
    machine_id = entry_machine_id.get().strip()
    package = combo_package.get()

    if not machine_id or package not in PACKAGES:
        messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ thông tin.")
        return

    license_data = generate_license(machine_id, package)
    encrypted_license = encrypt_license(license_data)

    if encrypted_license:
        result_text.delete("1.0", tk.END)
        result_text.insert(tk.END, encrypted_license)
        messagebox.showinfo("Thành công", "License đã được tạo thành công!")

        # Gợi ý lưu file
        save_license_to_file(encrypted_license)

# Sao chép vào clipboard
def copy_to_clipboard():
    result = result_text.get("1.0", tk.END).strip()
    if result:
        root.clipboard_clear()
        root.clipboard_append(result)
        messagebox.showinfo("Thông báo", "Đã sao chép vào clipboard.")

# Giao diện GUI
root = tk.Tk()
root.title("Admin - Tạo License")
root.geometry("500x400")
root.configure(bg="#2E2E2E")

# Nhập mã máy
tk.Label(root, text="Mã máy:", bg="#2E2E2E", fg="white").pack(pady=5)
entry_machine_id = tk.Entry(root, width=50, font=("Arial", 12))
entry_machine_id.pack(pady=5)

# Chọn gói
tk.Label(root, text="Chọn gói:", bg="#2E2E2E", fg="white").pack(pady=5)
combo_package = ttk.Combobox(root, values=list(PACKAGES.keys()), state="readonly", font=("Arial", 12))
combo_package.set("1M")
combo_package.pack(pady=5)

# Nút tạo license
generate_button = tk.Button(root, text="Tạo License", command=on_generate, bg="#4CAF50", fg="white", width=20)
generate_button.pack(pady=10)

# Hiển thị kết quả
result_text = tk.Text(root, height=10, width=50, wrap=tk.WORD, bg="#333333", fg="white", font=("Courier", 10))
result_text.pack(pady=10)

# Nút sao chép
copy_button = tk.Button(root, text="Sao chép", command=copy_to_clipboard, bg="#2196F3", fg="white", width=20)
copy_button.pack(pady=5)

# Label hiển thị key (chỉ phục vụ debug)
key_label = tk.Label(root, text=f"Key (giữ an toàn): {KEY.decode()}", bg="#2E2E2E", fg="#FFA726", font=("Courier", 8))
key_label.pack(pady=5, side=tk.BOTTOM)

# Chạy giao diện
root.mainloop()