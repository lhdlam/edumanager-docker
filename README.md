# EduManager Docker

Website quản lý trung tâm giáo dục, chạy bằng Python (Flask) + Docker Compose trên **port 3333**.

## 📁 Cấu trúc thư mục

```
edumanager-docker/
├── app.py                  # Flask app chính
├── database.py             # Kết nối & khởi tạo SQLite DB
├── requirements.txt        # Python dependencies
├── Dockerfile              # Build image Docker
├── docker-compose.yml      # Chạy với Docker Compose
├── templates/
│   ├── index.html          # Trang tra cứu (công khai)
│   └── admin.html          # Trang quản trị
└── data/                   # Thư mục lưu database SQLite (tự tạo)
    └── trungtam.sqlite     # Database (tự tạo khi chạy lần đầu)
```

## 🚀 Cách chạy

### Yêu cầu
- Cài [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Bước 1: Build và chạy

```bash
cd edumanager-docker
docker compose up -d --build
```

### Bước 2: Mở trình duyệt

- **Trang chủ (tra cứu)**: http://localhost:3333
- **Trang quản trị**: http://localhost:3333/admin

### Bước 3: Đăng nhập Admin

| Tài khoản | Mật khẩu |
|-----------|----------|
| `truonghuuphong` | `Tina2012@` |

---

## 📦 Import dữ liệu cũ (tùy chọn)

Nếu bạn có file `trungtam.sqlite` từ phiên bản cũ, copy vào thư mục `data/`:

```bash
cp /path/to/trungtam.sqlite ./data/trungtam.sqlite
```

Sau đó restart container:
```bash
docker compose restart
```

---

## 🛠️ Các lệnh quản lý

```bash
# Xem logs
docker compose logs -f

# Dừng
docker compose down

# Khởi động lại
docker compose restart

# Rebuild sau khi thay đổi code
docker compose up -d --build
```

---

## ⚙️ Cấu hình

Chỉnh sửa trong `docker-compose.yml`:
- Đổi port: `"3333:3333"` → `"8080:3333"`
- Thêm biến môi trường trong `environment:`
