# CCPack

[English](README.md) | Tiếng Việt

Công cụ dòng lệnh đóng gói project CapCut (bản desktop) kèm toàn bộ media thành một file `.ccpack`, và cài gói đó vào CapCut trên máy khác.

- Gom media bên ngoài vào project và sửa lại đường dẫn.
- Lưu file không nén (ZIP64, hỗ trợ file trên 4 GB), kèm checksum SHA-256 cho từng file.
- Có thể đóng gói kèm font đã cài trên máy.
- Không sửa project gốc.

## Tải về

Tải file theo hệ điều hành ở mục [Releases](../../releases). Không cần cài Python.

| Hệ điều hành | File |
|---|---|
| Windows 10/11 | `ccpack-windows-x64.exe` |
| macOS Apple Silicon | `ccpack-macos-arm64.zip` |
| macOS Intel | `ccpack-macos-x64.zip` |

File chưa được ký số.

- **Windows:** nếu SmartScreen chặn, chọn **More info → Run anyway**.
- **macOS:** giải nén, rồi chạy `xattr -d com.apple.quarantine ccpack`, hoặc chuột phải → **Open**.

## Sử dụng

Giao diện chỉ có tiếng Anh.

### Menu

Chạy `ccpack` không kèm tham số, hoặc bấm đúp vào file:

```
1. Pack project
2. Import package
3. Verify package
0. Quit
```

| Việc | Các bước |
|---|---|
| Gửi project | Đóng project trong CapCut (về màn hình Home). Chọn **1**, rồi chọn project. Gói được kiểm tra ngay sau khi ghi. |
| Nhận project | Chọn **2** rồi kéo file `.ccpack` vào (Windows: hoặc thả file lên `ccpack.exe`). Cài các font đi kèm theo danh sách in ra. |
| Lưu trữ project | Đóng gói, chép gói tới nơi lưu, rồi chọn **3** để kiểm tra bản đã chép. Chỉ xoá media gốc khi kết quả là `OK`. |

### Lệnh

```
ccpack scan   <project> [--json]
ccpack pack   <project> [-o OUTPUT] [--folder] [--fonts] [--allow-missing] [--force]
ccpack verify <package>
ccpack unpack <package> [--name NAME] [--no-verify]
```

| Lệnh | Mô tả |
|---|---|
| `scan` | Liệt kê media, font, hiệu ứng project đang dùng và báo file bị thiếu. |
| `pack` | Ghi file `.ccpack` (hoặc thư mục, với `--folder`). |
| `verify` | Kiểm tra từng file theo checksum trong manifest. Trả mã thoát 1 nếu lỗi. |
| `unpack` | Kiểm tra rồi cài gói vào CapCut. Nếu trùng tên, project được thêm hậu tố ` (1)`, ` (2)`… |

`<project>` là tên project hoặc đường dẫn tới thư mục project. Chạy `ccpack <lệnh> --help` để xem đầy đủ tuỳ chọn.

### Thư mục project

Thứ tự ưu tiên:

1. `--drafts-dir PATH` (tuỳ chọn chung, đặt trước tên lệnh).
2. Mục **Settings → Draft → Save to** của CapCut.
3. Thư mục nhập lần gần nhất (CCPack hỏi khi thư mục không tồn tại hoặc không có project).
4. Thư mục mặc định của CapCut.

## Giới hạn

- Hiệu ứng, transition, sticker từ thư viện CapCut không được đóng gói. CapCut tự tải lại khi mở project (cần đăng nhập; tài nguyên Pro cần tài khoản Pro).
- Font chỉ được đóng gói khi dùng menu hoặc `--fonts`.
- Đã kiểm tra với CapCut 9.6 trên Windows và macOS. Định dạng project của CapCut không được công bố và có thể thay đổi.

## Build từ mã nguồn

Cần Python 3.10 trở lên. Build trên đúng hệ điều hành cần dùng; PyInstaller không build chéo.

```bash
git clone https://github.com/thangghm/CCPack.git
cd CCPack
python3 -m venv .venv
.venv/bin/python -m pip install pyinstaller
.venv/bin/python build.py
```

Trên Windows, dùng `python` thay cho `python3` và `.venv\Scripts\python` thay cho `.venv/bin/python`.

Kết quả: `dist/ccpack` (macOS) hoặc `dist/ccpack.exe` (Windows).

## Miễn trừ trách nhiệm

CCPack là công cụ độc lập, không liên kết hay được xác nhận bởi CapCut hoặc ByteDance. Phần mềm được cung cấp "nguyên trạng", không kèm bảo đảm. Chạy `verify` trước khi xoá media gốc. Người dùng tự chịu trách nhiệm về bản quyền của media, font, nhạc khi chia sẻ.
