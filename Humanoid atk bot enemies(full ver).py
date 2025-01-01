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
print("Connecting to Wi-Fi...")
while not wlan.isconnected():
    time.sleep(1)

# Jika terhubung, tampilkan alamat IP
print("Connected to Wi-Fi!")
print("IP Address:", wlan.ifconfig()[0])

# IP dan port server (ally)
ally_ip = "192.168.32.8"  # IP server (robot ally)
port = 50001  # Port server

# Inisialisasi pin GPIO
atk_pin = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)  # Tombol ATK
block_pin = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)  # Tombol BLOCK
red_led = machine.Pin(25, machine.Pin.OUT)  # LED Merah (indikasi HP rendah/defeated)
yellow_led = machine.Pin(26, machine.Pin.OUT)  # LED Kuning (indikasi koneksi)
atk_led = machine.Pin(27, machine.Pin.OUT)  # LED ATK (indikasi pengiriman serangan)

# Main stats robot client
hp = 100  # Health points
atk = 50  # Attack power
defense = 20  # Defense value (in percentage)

# Fungsi untuk menghubungkan ke server (robot ally)
def connect_to_server():
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ally_ip, port))
        client_socket.setblocking(False)  # Non-blocking mode untuk socket
        print(f"Connected to server (ally) {ally_ip} on port {port}")
        yellow_led.on()  # Indikasi koneksi berhasil
        return client_socket
    except OSError as e:
        print(f"Error connecting to server: {e}")
        yellow_led.off()
        return None

# Fungsi untuk mengirimkan sinyal tombol dan serangan ke server (ally)
def send_signal_and_attack(client_socket):
    try:
        client_socket.sendall(b"Button pressed!\n")
        attack_message = f"Atk {atk}".encode()
        client_socket.sendall(attack_message)
        atk_led.on()  # LED ATK menyala saat berhasil mengirim sinyal
    except OSError as e:
        print(f"Error sending data to server: {e}")
        atk_led.off()  # LED ATK mati jika gagal mengirim sinyal

# Fungsi untuk menangani serangan yang diterima dari server
def handle_received_attack(data):
    global hp
    if block_pin.value() == 0:  # Jika tombol block ditekan
        print("Attack blocked! No damage taken.")
        return True

    if data.startswith("Atk"):
        attack_received = int(data.split()[1])
        damage = max((attack_received * (100 - defense)) // 100, 0)  # Mengurangi damage dengan defense percentage
        hp -= damage
        print(f"Attack received! Damage: {damage}. Remaining HP: {hp}")

        if hp <= 0:
            print("Robot defeated! HP < 0")
            red_led.on()  # LED merah menyala terus
            return False
        elif hp < 25:
            blink_red_led()  # Blink jika HP rendah
    return True

# Fungsi untuk blink LED merah jika HP rendah
def blink_red_led():
    for _ in range(3):
        red_led.on()
        time.sleep(0.3)
        red_led.off()
        time.sleep(0.3)

# Fungsi utama untuk mendeteksi tombol dan menjaga koneksi tetap hidup
def main_loop():
    client_socket = None
    robot_alive = True

    last_atk_state = 1
    last_block_state = 1
    debounce_time = 50  # dalam milidetik
    last_debounce_time = time.ticks_ms()

    yellow_led.off()  # Awalnya LED kuning mati
    atk_led.off()  # Awalnya LED ATK mati

    while True:
        # Jika tidak ada koneksi, coba sambungkan ke server
        if client_socket is None:
            client_socket = connect_to_server()

        # Periksa koneksi Wi-Fi
        if wlan.isconnected():
            yellow_led.on()  # Wi-Fi terkoneksi
        else:
            yellow_led.off()

        # Periksa status tombol ATK dan BLOCK
        current_atk_state = atk_pin.value()
        current_block_state = block_pin.value()

        if current_atk_state != last_atk_state:
            last_debounce_time = time.ticks_ms()

        if time.ticks_diff(time.ticks_ms(), last_debounce_time) > debounce_time:
            if current_atk_state == 0 and robot_alive:  # Tombol ATK ditekan
                print("Attack button pressed!")
                if client_socket:
                    send_signal_and_attack(client_socket)
            elif current_block_state == 0:  # Tombol BLOCK ditekan
                print("Block button pressed!")

        last_atk_state = current_atk_state
        last_block_state = current_block_state

        # Terima balasan dari server
        if client_socket and robot_alive:
            try:
                data = client_socket.recv(1024)
                if data:
                    print("From server:", data.decode())
                    if "Atk" in data.decode():
                        if not handle_received_attack(data.decode()):
                            robot_alive = False  # Robot mati, tetapi tetap terhubung
            except:
                pass  # Tidak ada data atau kesalahan

        time.sleep(0.1)

# Menjalankan loop utama
main_loop()
