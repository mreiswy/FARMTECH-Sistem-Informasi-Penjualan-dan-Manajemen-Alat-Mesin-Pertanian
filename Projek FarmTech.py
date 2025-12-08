import sys
from datetime import datetime, date
from datetime import timedelta
from getpass import getpass
import psycopg2
import os

try:
    from tabulate import tabulate
except Exception:
    def tabulate(x, headers=None, tablefmt=None):
        # fallback very simple
        out = ""
        if headers:
            out += " | ".join(headers) + "\n"
            out += "-" * 40 + "\n"
        for row in x:
            out += " | ".join(str(i) for i in row) + "\n"
        return out

try:
    import pyfiglet
    from termcolor import colored
    def show_banner():
        f = pyfiglet.Figlet(font="alligator")
        print(colored(f.renderText("F A R M T E C H"), "green"))
except Exception:
    def show_banner():
        print("\n=== FARMTECH ===\n")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# -------------------------
# Koneksi DB
# -------------------------
DB_HOST = "localhost"
DB_NAME = "FarmTechFix"
DB_USER = "postgres"
DB_PASS = "190727"
DB_PORT = 5432

def connect_db():
    try:
        conn = psycopg2.connect(host=DB_HOST,dbname=DB_NAME,user=DB_USER,password=DB_PASS,port=DB_PORT)
        print("Berhasil koneksi ke database.")
        return conn
    except Exception as e:
        print("Gagal koneksi ke database.", e)
        return None

# -------------------------
# Helpers
# -------------------------
def format_rp(x):
    try:
        return "Rp {:,}".format(int(x)).replace(",", ".")
    except:
        return str(x)

def input_int(prompt, default=None):
    s = input(prompt)
    if s.strip() == "" and default is not None:
        return default
    try:
        return int(s)
    except:
        return None

def pause():
    input("\nTekan Enter untuk kembali...")

# -------------------------
# Pengguna / User functions
# -------------------------
def fetch_user_with_role(cur, username, password):
    """
    Return dict {user_id, username, role_name, user_role_id}
    """
    cur.execute("""
        SELECT u.user_id, u.username, r.role_name, ur.user_role_id
        FROM users u
        JOIN user_role ur ON ur.user_id = u.user_id
        JOIN role r ON r.role_id = ur.role_id
        WHERE u.username = %s AND u.password = %s
    """, (username, password))
    row = cur.fetchone()
    if row:
        return {"user_id": row[0], "username": row[1], "role": row[2], "user_role_id": row[3]}
    return None

def get_pegawai_by_user_role(cur, user_role_id):
    cur.execute("""
        SELECT pegawai_id, nama FROM pegawai WHERE user_role_id = %s
    """, (user_role_id,))
    r = cur.fetchone()
    if r:
        return {"pegawai_id": r[0], "nama": r[1]}
    return None

# -------------------------
# Kelola Akun Owner
# -------------------------
def tampilkan_daftar_owner(cur):
    """
    Menampilkan daftar owner:
    ID | Username
    """
    cur.execute("""
        SELECT u.user_id, u.username
        FROM users u
        JOIN user_role ur ON ur.user_id = u.user_id
        JOIN role r ON r.role_id = ur.role_id
        WHERE r.role_name = 'Owner'
        ORDER BY u.user_id
    """)
    rows = cur.fetchall()
    if not rows:
        print("Belum ada akun owner.")
        return []
    print(tabulate(rows, headers=["ID", "Username"], tablefmt="grid"))
    return rows


def tambah_owner(conn, cur):
    """
    Tambah akun owner:
    - input username
    - input password
    - username tidak boleh duplikat
    - insert users + user_role (role Owner)
    """
    print("\n=== TAMBAH AKUN OWNER BARU ===")
    username = input("Username baru: ").strip()
    if not username:
        print("Username wajib.")
        return

    # cek duplikat username
    cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        print("Username sudah dipakai. Pilih username lain.")
        return

    password = getpass("Password: ").strip()
    if not password:
        print("Password wajib.")
        return

    # ambil role_id owner
    cur.execute("SELECT role_id FROM role WHERE role_name = 'Owner'")
    r = cur.fetchone()
    if not r:
        print("Role Owner tidak ditemukan di database!")
        return
    role_id_owner = r[0]

    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING user_id",
                    (username, password))
        user_id = cur.fetchone()[0]

        cur.execute("INSERT INTO user_role (user_id, role_id) VALUES (%s, %s)",
                    (user_id, role_id_owner))

        conn.commit()
        print(f"Akun owner berhasil ditambahkan! (user_id = {user_id})")
    except Exception as e:
        conn.rollback()
        print("Gagal menambah akun owner:", e)


def ubah_owner(conn, cur):
    """
    Ubah akun owner:
    - Username baru (kosong = tetap)
    - Password baru (kosong = tetap)
    """
    print("\n=== UBAH AKUN OWNER ===")
    rows = tampilkan_daftar_owner(cur)
    if not rows:
        return

    owner_id = input_int("Masukkan ID Owner yang akan diubah: ")
    if not owner_id:
        print("ID tidak valid.")
        return

    # Ambil data lama
    cur.execute("SELECT username, password FROM users WHERE user_id = %s", (owner_id,))
    row = cur.fetchone()
    if not row:
        print("Akun owner tidak ditemukan.")
        return
    
    username_lama, password_lama = row

    print("\nKosongkan input untuk mempertahankan nilai lama.")
    username_baru = input(f"Username baru ({username_lama}): ").strip()
    password_baru = getpass("Password baru (kosong = tetap): ").strip()

    # nilai tetap
    if username_baru == "":
        username_baru = username_lama

    # cek username jika berubah
    if username_baru != username_lama:
        cur.execute("SELECT 1 FROM users WHERE username = %s", (username_baru,))
        if cur.fetchone():
            print("Username baru sudah digunakan oleh akun lain. Pembaruan dibatalkan.")
            return

    try:
        # update users
        if password_baru.strip() == "":
            cur.execute("UPDATE users SET username = %s WHERE user_id = %s",
                        (username_baru, owner_id))
        else:
            cur.execute("UPDATE users SET username = %s, password = %s WHERE user_id = %s",
                        (username_baru, password_baru, owner_id))

        conn.commit()
        print("Akun owner berhasil diperbarui.")
    except Exception as e:
        conn.rollback()
        print("Gagal memperbarui akun owner:", e)


def hapus_owner(conn, cur, user):
    """
    Hapus akun owner:
    - Tidak boleh menghapus akun yang sedang login
    - Full delete: user_role -> users
    """
    print("\n=== HAPUS AKUN OWNER ===")
    rows = tampilkan_daftar_owner(cur)
    if not rows:
        return

    owner_id = input_int("Masukkan ID Owner yang akan dihapus: ")
    if not owner_id:
        print("ID tidak valid.")
        return

    if owner_id == user["user_id"]:
        print("Anda tidak dapat menghapus akun owner yang sedang digunakan!")
        return

    # ambil user_role_id
    cur.execute("""
        SELECT ur.user_role_id
        FROM user_role ur
        JOIN role r ON r.role_id = ur.role_id
        WHERE ur.user_id = %s AND r.role_name = 'Owner'
    """, (owner_id,))
    row = cur.fetchone()
    if not row:
        print("Akun owner tidak ditemukan.")
        return
    user_role_id = row[0]

    konfirm = input("Yakin ingin menghapus akun owner ini? (y/n): ").lower()
    if konfirm != "y":
        print("Dibatalkan.")
        return

    try:
        cur.execute("DELETE FROM user_role WHERE user_role_id = %s", (user_role_id,))
        cur.execute("DELETE FROM users WHERE user_id = %s", (owner_id,))
        conn.commit()
        print("Akun owner berhasil dihapus.")
    except Exception as e:
        conn.rollback()
        print("Gagal menghapus owner:", e)


def kelola_akun_owner(conn, cur, user):
    """
    Submenu Kelola Akun Owner
    """
    while True:
        clear_screen()
        show_banner()
        print("\n=== KELOLA AKUN OWNER ===")
        print("1. Lihat akun owner")
        print("2. Tambah owner")
        print("3. Ubah owner")
        print("4. Hapus owner")
        print("5. Kembali")
        pilih = input("Pilih: ").strip()
        clear_screen()
        if pilih == "1":
            tampilkan_daftar_owner(cur)
            pause()
        elif pilih == "2":
            tambah_owner(conn, cur)
            pause()
        elif pilih == "3":
            ubah_owner(conn, cur)
            pause()
        elif pilih == "4":
            hapus_owner(conn, cur, user)
            pause()
        elif pilih == "5":
            break
        else:
            print("Pilihan tidak valid.")
            pause()

# -------------------------
# Kelola Data Admin (Owner)
# -------------------------
def tampilkan_daftar_admin(cur):
    """
    Menampilkan daftar admin:
    ID | Nama | Username | No HP | Alamat
    """
    cur.execute("""
        SELECT p.pegawai_id, p.nama, u.username, p.no_hp, p.alamat
        FROM pegawai p
        JOIN user_role ur ON ur.user_role_id = p.user_role_id
        JOIN users u ON u.user_id = ur.user_id
        JOIN role r ON r.role_id = ur.role_id
        WHERE r.role_name = 'Admin'
        ORDER BY p.pegawai_id
    """)
    rows = cur.fetchall()
    if not rows:
        print("Belum ada admin terdaftar.")
        return []
    print(tabulate(rows, headers=["ID","Nama","Username","No HP","Alamat"], tablefmt="grid"))
    return rows

def tambah_admin(conn, cur):
    """
    Owner menambah admin:
    - input biodata wajib (nama, no_hp)
    - input username/password (username harus unik)
    - insert users -> user_role (Admin) -> pegawai
    """
    print("\n=== TAMBAH ADMIN BARU ===")
    nama = input("Nama admin: ").strip()
    alamat = input("Alamat: ").strip()
    no_hp = input("No HP: ").strip()

    if not nama:
        print("Nama wajib diisi.")
        return
    if not no_hp:
        print("No HP wajib diisi.")
        return

    username = input("Username (untuk login): ").strip()
    if not username:
        print("Username wajib.")
        return

    # cek duplikat username
    cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        print("Username sudah terpakai. Pilih username lain.")
        return

    password = getpass("Password: ").strip()
    if not password:
        print("Password wajib.")
        return

    # ambil role_id untuk Admin
    cur.execute("SELECT role_id FROM role WHERE role_name = 'Admin'")
    r = cur.fetchone()
    if not r:
        print("Role 'Admin' tidak ditemukan di tabel role. Hubungi developer.")
        return
    role_id_admin = r[0]

    # Lakukan insert dalam satu transaksi
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING user_id", (username, password))
        user_id = cur.fetchone()[0]

        cur.execute("INSERT INTO user_role (user_id, role_id) VALUES (%s, %s) RETURNING user_role_id", (user_id, role_id_admin))
        user_role_id = cur.fetchone()[0]

        cur.execute("INSERT INTO pegawai (user_role_id, nama, alamat, no_hp) VALUES (%s, %s, %s, %s) RETURNING pegawai_id",
                    (user_role_id, nama, alamat, no_hp))
        pegawai_id = cur.fetchone()[0]

        conn.commit()
        print(f"Admin berhasil ditambahkan (pegawai_id = {pegawai_id}, username = {username}).")
    except Exception as e:
        conn.rollback()
        print("Gagal menambah admin:", e)

def ubah_admin(conn, cur):
    """
    Ubah data admin:
    - input kosong = tetap nilai lama
    - jika username berubah: cek duplikat
    """
    print("\n=== UBAH DATA ADMIN ===")
    rows = tampilkan_daftar_admin(cur)
    if not rows:
        return

    pegawai_id = input_int("Masukkan ID Pegawai yang akan diubah: ")
    if not pegawai_id:
        print("ID tidak valid.")
        return

    # Ambil data lama
    cur.execute("""
        SELECT p.nama, p.alamat, p.no_hp, u.username, ur.user_role_id, u.user_id
        FROM pegawai p
        JOIN user_role ur ON ur.user_role_id = p.user_role_id
        JOIN users u ON u.user_id = ur.user_id
        JOIN role r ON r.role_id = ur.role_id
        WHERE p.pegawai_id = %s AND r.role_name = 'Admin'
    """, (pegawai_id,))
    old = cur.fetchone()
    if not old:
        print("Admin tidak ditemukan.")
        return

    nama_lama, alamat_lama, no_hp_lama, username_lama, user_role_id, user_id = old

    print("\nKosongkan input untuk mempertahankan nilai lama.")
    nama_baru = input(f"Nama ({nama_lama}): ").strip()
    alamat_baru = input(f"Alamat ({alamat_lama}): ").strip()
    no_hp_baru = input(f"No HP ({no_hp_lama}): ").strip()
    username_baru = input(f"Username ({username_lama}): ").strip()
    password_baru = getpass("Password baru (kosong = tetap): ").strip()

    # jika kosong, tetap nilai lama
    if nama_baru == "":
        nama_baru = nama_lama
    if alamat_baru == "":
        alamat_baru = alamat_lama
    if no_hp_baru == "":
        no_hp_baru = no_hp_lama
    if username_baru == "":
        username_baru = username_lama

    # cek username jika berubah
    if username_baru != username_lama:
        cur.execute("SELECT 1 FROM users WHERE username = %s", (username_baru,))
        if cur.fetchone():
            print("Username baru sudah digunakan oleh akun lain. Pembaruan dibatalkan.")
            return

    try:
        # update users (username +/- password)
        if username_baru != username_lama and password_baru != "":
            cur.execute("UPDATE users SET username = %s, password = %s WHERE user_id = %s",
                        (username_baru, password_baru, user_id))
        elif username_baru != username_lama:
            cur.execute("UPDATE users SET username = %s WHERE user_id = %s", (username_baru, user_id))
        elif password_baru != "":
            cur.execute("UPDATE users SET password = %s WHERE user_id = %s", (password_baru, user_id))

        # update pegawai (biodata)
        cur.execute("UPDATE pegawai SET nama = %s, alamat = %s, no_hp = %s WHERE pegawai_id = %s",
                    (nama_baru, alamat_baru, no_hp_baru, pegawai_id))

        conn.commit()
        print("Data admin berhasil diperbarui.")
    except Exception as e:
        conn.rollback()
        print("Gagal memperbarui data admin:", e)

def hapus_admin(conn, cur, user):
    """
    Hapus admin (full delete):
    - konfirmasi
    - urutan: hapus pegawai -> hapus user_role -> hapus users
    """
    print("\n=== HAPUS ADMIN ===")
    rows = tampilkan_daftar_admin(cur)
    if not rows:
        return

    pegawai_id = input_int("Masukkan ID Pegawai yang akan dihapus: ")
    if not pegawai_id:
        print("ID tidak valid.")
        return

    # ambil user_role_id dan user_id
    cur.execute("""
        SELECT ur.user_role_id, u.user_id
        FROM pegawai p
        JOIN user_role ur ON ur.user_role_id = p.user_role_id
        JOIN users u ON u.user_id = ur.user_id
        JOIN role r ON r.role_id = ur.role_id
        WHERE p.pegawai_id = %s AND r.role_name = 'Admin'
    """, (pegawai_id,))
    row = cur.fetchone()
    if not row:
        print("Admin tidak ditemukan.")
        return
    user_role_id, user_id = row

    # Proteksi: jangan hapus akun yang sedang login (biasanya owner, tapi safety)
    if user_id == user.get("user_id"):
        print("Anda tidak dapat menghapus akun yang sedang digunakan.")
        return

    konfirm = input(f"Yakin ingin menghapus admin dengan pegawai_id={pegawai_id}? (y/n): ").lower()
    if konfirm != "y":
        print("Hapus dibatalkan.")
        return

    try:
        cur.execute("DELETE FROM pegawai WHERE pegawai_id = %s", (pegawai_id,))
        cur.execute("DELETE FROM user_role WHERE user_role_id = %s", (user_role_id,))
        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        print("Admin berhasil dihapus.")
    except Exception as e:
        conn.rollback()
        print("Gagal menghapus admin:", e)

def kelola_data_admin(conn, cur, user):
    """
    Submenu Kelola Data Admin (dipanggil oleh owner)
    """
    while True:
        clear_screen()
        show_banner()
        print("\n=== KELOLA DATA ADMIN (OWNER) ===")
        print("1. Lihat daftar admin")
        print("2. Tambah admin")
        print("3. Ubah data admin")
        print("4. Hapus admin")
        print("5. Kembali")
        pilih = input("Pilih: ").strip()
        clear_screen()
        if pilih == "1":
            tampilkan_daftar_admin(cur)
            pause()
        elif pilih == "2":
            tambah_admin(conn, cur)
            pause()
        elif pilih == "3":
            ubah_admin(conn, cur)
            pause()
        elif pilih == "4":
            hapus_admin(conn, cur, user)
            pause()
        elif pilih == "5":
            clear_screen()
            break
        else:
            print("Pilihan tidak valid.")
            pause()

def tampilkan_data_diri(cur, user):
    """
    Menampilkan data admin yang sedang login.
    """
    cur.execute("""
        SELECT p.pegawai_id, p.nama, p.alamat, p.no_hp, u.username
        FROM pegawai p
        JOIN user_role ur ON ur.user_role_id = p.user_role_id
        JOIN users u ON u.user_id = ur.user_id
        JOIN role r ON r.role_id = ur.role_id
        WHERE u.user_id = %s AND r.role_name = 'Admin'
    """, (user["user_id"],))

    data = cur.fetchone()
    if not data:
        print("Data admin tidak ditemukan dalam tabel pegawai.")
        return None

    print(tabulate(
        [[data[0], data[1], data[2], data[3], data[4]]],
        headers=["Pegawai ID", "Nama", "Alamat", "No HP", "Username"],
        tablefmt="grid"
    ))
    return data

def ubah_biodata_admin(conn, cur, user):
    print("\n=== UBAH BIODATA DIRI ===")

    data = tampilkan_data_diri(cur, user)
    if not data:
        return

    pegawai_id, nama_lama, alamat_lama, no_hp_lama, _ = data

    print("\nKosongkan input jika ingin tetap menggunakan data lama.")
    nama_baru = input(f"Nama ({nama_lama}): ").strip()
    alamat_baru = input(f"Alamat ({alamat_lama}): ").strip()
    no_hp_baru = input(f"No HP ({no_hp_lama}): ").strip()

    if nama_baru == "":
        nama_baru = nama_lama
    if alamat_baru == "":
        alamat_baru = alamat_lama
    if no_hp_baru == "":
        no_hp_baru = no_hp_lama

    try:
        cur.execute("""
            UPDATE pegawai
            SET nama = %s, alamat = %s, no_hp = %s
            WHERE pegawai_id = %s
        """, (nama_baru, alamat_baru, no_hp_baru, pegawai_id))

        conn.commit()
        print("Biodata berhasil diperbarui.")
    except Exception as e:
        conn.rollback()
        print("Gagal memperbarui biodata:", e)

def ubah_username_admin(conn, cur, user):
    print("\n=== UBAH USERNAME ===")

    data = tampilkan_data_diri(cur, user)
    if not data:
        return

    username_lama = data[4]

    username_baru = input(f"Username baru ({username_lama}): ").strip()
    if username_baru == "":
        print("Tidak ada perubahan username.")
        return

    # cek apakah username sudah dipakai user lain
    cur.execute("SELECT 1 FROM users WHERE username = %s AND user_id != %s",
                (username_baru, user["user_id"]))
    if cur.fetchone():
        print("Username sudah digunakan oleh akun lain.")
        return

    try:
        cur.execute("UPDATE users SET username = %s WHERE user_id = %s",
                    (username_baru, user["user_id"]))
        conn.commit()
        print("Username berhasil diperbarui.")
    except Exception as e:
        conn.rollback()
        print("Gagal memperbarui username:", e)

def ubah_password_admin(conn, cur, user):
    print("\n=== UBAH PASSWORD ===")

    password_baru = getpass("Masukkan password baru: ").strip()
    if not password_baru:
        print("Password tidak boleh kosong.")
        return

    try:
        cur.execute("UPDATE users SET password = %s WHERE user_id = %s",
                    (password_baru, user["user_id"]))
        conn.commit()
        print("Password berhasil diperbarui.")
    except Exception as e:
        conn.rollback()
        print("Gagal memperbarui password:", e)

def kelola_data_diri_admin(conn, cur, user):
    while True:
        clear_screen()
        show_banner()
        print("\n=== MANAJEMEN DATA DIRI ADMIN ===")
        print("1. Lihat Data Diri")
        print("2. Ubah Biodata (Nama, Alamat, No HP)")
        print("3. Ubah Username")
        print("4. Ubah Password")
        print("5. Kembali")

        pilih = input("Pilih menu: ").strip()
        clear_screen()

        if pilih == "1":
            tampilkan_data_diri(cur, user)
            pause()

        elif pilih == "2":
            ubah_biodata_admin(conn, cur, user)
            pause()

        elif pilih == "3":
            ubah_username_admin(conn, cur, user)
            pause()

        elif pilih == "4":
            ubah_password_admin(conn, cur, user)
            pause()

        elif pilih == "5":
            break

        else:
            print("Pilihan tidak valid.")
            pause()

# -------------------------
# Kelola Data Pegawai (Kasir) - untuk Admin
# -------------------------
def tampilkan_daftar_kasir(cur):
    """
    Menampilkan daftar pegawai dengan role 'Kasir':
    ID | Nama | Username | No HP | Alamat
    """
    cur.execute("""
        SELECT p.pegawai_id, p.nama, u.username, p.no_hp, p.alamat
        FROM pegawai p
        JOIN user_role ur ON ur.user_role_id = p.user_role_id
        JOIN users u ON u.user_id = ur.user_id
        JOIN role r ON r.role_id = ur.role_id
        WHERE r.role_name = 'Kasir'
        ORDER BY p.pegawai_id
    """)
    rows = cur.fetchall()
    if not rows:
        print("Belum ada kasir terdaftar.")
        return []
    print(tabulate(rows, headers=["ID","Nama","Username","No HP","Alamat"], tablefmt="grid"))
    return rows

def tambah_kasir(conn, cur):
    """
    Admin menambah kasir:
    - nama wajib
    - no_hp wajib
    - username wajib & harus unik
    - password wajib
    - buat users -> user_role (Kasir) -> pegawai
    """
    print("\n=== TAMBAH KASIR BARU ===")
    nama = input("Nama kasir: ").strip()
    alamat = input("Alamat: ").strip()
    no_hp = input("No HP: ").strip()

    if not nama:
        print("Nama wajib diisi.")
        return
    if not no_hp:
        print("No HP wajib diisi.")
        return

    username = input("Username (untuk login): ").strip()
    if not username:
        print("Username wajib.")
        return

    # cek duplikat username
    cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        print("Username sudah terpakai. Pilih username lain.")
        return

    password = getpass("Password: ").strip()
    if not password:
        print("Password wajib.")
        return

    # ambil role_id untuk Kasir
    cur.execute("SELECT role_id FROM role WHERE role_name = 'Kasir'")
    r = cur.fetchone()
    if not r:
        print("Role 'Kasir' tidak ditemukan di tabel role. Hubungi developer.")
        return
    role_id_kasir = r[0]

    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING user_id", (username, password))
        user_id = cur.fetchone()[0]

        cur.execute("INSERT INTO user_role (user_id, role_id) VALUES (%s, %s) RETURNING user_role_id", (user_id, role_id_kasir))
        user_role_id = cur.fetchone()[0]

        cur.execute("INSERT INTO pegawai (user_role_id, nama, alamat, no_hp) VALUES (%s, %s, %s, %s) RETURNING pegawai_id",
                    (user_role_id, nama, alamat, no_hp))
        pegawai_id = cur.fetchone()[0]

        conn.commit()
        print(f"Kasir berhasil ditambahkan (pegawai_id = {pegawai_id}, username = {username}).")
    except Exception as e:
        conn.rollback()
        print("Gagal menambah kasir:", e)

def ubah_kasir(conn, cur):
    """
    Ubah data kasir:
    - input kosong = tetap nilai lama
    - admin boleh ubah username & password
    """
    print("\n=== UBAH DATA KASIR ===")
    rows = tampilkan_daftar_kasir(cur)
    if not rows:
        return

    pegawai_id = input_int("Masukkan ID Pegawai yang akan diubah: ")
    if not pegawai_id:
        print("ID tidak valid.")
        return

    # Ambil data lama
    cur.execute("""
        SELECT p.nama, p.alamat, p.no_hp, u.username, ur.user_role_id, u.user_id
        FROM pegawai p
        JOIN user_role ur ON ur.user_role_id = p.user_role_id
        JOIN users u ON u.user_id = ur.user_id
        JOIN role r ON r.role_id = ur.role_id
        WHERE p.pegawai_id = %s AND r.role_name = 'Kasir'
    """, (pegawai_id,))
    old = cur.fetchone()
    if not old:
        print("Kasir tidak ditemukan.")
        return

    nama_lama, alamat_lama, no_hp_lama, username_lama, user_role_id, user_id = old

    print("\nKosongkan input untuk mempertahankan nilai lama.")
    nama_baru = input(f"Nama ({nama_lama}): ").strip()
    alamat_baru = input(f"Alamat ({alamat_lama}): ").strip()
    no_hp_baru = input(f"No HP ({no_hp_lama}): ").strip()
    username_baru = input(f"Username ({username_lama}): ").strip()
    password_baru = getpass("Password baru (kosong = tetap): ").strip()

    # jika kosong, tetap nilai lama
    if nama_baru == "":
        nama_baru = nama_lama
    if alamat_baru == "":
        alamat_baru = alamat_lama
    if no_hp_baru == "":
        no_hp_baru = no_hp_lama
    if username_baru == "":
        username_baru = username_lama

    # cek username jika berubah (exclude current user_id)
    if username_baru != username_lama:
        cur.execute("SELECT 1 FROM users WHERE username = %s AND user_id != %s", (username_baru, user_id))
        if cur.fetchone():
            print("Username baru sudah digunakan oleh akun lain. Pembaruan dibatalkan.")
            return

    try:
        # update users (username +/- password)
        if username_baru != username_lama and password_baru != "":
            cur.execute("UPDATE users SET username = %s, password = %s WHERE user_id = %s",
                        (username_baru, password_baru, user_id))
        elif username_baru != username_lama:
            cur.execute("UPDATE users SET username = %s WHERE user_id = %s", (username_baru, user_id))
        elif password_baru != "":
            cur.execute("UPDATE users SET password = %s WHERE user_id = %s", (password_baru, user_id))

        # update pegawai (biodata)
        cur.execute("UPDATE pegawai SET nama = %s, alamat = %s, no_hp = %s WHERE pegawai_id = %s",
                    (nama_baru, alamat_baru, no_hp_baru, pegawai_id))

        conn.commit()
        print("Data kasir berhasil diperbarui.")
    except Exception as e:
        conn.rollback()
        print("Gagal memperbarui data kasir:", e)

def hapus_kasir(conn, cur, user):
    """
    Hapus kasir (full delete):
    - konfirmasi
    - urutan: hapus pegawai -> hapus user_role -> hapus users
    - tidak boleh hapus akun yang sedang login
    """
    print("\n=== HAPUS KASIR ===")
    rows = tampilkan_daftar_kasir(cur)
    if not rows:
        return

    pegawai_id = input_int("Masukkan ID Pegawai yang akan dihapus: ")
    if not pegawai_id:
        print("ID tidak valid.")
        return

    # ambil user_role_id dan user_id
    cur.execute("""
        SELECT ur.user_role_id, u.user_id
        FROM pegawai p
        JOIN user_role ur ON ur.user_role_id = p.user_role_id
        JOIN users u ON u.user_id = ur.user_id
        JOIN role r ON r.role_id = ur.role_id
        WHERE p.pegawai_id = %s AND r.role_name = 'Kasir'
    """, (pegawai_id,))
    row = cur.fetchone()
    if not row:
        print("Kasir tidak ditemukan.")
        return
    user_role_id, user_id = row

    # Proteksi: jangan hapus akun yang sedang login
    if user_id == user.get("user_id"):
        print("Anda tidak dapat menghapus akun yang sedang digunakan.")
        return

    konfirm = input(f"Yakin ingin menghapus kasir dengan pegawai_id={pegawai_id}? (y/n): ").lower()
    if konfirm != "y":
        print("Hapus dibatalkan.")
        return

    try:
        cur.execute("DELETE FROM pegawai WHERE pegawai_id = %s", (pegawai_id,))
        cur.execute("DELETE FROM user_role WHERE user_role_id = %s", (user_role_id,))
        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        print("Kasir berhasil dihapus.")
    except Exception as e:
        conn.rollback()
        print("Gagal menghapus kasir:", e)

def kelola_data_kasir(conn, cur, user):
    """
    Submenu Kelola Data Pegawai (Admin) - hanya untuk kasir management
    """
    while True:
        clear_screen()
        show_banner()
        print("\n=== KELOLA KASIR) ===")
        print("1. Lihat daftar kasir")
        print("2. Tambah kasir")
        print("3. Ubah kasir")
        print("4. Hapus kasir")
        print("5. Kembali")
        pilih = input("Pilih: ").strip()
        clear_screen()
        if pilih == "1":
            tampilkan_daftar_kasir(cur)
            pause()
        elif pilih == "2":
            tambah_kasir(conn, cur)
            pause()
        elif pilih == "3":
            ubah_kasir(conn, cur)
            pause()
        elif pilih == "4":
            hapus_kasir(conn, cur, user)
            pause()
        elif pilih == "5":
            break
        else:
            print("Pilihan tidak valid.")
            pause()


# -------------------------
# Kelola Data Teknisi
# -------------------------
def tampilkan_daftar_teknisi(cur):
    cur.execute("""
        SELECT teknisi_id, nama, no_hp
        FROM teknisi
        ORDER BY teknisi_id
    """)
    rows = cur.fetchall()

    if not rows:
        print("Belum ada teknisi terdaftar.")
        return []

    print(tabulate(rows, headers=["ID", "Nama", "No HP"], tablefmt="grid"))
    return rows

def tambah_teknisi(conn, cur):
    print("\n=== TAMBAH TEKNISI BARU ===")

    nama = input("Nama teknisi: ").strip()
    no_hp = input("No HP (opsional): ").strip()

    if not nama:
        print("Nama wajib diisi.")
        return

    try:
        cur.execute("""
            INSERT INTO teknisi (nama, no_hp)
            VALUES (%s, %s)
        """, (nama, no_hp))

        conn.commit()
        print("Teknisi berhasil ditambahkan.")
    except Exception as e:
        conn.rollback()
        print("Gagal menambahkan teknisi:", e)

def ubah_teknisi(conn, cur):
    print("\n=== UBAH DATA TEKNISI ===")
    rows = tampilkan_daftar_teknisi(cur)
    if not rows:
        return

    teknisi_id = input_int("Masukkan ID Teknisi yang akan diubah: ")
    if not teknisi_id:
        print("ID tidak valid.")
        return

    cur.execute("""
        SELECT nama, no_hp
        FROM teknisi
        WHERE teknisi_id = %s
    """, (teknisi_id,))
    old = cur.fetchone()

    if not old:
        print("Teknisi tidak ditemukan.")
        return

    nama_lama, no_hp_lama = old

    print("\nKosongkan input jika ingin mempertahankan nilai lama.")
    nama_baru = input(f"Nama ({nama_lama}): ").strip()
    no_hp_baru = input(f"No HP ({no_hp_lama}): ").strip()

    if nama_baru == "":
        nama_baru = nama_lama
    if no_hp_baru == "":
        no_hp_baru = no_hp_lama

    try:
        cur.execute("""
            UPDATE teknisi
            SET nama = %s, no_hp = %s
            WHERE teknisi_id = %s
        """, (nama_baru, no_hp_baru, teknisi_id))

        conn.commit()
        print("Data teknisi berhasil diperbarui.")
    except Exception as e:
        conn.rollback()
        print("Gagal memperbarui teknisi:", e)

def hapus_teknisi(conn, cur):
    print("\n=== HAPUS TEKNISI ===")
    rows = tampilkan_daftar_teknisi(cur)
    if not rows:
        return

    teknisi_id = input_int("Masukkan ID Teknisi yang akan dihapus: ")
    if not teknisi_id:
        print("ID tidak valid.")
        return

    # cek apakah teknisi sedang menangani servis yang masih proses
    cur.execute("""
        SELECT 1 FROM servis
        WHERE teknisi_id = %s AND status_servis = 'Proses'
    """, (teknisi_id,))
    if cur.fetchone():
        print("Tidak dapat menghapus teknisi yang masih memiliki servis berstatus PROSES.")
        return

    konfirm = input("Yakin ingin menghapus teknisi ini? (y/n): ").lower()
    if konfirm != "y":
        print("Dibatalkan.")
        return

    try:
        cur.execute("DELETE FROM teknisi WHERE teknisi_id = %s", (teknisi_id,))
        conn.commit()
        print("Teknisi berhasil dihapus.")
    except Exception as e:
        conn.rollback()
        print("Gagal menghapus teknisi:", e)

def kelola_teknisi(conn, cur, user):
    while True:
        clear_screen()
        show_banner()
        print("\n=== KELOLA DATA TEKNISI ===")
        print("1. Lihat daftar teknisi")
        print("2. Tambah teknisi")
        print("3. Ubah teknisi")
        print("4. Hapus teknisi")
        print("5. Kembali")

        pilih = input("Pilih: ").strip()
        clear_screen()

        if pilih == "1":
            tampilkan_daftar_teknisi(cur)
            pause()

        elif pilih == "2":
            tambah_teknisi(conn, cur)
            pause()

        elif pilih == "3":
            ubah_teknisi(conn, cur)
            pause()

        elif pilih == "4":
            hapus_teknisi(conn, cur)
            pause()

        elif pilih == "5":
            break

        else:
            print("Pilihan tidak valid.")
            pause()

# -------------------------
#Manajemen produk
# -------------------------
def list_produk(cur):
    cur.execute("SELECT produk_id, nama_produk, kategori, harga, stok FROM produk ORDER BY produk_id")
    rows = cur.fetchall()
    print(tabulate([[r[0], r[1], r[2], format_rp(r[3]), r[4]] for r in rows],
                   headers=["ID","Nama","Kategori","Harga","Stok"], tablefmt="grid"))
    return rows

def tambah_produk(conn, cur):
    print("\n=== TAMBAH PRODUK BARU ===")

    nama = input("Nama produk: ").strip()
    kategori = input("Kategori: ").strip()
    harga = input_int("Harga jual: ")
    stok = input_int("Stok awal: ")
    harga_beli = input_int("Harga beli: ")

    if not nama:
        print("Nama produk wajib diisi.")
        return
    if harga is None or harga <= 0:
        print("Harga tidak valid.")
        return
    if stok is None or stok < 0:
        print("Stok tidak valid.")
        return
    if harga_beli is None or harga_beli <= 0:
        print("Harga beli tidak valid.")
        return
    if harga < harga_beli:
        print("Harga jual tidak boleh lebih rendah dari harga beli!")
        return

    # Pilih supplier
    print("\nPilih Supplier:")
    list_supplier(cur)
    supplier_id = input_int("Supplier ID: ")
    if not supplier_id:
        print("Supplier tidak valid.")
        return

    # Validasi supplier
    cur.execute("SELECT supplier_id FROM supplier WHERE supplier_id = %s", (supplier_id,))
    if not cur.fetchone():
        print("Supplier tidak ditemukan.")
        return

    try:
        cur.execute("""
            INSERT INTO produk (supplier_id, nama_produk, kategori, harga, harga_beli, stok, tanggal_input)
VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE)
        """, (supplier_id, nama, kategori, harga, harga_beli, stok))

        conn.commit()
        print("Produk berhasil ditambahkan.")
    except Exception as e:
        conn.rollback()
        print("Gagal menambah produk:", e)

def ubah_produk(conn, cur):
    print("\n=== UBAH PRODUK ===")

    rows = list_produk(cur)
    if not rows:
        return

    produk_id = input_int("Masukkan ID Produk yang akan diubah: ")
    if not produk_id:
        print("ID tidak valid.")
        return

    # Ambil data lama termasuk harga_beli
    cur.execute("""
        SELECT nama_produk, kategori, harga, harga_beli, stok, supplier_id
        FROM produk
        WHERE produk_id = %s
    """, (produk_id,))
    old = cur.fetchone()

    if not old:
        print("Produk tidak ditemukan.")
        return

    nama_lama, kategori_lama, harga_lama, harga_beli_lama, stok_lama, supplier_lama = old

    print("\nKosongkan jika ingin tetap.")
    nama_baru = input(f"Nama ({nama_lama}): ").strip()
    kategori_baru = input(f"Kategori ({kategori_lama}): ").strip()

    harga_baru = input_int(f"Harga jual ({harga_lama}): ", default=harga_lama)
    harga_beli_baru = input_int(f"Harga beli ({harga_beli_lama}): ", default=harga_beli_lama)
    stok_baru = input_int(f"Stok ({stok_lama}): ", default=stok_lama)

    # === Validasi harga wajib bernilai positif ===
    if harga_baru is None or harga_baru <= 0:
        print("Harga jual tidak valid.")
        return

    if harga_beli_baru is None or harga_beli_baru <= 0:
        print("Harga beli tidak valid.")
        return
    
    if harga_baru < harga_beli_baru:
        print("Harga jual tidak boleh lebih rendah dari harga beli!")
        return

    if stok_baru is None or stok_baru < 0:
        print("Stok tidak valid.")
        return

    # Supplier tetap atau ganti?
    print("\nSupplier sekarang:", supplier_lama)
    ganti = input("Ganti supplier? (y/n): ").lower()

    if ganti == "y":
        list_supplier(cur)
        supplier_baru = input_int("Supplier ID baru: ")
        cur.execute("SELECT supplier_id FROM supplier WHERE supplier_id = %s", (supplier_baru,))
        if not cur.fetchone():
            print("Supplier tidak ditemukan. Update dibatalkan.")
            return
    else:
        supplier_baru = supplier_lama

    # Kosong = tetap
    if nama_baru == "":
        nama_baru = nama_lama
    if kategori_baru == "":
        kategori_baru = kategori_lama

    try:
        cur.execute("""
            UPDATE produk
            SET nama_produk = %s,
                kategori = %s,
                harga = %s,
                harga_beli = %s,
                stok = %s,
                supplier_id = %s
            WHERE produk_id = %s
        """, (nama_baru, kategori_baru, harga_baru, harga_beli_baru, stok_baru, supplier_baru, produk_id))

        conn.commit()
        print("Produk berhasil diperbarui.")
    except Exception as e:
        conn.rollback()
        print("Gagal memperbarui produk:", e)

def hapus_produk(conn, cur):
    print("\n=== HAPUS PRODUK ===")

    rows = list_produk(cur)
    if not rows:
        return

    produk_id = input_int("Masukkan ID Produk: ")
    if not produk_id:
        print("ID tidak valid.")
        return

    # Cek apakah pernah digunakan transaksi
    cur.execute("SELECT 1 FROM detail_penjualan WHERE produk_id = %s", (produk_id,))
    if cur.fetchone():
        print("Tidak bisa menghapus produk yang sudah pernah dijual.")
        return

    cur.execute("SELECT 1 FROM detail_pembelian WHERE produk_id = %s", (produk_id,))
    if cur.fetchone():
        print("Tidak bisa menghapus produk yang sudah pernah dibeli.")
        return

    cur.execute("SELECT 1 FROM barang_tidak_laku WHERE produk_id = %s", (produk_id,))
    if cur.fetchone():
        print("Tidak bisa menghapus produk yang terdaftar sebagai barang tidak laku.")
        return

    konfirm = input("Yakin ingin menghapus produk ini? (y/n): ").lower()
    if konfirm != "y":
        print("Dibatalkan.")
        return

    try:
        cur.execute("DELETE FROM produk WHERE produk_id = %s", (produk_id,))
        conn.commit()
        print("Produk berhasil dihapus.")
    except Exception as e:
        conn.rollback()
        print("Gagal menghapus produk:", e)

def kelola_produk(conn, cur, user):
    while True:
        clear_screen()
        show_banner()
        print("\n=== MANAJEMEN PRODUK ===")
        print("1. Lihat produk")
        print("2. Tambah produk")
        print("3. Ubah produk")
        print("4. Hapus produk")
        print("5. Kembali")

        pilih = input("Pilih: ").strip()
        clear_screen()

        if pilih == "1":
            list_produk(cur)
            pause()

        elif pilih == "2":
            tambah_produk(conn, cur)
            pause()

        elif pilih == "3":
            ubah_produk(conn, cur)
            pause()

        elif pilih == "4":
            hapus_produk(conn, cur)
            pause()

        elif pilih == "5":
            break

        else:
            print("Pilihan tidak valid.")
            pause()

#--------------------------
#Manajemen Supplier
#--------------------------
def list_supplier(cur):
    cur.execute("SELECT supplier_id, nama_supplier, alamat, no_hp FROM supplier ORDER BY supplier_id")
    rows = cur.fetchall()
    print(tabulate(rows, headers=["ID","Supplier","Alamat","No HP"], tablefmt="grid"))
    return rows

def tambah_supplier(conn, cur):
    print("\n=== TAMBAH SUPPLIER BARU ===")

    nama = input("Nama Supplier: ").strip()
    alamat = input("Alamat: ").strip()
    no_hp = input("No HP: ").strip()

    if not nama:
        print("Nama supplier wajib diisi.")
        return

    try:
        cur.execute("""
            INSERT INTO supplier (nama_supplier, alamat, no_hp)
            VALUES (%s, %s, %s)
        """, (nama, alamat, no_hp))

        conn.commit()
        print("Supplier berhasil ditambahkan.")
    except Exception as e:
        conn.rollback()
        print("Gagal menambah supplier:", e)

def ubah_supplier(conn, cur):
    print("\n=== UBAH DATA SUPPLIER ===")

    rows = list_supplier(cur)
    if not rows:
        return

    supplier_id = input_int("Masukkan ID Supplier yang akan diubah: ")
    if not supplier_id:
        print("ID tidak valid.")
        return

    cur.execute("""
        SELECT nama_supplier, alamat, no_hp
        FROM supplier
        WHERE supplier_id = %s
    """, (supplier_id,))
    old = cur.fetchone()

    if not old:
        print("Supplier tidak ditemukan.")
        return

    nama_lama, alamat_lama, no_hp_lama = old

    print("\nKosongkan jika ingin tetap.")
    nama_baru = input(f"Nama ({nama_lama}): ").strip()
    alamat_baru = input(f"Alamat ({alamat_lama}): ").strip()
    no_hp_baru = input(f"No HP ({no_hp_lama}): ").strip()

    if nama_baru == "":
        nama_baru = nama_lama
    if alamat_baru == "":
        alamat_baru = alamat_lama
    if no_hp_baru == "":
        no_hp_baru = no_hp_lama

    try:
        cur.execute("""
            UPDATE supplier
            SET nama_supplier = %s,
                alamat = %s,
                no_hp = %s
            WHERE supplier_id = %s
        """, (nama_baru, alamat_baru, no_hp_baru, supplier_id))

        conn.commit()
        print("Data supplier berhasil diperbarui.")
    except Exception as e:
        conn.rollback()
        print("Gagal memperbarui supplier:", e)

def hapus_supplier(conn, cur):
    print("\n=== HAPUS SUPPLIER ===")

    rows = list_supplier(cur)
    if not rows:
        return

    supplier_id = input_int("Masukkan ID Supplier: ")
    if not supplier_id:
        print("ID tidak valid.")
        return

    # Cek apakah supplier digunakan di produk
    cur.execute("SELECT 1 FROM produk WHERE supplier_id = %s", (supplier_id,))
    if cur.fetchone():
        print("Tidak bisa menghapus supplier karena masih digunakan di tabel produk.")
        return

    # Cek apakah supplier digunakan di pembelian
    cur.execute("SELECT 1 FROM pembelian WHERE supplier_id = %s", (supplier_id,))
    if cur.fetchone():
        print("Tidak bisa menghapus supplier karena sudah pernah dipakai transaksi pembelian.")
        return

    konfirm = input("Yakin ingin menghapus supplier ini? (y/n): ").lower()
    if konfirm != "y":
        print("Dibatalkan.")
        return

    try:
        cur.execute("DELETE FROM supplier WHERE supplier_id = %s", (supplier_id,))
        conn.commit()
        print("Supplier berhasil dihapus.")
    except Exception as e:
        conn.rollback()
        print("Gagal menghapus supplier:", e)

def kelola_supplier(conn, cur):
    while True:
        clear_screen()
        show_banner()
        print("\n=== KELOLA SUPPLIER ===")
        print("1. Lihat daftar supplier")
        print("2. Tambah supplier")
        print("3. Ubah supplier")
        print("4. Hapus supplier")
        print("5. Kembali")

        pilih = input("Pilih: ").strip()
        clear_screen()

        if pilih == "1":
            list_supplier(cur)
            pause()

        elif pilih == "2":
            tambah_supplier(conn, cur)
            pause()

        elif pilih == "3":
            ubah_supplier(conn, cur)
            pause()

        elif pilih == "4":
            hapus_supplier(conn, cur)
            pause()

        elif pilih == "5":
            break

        else:
            print("Pilihan tidak valid.")
            pause()

# -------------------------
# Member
# -------------------------
def add_member(conn, cur):
    print("\n=== DAFTAR MEMBER BARU ===")
    nama = input("Nama: ").strip()
    no_hp = input("No HP: ").strip()
    alamat = input("Alamat: ").strip()
    if not nama:
        print("Nama wajib.")
        return None
    cur.execute("""
        INSERT INTO member (nama, no_hp, alamat, total_transaksi)
        VALUES (%s,%s,%s,0) RETURNING member_id
    """, (nama, no_hp, alamat))
    member_id = cur.fetchone()[0]
    conn.commit()
    print(f"Member tersimpan. ID = {member_id}")
    return member_id

def find_member_by_phone(cur, phone):
    cur.execute("SELECT member_id, nama, total_transaksi FROM member WHERE no_hp = %s", (phone,))
    return cur.fetchone()

def increment_member_tx(conn, cur, member_id):
    cur.execute("UPDATE member SET total_transaksi = total_transaksi + 1 WHERE member_id = %s", (member_id,))
    conn.commit()



# -------------------------
# Penjualan
# -------------------------
def get_produk(cur, produk_id):
    cur.execute("SELECT produk_id, nama_produk, harga, stok FROM produk WHERE produk_id = %s", (produk_id,))
    return cur.fetchone()

PPN_RATE = 0.12
def transaksi_penjualan(conn, cur, pegawai):
    print("\n=== TRANSAKSI PENJUALAN ===")

    # --- CEK MEMBER ---
    member_id = None
    if input("Pelanggan member? (y/n): ").lower() == "y":
        phone = input("No HP member: ").strip()
        m = find_member_by_phone(cur, phone)
        if m:
            member_id = m[0]
            print(f"Member: {m[1]} (total tx: {m[2]})")
        else:
            if input("Member tidak ditemukan. Daftar sekarang? (y/n): ").lower() == "y":
                member_id = add_member(conn, cur)

    # --- KERANJANG ---
    cart = []
    while True:
        list_produk(cur)
        pid = input_int("Masukkan ID produk (enter untuk selesai): ")
        if pid is None:
            break

        prod = get_produk(cur, pid)   # (id, nama, harga, stok)
        if not prod:
            print("Produk tidak ditemukan.")
            continue

        qty = input_int("Jumlah: ")
        if qty is None or qty <= 0:
            print("Jumlah tidak valid.")
            continue

        if prod[3] < qty:
            print(f"Stok tidak cukup (stok: {prod[3]}).")
            continue

        # --- CEK DISKON BARANG TIDAK LAKU ---
        cur.execute("""
            SELECT diskon_otomatis 
            FROM barang_tidak_laku 
            WHERE produk_id = %s
        """, (prod[0],))
        d = cur.fetchone()

        harga_asli = prod[2]

        if d:
            diskon_persen = d[0]
            harga_setelah_diskon = int(harga_asli * (1 - (diskon_persen / 100)))
            print(
                f"Produk ini termasuk TIDAK LAKU (diskon {diskon_persen}%). "
                f"Harga: {format_rp(harga_asli)} → {format_rp(harga_setelah_diskon)}"
            )
            harga_dipakai = harga_setelah_diskon
        else:
            harga_dipakai = harga_asli

        # Masukkan ke keranjang
        cart.append({
            "produk_id": prod[0],
            "nama": prod[1],
            "harga": harga_dipakai,
            "qty": qty,
            "harga_asli": harga_asli
        })

        if input("Tambah produk lain? (y/n): ").lower() != "y":
            break

    if not cart:
        print("Transaksi dibatalkan (keranjang kosong).")
        return

    # --- TAMPILKAN KERANJANG ---
    table = []
    subtotal = 0
    for it in cart:
        sub = it["harga"] * it["qty"]
        subtotal += sub
        table.append([
            it["produk_id"],
            it["nama"],
            format_rp(it["harga"]),
            it["qty"],
            format_rp(sub)
        ])

    print(tabulate(table, headers=["ID", "Produk", "Harga", "Qty", "Subtotal"], tablefmt="grid"))

    # --- HITUNG PPN ---
    ppn = int(subtotal * PPN_RATE)

    # --- DISKON MEMBER (tiap kelipatan 10 transaksi) ---
    diskon_rate = 0.0
    if member_id:
        cur.execute("SELECT total_transaksi FROM member WHERE member_id = %s", (member_id,))
        tt = cur.fetchone()[0] or 0
        if tt > 0 and tt % 10 == 0:
            diskon_rate = 0.10

    diskon_member = int(subtotal * diskon_rate)

    total = subtotal + ppn - diskon_member

    print(f"\nSubtotal: {format_rp(subtotal)}")
    print(f"PPN (12%): {format_rp(ppn)}")
    print(f"Diskon member: {format_rp(diskon_member)}")
    print(f"TOTAL: {format_rp(total)}")

    if input("Simpan transaksi? (y/n): ").lower() != "y":
        print("Transaksi dibatalkan.")
        return

    # --- SIMPAN HEADER TRANSAKSI ---
    cur.execute("""
        INSERT INTO penjualan 
        (kasir_id, member_id, tanggal_transaksi, subtotal, ppn, diskon, total_harga)
        VALUES (%s,%s,NOW(),%s,%s,%s,%s)
        RETURNING penjualan_id
    """, (pegawai["pegawai_id"], member_id, subtotal, ppn, diskon_member, total))
    penjualan_id = cur.fetchone()[0]

    # --- SIMPAN DETAIL + UPDATE STOK ---
    for it in cart:
        cur.execute("""
            INSERT INTO detail_penjualan (penjualan_id, produk_id, qty, harga_saat_penjualan)
            VALUES (%s,%s,%s,%s)
        """, (penjualan_id, it["produk_id"], it["qty"], it["harga"]))

        cur.execute(
            "UPDATE produk SET stok = stok - %s WHERE produk_id = %s",
            (it["qty"], it["produk_id"])
        )

        # --- PRODUK TIDAK LAKU TERJUAL → HAPUS DARI TABEL ---
        cur.execute(
            "DELETE FROM barang_tidak_laku WHERE produk_id = %s",
            (it["produk_id"],)
        )

    # Update total transaksi member
    if member_id:
        increment_member_tx(conn, cur, member_id)

    conn.commit()
    print(f"Transaksi tersimpan (ID = {penjualan_id}).")

# -------------------------
# Pembelian / Restock
# -------------------------
def restock_pembelian(conn, cur):
    print("\n=== RESTOCK / PEMBELIAN ===")
    list_supplier(cur)
    sid = input_int("Pilih supplier ID: ")
    if sid is None:
        print("Batal.")
        return

    # Validasi supplier
    cur.execute("SELECT supplier_id FROM supplier WHERE supplier_id = %s", (sid,))
    if cur.fetchone() is None:
        print("Supplier tidak ditemukan.")
        return

    items = []

    while True:
        list_produk(cur)
        pid = input_int("ID produk (enter batal): ")
        if pid is None:
            break

        # Ambil data produk
        cur.execute("SELECT produk_id, nama_produk, harga, harga_beli FROM produk WHERE produk_id = %s", (pid,))
        p = cur.fetchone()
        if not p:
            print("Produk tidak ada.")
            continue

        produk_id, nama_produk, harga_jual, harga_beli_lama = p

        qty = input_int("Jumlah beli: ")
        if qty is None or qty <= 0:
            print("Jumlah tidak valid.")
            continue

        # Input harga beli baru
        harga_beli_baru = input_int(f"Harga beli per unit (default {harga_beli_lama}): ", default=harga_beli_lama)

        # Validasi harga jual >= harga beli
        # Harga beli wajib positif
        if harga_beli_baru is None or harga_beli_baru <= 0:
            print("Harga beli tidak valid.")
            continue

        # Jika harga beli lebih tinggi dari harga jual → bukan batal, tapi pembeli harus menaikkan harga jual
        if harga_beli_baru > harga_jual:
            print("\n Harga beli BARU lebih tinggi dari harga jual saat ini!")
            print(f"- Harga jual saat ini : {harga_jual}")
            print(f"- Harga beli baru    : {harga_beli_baru}")

            konfirm = input("Naikkan harga jual agar tidak rugi? (y/n): ").lower()
            if konfirm == "y":
                harga_jual_baru = input_int("Masukkan harga jual baru: ")
                if harga_jual_baru is None or harga_jual_baru <= 0:
                    print("Harga jual tidak valid. Item dibatalkan.")
                    continue

                if harga_jual_baru < harga_beli_baru:
                    print("Harga jual tidak boleh lebih rendah dari harga beli! Item dibatalkan.")
                    continue

                # Update harga jual produk
                cur.execute("""
                    UPDATE produk 
                    SET harga = %s
                    WHERE produk_id = %s
                    """, (harga_jual_baru, produk_id))

                harga_jual = harga_jual_baru  # update variabel untuk dipakai
            else:
                print("Item dibatalkan.")
                continue

        # Simpan ke data keranjang pembelian
        items.append((pid, qty, harga_beli_baru))

        if input("Tambah barang lagi? (y/n): ").lower() != "y":
            break

    if not items:
        print("Tidak ada item. Batal.")
        return

    # Hitung total pembelian
    total = sum(q * h for (_, q, h) in items)

    #  Insert header pembelian
    cur.execute("""
        INSERT INTO pembelian (supplier_id, tanggal_pembelian, total_pembelian)
        VALUES (%s, NOW(), %s) RETURNING pembelian_id
    """, (sid, total))
    pembelian_id = cur.fetchone()[0]

    # insert per item + update stok + update harga beli produk
    for pid, qty, harga_beli_baru in items:

        # detail pembelian
        cur.execute("""
            INSERT INTO detail_pembelian (pembelian_id, produk_id, qty, harga_beli)
            VALUES (%s, %s, %s, %s)
        """, (pembelian_id, pid, qty, harga_beli_baru))

        # update stok
        cur.execute("""
            UPDATE produk 
            SET stok = stok + %s,
                harga_beli = %s   -- update harga beli terbaru
            WHERE produk_id = %s
        """, (qty, harga_beli_baru, pid))

    conn.commit()

    print(f"Pembelian tersimpan (ID = {pembelian_id}), Total = {format_rp(total)}")

# -------------------------
# Servis
# -------------------------
def list_servis_belum_selesai(cur):
    """
    Menampilkan daftar servis yang masih PROSES atau SELESAI (belum diambil).
    """
    cur.execute("""
        SELECT 
            s.servis_id,
            COALESCE(m.nama, '-'),
            s.nama_alat,
            t.nama AS teknisi,
            s.status_servis,
            s.tanggal_masuk
        FROM servis s
        LEFT JOIN member m ON m.member_id = s.member_id
        LEFT JOIN teknisi t ON t.teknisi_id = s.teknisi_id
        WHERE s.status_servis IN ('Proses', 'Selesai')
        ORDER BY s.servis_id;
    """)

    rows = cur.fetchall()

    if not rows:
        print("Tidak ada servis yang masih PROSES atau SELESAI.")
        return []

    tabel = []
    for r in rows:
        tabel.append([
            r[0],                      # ID servis
            r[1],                      # Nama member
            r[2],                      # Nama alat
            r[3],                      # Teknisi
            r[4],                      # Status
            r[5].strftime("%d-%m-%Y")  # Tanggal masuk
        ])

    print("\n=== DAFTAR SERVIS BELUM SELESAI ===")
    print(tabulate(
        tabel,
        headers=["ID", "Member", "Alat", "Teknisi", "Status", "Tgl Masuk"],
        tablefmt="grid"
    ))

    return rows

def input_servis(conn, cur, pegawai):
    print("\n=== INPUT SERVIS BARU ===")

    # --- Member ---
    member_id = None
    if input("Pelanggan member? (y/n): ").lower() == "y":
        phone = input("No HP member: ").strip()
        m = find_member_by_phone(cur, phone)
        if m:
            member_id = m[0]
            print(f"Member: {m[1]} (Total transaksi: {m[2]})")
        else:
            if input("Member tidak ditemukan. Daftar baru? (y/n): ").lower() == "y":
                member_id = add_member(conn, cur)

    # --- Pilih Teknisi ---
    cur.execute("SELECT teknisi_id, nama, no_hp FROM teknisi ORDER BY teknisi_id")
    techs = cur.fetchall()
    if not techs:
        print("Belum ada teknisi terdaftar. Hubungi admin.")
        return

    print(tabulate(techs, headers=["ID", "Nama", "No HP"], tablefmt="grid"))
    teknisi_id = input_int("Pilih ID teknisi: ")
    if not teknisi_id:
        print("Teknisi tidak valid.")
        return

    # --- Detail Servis ---
    nama_alat = input("Nama alat/mesin: ").strip()
    keluhan = input("Keluhan kerusakan: ").strip()

    # biaya_servis = NULL dulu, status = PROSES
    cur.execute("""
        INSERT INTO servis (
            member_id, kasir_id, teknisi_id, nama_alat, keluhan,
            biaya_servis, status_servis, tanggal_masuk
        )
        VALUES (%s, %s, %s, %s, %s, NULL, 'Proses', NOW())
        RETURNING servis_id
    """, (member_id, pegawai["pegawai_id"], teknisi_id, nama_alat, keluhan))

    servis_id = cur.fetchone()[0]
    conn.commit()

    print(f"Servis berhasil didaftarkan. ID = {servis_id}. Status = PROSES")

def update_status_servis(conn, cur):
    print("\n=== UPDATE STATUS SERVIS ===")

    # Tampilkan dahulu daftar servis yang bisa diupdate
    rows = list_servis_belum_selesai(cur)
    if not rows:
        return

    # Input ID servis
    servis_id = input_int("\nMasukkan ID Servis yang akan diupdate: ")
    if not servis_id:
        print("ID tidak valid.")
        return

    # Ambil status servis
    cur.execute("SELECT status_servis FROM servis WHERE servis_id = %s", (servis_id,))
    row = cur.fetchone()

    if not row:
        print("Servis tidak ditemukan!")
        return

    status = row[0]

    # PROSES → SELESAI
    if status == "Proses":
        print("\nStatus saat ini: PROSES")
        print("Perubahan → SELESAI")

        biaya = input_int("Masukkan biaya servis: ")
        if biaya is None:
            print("Biaya tidak valid.")
            return

        cur.execute("""
            UPDATE servis
            SET status_servis = 'Selesai',
                biaya_servis = %s,
                tanggal_selesai = CURRENT_DATE
            WHERE servis_id = %s
        """, (biaya, servis_id))

        conn.commit()
        print("Status diubah menjadi SELESAI.")

    # SELESAI → DIAMBIL
    elif status == "Selesai":
        print("\nStatus saat ini: SELESAI")
        print("Perubahan → DIAMBIL")

        cur.execute("""
            UPDATE servis
            SET status_servis = 'Diambil'
            WHERE servis_id = %s
        """, (servis_id,))

        conn.commit()
        print("Servis ditandai sebagai DIAMBIL.")

    else:
        print("Servis sudah DIAMBIL dan tidak dapat diubah lagi.")

# menu transaksi servis
def transaksi_servis(conn, cur, pegawai):
    while True:
        print("\n=== MENU SERVIS ===")
        print("1. Input Servis Baru")
        print("2. Update Status Servis")
        print("3. Kembali")
        pilihan = input("Pilih menu: ")
        clear_screen()
        if pilihan == "1":
            input_servis(conn, cur, pegawai)
        elif pilihan == "2":
            update_status_servis(conn, cur)
        elif pilihan == "3":
            clear_screen()
            break
        else:
            print("Pilihan tidak valid!")

# -------------------------
# Laporan penjualan
# -------------------------
def laporan_penjualan(cur):
    # Input periode
    print("\n=== LAPORAN PENJUALAN ===")
    tahun = input("Masukkan tahun (default tahun ini): ").strip()
    bulan = input("Masukkan bulan (1-12, default bulan ini): ").strip()

    tahun = int(tahun) if tahun else datetime.now().year
    bulan = int(bulan) if bulan else datetime.now().month

    # Range bulan
    start = date(tahun, bulan, 1)
    if bulan == 12:
        end = date(tahun + 1, 1, 1)
    else:
        end = date(tahun, bulan + 1, 1)

    # Query
    cur.execute("""
        SELECT tp.penjualan_id, tp.tanggal_transaksi, tp.total_harga, m.nama
        FROM penjualan tp
        LEFT JOIN member m ON tp.member_id = m.member_id
        WHERE DATE(tp.tanggal_transaksi) >= %s
        AND DATE(tp.tanggal_transaksi) < %s
        ORDER BY tp.tanggal_transaksi
    """, (start, end))

    rows = cur.fetchall()

    print(colored(f"\n=== LAPORAN PENJUALAN PERIODE {bulan}-{tahun} ===", "cyan"))

    if not rows:
        print(colored("Tidak ada transaksi pada periode ini.", "yellow"))
        return

    # Format tampilan
    tabel = []
    for r in rows:
        tanggal = r[1].strftime("%d-%m-%Y %H:%M")
        tabel.append([
            r[0],
            tanggal,
            format_rp(r[2]),
            r[3] if r[3] else "-"
        ])

    print(tabulate(tabel, headers=["ID", "Tanggal", "Total", "Member"], tablefmt="grid"))

    total = sum((r[2] or 0) for r in rows)
    print(colored("\nTotal pendapatan: " + format_rp(total), "green"))
# -------------------------
# LAPORAN SERVIS (OWNER)
# -------------------------
def laporan_servis(cur):
    print("\n=== LAPORAN SERVIS PER PERIODE ===")

    tahun = input("Masukkan tahun (default tahun ini): ").strip()
    bulan = input("Masukkan bulan (1-12, default bulan ini): ").strip()

    tahun = int(tahun) if tahun else datetime.now().year
    bulan = int(bulan) if bulan else datetime.now().month

    start = date(tahun, bulan, 1)
    end = date(tahun + 1, 1, 1) if bulan == 12 else date(tahun, bulan + 1, 1)

    # Ambil data asli untuk hitungan
    cur.execute("""
        SELECT 
            t.teknisi_id,
            t.nama,
            COUNT(s.servis_id) AS jumlah_servis,
            COALESCE(SUM(s.biaya_servis), 0) AS total_pendapatan
        FROM teknisi t
        LEFT JOIN servis s 
            ON s.teknisi_id = t.teknisi_id
            AND s.status_servis IN ('Selesai', 'Diambil')
            AND DATE(s.tanggal_selesai) >= %s
            AND DATE(s.tanggal_selesai) < %s
        GROUP BY t.teknisi_id, t.nama
        ORDER BY t.teknisi_id
    """, (start, end))

    rows_raw = cur.fetchall()

    print(colored(f"\n=== LAPORAN SERVIS PERIODE {bulan}-{tahun} ===", "cyan"))

    if not rows_raw:
        print("Tidak ada data servis.")
        return

    tabel = []
    for r in rows_raw:
        tabel.append([
            r[0],                   # ID teknisi
            r[1],                   # nama teknisi
            r[2],                   # jumlah servis
            format_rp(r[3])         # format pendapatan
        ])

    print(tabulate(
        tabel,
        headers=["ID Teknisi", "Nama Teknisi", "Jumlah Servis", "Pendapatan"],
        tablefmt="grid"
    ))

    # hitung total pendapatan dengan data asli
    total_semua = sum(r[3] for r in rows_raw)

    print(colored("\nTotal Pendapatan Servis: " + format_rp(total_semua), "green"))

# -------------------------
# LAPORAN BARANG TIDAK LAKU
# -------------------------
def laporan_barang_tidak_laku(cur):
    print("\n=== LAPORAN BARANG TIDAK LAKU ===")

    # ======================================================
    # UPDATE OTOMATIS BARANG TIDAK LAKU (LOGIKA GABUNGAN)
    # ======================================================
    cur.execute("""
        WITH last_sale AS (
            SELECT
                p.produk_id,
                p.nama_produk,
                p.tanggal_input,
                MAX(DATE(tp.tanggal_transaksi)) AS terakhir_jual
            FROM produk p
            LEFT JOIN detail_penjualan dp ON dp.produk_id = p.produk_id
            LEFT JOIN penjualan tp ON tp.penjualan_id = dp.penjualan_id
            GROUP BY p.produk_id
        ),
        to_update AS (
            SELECT
                ls.produk_id,
                COALESCE(ls.terakhir_jual, ls.tanggal_input) AS tanggal_acuan
            FROM last_sale ls
            WHERE COALESCE(ls.terakhir_jual, ls.tanggal_input) 
                  <= CURRENT_DATE - INTERVAL '120 days'
        )
        INSERT INTO barang_tidak_laku (produk_id, terakhir_terjual, diskon_otomatis)
        SELECT produk_id, tanggal_acuan, 20
        FROM to_update
        ON CONFLICT (produk_id)
        DO UPDATE SET
            terakhir_terjual = EXCLUDED.terakhir_terjual,
            diskon_otomatis = EXCLUDED.diskon_otomatis;
    """)

    # ======================================================
    # TAMPILKAN LAPORAN
    # ======================================================

    cur.execute("""
        SELECT b.produk_id, p.nama_produk, b.terakhir_terjual,
               b.diskon_otomatis, p.harga
        FROM barang_tidak_laku b
        JOIN produk p ON p.produk_id = b.produk_id
        ORDER BY b.terakhir_terjual ASC
    """)

    rows = cur.fetchall()

    if not rows:
        print("Tidak ada barang tidak laku.")
        return

    tabel = []
    for r in rows:
        harga_asli = r[4]
        diskon = (r[3] / 100) * harga_asli
        harga_setelah_diskon = harga_asli - diskon

        tanggal = r[2].strftime("%d-%m-%Y") if r[2] else "-"

        tabel.append([
            r[0],               # ID Produk
            r[1],               # Nama Produk
            tanggal,            # Terakhir Terjual / tanggal acuan
            f"{r[3]}%",
            format_rp(harga_asli),
            format_rp(harga_setelah_diskon)
        ])

    print(tabulate(
        tabel,
        headers=[
            "ID Produk",
            "Nama Produk",
            "Terakhir Terjual",
            "Diskon",
            "Harga Asli",
            "Harga Setelah Diskon"
        ],
        tablefmt="grid"
    ))

# -------------------------
# Laporan analisis
# -------------------------
def laporan_analisis(cur):
    print("\n=== LAPORAN ANALISIS ===")
    tahun = input("Masukkan tahun (default tahun ini): ").strip()
    bulan = input("Masukkan bulan (1-12, default bulan ini): ").strip()

    tahun = int(tahun) if tahun else datetime.now().year
    bulan = int(bulan) if bulan else datetime.now().month

    start = date(tahun, bulan, 1)
    end = date(tahun + 1, 1, 1) if bulan == 12 else date(tahun, bulan + 1, 1)

    # Query total penjualan
    cur.execute("""
        SELECT COALESCE(SUM(total_harga), 0)
        FROM penjualan
        WHERE DATE(tanggal_transaksi) >= %s
        AND DATE(tanggal_transaksi) < %s
    """, (start, end))
    total_penjualan = cur.fetchone()[0]

    # Query total pembelian
    cur.execute("""
        SELECT COALESCE(SUM(total_pembelian), 0)
        FROM pembelian
        WHERE DATE(tanggal_pembelian) >= %s
        AND DATE(tanggal_pembelian) < %s
    """, (start, end))
    total_pembelian = cur.fetchone()[0]

    laba = total_penjualan - total_pembelian

    print(colored(f"\n=== LAPORAN ANALISIS PERIODE {bulan}-{tahun} ===", "cyan"))

    rows = [
        ["Total Penjualan", format_rp(total_penjualan)],
        ["Total Pembelian", format_rp(total_pembelian)],
        ["Laba Kotor", colored(format_rp(laba), "green" if laba >= 0 else "red")]
    ]

    print(tabulate(rows, headers=["Item", "Nilai"], tablefmt="grid"))

def laporan_stok_produk(cur):
    print("\n=== LAPORAN STOK PRODUK ===")

    BATAS_MENIPIS = 5  # fixed

    cur.execute("""
        SELECT produk_id, nama_produk, kategori, harga, stok
        FROM produk
        ORDER BY stok ASC, produk_id ASC
    """)

    rows = cur.fetchall()
    if not rows:
        print("Tidak ada data produk.")
        return

    tabel = []
    for r in rows:
        status = "MENIPIS" if r[4] <= BATAS_MENIPIS else "-"
        tabel.append([
            r[0],          # ID
            r[1],          # Nama Produk
            r[2],          # Kategori
            format_rp(r[3]),
            r[4],          # Stok
            status
        ])

    print(tabulate(
        tabel,
        headers=["ID","Produk","Kategori","Harga","Stok","Status"],
        tablefmt="grid"
    ))

# -------------------------
# Menus per role
# -------------------------
def menu_kasir(conn, cur, user):
    pegawai = get_pegawai_by_user_role(cur, user["user_role_id"])
    if not pegawai:
        print("Anda belum terdaftar sebagai pegawai (admin/kasir). Hubungi owner/admin.")
        return
    while True:
        clear_screen()
        show_banner()
        print("\n=== MENU KASIR ===")
        print("1. Daftarkan Member")
        print("2. Transaksi Penjualan")
        print("3. Transaksi Servis")
        print("4. Logout")
        c = input("Pilih: ").strip()
        clear_screen()
        if c == "1":
            add_member(conn, cur)
            pause()
            clear_screen()
        elif c == "2":
            transaksi_penjualan(conn, cur, pegawai)
            pause()
            clear_screen()
        elif c == "3":
            transaksi_servis(conn, cur, pegawai)
            pause()
            clear_screen()
        elif c == "4":
            clear_screen()
            break
        else:
            print("Pilihan tidak valid.")

def menu_admin(conn, cur, user):
    pegawai = get_pegawai_by_user_role(cur, user["user_role_id"])
    if not pegawai:
        print("Anda belum terdaftar sebagai pegawai (admin).")
        return

    while True:
        clear_screen()
        show_banner()
        print("\n=== MENU ADMIN ===")
        print("1. Manajemen Data Diri")
        print("2. Manajemen Kasir")
        print("3. Manajemen Teknisi")
        print("4. Kelola Produk")
        print("5. Kelola Supplier")
        print("6. Laporan Stok Produk")
        print("7. Restock / Pembelian")
        print("8. Logout")

        c = input("Pilih: ").strip()
        clear_screen()

        if c == "1":
            kelola_data_diri_admin(conn, cur, user)

        elif c == "2":
            kelola_data_kasir(conn, cur, user)
        
        elif c == "3":
            kelola_teknisi(conn, cur, user)
        
        elif c == "4":
            kelola_produk(conn, cur, user)

        elif c == "5":
            kelola_supplier(conn, cur)
        
        elif c == "6":
            laporan_stok_produk(cur)
            pause()

        elif c == "7":
            restock_pembelian(conn, cur)
            pause()

        elif c == "8":
            break

        else:
            print("Pilihan tidak valid.")
            pause()

def menu_owner(conn, cur, user):
    while True:
        clear_screen()
        show_banner()
        print("\n=== MENU OWNER ===")
        print("1. Kelola Akun Owner")
        print("2. Kelola Data Admin")
        print("3. Laporan Penjualan (periode)")
        print("4. Laporan Analisis (periode)")
        print("5. Laporan Servis (Periode)")
        print("6. Laporan Barang Tidak Laku")
        print("7. Logout")
        c = input("Pilih: ").strip()
        clear_screen()

        if c == "1":
            kelola_akun_owner(conn, cur, user)
        elif c == "2":
            kelola_data_admin(conn, cur, user)
        elif c == "3":
            laporan_penjualan(cur)
            pause()
        elif c == "4":
            laporan_analisis(cur)
            pause()
        elif c == "5":
            laporan_servis(cur)
            pause()
        elif c == "6":
            laporan_barang_tidak_laku(cur)
            pause()
        elif c == "7":
            break
        else:
            print("Pilihan tidak valid.")
            pause()

# -------------------------
# Main
# -------------------------
def main():
    try:
        conn = connect_db()
        cur = conn.cursor()
    except Exception as e:
        print("Gagal koneksi DB:", e)
        sys.exit(1)

    clear_screen()
    print("Selamat datang di FarmTech")

    while True:
        show_banner()
        print("\n=== LOGIN ===")
        username = input("\nUsername: ").strip()
        password = getpass("Password: ").strip()
        
        user = fetch_user_with_role(cur, username, password)
        if not user:
            print("Login gagal. Periksa kredensial.")
            if input("Coba lagi? (y/n): ").lower() != "y":
                clear_screen()
                break
            clear_screen()
            continue

        clear_screen()
        print(f"Sukses login sebagai '{user['role']}' (user: {user['username']})")

        if user["role"].lower() == "kasir":
            menu_kasir(conn, cur, user)
        elif user["role"].lower() == "admin":
            menu_admin(conn, cur, user)
        elif user["role"].lower() == "owner":
            menu_owner(conn, cur, user)
        else:
            print("Role tidak dikenali. Hubungi admin.")
        if input("\nLogin lagi? (y/n): ").lower() != "y":
            clear_screen()
            break

    cur.close()
    conn.close()
    show_banner()
    print("Keluar. Sampai jumpa.")

if __name__ == "__main__":
    main()
