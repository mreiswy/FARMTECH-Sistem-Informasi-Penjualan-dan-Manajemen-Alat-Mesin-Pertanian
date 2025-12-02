--Buat Tabel
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);
CREATE TABLE role (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
);
CREATE TABLE user_role (
    user_role_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    role_id INT NOT NULL
);
CREATE TABLE pegawai (
    pegawai_id SERIAL PRIMARY KEY,
    user_role_id INT NOT NULL,
    nama VARCHAR(100) NOT NULL,
    alamat VARCHAR(255),
    no_hp VARCHAR(20)
);
CREATE TABLE teknisi (
    teknisi_id SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    no_hp VARCHAR(20)
);
CREATE TABLE "member" (
    member_id SERIAL PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    no_hp VARCHAR(20),
    alamat VARCHAR(255),
    total_transaksi INT DEFAULT 0
);
CREATE TABLE supplier (
    supplier_id SERIAL PRIMARY KEY,
    nama_supplier VARCHAR(100) NOT NULL,
    alamat VARCHAR(255),
    no_hp VARCHAR(20)
);
CREATE TABLE produk (
    produk_id SERIAL PRIMARY KEY,
    supplier_id INT NOT NULL,
    nama_produk VARCHAR(100) NOT NULL,
    kategori VARCHAR(50),
    harga INT NOT NULL,
    stok INT DEFAULT 0,
    tanggal_input DATE NOT NULL
);
CREATE TABLE pembelian (
    pembelian_id SERIAL PRIMARY KEY,
    supplier_id INT NOT NULL,
    tanggal_pembelian DATE NOT NULL,
    total_pembelian INT NOT NULL
);
CREATE TABLE detail_pembelian (
    detail_pembelian_id SERIAL PRIMARY KEY,
    pembelian_id INT NOT NULL,
    produk_id INT NOT NULL,
    qty INT NOT NULL,
    harga_beli INT NOT NULL
);
CREATE TABLE penjualan (
    penjualan_id SERIAL PRIMARY KEY,
    kasir_id INT NOT NULL,
    member_id INT,
    tanggal_transaksi DATE NOT NULL,
    subtotal INT NOT NULL,
    ppn INT NOT NULL,
    diskon INT,
    total_harga INT NOT NULL
);
CREATE TABLE detail_penjualan (
    detail_penjualan_id SERIAL PRIMARY KEY,
    penjualan_id INT NOT NULL,
    produk_id INT NOT NULL,
    qty INT NOT NULL,
    harga_saat_penjualan INT NOT NULL
);
CREATE TABLE servis (
    servis_id SERIAL PRIMARY KEY,
    member_id INT,
    kasir_id INT NOT NULL,
    teknisi_id INT NOT NULL,
    nama_alat VARCHAR(100) NOT NULL,
    keluhan TEXT NOT NULL,
    biaya_servis INT NOT NULL,
    status_servis VARCHAR(50) NOT NULL,
    tanggal_masuk DATE NOT NULL,
    tanggal_selesai DATE
);
CREATE TABLE barang_tidak_laku (
    id SERIAL PRIMARY KEY,
    produk_id INT NOT NULL,
    terakhir_terjual DATE,
    diskon_otomatis INT DEFAULT 20
);

--penghubung
ALTER TABLE user_role
ADD CONSTRAINT fk_userrole_user
FOREIGN KEY (user_id) REFERENCES users(user_id);

ALTER TABLE user_role
ADD CONSTRAINT fk_userrole_role
FOREIGN KEY (role_id) REFERENCES role(role_id);

ALTER TABLE pegawai
ADD CONSTRAINT fk_pegawai_userrole
FOREIGN KEY (user_role_id) REFERENCES user_role(user_role_id);

ALTER TABLE produk
ADD CONSTRAINT fk_produk_supplier
FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id);

ALTER TABLE detail_pembelian
ADD CONSTRAINT fk_dp_pembelian
FOREIGN KEY (pembelian_id) REFERENCES pembelian(pembelian_id);

ALTER TABLE detail_pembelian
ADD CONSTRAINT fk_dp_produk
FOREIGN KEY (produk_id) REFERENCES produk(produk_id);

ALTER TABLE penjualan
ADD CONSTRAINT fk_tp_member
FOREIGN KEY (member_id) REFERENCES member(member_id);

ALTER TABLE penjualan
ADD CONSTRAINT fk_tp_kasir
FOREIGN KEY (kasir_id) REFERENCES pegawai(pegawai_id);

ALTER TABLE detail_penjualan
ADD CONSTRAINT fk_dt_transaksi
FOREIGN KEY (penjualan_id) REFERENCES penjualan(penjualan_id);

ALTER TABLE detail_penjualan
ADD CONSTRAINT fk_dt_produk
FOREIGN KEY (produk_id) REFERENCES produk(produk_id);

ALTER TABLE servis
ADD CONSTRAINT fk_servis_member
FOREIGN KEY (member_id) REFERENCES member(member_id);

ALTER TABLE servis
ADD CONSTRAINT fk_servis_kasir
FOREIGN KEY (kasir_id) REFERENCES pegawai(pegawai_id);

ALTER TABLE servis
ADD CONSTRAINT fk_servis_teknisi
FOREIGN KEY (teknisi_id) REFERENCES teknisi(teknisi_id);

ALTER TABLE barang_tidak_laku
ADD CONSTRAINT fk_btl_produk
FOREIGN KEY (produk_id) REFERENCES produk(produk_id);

--Perubahan
ALTER TABLE servis
ALTER COLUMN biaya_servis DROP NOT NULL;


--build Database
INSERT INTO role (role_name) VALUES
('Owner'),
('Admin'),
('Kasir');

INSERT INTO users (username, password) VALUES
('arfian', 'owner123'),
('hadil', 'admin123'),
('reihan', 'kasir123');

INSERT INTO user_role (user_id, role_id) VALUES
(1, 1),  -- Arfian = Owner
(2, 2),  -- Hadil = Admin
(3, 3);  -- Reihan = Kasir

INSERT INTO pegawai (user_role_id, nama, alamat, no_hp) VALUES
(2, 'Hadil', 'Jl. Merpati No. 10', '081234567890'),
(3, 'Reihan', 'Jl. Anggrek Raya No. 21', '089876543210');

INSERT INTO teknisi (nama, no_hp) VALUES
('Budi', '081200111222'),
('Rezaq', '081233445566'),
('Javier', '085212345678');

INSERT INTO "member" (nama, no_hp, alamat, total_transaksi) VALUES
('Sutrisno', '081223334444', 'Desa Kemuning No. 12', 3),
('Agus Salim', '081233211223', 'Dusun Karang Tengah', 1),
('Rani Lestari', '089912345671', 'Jl. Mawar Indah', 5),
('Yuni Kartika', '088899776655', 'Perumahan Harmonika', 0),
('Fajar Nugroho', '087722334455', 'Jl. Sudirman', 2),
('Samsul Hadi', '081255667788', 'Desa Kemiri', 4),
('Miftahudin', '085278990011', 'Jl. Melati', 7),
('Joko Purwanto', '085266554433', 'Dusun Randu Alas', 0),
('Siti Fatimah', '081325001122', 'Jl. Cemara Raya', 6),
('Rahmad Setia', '082113334455', 'Desa Genengan', 1);

INSERT INTO supplier (nama_supplier, alamat, no_hp) VALUES
('AgroTech Supply', 'Jakarta Barat', '081234000001'),
('FarmSource Indonesia', 'Bandung', '081234000002'),
('Anugrah Mesin Tani', 'Semarang', '081234000003'),
('Mitra Agri Jaya', 'Surabaya', '081234000004'),
('TaniMakmur Tools', 'Yogyakarta', '081234000005'),
('Garuda Agriculture', 'Malang', '081234000006'),
('PT Sumber Pangan', 'Tangerang', '081234000007'),
('Nusantara Alat Tani', 'Solo', '081234000008');

INSERT INTO produk (supplier_id, nama_produk, kategori, harga, stok, tanggal_input) VALUES
(1, 'Cangkul Baja Super', 'Alat Manual', 85000, 30, CURRENT_DATE),
(1, 'Sekop Stainless Steel', 'Alat Manual', 65000, 25, CURRENT_DATE),
(2, 'Mesin Pompa Air 1 Inch', 'Mesin Pertanian', 1250000, 10, CURRENT_DATE),
(2, 'Mesin Pompa Air 2 Inch', 'Mesin Pertanian', 1750000, 8, CURRENT_DATE),
(3, 'Sprayer Elektrik 16 Liter', 'Penyemprotan', 450000, 20, CURRENT_DATE),
(3, 'Sprayer Manual 14 Liter', 'Penyemprotan', 250000, 18, CURRENT_DATE),
(4, 'Traktor Mini Rotary', 'Mesin Berat', 6500000, 4, CURRENT_DATE),
(4, 'Mesin Giling Padi Portable', 'Pengolahan', 2800000, 5, CURRENT_DATE),
(5, 'Parang Baja Hitam', 'Alat Manual', 55000, 40, CURRENT_DATE),
(5, 'Sarung Tangan Kebun', 'Perlengkapan', 15000, 60, CURRENT_DATE),
(5, 'Boots Anti Air', 'Perlengkapan', 90000, 35, CURRENT_DATE),
(6, 'Selang Air 20 Meter', 'Irigasi', 80000, 25, CURRENT_DATE),
(6, 'Nozzle 7 Mode Sprayer', 'Irigasi', 35000, 30, CURRENT_DATE),
(7, 'Pupuk Organik Granul 5kg', 'Pupuk', 45000, 50, CURRENT_DATE),
(7, 'Pupuk NPK 16-16-16 10kg', 'Pupuk', 120000, 40, CURRENT_DATE),
(8, 'Gembor Air Besar', 'Irigasi', 60000, 22, CURRENT_DATE),
(8, 'Alat Ukur pH Tanah Digital', 'Pengukuran', 150000, 12, CURRENT_DATE),
(2, 'Mesin Pengiris Singkong', 'Pengolahan', 900000, 9, CURRENT_DATE),
(3, 'Sprinkler Taman', 'Irigasi', 30000, 45, CURRENT_DATE),
(4, 'Mesin Kultivator Mini', 'Mesin Pertanian', 3200000, 6, CURRENT_DATE),
(1, 'Garpu Tanah Baja', 'Alat Manual', 70000, 15, CURRENT_DATE),
(6, 'Klem Selang 1 Inch', 'Irigasi', 8000, 100, CURRENT_DATE),
(5, 'Masker Debu Pertanian', 'Perlengkapan', 5000, 150, CURRENT_DATE),
(7, 'Pestisida Cair 1 Liter', 'Pestisida', 95000, 30, CURRENT_DATE),
(7, 'Herbisida Gramoxone 500ml', 'Pestisida', 68000, 20, CURRENT_DATE);

INSERT INTO pembelian (supplier_id, tanggal_pembelian, total_pembelian) VALUES
(1, CURRENT_DATE - 20, 2500000),
(3, CURRENT_DATE - 18, 3100000),
(5, CURRENT_DATE - 15, 1450000),
(7, CURRENT_DATE - 10, 2800000),
(2, CURRENT_DATE - 5, 3500000);

INSERT INTO detail_pembelian (pembelian_id, produk_id, qty, harga_beli) VALUES
-- Pembelian 1
(1, 1, 20, 65000),
(1, 2, 10, 50000),

-- Pembelian 2
(2, 5, 15, 300000),
(2, 6, 10, 180000),

-- Pembelian 3
(3, 9, 25, 35000),
(3, 10, 40, 9000),

-- Pembelian 4
(4, 15, 20, 90000),
(4, 16, 10, 110000),

-- Pembelian 5
(5, 3, 5, 1000000),
(5, 4, 3, 1550000);

INSERT INTO penjualan 
(kasir_id, member_id, tanggal_transaksi, subtotal, ppn, diskon, total_harga) VALUES
(2, 1, CURRENT_DATE, 300000, 36000, 0, 336000),
(2, 3, CURRENT_DATE, 900000, 108000, 90000, 918000),
(2, 5, CURRENT_DATE, 150000, 18000, 0, 168000),
(2, 7, CURRENT_DATE, 450000, 54000, 45000, 459000),
(2, 10, CURRENT_DATE, 80000, 9600, 0, 89600),
(2, 6, CURRENT_DATE, 250000, 30000, 0, 280000),
(2, 2, CURRENT_DATE, 120000, 14400, 0, 134400),
(2, 4, CURRENT_DATE, 60000, 7200, 0, 67200),
(2, 8, CURRENT_DATE, 450000, 54000, 45000, 459000),
(2, 9, CURRENT_DATE, 90000, 10800, 0, 100800);

INSERT INTO detail_penjualan (penjualan_id, produk_id, qty, harga_saat_penjualan) VALUES
(1, 9, 4, 55000),
(2, 3, 2, 450000),
(3, 10, 10, 15000),
(4, 5, 2, 250000),
(5, 12, 1, 80000),
(6, 1, 2, 85000),
(7, 21, 1, 120000),
(8, 10, 4, 15000),
(9, 5, 2, 250000),
(10, 23, 3, 30000);

INSERT INTO servis 
(member_id, kasir_id, teknisi_id, nama_alat, keluhan, biaya_servis, status_servis, tanggal_masuk, tanggal_selesai) VALUES
(1, 2, 1, 'Sprayer Elektrik 16L', 'Baterai rusak', 100000, 'Selesai', CURRENT_DATE - 5, CURRENT_DATE - 3),
(3, 2, 2, 'Pompa Air 2 Inch', 'Mesin panas berlebih', 150000, 'Selesai', CURRENT_DATE - 4, CURRENT_DATE - 2),
(5, 2, 3, 'Traktor Mini', 'Rantai longgar', 250000, 'Proses', CURRENT_DATE - 2, NULL),
(7, 2, 2, 'Mesin Giling Padi', 'Pisau tumpul', 175000, 'Selesai', CURRENT_DATE - 6, CURRENT_DATE - 1),
(2, 2, 3, 'Sprayer Manual', 'Bocor', 50000, 'Selesai', CURRENT_DATE - 3, CURRENT_DATE - 2),
(9, 2, 1, 'Pengiris Singkong', 'Motor lemah', 90000, 'Proses', CURRENT_DATE - 1, NULL);

INSERT INTO barang_tidak_laku (produk_id, terakhir_terjual, diskon_otomatis) VALUES
(21, CURRENT_DATE - 120, 20),
(17, CURRENT_DATE - 150, 20),
(12, CURRENT_DATE - 200, 20),
(23, CURRENT_DATE - 180, 20),
(10, CURRENT_DATE - 160, 20);
