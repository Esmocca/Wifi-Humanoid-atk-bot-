# Code HAB-W for multi clients
# Identify your hp based on region
# Change client_name for client 2 or else 
# Atk button disabled while blocking
# Redled for hp indicator & atk received
# Blocking consume energy by -1 of current energy

import socket
import machine
import time
import network
import ssd1306
import _thread
from machine import Pin, I2C

# Inisiasi nama klien
client_name = "Stellar"  # Ganti dengan "Client2" untuk klien kedua

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

custom_print(f"{client_name}\nConnecting to\nWi-Fi...")
while not wlan.isconnected():
    time.sleep(0.1)

custom_print(f"{client_name} connected to Wi-Fi!")
custom_print("IP Address:\n" + wlan.ifconfig()[0])

# Konfigurasi server
server_ip = "192.168.95.96"  # IP server yang telah terdeteksi jika tidak berhasil coba ini "192.168.32.96"
server_port = 50003

# Pin tombol
atk_pin = Pin(14, Pin.IN, Pin.PULL_UP)
block_pin = Pin(15, Pin.IN, Pin.PULL_UP)
rled_pin = Pin(5, Pin.OUT)  # LED merah mati saat inisialisasi

# Status robot
hp = 100
atk = 30
defense = 20
energy = 30
energy_max = 30
energy_regen_rate = 10
energy_regen_interval = 5  # Interval regenerasi energi dalam detik
robot_alive = True
isblocking = False  # Status blocking

# Fungsi koneksi ke server
def connect_to_server():
    while True:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((server_ip, server_port))
            client_socket.setblocking(False)
            custom_print(f"{client_name} connected to server!")
            return client_socket
        except OSError as e:
            custom_print(f"Connection failed: {e}. Retrying...")
            time.sleep(5)

# Fungsi utama
def main():
    global hp, atk, defense, energy, robot_alive, isblocking
    client_socket = connect_to_server()
    #custom_print(f"{client_name}\nWait 5 seconds\nto boot...")
    #time.sleep(5)

    atk_last_press = 0  # Waktu terakhir tombol atk ditekan
    atk_button_released = True  # Status tombol atk
    last_energy_regen = time.ticks_ms()

    while robot_alive:
        # Regenerasi energi
        rled_pin.value(0)
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, last_energy_regen) >= energy_regen_interval * 1000:
            if energy < energy_max:
                energy += energy_regen_rate
                if energy > energy_max:
                    energy = energy_max
            last_energy_regen = current_time

        # Menampilkan statistik robot
        stats = f"{client_name}\nHP: {hp}\nATK: {atk}\nDEF: {defense}\nENGY: {energy}"
        display_on_oled(stats)

        # Menerima data dari server
        try:
            data = client_socket.recv(1024)
            if data:
                decoded_data = data.decode().strip() #Mnerima sinyal atk
                custom_print(f"Received: {decoded_data}")
                rled_pin.value(1)
                time.sleep(0.02)
                rled_pin.value(0)

                if "Atk" in decoded_data:
                    try:
                        attack_received = int(decoded_data.split()[1])
                        if isblocking:
                            custom_print("Attack blocked!")
                        else:
                            damage = max((attack_received * (100 - defense)) // 100, 0)
                            hp -= damage
                            custom_print(f"HP Remaining: {hp}")
                            if hp <= 0:
                                robot_alive = False
                                rled_pin.value(1) # Mengatur status LED mera
                                custom_print("You're defeated!")
                                display_on_oled("You're defeated!")
                    except ValueError:
                        custom_print("Invalid attack data!")
        except OSError as e:
            if e.args[0] != 11:
                custom_print(f"Receive error: {e}")
                break

        # Periksa tombol BLOCK
        if block_pin.value() == 0:
            if energy > 0:
                isblocking = True
                energy -= 1  # Konsumsi energi saat tombol block ditekan
                custom_print(f"Blocking attack!")
            else:
                isblocking = False
                custom_print("Low Energy!")
        else:
            isblocking = False

        # Mengirim data ke server jika tombol atk ditekan dan tidak dalam mode blocking
        if not isblocking and atk_pin.value() == 0 and atk_button_released:
            if energy >= 10:  # Periksa apakah energi cukup
                if time.ticks_diff(time.ticks_ms(), atk_last_press) > 1000:
                    try:
                        message = f"Atk {atk}\n"
                        client_socket.sendall(message.encode())
                        custom_print("Attack sent!")
                        atk_last_press = time.ticks_ms()
                        atk_button_released = False
                        energy -= 10  # Kurangi energi setelah menyerang
                    except OSError as e:
                        custom_print(f"Send error: {e}")
            else:
                custom_print("Low energy!\nWait 5s.")

        # Memastikan tombol dilepaskan sebelum bisa mendeteksi penekanan berikutnya
        if atk_pin.value() == 1:
            atk_button_released = True

        time.sleep(0.1)

main()


