#Robot ally (server)v2
#-Energy system to avoid atk spam
import socket
import machine
import time
import network
import ssd1306
import _thread

# Konfigurasi Wi-Fi
ssid = "Alamak"  # Nama Wi-Fi
password = "ndaktaukoktanyasaya"  # Password Wi-Fi

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

custom_print("Connected to\nWi-Fi!")
custom_print("IP Address: " + wlan.ifconfig()[0])

# IP dan port server (ally)
host_ip = wlan.ifconfig()[0]  # IP server (robot ally)
port = 50003  # Port server

# Inisialisasi pin GPIO
atk_pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)  # Tombol ATK
block_pin = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)  # Tombol BLOCK

# Main stats robot server
hp = 100  # Health points
atk = 30  # Attack power
defense = 20  # Defense value (in percentage)
energy = 60  # Energy points
energy_max = 60
energy_regen_rate = 10  # Jumlah energi yang diregenerasi
energy_regen_interval = 5  # Interval regenerasi dalam detik
robot_alive = True
atk_last_press = 0  # Waktu terakhir tombol ATK ditekan
atk_button_released = True  # Status tombol ATK

# Fungsi untuk menginisialisasi server
def init_server():
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host_ip, port))
        server_socket.listen(1)  # Maksimal 1 koneksi sekaligus
        custom_print(f"Available ip:\n{host_ip}\nPort:{port}")
        return server_socket
    except OSError as e:
        #custom_print(f"Error initializing server: {e}")
        custom_print(f"Port on busy")
        return None

# Fungsi utama untuk menangani koneksi dan tombol
def main_loop():
    global robot_alive, hp, atk, defense, atk_last_press, atk_button_released, energy
    server_socket = init_server()
    if not server_socket:
        return

    client_socket = None
    last_energy_regen = time.ticks_ms()

    while True:
        # Regenerasi energi
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, last_energy_regen) >= energy_regen_interval * 1000:
            if energy < energy_max:
                energy += energy_regen_rate
                if energy > energy_max:
                    energy = energy_max
            last_energy_regen = current_time

        if client_socket is None:
            try:
                client_socket, client_address = server_socket.accept()
                custom_print(f"Client connected from {client_address}")
                client_socket.setblocking(False)

                # Tampilkan current stats setelah client terhubung
                current_stats = f"STATS:\nHP: {hp}\nATK: {atk}\nDEF: {defense}\nENGY: {energy}"
                custom_print(current_stats)

            except Exception as e:
                print(f"Error accepting connection: {e}")
                continue

        if client_socket is not None and robot_alive:
            # Terima data dari klien
            try:
                data = client_socket.recv(1024)  # Baca data dari klien
                if data:
                    decoded_data = data.decode().strip()
                    custom_print(f"Received data: {decoded_data}")
                    if decoded_data.startswith("Atk"):
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
                                    custom_print("You're defeated!\nGame over!")
                                    robot_alive = False  # Matikan robot
                        except (ValueError, IndexError):
                            custom_print("Invalid attack data format received!")
                    else:
                        custom_print("No valid attack data found.")
            except OSError as e:
                if e.args[0] == 11:  # EAGAIN error (tidak ada data)
                    # Tampilkan current stats di OLED jika tidak ada tombol yang ditekan
                    if block_pin.value() == 1 and atk_pin.value() == 1:
                        current_stats = f"STATS:\nHP: {hp}\nATK: {atk}\nDEF: {defense}\nENGY: {energy}"
                        with oled_lock:
                            display_on_oled(current_stats)
                elif e.args[0] == 9:  # EBADF error (soket ditutup)
                    custom_print("Client disconnected")
                    client_socket = None
                else:
                    custom_print(f"Error receiving data: {e}")

            # Cek tombol ATK
            current_time = time.ticks_ms()
            if atk_pin.value() == 0 and atk_button_released:
                atk_button_released = False  # Set tombol ATK sebagai ditekan
                if energy > 0:
                    if time.ticks_diff(current_time, atk_last_press) > 1000:  # Delay 1 detik
                        atk_last_press = current_time  # Perbarui waktu terakhir tombol ditekan
                        energy -= 10  # Konsumsi energi
                        attack_message = f"Atk {atk}\n".encode()
                        try:
                            client_socket.sendall(attack_message)
                            custom_print(f"Attacking! :\n{atk}")
                        except Exception as e:
                            custom_print(f"Error sending attack: {e}")
                else:
                    custom_print("Low energy!\nWait 5s")
                    time.sleep(5)
            elif atk_pin.value() == 1:
                atk_button_released = True  # Reset status tombol ATK

            # Cek tombol BLOCK
            if block_pin.value() == 0:
                custom_print("Blocking!")
                time.sleep(0.1)  # Tambahkan delay kecil

# Menjalankan loop utama
main_loop()
