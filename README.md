# CCPack - CapCut Project Packer

CCPack đóng gói một project CapCut (bản desktop) **cùng toàn bộ media** thành một file `.ccpack` duy nhất, để:

- **Chuyển project cho người khác** chỉnh sửa tiếp trên máy của họ.
- **Lưu trữ project** trước khi dọn ổ cứng, mà không lo mất video, ảnh, nhạc.

CapCut chỉ lưu đường dẫn tới file media trên máy bạn. Vì vậy chép thư mục project sang máy khác sẽ bị báo thiếu media. CCPack gom media vào trong project, sửa lại đường dẫn, rồi đóng gói tất cả, kèm mã kiểm tra (sha256) cho từng file.

## Tính năng

- Quét project: liệt kê media, font, hiệu ứng đang dùng, báo file bị thiếu hoặc chỉ có trên cloud (Dropbox, OneDrive…).
- Đóng gói thành file `.ccpack` (zip không nén, hỗ trợ file trên 4 GB), có thể kèm font.
- Kiểm tra gói còn nguyên vẹn trước khi xoá media gốc.
- Cài gói vào CapCut trên máy khác: project hiện ở đầu danh sách, mở là đủ media.
- Không sửa project gốc.

## Tải về

Vào mục [Releases](../../releases), tải file theo hệ điều hành:

| Hệ điều hành | File |
|---|---|
| Windows 10/11 | `ccpack-windows-x64.exe` |
| macOS Apple Silicon (M1/M2/M3…) | `ccpack-macos-arm64.zip` |
| macOS Intel | `ccpack-macos-x64.zip` |

Không cần cài Python.

- **Windows:** lần đầu chạy, SmartScreen có thể cảnh báo vì file chưa được ký số. Bấm **More info → Run anyway**.
- **macOS:** giải nén file zip. Lần đầu chạy, macOS có thể chặn vì ứng dụng chưa được ký số. Chuột phải vào `ccpack` → **Open**, hoặc chạy `xattr -d com.apple.quarantine ccpack` trong Terminal.

## Hướng dẫn sử dụng

### Cách đơn giản (menu)

Bấm đúp vào `ccpack`, chọn số trong menu:

```
1. Đóng gói project (để gửi người khác / lưu trữ)
2. Cài file .ccpack vào CapCut
3. Kiểm tra file .ccpack còn nguyên vẹn
0. Thoát
```

**Người gửi**

1. Trong CapCut, đóng project cần gửi (quay về màn hình Home).
2. Mở `ccpack`, chọn **1**, chọn số thứ tự project.
3. Chọn thư mục lưu. CCPack đóng gói rồi tự kiểm tra lại file vừa tạo.
4. Gửi file `.ccpack` cho người nhận.

**Người nhận**

1. Kéo file `.ccpack` thả vào `ccpack` (hoặc mở `ccpack`, chọn **2**, kéo file vào cửa sổ rồi Enter).
2. Nếu có font đi kèm, cài font theo đường dẫn CCPack in ra.
3. **Tắt hẳn CapCut rồi mở lại.** CapCut chỉ nhận project mới khi khởi động. Project sẽ nằm đầu danh sách.

**Lưu trữ trước khi dọn ổ cứng**

1. Đóng gói project như trên.
2. Chọn **3** để kiểm tra file `.ccpack`. Chỉ xoá media gốc khi kết quả là `OK`.

### Dòng lệnh

```
ccpack scan   "<tên project>"               # xem project dùng những gì
ccpack pack   "<tên project>" [-o file.ccpack] [--fonts] [--folder] [--allow-missing] [--force]
ccpack verify  file.ccpack                  # kiểm tra hash từng file
ccpack unpack  file.ccpack [--name "Tên mới"] [--no-verify]
```

- Trên Windows, đổi tên file tải về thành `ccpack.exe` (hoặc gõ đúng tên file) và chạy trong thư mục chứa nó.
- `<tên project>` là tên hiển thị trong CapCut, hoặc đường dẫn tới thư mục project.
- CapCut lưu project ở vị trí khác mặc định thì thêm `--drafts-dir` trước tên lệnh: `ccpack --drafts-dir "D:\CapCut Drafts" scan "<tên project>"`.
- `ccpack <lệnh> --help` để xem đầy đủ tuỳ chọn.

### Lưu ý

- Hiệu ứng, transition, sticker từ thư viện CapCut không được đóng gói. CapCut tự tải lại khi mở project (cần đăng nhập; hiệu ứng Pro cần tài khoản Pro).
- Font cài thêm trên máy chỉ được đóng gói khi dùng menu hoặc `--fonts`. Người nhận cần tự cài font.
- Đã kiểm tra với CapCut 9.6 trên Windows. Trên macOS, vị trí thư mục project mặc định chưa được kiểm chứng; nếu không tìm thấy project, dùng `--drafts-dir`.

## Phát triển

Yêu cầu Python 3.10 trở lên, không cần thư viện ngoài.

```bash
git clone https://github.com/thangghm/CCPack.git
cd CCPack
python -m ccpack --help
```

Build file chạy cho hệ điều hành đang dùng (PyInstaller không build chéo được):

```bash
python -m venv .venv
.venv/Scripts/python -m pip install pyinstaller   # macOS: .venv/bin/python
.venv/Scripts/python build.py                     # kết quả: dist/ccpack(.exe)
```

Phát hành bản mới: tăng `__version__` trong `ccpack/__init__.py` và `version` trong `pyproject.toml`, rồi push tag cùng số phiên bản:

```bash
git tag v0.1.1
git push origin v0.1.1
```

GitHub Actions sẽ build bản Windows và macOS rồi tạo Release (xem `.github/workflows/release.yml`).

Cấu trúc mã nguồn:

| File | Vai trò |
|---|---|
| `ccpack/capcut.py` | Vị trí thư mục và cấu trúc file project CapCut |
| `ccpack/rewrite.py` | Tìm và sửa mọi đường dẫn trong file JSON của project |
| `ccpack/scan.py` | Quét project, lập danh sách media / font / hiệu ứng |
| `ccpack/pack.py` | Ghi file `.ccpack` và `manifest.json` |
| `ccpack/package.py`, `verify.py`, `unpack.py` | Đọc, kiểm tra và cài gói |
| `ccpack/cli.py`, `interactive.py` | Dòng lệnh và menu |

## Disclaimer

- CCPack là công cụ độc lập, **không liên kết, không được tài trợ hay xác nhận** bởi CapCut, ByteDance hoặc các công ty liên quan. CapCut là thương hiệu của chủ sở hữu tương ứng.
- CCPack đọc và sửa định dạng project nội bộ của CapCut, vốn không được công bố và có thể thay đổi ở các phiên bản CapCut sau. Công cụ có thể không hoạt động đúng với phiên bản khác bản đã kiểm tra.
- Phần mềm được cung cấp "nguyên trạng" (as is), không kèm bất kỳ bảo đảm nào. Người dùng tự chịu trách nhiệm khi sử dụng. Hãy sao lưu dữ liệu quan trọng và chạy `verify` trước khi xoá media gốc.
- Người dùng có trách nhiệm tuân thủ bản quyền và giấy phép của media, font, nhạc và hiệu ứng trong project khi chia sẻ file `.ccpack`.
