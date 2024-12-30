import socket
import machine
import time
import network

# Konfigurasi Wi-Fi
ssid = "OPPO A96"  # Nama Wi-Fi
password = "Baksotanpatepung"  # Password Wi-Fi

# Inisialisasi Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

# Tunggu hingga koneksi berhasil
print("Menghubungkan ke Wi-Fi...")
while not wlan.isconnected():
    time.sleep(1)

# Jika terhubung, tampilkan alamat IP
print("Terhubung ke Wi-Fi!")
print("Alamat IP:", wlan.ifconfig()[0])  # Menampilkan Alamat IP

# IP dan port server (ally)
ally_ip = "192.168.32.8"  # IP server (robot ally)
port = 50001  # Port server

# Inisialisasi pin GP14 sebagai input (tombol atk)
button_pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)

# Main stats robot client
hp = 100  # Health points
atk = 50  # Attack power
defense = 20  # Defense value

# Fungsi untuk menghubungkan ke server (robot ally)
def connect_to_server():
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ally_ip, port))
        client_socket.setblocking(False)  # Non-blocking mode untuk socket
        print(f"Terhubung ke server (ally) {ally_ip} pada port {port}")
        return client_socket
    except OSError as e:
        print(f"Kesalahan saat menghubungkan ke server: {e}")
        return None

# Fungsi untuk mengirimkan sinyal tombol dan serangan ke server (ally)
def send_signal_and_attack(client_socket):
    try:
        # Mengirim sinyal tombol ditekan
        client_socket.sendall(b"Tombol ditekan!\n")
        
        # Kirim sinyal serangan
        attack_message = f"Atk {atk}".encode()
        client_socket.sendall(attack_message)
        
        # Menerima balasan dari server (ally)
        data = client_socket.recv(1024)
        if data:
            print("Dari server:", data.decode())
            # Jika server mengirimkan serangan, update HP client
            if "Atk" in data.decode():
                handle_received_attack(data.decode())
    except OSError as e:
        print(f"Kesalahan saat mengirim data ke server: {e}")

# Fungsi untuk menangani serangan yang diterima dari server
def handle_received_attack(data):
    global hp
    if data.startswith("Atk"):
        # Parse nilai serangan dari server
        attack_received = int(data.split()[1])
        damage = max(attack_received - defense, 0)  # Mengurangi damage dengan defense
        hp -= damage
        print(f"Serangan diterima! Damage: {damage}. HP tersisa: {hp}")
        
        if hp <= 0:
            print("Robot client kalah! HP < 0")
            print("Robot enemy defeated!")
            print("Tidak menerima sinyal")
            return False  # Menghentikan penerimaan sinyal
    return True

# Fungsi utama untuk mendeteksi tombol dan menjaga koneksi tetap hidup
def main_loop():
    client_socket = None
    robot_alive = True  # Status untuk memeriksa apakah robot masih hidup

    # Status tombol untuk debouncing
    last_button_state = 1
    debounce_time = 50  # dalam milidetik
    last_debounce_time = time.ticks_ms()

    while True:
        # Jika HP kurang dari 0, robot dianggap kalah dan tidak menerima sinyal
        if hp <= 0:
            print("Robot enemy defeated!")
            print("Tidak menerima sinyal")
            robot_alive = False
            continue  # Lewati loop utama dan tidak menerima sinyal lagi

        # *1. Periksa status tombol*
        current_button_state = button_pin.value()

        # Debouncing tombol
        if current_button_state != last_button_state:
            last_debounce_time = time.ticks_ms()

        if time.ticks_diff(time.ticks_ms(), last_debounce_time) > debounce_time:
            if current_button_state == 0:  # Tombol ditekan
                print("Tombol ATK ditekan!")
                if client_socket is None:
                    # Koneksi pertama kali saat tombol ditekan
                    client_socket = connect_to_server()

                if client_socket:
                    send_signal_and_attack(client_socket)  # Kirim serangan ke ally
                time.sleep(0.5)  # Delay kecil agar tidak mengirim terlalu cepat
            else:
                print("Tombol tidak ditekan...")

        last_button_state = current_button_state

        # *2. Periksa koneksi client*
        if client_socket is None:
            # Jika tidak ada koneksi, coba untuk konek ke server
            client_socket = connect_to_server()

        # *3. Terima balasan dari server dan perbarui status*
        if client_socket and robot_alive:
            try:
                data = client_socket.recv(1024)
                if data:
                    print("Dari server:", data.decode())
                    # Jika server mengirimkan data selain "Atk"
                    if "Atk" in data.decode():
                        if not handle_received_attack(data.decode()):
                            break  # Keluar dari loop jika HP <= 0
            except:
                pass  # Tidak ada data atau kesalahan

        time.sleep(0.1)  # Jeda untuk mengurangi penggunaan CPU

# Menjalankan loop utama
main_loop()
