### Danh sách tất cả các thư viện cần cài đặt cho dự án của bạn:
--fastapi: Khung làm việc (framework) web để xây dựng API.
--python-multipart: Thư viện để xử lý dữ liệu biểu mẫu (multipart/form-data).
--uvicorn[standard]: Máy chủ ASGI hiệu năng cao để chạy ứng dụng FastAPI.
--sqlalchemy[asyncio]: Thư viện ORM (Object Relational Mapper) hỗ trợ làm việc bất đồng bộ với cơ sở dữ liệu.
--aiomysql: Trình điều khiển (driver) để kết nối với MySQL một cách bất đồng bộ.
--alembic: Công cụ di chuyển (migration) cơ sở dữ liệu cho SQLAlchemy.
--pydantic-settings: Thư viện để quản lý cấu hình dự án thông qua Pydantic.
--python-jose[cryptography]: Thư viện xử lý JSON Web Tokens (JWT).
--passlib[bcrypt]: Thư viện hỗ trợ băm mật khẩu và xác thực.
--structlog: Thư viện hỗ trợ ghi log có cấu trúc.
--fastapi-babel: Thư viện hỗ trợ đa ngôn ngữ cho FastAPI.
--Babel: Thư viện tiêu chuẩn cho việc quốc tế hóa và nội địa hóa trong Python.
### Để cài đặt tất cả các thư viện này cùng một lúc, bạn có thể chạy lệnh sau trong terminal: 
pip install -r requirements.txt
### Cài đặt bổ sung thư viện jinja2:
pip install jinja2

## Hướng dẫn Cài đặt Database (MariaDB)
Dự án sử dụng cơ sở dữ liệu **MariaDB**. Làm theo các bước dưới đây để thiết lập môi trường database trên máy cục bộ của bạn.
---
### 1. Tạo Database và User
Mở Terminal / Command Prompt (CMD) và đăng nhập vào MariaDB bằng quyền `root`:
mariadb -u root -p

### 2. Sau khi đăng nhập thành công, chạy các lệnh SQL sau để khởi tạo database và cấp quyền:
-- 1. Tạo database cho dự án
CREATE DATABASE hotel_booking CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 2. Tạo User kết nối (Trùng với cấu hình trong file .env)
CREATE USER '1234'@'127.0.0.1' IDENTIFIED BY '1234';
-- 3. Cấp toàn bộ quyền cho User trên database vừa tạo
GRANT ALL PRIVILEGES ON hotel_booking.* TO '1234'@'127.0.0.1';
-- 4. Áp dụng thay đổi quyền
FLUSH PRIVILEGES;
-- 5. Thoát khỏi MariaDB CLI
EXIT;

### 3. Khởi tạo Cấu trúc Bảng (Schema)
Đăng nhập lại vào MariaDB bằng User 1234 vừa tạo hoặc sử dụng tool UI (như DBeaver, HeidiSQL) để chạy cấu hình bảng dữ liệu: 
mariadb -u 1234 -p hotel_booking
(Nhập mật khẩu là 1234)

### 4. Chạy lệnh SQL dưới đây để tạo bảng nhật ký thông báo (notification_logs) (nếu chưa có)
-- 1. Xem danh sách tất cả database đang có: 
SHOW DATABASES;
Kiểm tra xem đã có notification_logs chưa
Nếu chưa thì chạy lệnh dưới đây để tạo:
CREATE TABLE notification_logs (
    id INT(11) NOT NULL AUTO_INCREMENT,
    booking_id INT(11) NOT NULL,
    interaction_type VARCHAR(50) NOT NULL,
    guest_name VARCHAR(255) NULL DEFAULT 'Unknown',
    message TEXT NULL DEFAULT NULL,
    action VARCHAR(50) NULL DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

### Các đường link truy cập web
---
### sau khi cài đặt database thành công, bước tiếp theo cần làm là lên VS Code của dự án rồi chạy kệnh Alembic:
alembic upgrade head

### khởi động dự án bằng lệnh:
uvicorn app.main:app --reload

### Link truy cập trang web dành cho User:
http://127.0.0.1:8000/
### Link truy cập trang web dành cho Admin:
http://127.0.0.1:8000/admin/login
