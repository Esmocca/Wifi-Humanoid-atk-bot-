import socket
import time
import machine
import network

# IP dan port server (ally)
host = "192.168.32.8"  # IP server (robot ally)
port = 50001  # Port server
allowed_client_ip = "192.168.32.2"  # Alamat IP client yang diizinkan

# Main stats robot
atk = 50  # Attack power
defense = 20  # Defense value
hp = 100  # Health points

# Konfigurasi tombol untuk attack
button_pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)

# Fungsi untuk menghubungkan ke Wi-Fi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect("OPPO A96", "Baksotanpatepung")  # Ganti SSID dan password jika perlu

    print("Menghubungkan ke Wi-Fi...")
    while not wlan.isconnected():
        time.sleep(1)
    print("Terhubung ke Wi-Fi!")
    print("Alamat IP:", wlan.ifconfig()[0])  # Menampilkan alamat IP perangkat

# Fungsi untuk menangani serangan dari enemy
def handle_attack(data):
    global hp
    if data.startswith("Atk"):
        attack_received = int(data.split()[1])
        damage = max(attack_received - defense, 0)  # Mengurangi damage dengan defense
        hp -= damage
        print(f"Serangan diterima! Damage: {damage}. HP tersisa: {hp}")
        
        if hp <= 0:
            print("Ally robot kalah! HP < 0")
            return False
    return True

# Fungsi utama untuk memeriksa tombol dan server secara bersamaan
def main():
    global hp

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
    last_button_state = 1
    debounce_time = 50  # dalam milidetik
    last_debounce_time = time.ticks_ms()

    while True:
        # Jika robot sudah kalah (HP <= 0), jangan terima sinyal apapun dari client
        if hp <= 0:
            print("Robot Ally defeated. Tidak menerima sinyal.")
            time.sleep(1)  # Jeda sejenak agar log terlihat
            continue  # Loop terus berjalan, tapi tidak menerima data atau mengirim

        # 1. Periksa status tombol
        current_button_state = button_pin.value()

        # Debouncing tombol
        if current_button_state != last_button_state:
            last_debounce_time = time.ticks_ms()

        if time.ticks_diff(time.ticks_ms(), last_debounce_time) > debounce_time:
            if current_button_state == 0:  # Tombol ditekan
                print("Tombol ATK ditekan!")
                if client_socket:  # Jika ada koneksi dengan client
                    try:
                        # Kirim serangan ke client jika tombol ditekan
                        attack_message = f"Atk {atk}".encode()  # Mengirimkan nilai attack
                        client_socket.sendall(attack_message)
                        print(f"Serangan dikirim: {atk}")
                    except Exception as e:
                        print(f"Error mengirim data ke client: {e}")
            else:
                print("Tombol tidak ditekan...")

        last_button_state = current_button_state

        # 2. Periksa koneksi server
        if client_socket is None:
            try:
                client_socket, client_address = server_socket.accept()
                print(f"Terhubung ke client {client_address}")

                # Periksa alamat IP client
                if client_address[0] != allowed_client_ip:
                    print(f"Koneksi ditolak. IP client {client_address[0]} tidak diizinkan.")
                    client_socket.close()
                    client_socket = None
                    continue  # Tunggu koneksi lain
                client_socket.setblocking(False)  # Non-blocking mode untuk client socket
            except:
                pass  # Tidak ada koneksi masuk

        # 3. Periksa data dari client
        if client_socket:
            try:
                data = client_socket.recv(1024).decode()  # Menerima data dari client
                if data:
                    print(f"Dari client: {data}")
                    
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
                pass  # Tidak ada data dari client

        # 4. Bersihkan koneksi jika client terputus
        if client_socket:
            try:
                # Kirim heartbeat untuk memastikan koneksi aktif
                client_socket.sendall(b"")
            except:
                print("Koneksi client terputus.")
                client_socket.close()
                client_socket = None

        time.sleep(0.1)  # Jeda untuk mengurangi penggunaan CPU

# Menjalankan program utama
main()