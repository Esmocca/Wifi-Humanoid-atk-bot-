import socket
import machine
import time
import network
import ssd1306
import _thread  # Menggunakan threading untuk komunikasi dua arah
from machine import Pin, I2C

# Konfigurasi Wi-Fi
ssid = "OPPO A96"  # Nama Wi-Fi
password = "Baksotanpatepung"  # Password Wi-Fi

# Inisialisasi I2C pada pin GP20 (SDA) dan GP21 (SCL)
i2c = machine.I2C(0, scl=machine.Pin(21), sda=machine.Pin(20))

# Buat objek SSD1306 dengan ukuran 128x64 piksel
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

# Bersihkan layar OLED
oled.fill(0)
oled.show()
oled_lock = _thread.allocate_lock()
# Inisialisasi Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

# Fungsi untuk menampilkan teks pada OLED
def display_on_oled(text):
    oled.fill(0)
    lines = text.splitlines()
    for i, line in enumerate(lines[:6]):
        oled.text(line[:16], 0, i * 10)
    oled.show()
    time.sleep(0.1)  # Tambahkan delay


# Fungsi custom print untuk menampilkan pesan pada OLED dan shell
def custom_print(text):
    print(text)  # Debugging
    with oled_lock:  # Pastikan hanya satu thread mengakses OLED
        display_on_oled(text)

# Tunggu hingga koneksi Wi-Fi berhasil
custom_print("Connecting to\nWi-Fi...")
while not wlan.isconnected():
    time.sleep(0.1)

custom_print("Connected to Wi-Fi!")
custom_print("IP Address: " + wlan.ifconfig()[0])

# IP dan port server (ally)
host_ip = "192.168.32.8"  # IP server (robot ally)
port = 50023  # Port server

# Inisialisasi pin GPIO
atk_pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)  # Tombol ATK
block_pin = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)  # Tombol BLOCK

# Main stats robot server
hp = 100  # Health points
atk = 30  # Attack power
defense = 20  # Defense value (in percentage)
robot_alive = True

# Fungsi untuk menginisialisasi server
def init_server():
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host_ip, port))
        server_socket.listen(1)  # Maksimal 1 koneksi sekaligus
        custom_print(f"Available ip:\n{host_ip}\nPort:{port}")
        return server_socket
    except OSError as e:
        custom_print(f"Error initializing server: {e}")
        return None

# Fungsi untuk menerima data dari klien
def receive_data(client_socket):
    global hp, atk, defense, robot_alive
    while robot_alive:
        try:
            data = client_socket.recv(1024)
            if data:
                decoded_data = data.decode().strip()
                custom_print(f"Received data: {decoded_data}")
                if "Atk" in decoded_data:
                    try:
                        attack_received = int(decoded_data.split()[1])
                        custom_print(f"Attack received! Damage: {attack_received}")
                        if block_pin.value() == 0:
                            custom_print("Attack blocked! No damage taken.")
                        else:
                            damage = max((attack_received * (100 - defense)) // 100, 0)
                            hp -= damage
                            custom_print(f"Damage received! Remaining HP: {hp}")

                            if hp <= 0:
                                custom_print("You're defeated! HP < 0")
                                robot_alive = False  # Matikan robot
                                break
                    except ValueError:
                        custom_print("Invalid attack data received!")
                else:
                    custom_print("No attack data found.")
        except OSError as e:
            if e.args[0] == 11:  # EAGAIN error (no data yet)
                status_text = f"BASE STATS:\nHP: {hp}\nATK: {atk}\nDEF: {defense}"
                custom_print(status_text)
            elif e.args[0] == 9:  # EBADF error
                custom_print("Client\ndisconnected")
                break
            else:
                custom_print(f"Error receiving data: {e}")

# Fungsi untuk loop tombol BLOCK
def block_button_loop():
    global robot_alive
    while robot_alive:
        if block_pin.value() == 0:
            custom_print("Block button pressed!")
        time.sleep(0.1)

# Fungsi utama untuk menangani koneksi dan tombol
def main_loop():
    global robot_alive, hp, atk, defense
    server_socket = init_server()
    if not server_socket:
        return

    client_socket = None

    while True:
        if client_socket is None:
            try:
                client_socket, client_address = server_socket.accept()
                custom_print(f"Client connected from {client_address}")
                client_socket.setblocking(False)

                # Mulai thread untuk menerima data dan tombol BLOCK
                _thread.start_new_thread(receive_data, (client_socket,))
                _thread.start_new_thread(block_button_loop, ())
            except Exception as e:
                print(f"Error accepting connection: {e}")
                continue

        if client_socket is not None and robot_alive:
            try:
                if atk_pin.value() == 0:  # Tombol ATK ditekan
                    attack_message = f"Atk {atk}\n".encode()
                    client_socket.sendall(attack_message)
                    custom_print("Attacking! :\n{atk}")
                time.sleep(0.1)
            except Exception as e:
                custom_print(f"Error in ATK loop: {e}")

# Menjalankan loop utama
main_loop()
