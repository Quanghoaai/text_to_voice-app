# get_machine.py

import uuid

def get_machine_id():
    """
    Lấy mã máy dựa trên địa chỉ MAC.
    """
    mac = uuid.getnode()
    return ":".join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))

if __name__ == "__main__":
    machine_id = get_machine_id()
    print("Mã máy của bạn là:")
    print(machine_id)

    # Ghi vào file (tuỳ chọn)
    with open("machine_id.txt", "w") as f:
        f.write(machine_id)

    print("Mã máy đã được lưu vào file 'machine_id.txt'")