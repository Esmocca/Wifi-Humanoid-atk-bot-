# Code server multi clients
import socket
import time
import network
import ssd1306
import _thread

# Konfigurasi Wi-Fi
ssid = "Alamak"
password = "ndaktaukoktanyasaya"

# Inisialisasi OLED
i2c = machine.I2C(0, scl=machine.Pin(21), sda=machine.Pin(20))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
oled.fill(0)
oled.show()
oled_lock = _thread.allocate_lock()

# Inisialisasi Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

# Fungsi menampilkan teks pada OLED
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

# Tunggu hingga terhubung ke Wi-Fi
custom_print("Connecting to\nWi-Fi...")
while not wlan.isconnected():
    time.sleep(0.1)

custom_print("Connected to\nWi-Fi!")
custom_print("IP Address:\n" + wlan.ifconfig()[0])

# Konfigurasi Server
host_ip = wlan.ifconfig()[0]
port = 50003

# Inisialisasi server
try:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host_ip, port))
    server_socket.listen(5)  # Maksimal 5 koneksi
    server_socket.setblocking(False)
    custom_print(f"Server ready:\nIP {host_ip}\nPort {port}")
except OSError as e:
    custom_print(f"Error starting\nserver: {e}")
    server_socket = None

clients = []  # Daftar klien yang terhubung

# Main loop
def mainloop():
    communication_started = False

    while True:
        # Terima koneksi baru
        try:
            client_socket, client_address = server_socket.accept()
            client_socket.setblocking(False)
            clients.append(client_socket)
            custom_print(f"Client {len(clients)}\nconnected")
        except OSError:
            pass  # Tidak ada koneksi baru, lanjutkan

        # Periksa jumlah klien untuk memulai komunikasi
        if len(clients) >= 2 and not communication_started:
            communication_started = True
            custom_print("Communication\nstarted!")

        # Komunikasi antar klien
        for client in clients[:]:  # Salin daftar untuk iterasi aman
            try:
                data = client.recv(1024)
                if data:
                    decoded_data = data.decode().strip()
                    custom_print(f"Received: {decoded_data}")

                    # Kirim data ke klien lain
                    for other_client in clients:
                        if other_client != client:
                            try:
                                other_client.sendall(data)
                            except Exception as e:
                                custom_print(f"Error sending:\n{e}")
                                clients.remove(other_client)

            except OSError as e:
                if e.args[0] == 11:  # Tidak ada data diterima (non-blocking socket)
                    continue
                else:
                    custom_print("Client disconnected")
                    clients.remove(client)

# Jalankan loop utama jika server berhasil diinisialisasi
if server_socket:
    mainloop()

