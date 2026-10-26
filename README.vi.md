# CCPack

[English](README.md) | Tiếng Việt

Công cụ CLI đóng gói project CapCut (bản desktop) kèm toàn bộ media thành một file `.ccpack`, để có thể cài gói đó vào CapCut trên máy khác.

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

### Chạy trong Terminal

Các lệnh được gõ trong Terminal (macOS) hoặc PowerShell (Windows). Terminal chỉ tìm thấy `ccpack` khi file nằm trong một thư mục thuộc `PATH`; nếu không sẽ báo `command not found`. Có hai cách: chạy bằng đường dẫn, hoặc cài một lần.

Chạy bằng đường dẫn, từ thư mục chứa file:

```bash
cd ~/Downloads
./ccpack --help            # Windows: .\ccpack.exe --help
```

Cài trên macOS để gõ `ccpack` ở bất kỳ thư mục nào:

```bash
mkdir -p ~/.local/bin
cp ~/Downloads/ccpack ~/.local/bin/
xattr -d com.apple.quarantine ~/.local/bin/ccpack
ccpack --help
```

Nếu vẫn báo không tìm thấy `ccpack`, thêm `~/.local/bin` vào `PATH`: chạy `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc`, rồi mở cửa sổ Terminal mới. Nếu báo `permission denied`, chạy `chmod +x ~/.local/bin/ccpack`.

### Lệnh

```
ccpack [--drafts-dir PATH] <lệnh> [tuỳ chọn]
```

`<project>` là tên project hiển thị trong CapCut, hoặc đường dẫn tới thư mục project. `<package>` là file `.ccpack`, hoặc thư mục tạo bởi `pack --folder`. Trên Windows, đổi tên file tải về thành `ccpack.exe` để gõ lệnh như hướng dẫn.

**Tuỳ chọn chung** (đặt trước tên lệnh)

| Tuỳ chọn | Mô tả |
|---|---|
| `--drafts-dir PATH` | Thư mục project CapCut, chỉ áp dụng cho lần chạy này. Xem [Thư mục project](#thư-mục-project). |
| `--version` | In số phiên bản. |
| `-h`, `--help` | Xem trợ giúp. `ccpack <lệnh> --help` xem tuỳ chọn của từng lệnh. |

**`scan <project>`** liệt kê media, font, hiệu ứng thư viện và file bị thiếu. Chỉ đọc, không ghi.

| Tuỳ chọn | Mô tả |
|---|---|
| `--json` | In kết quả dạng JSON. |

**`pack <project>`** ghi project và media vào gói, rồi in tóm tắt.

| Tuỳ chọn | Mô tả |
|---|---|
| `-o`, `--output PATH` | Đường dẫn đầu ra. Mặc định: `<project>.ccpack` trong thư mục hiện tại (`<project>_ccpack` khi dùng `--folder`). |
| `--folder` | Ghi ra thư mục thường thay vì file `.ccpack`. |
| `--fonts` | Đóng gói kèm font đã cài mà project dùng. |
| `--allow-missing` | Vẫn đóng gói khi thiếu media. Danh sách file thiếu ghi trong `manifest.json`. |
| `--force` | Ghi đè đầu ra có sẵn. Cho phép đóng gói cả project đang mở trong CapCut; chỉ dùng khi CapCut không chỉnh sửa project đó. |

**`verify <package>`** kiểm tra từng file theo checksum trong manifest. Không có tuỳ chọn.

**`unpack <package>`** kiểm tra gói, rồi cài vào thư mục project.

| Tuỳ chọn | Mô tả |
|---|---|
| `--name NAME` | Tên project trong CapCut. Mặc định: tên gốc, thêm ` (1)`, ` (2)`… nếu trùng. |
| `--no-verify` | Bỏ qua bước kiểm tra checksum trước khi giải nén. |

Mã thoát: `0` thành công, `1` lỗi hoặc kiểm tra thất bại, `2` sai tham số.

**Ví dụ**

```bash
ccpack scan "My Video"
ccpack scan "My Video" --json > my-video.json
ccpack pack "My Video" -o ~/Archive/my-video.ccpack --fonts
ccpack pack "My Video" --allow-missing --force
ccpack verify ~/Archive/my-video.ccpack
ccpack unpack my-video.ccpack --name "My Video (review)"
ccpack --drafts-dir "D:\CapCut Drafts" pack "My Video"
```

### Thư mục project

ccpack tự tìm thư mục project của CapCut theo thứ tự:

1. `--drafts-dir PATH`, nếu có.
2. Mục **Settings → Draft → Save to** của CapCut.
3. Thư mục đã nhập trong menu lần gần nhất.
4. Thư mục mặc định của CapCut:
   - macOS: `~/Movies/CapCut/User Data/Projects/com.lveditor.draft`
   - Windows: `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`

`ccpack --help` hiện thư mục đang dùng ở giá trị mặc định của `--drafts-dir`.

**Nếu không tìm thấy thư mục**

- **Menu:** ccpack hỏi thư mục khi thư mục không tồn tại hoặc không có project. Trong CapCut, mở **Settings → Draft**, copy đường dẫn ở mục **Save to** rồi dán vào, hoặc kéo thư mục vào cửa sổ. Có thể nhập thư mục project, thư mục cha của nó, hoặc một project bên trong. Thư mục được lưu cho các lần chạy sau.
- **Lệnh:** các lệnh không hỏi. Thêm `--drafts-dir PATH` (thư mục chứa các project), hoặc truyền đường dẫn thư mục project thay cho tên. Muốn lưu thư mục, nhập một lần trong menu.
- **Chưa từng mở CapCut trên máy:** mở CapCut một lần để CapCut tạo thư mục project, rồi chạy lại.

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
