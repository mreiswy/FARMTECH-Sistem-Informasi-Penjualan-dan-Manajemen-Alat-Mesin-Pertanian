import sys
from datetime import datetime, date
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
        f = pyfiglet.Figlet(font="block")
        print(colored(f.renderText("FARMTECH"), "yellow"))
except Exception:
    def show_banner():
        # simple fallback
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
# Member functions
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
# Def untuk produk dan supplier
# -------------------------
def list_produk(cur):
    cur.execute("SELECT produk_id, nama_produk, kategori, harga, stok FROM produk ORDER BY produk_id")
    rows = cur.fetchall()
    print(tabulate([[r[0], r[1], r[2], format_rp(r[3]), r[4]] for r in rows],
                   headers=["ID","Nama","Kategori","Harga","Stok"], tablefmt="grid"))
    return rows

def get_produk(cur, produk_id):
    cur.execute("SELECT produk_id, nama_produk, harga, stok FROM produk WHERE produk_id = %s", (produk_id,))
    return cur.fetchone()

def list_supplier(cur):
    cur.execute("SELECT supplier_id, nama_supplier, alamat, no_hp FROM supplier ORDER BY supplier_id")
    rows = cur.fetchall()
    print(tabulate(rows, headers=["ID","Supplier","Alamat","No HP"], tablefmt="grid"))
    return rows

# -------------------------
# Laporan penjualan
# -------------------------
from termcolor import colored

def laporan_penjualan(cur):
    # Input periode
    print("\n=== LAPORAN PENJUALAN ===")
    tahun = input("Masukkan tahun (default tahun ini): ").strip()
    bulan = input("Masukkan bulan (1–12, default bulan ini): ").strip()

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
# Laporan analisis
# -------------------------
def laporan_analisis(cur):
    print("\n=== LAPORAN ANALISIS ===")
    tahun = input("Masukkan tahun (default tahun ini): ").strip()
    bulan = input("Masukkan bulan (1–12, default bulan ini): ").strip()

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

# -------------------------
# Penjualan
# -------------------------
PPN_RATE = 0.12
def transaksi_penjualan(conn, cur, pegawai):
    print("\n=== TRANSAKSI PENJUALAN ===")
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

    # build cart
    cart = []
    while True:
        list_produk(cur)
        pid = input_int("Masukkan ID produk (enter untuk selesai): ")
        if pid is None:
            break
        prod = get_produk(cur, pid)
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
        cart.append({"produk_id": prod[0], "nama": prod[1], "harga": prod[2], "qty": qty})
        if input("Tambah produk lain? (y/n): ").lower() != "y":
            break

    if not cart:
        print("Transaksi dibatalkan (keranjang kosong).")
        return

    # tampilkan keranjang
    table = []
    subtotal = 0
    for it in cart:
        sub = it["harga"] * it["qty"]
        subtotal += sub
        table.append([it["produk_id"], it["nama"], format_rp(it["harga"]), it["qty"], format_rp(sub)])
    print(tabulate(table, headers=["ID","Produk","Harga","Qty","Subtotal"], tablefmt="grid"))

    ppn = int(subtotal * PPN_RATE)
    # discount for member: every 10th transaction get 10% (as discussed)
    diskon_rate = 0.0
    if member_id:
        cur.execute("SELECT total_transaksi FROM member WHERE member_id = %s", (member_id,))
        tt = cur.fetchone()[0] or 0
        if tt > 0 and tt % 10 == 0:
            diskon_rate = 0.10
    diskon = int(subtotal * diskon_rate)
    total = subtotal + ppn - diskon

    print(f"\nSubtotal: {format_rp(subtotal)} | PPN: {format_rp(ppn)} | Diskon: {format_rp(diskon)}")
    print(f"TOTAL: {format_rp(total)}")

    if input("Simpan transaksi? (y/n): ").lower() != "y":
        print("Transaksi dibatalkan.")
        return

    # insert header
    cur.execute("""
        INSERT INTO penjualan (kasir_id, member_id, tanggal_transaksi, subtotal, ppn, diskon, total_harga)
        VALUES (%s,%s,NOW(),%s,%s,%s,%s) RETURNING penjualan_id
    """, (pegawai["pegawai_id"], member_id, subtotal, ppn, diskon, total))
    penjualan_id = cur.fetchone()[0]

    # insert details and update stok
    for it in cart:
        cur.execute("""
            INSERT INTO detail_penjualan (penjualan_id, produk_id, qty, harga_saat_penjualan)
            VALUES (%s,%s,%s,%s)
        """, (penjualan_id, it["produk_id"], it["qty"], it["harga"]))
        cur.execute("UPDATE produk SET stok = stok - %s WHERE produk_id = %s", (it["qty"], it["produk_id"]))
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
    # check supplier exists
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
        cur.execute("SELECT produk_id, nama_produk, harga FROM produk WHERE produk_id = %s", (pid,))
        p = cur.fetchone()
        if not p:
            print("Produk tidak ada.")
            continue
        qty = input_int("Jumlah beli: ")
        if qty is None or qty <= 0:
            print("Jumlah tidak valid.")
            continue
        harga_beli = input_int(f"Harga beli per unit (default {p[2]}): ", default=p[2])
        items.append((pid, qty, harga_beli))
        if input("Tambah barang lagi? (y/n): ").lower() != "y":
            break

    if not items:
        print("Tidak ada item. Batal.")
        return

    total = sum(q*h for (_,q,h) in items)
    cur.execute("INSERT INTO pembelian (supplier_id, tanggal_pembelian, total_pembelian) VALUES (%s, NOW(), %s) RETURNING pembelian_id",
                (sid, total))
    pembelian_id = cur.fetchone()[0]
    for pid, qty, harga_beli in items:
        cur.execute("INSERT INTO detail_pembelian (pembelian_id, produk_id, qty, harga_beli) VALUES (%s,%s,%s,%s)",
                    (pembelian_id, pid, qty, harga_beli))
        cur.execute("UPDATE produk SET stok = stok + %s WHERE produk_id = %s", (qty, pid))
    conn.commit()
    print(f"Pembelian tersimpan (ID = {pembelian_id}), Total = {format_rp(total)}")

# -------------------------
# Servis
# -------------------------
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

    servis_id = input_int("Masukkan ID Servis: ")
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
        print("Status saat ini: PROSES")
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
        print("Status diubah menjadi SELESAI + biaya tersimpan.")

    # SELESAI → DIAMBIL
    elif status == "Selesai":
        print("Status saat ini: SELESAI")
        print("Perubahan → DIAMBIL")

        cur.execute("""
            UPDATE servis
            SET status_servis = 'Diambil'
            WHERE servis_id = %s
        """, (servis_id,))

        conn.commit()
        print("Servis ditandai sebagai DIAMBIL.")

    # DIAMBIL → tidak bisa diubah
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
        print("1. Restock / Pembelian")
        print("2. Logout")
        c = input("Pilih: ").strip()
        clear_screen()
        if c == "1":
            restock_pembelian(conn, cur)
            pause()
            clear_screen()
        elif c == "2":
            clear_screen()
            break
        else:
            print("Pilihan tidak valid.")

def menu_owner(conn, cur, user):
    while True:
        clear_screen()
        show_banner()
        print("\n=== MENU OWNER ===")
        print("1. Laporan Penjualan (periode)")
        print("2. Laporan Analisis (periode)")
        print("3. Logout")
        c = input("Pilih: ").strip()
        clear_screen()
        if c == "1":
            laporan_penjualan(cur)
            pause()
            clear_screen()
        elif c == "2":
            laporan_analisis(cur)
            pause()
            clear_screen()
        elif c == "3":
            clear_screen()
            break
        else:
            print("Pilihan tidak valid.")

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