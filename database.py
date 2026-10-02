import sqlite3
import os

# Trong Docker, database lưu tại /data (volume mount)
# Khi chạy local, lưu tại thư mục hiện tại
BASE_DIR = os.environ.get('DATA_DIR', os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'trungtam.sqlite')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS cai_dat_ca_hoc (
            ca_id INTEGER PRIMARY KEY, 
            buoi TEXT, 
            thoi_gian TEXT, 
            mau_sac TEXT
        );
        CREATE TABLE IF NOT EXISTS thoi_khoa_bieu (
            thu INTEGER, 
            ca_id INTEGER, 
            noi_dung TEXT, 
            PRIMARY KEY (thu, ca_id)
        );
        CREATE TABLE IF NOT EXISTS hoc_vien (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            ma_hv TEXT UNIQUE, 
            ho_ten TEXT, 
            ngay_sinh TEXT, 
            lop_truong TEXT, 
            so_dien_thoai TEXT, 
            ngay_bat_dau TEXT, 
            trang_thai TEXT DEFAULT 'Đang học'
        );
        CREATE TABLE IF NOT EXISTS lop_hoc (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            ma_lop TEXT UNIQUE, 
            ten_lop TEXT, 
            mon_hoc TEXT, 
            lich_hoc TEXT, 
            giao_vien TEXT, 
            hoc_phi REAL
        );
        CREATE TABLE IF NOT EXISTS thu_hoc_phi (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            ma_hv TEXT, 
            ma_lop TEXT, 
            thang_thu TEXT, 
            hoc_phi_phai_dong REAL, 
            da_dong REAL, 
            ngay_thu TEXT, 
            hinh_thuc TEXT
        );
        CREATE TABLE IF NOT EXISTS ngay_hoc (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            ma_lop TEXT, 
            thang TEXT, 
            ngay_1 TEXT, ngay_2 TEXT, ngay_3 TEXT, ngay_4 TEXT, 
            ngay_5 TEXT, ngay_6 TEXT, ngay_7 TEXT, ngay_8 TEXT
        );
        CREATE TABLE IF NOT EXISTS diem_danh (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            ma_hv TEXT, 
            ma_lop TEXT, 
            ngay_diem_danh TEXT, 
            trang_thai TEXT
        );
        CREATE TABLE IF NOT EXISTS hoc_vien_lop (
            ma_hv TEXT, 
            ma_lop TEXT, 
            PRIMARY KEY(ma_hv, ma_lop)
        );
        CREATE TABLE IF NOT EXISTS chi_phi (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            loai_chi_phi TEXT, 
            so_tien REAL, 
            ngay_chi TEXT
        );
    """)

    # Đồng bộ học viên lớp từ thu_hoc_phi nếu có
    cursor.execute("INSERT OR IGNORE INTO hoc_vien_lop (ma_hv, ma_lop) SELECT ma_hv, ma_lop FROM thu_hoc_phi")

    cursor.execute("SELECT COUNT(*) FROM cai_dat_ca_hoc")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO cai_dat_ca_hoc VALUES (?,?,?,?)", [
            (1, 'Sáng', '7h00-8h30', '#fce4d6'),
            (2, 'Sáng', '8h30-10h00', '#f8cbad'),
            (3, 'Chiều', '14h00-15h30', '#deeaf6'),
            (4, 'Chiều', '15h30-17h00', '#bdd7ee'),
            (5, 'Tối', '17h30-19h00', '#5b9bd5')
        ])

    conn.commit()
    conn.close()
