# Program robot type ally (server)
import socket
import time
import machine
import network

# IP dan port server (ally)
host = "192.168.32.8"  # IP server (robot ally)
port = 50001  # Port server
allowed_client_ip = "192.168.32.2"  # Alamat IP client yang diizinkan

# Main stats robot
atk = 30  # Attack power
defense = 20  # Defense value
hp = 100  # Health points
block_stun_value = defense * 3  # Threshold for stun

# Konfigurasi tombol untuk attack dan block
atk_pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)
block_pin = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)

# Konfigurasi LED
red_led = machine.Pin(16, machine.Pin.OUT)
yellow_led = machine.Pin(17, machine.Pin.OUT)
atk_led = machine.Pin(18, machine.Pin.OUT)

# State variables
is_stunned = False
stun_end_time = 0
block_active = False

# Fungsi untuk menghubungkan ke Wi-Fi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect("OPPO A96", "Baksotanpatepung")  # Ganti SSID dan password jika perlu

    print("Connecting to Wi-Fi...")
    while not wlan.isconnected():
        time.sleep(1)
    print("Connected to Wi-Fi!")
    yellow_led.value(1)  # Turn on yellow LED
    print("Robot IP:", wlan.ifconfig()[0])  # Display device IP address

# Fungsi untuk menangani serangan dari enemy
def handle_attack(data):
    global hp
    if data.startswith("Atk"):
        attack_received = int(data.split()[1])
        damage = max((attack_received *(100 - defense)) // 100, 0)  # Reduce damage by defense
        if block_active:
            print("Attack blocked! No damage taken.")
            return True
        hp -= damage
        print(f"Attack received! Damage from enemy: {damage}. Current HP: {hp}")

        if hp <= 0:
            print("Ally robot defeated! HP <= 0.")
            red_led.value(1)  # Turn on red LED permanently
            return False
    return True

# Fungsi utama untuk memeriksa tombol dan server secara bersamaan
def main():
    global hp, is_stunned, stun_end_time, block_active

    # Menghubungkan ke Wi-Fi
    connect_wifi()

    # Konfigurasi server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setblocking(False)  # Non-blocking mode untuk socket
    server_socket.bind((host, port))
    server_socket.listen(1)  # Maksimal 1 koneksi sekaligus

    print(f"Server listening on {host}:{port}")
    client_socket = None

    # Status tombol untuk debouncing
    last_atk_state = 1
    last_block_state = 1
    debounce_time = 50  # dalam milidetik
    last_debounce_time_atk = time.ticks_ms()
    last_debounce_time_block = time.ticks_ms()

    while True:
        # Jika robot sudah kalah (HP <= 0), tidak menerima sinyal serangan baru
        if hp <= 0:
            print("Robot Ally defeated. Not accepting signals.")
            time.sleep(1)  # Jeda sejenak agar log terlihat
            continue

        # Cek apakah robot dalam kondisi stun
        if is_stunned:
            if time.ticks_ms() > stun_end_time:
                is_stunned = False
                print("Stun ended. Robot is active again.")
            else:
                time.sleep(0.1)
                continue

        # 1. Periksa tombol attack (atk_pin)
        current_atk_state = atk_pin.value()
        if current_atk_state != last_atk_state:
            last_debounce_time_atk = time.ticks_ms()

        if time.ticks_diff(time.ticks_ms(), last_debounce_time_atk) > debounce_time:
            if current_atk_state == 0:  # Tombol attack ditekan
                print("Attack button pressed!")
                if client_socket:  # Jika ada koneksi dengan client
                    try:
                        # Kirim serangan ke client jika tombol ditekan
                        attack_message = f"Atk {atk}".encode()  # Mengirimkan nilai attack
                        client_socket.sendall(attack_message)
                        atk_led.value(1)  # Turn on attack LED
                        print(f"Attack sent: {atk}")
                    except Exception as e:
                        print(f"Error sending data to client: {e}")
                        atk_led.value(0)  # Turn off attack LED on error
            else:
                atk_led.value(0)  # Turn off attack LED if not attacking

        last_atk_state = current_atk_state

        # 2. Periksa tombol block (block_pin)
        current_block_state = block_pin.value()
        if current_block_state != last_block_state:
            last_debounce_time_block = time.ticks_ms()

        if time.ticks_diff(time.ticks_ms(), last_debounce_time_block) > debounce_time:
            if current_block_state == 0:  # Tombol block ditekan
                print("Block button pressed!")
                if not is_stunned:  # Hanya berfungsi jika robot tidak dalam kondisi stun
                    try:
                        print("Blocking enemy attack!")
                        block_active = True  # Activate block
                        time.sleep(0.2)  # Simulate block duration (optional)
                        block_active = False  # Deactivate block
                    except Exception as e:
                        print(f"Error while blocking: {e}")
                else:
                    print("Cannot block, robot is stunned!")

        last_block_state = current_block_state

        # 3. Periksa koneksi server
        if client_socket is None:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"Connected to client {client_address}")

                # Periksa alamat IP client
                if client_address[0] != allowed_client_ip:
                    print(f"Connection rejected. Client IP {client_address[0]} not allowed.")
                    client_socket.close()
                    client_socket = None
                    continue  # Wait for another connection
                client_socket.setblocking(False)  # Non-blocking mode untuk client socket
                yellow_led.value(0)  # Turn off steady yellow LED
                for _ in range(5):
                    yellow_led.value(1)
                    time.sleep(0.2)
                    yellow_led.value(0)
                    time.sleep(0.2)
            except:
                pass  # No incoming connection

        # 4. Periksa data dari client
        if client_socket:
            try:
                data = client_socket.recv(1024).decode()  # Menerima data dari client
                if data:
                    print(f"From client: {data}")

                    if data.startswith("Atk"):
                        # Handle attack message from client
                        if not handle_attack(data):
                            break  # Jika HP < 0, robot kalah, keluar dari loop
                    else:
                        # Kirim pesan balasan jika ada permintaan lain
                        response = f"Received: {data}".encode()
                        client_socket.sendall(response)

                    # Kirim balasan serangan (misalnya untuk memberi feedback tentang status)
                    response = f"HP: {hp}, Ready to fight!".encode()
                    client_socket.sendall(response)
            except:
                pass  # No data from client

        # 5. Bersihkan koneksi jika client terputus
        if client_socket:
            try:
                # Kirim heartbeat untuk memastikan koneksi aktif
                client_socket.sendall(b"")
            except:
                print("Client connection lost.")
                client_socket.close()
                client_socket = None

        time.sleep(0.1)  # Jeda untuk mengurangi penggunaan CPU

# Menjalankan program utama
main()
