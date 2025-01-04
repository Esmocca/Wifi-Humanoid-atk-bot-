#Humanoid atk bot Enemy(client)
import socket
import machine
import time
import network
import ssd1306
import _thread
from machine import Pin, I2C

# Konfigurasi Wi-Fi
ssid = "Alamak"
password = "ndaktaukoktanyasaya"

# Inisialisasi I2C untuk OLED
i2c = I2C(0, scl=Pin(21), sda=Pin(20))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
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

def custom_print(text):
    print(text)
    with oled_lock:
        display_on_oled(text)

custom_print("Connecting to Wi-Fi...")
while not wlan.isconnected():
    time.sleep(0.1)

custom_print("Connected to Wi-Fi!")
custom_print("IP Address: " + wlan.ifconfig()[0])

# Konfigurasi server
enemy_ip = "192.168.32.8"
enemy_port = 50003

# Pin tombol
atk_pin = Pin(14, Pin.IN, Pin.PULL_UP)
block_pin = Pin(15, Pin.IN, Pin.PULL_UP)

# Status robot
hp = 100
atk = 30
defense = 20
robot_alive = True

# Fungsi koneksi ke server
def connect_to_server():
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((enemy_ip, enemy_port))
            client_socket.setblocking(False)
            return client_socket
        except OSError as e:
            custom_print(f"Connection failed: {e}. Retrying...")
            time.sleep(5)

# Fungsi utama
def main():
    global hp, atk, defense, robot_alive
    client_socket = connect_to_server()
    custom_print("Connected to server.\nwait 5 seconds to boot")
    
    atk_pressed = False
    atk_delay = 0  # Variabel untuk delay
    atk_last_press = 0  # Waktu penekanan terakhir tombol atk
    atk_button_released = True  # Menyimpan status apakah tombol sudah dilepaskan
    
    while robot_alive:
        # Menampilkan statistik robot saat terhubung
        stats = f"STATS:\nHP: {hp}\nATK: {atk}\nDEF: {defense}"
        display_on_oled(stats)

        # Menerima data dari server
        try:
            data = client_socket.recv(1024)
            if data:
                decoded_data = data.decode().strip()
                custom_print(f"Received: {decoded_data}")

                if "Atk" in decoded_data:
                    try:
                        attack_received = int(decoded_data.split()[1])
                        if block_pin.value() == 0:
                            custom_print("Attack blocked!")
                        else:
                            damage = max((attack_received * (100 - defense)) // 100, 0)
                            hp -= damage
                            custom_print(f"HP Remaining: {hp}")
                            if hp <= 0:
                                robot_alive = False
                                custom_print("You're defeated!")
                                display_on_oled("You're defeated!")  # Tampilkan pesan "You're defeated" di OLED
                    except ValueError:
                        custom_print("Invalid attack data!")
        except OSError as e:
            if e.args[0] != 11:
                custom_print(f"Receive error: {e}")
                break

        # Mengirim data ke server jika tombol atk ditekan
        if atk_pin.value() == 0 and atk_button_released and (time.ticks_ms() - atk_last_press > 1000):
            # Tombol baru saja ditekan dan sudah lebih dari 1 detik sejak penekanan terakhir
            try:
                message = f"Atk {atk}\n"
                client_socket.sendall(message.encode())
                custom_print("Attack sent!")
                atk_last_press = time.ticks_ms()  # Set waktu penekanan tombol
                atk_button_released = False  # Menandakan tombol sedang ditekan
            except OSError as e:
                custom_print(f"Send error: {e}")

        # Memastikan tombol dilepaskan sebelum bisa mendeteksi penekanan berikutnya
        if atk_pin.value() == 1 and not atk_button_released:
            atk_button_released = True  # Tombol telah dilepaskan

        # Menampilkan status tombol jika tombol atk ditekan
        if atk_pin.value() == 0:
            status = "Attack Pressed"
            display_on_oled(status)
        
        # Menampilkan status tombol tidak ditekan (jika tidak tekan atk)
        elif atk_pin.value() == 1 and robot_alive:
            display_on_oled(stats)

        if block_pin.value() == 0:
            custom_print("Blocking attack!")

        time.sleep(0.1)

main()

