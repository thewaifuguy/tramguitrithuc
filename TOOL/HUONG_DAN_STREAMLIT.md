# Hướng dẫn deploy Streamlit Cloud — GCED Tool

Làm **đủ thứ tự** bên dưới. Bỏ qua mục tạo API key mới nếu key của bạn vẫn dùng được trên https://aistudio.google.com/

---

## Bước 1 — Push code mới lên GitHub

Trên máy (PowerShell):

```powershell
cd "c:\Users\milky\Documents\GCED\GCED"

git add TOOL/config.py TOOL/dashboard/app.py TOOL/dashboard/theme.py TOOL/.gitignore
git add TOOL/.env.example TOOL/.streamlit/secrets.toml.example
git add "TOOL/TRẠM_GỬI_TRI_THỨC_-_ĐÁNH_THỨC_TƯ_DUY.pdf"
git add TOOL/HUONG_DAN_STREAMLIT.md

git status
git commit -m "Fix Streamlit secrets loading and sample handbook deploy"
git push origin main
```

Đợi GitHub cập nhật xong (1–2 phút).

---

## Bước 2 — Cấu hình app trên Streamlit Cloud

Vào https://share.streamlit.io → chọn app GCED → **⚙️ Settings**:

| Mục | Giá trị đúng |
|-----|----------------|
| **Repository** | Repo GitHub chứa folder `TOOL` |
| **Branch** | `main` |
| **Main file path** | `TOOL/dashboard/app.py` |
| **Python version** | `3.11` (hoặc 3.10+) |

**Advanced settings** (nếu có):

| Mục | Giá trị |
|-----|---------|
| **Requirements file** | `requirements.txt` (file ở **thư mục gốc repo**, cùng cấp với `TOOL/`) |

Sau khi sửa → **Save** → **Reboot app**.

---

## Bước 3 — Secrets (quan trọng nhất)

**Settings → Secrets** — xóa hết nội dung cũ, dán **chính xác** (1 dòng, TOML):

```toml
GEMINI_API_KEY = "DÁN_KEY_CỦA_BẠN_VÀO_ĐÂY"
```

Quy tắc:

- Tên biến: `GEMINI_API_KEY` (viết hoa, gạch dưới)
- Có dấu `=` và dấu ngoặc kép `"..."` quanh key
- **Không** dùng format `.env` (`GEMINI_API_KEY=abc` không có ngoặc)
- **Không** thêm `[secrets]` hay section khác
- Không có khoảng trắng thừa trước/sau key

Ví dụ đúng:

```toml
GEMINI_API_KEY = "AIzaSyAbc123..."
```

**Save** → đợi 1 phút → **Manage app → Reboot app** (bắt buộc).

---

## Bước 4 — Kiểm tra trên app sau Reboot

Mở app → sidebar trái, cuối phần **🤖 Hệ thống**:

| Hiển thị | Ý nghĩa |
|----------|---------|
| ✅ `🔑 Gemini API: Đã nạp key` + `AIzaSy...xxxx` | Secrets OK |
| ❌ `Gemini API: chưa cấu hình` | Secrets sai tên / chưa reboot / chưa push code |
| `📖 Handbook mẫu PDF: có sẵn` | File PDF mẫu đã lên GitHub |
| `📖 Handbook mẫu PDF: chưa có` | Chưa push file PDF (làm Bước 1 lại) |

---

## Bước 5 — Chạy local (tùy chọn)

```powershell
cd "c:\Users\milky\Documents\GCED\GCED\TOOL"
copy .env.example .env
# Sửa .env: GEMINI_API_KEY=your_key_here

.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Hoặc dùng secrets local:

```powershell
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
# Sửa file secrets.toml, rồi streamlit run dashboard/app.py
```

---

## Bước 6 — Demo không cần API (khi thi / mất mạng)

Tab **Demo** → nút **⚡ Handbook mẫu: Đánh thức tư duy** → tải PDF `TRẠM_GỬI_TRI_THỨC_-_ĐÁNH_THỨC_TƯ_DUY.pdf` ngay, không cần Gemini.

Pipeline demo: nếu API lỗi vẫn fallback sang handbook mẫu + demo data.

---

## Xử lý lỗi thường gặp

### `GEMINI_API_KEY not set`

1. Secrets đúng format TOML (Bước 3)
2. **Reboot app** sau khi Save Secrets
3. Main file = `TOOL/dashboard/app.py` (Bước 2)
4. Đã push `config.py` + `app.py` mới (Bước 1)
5. Xem sidebar: vẫn đỏ → Secrets chưa vào app (sai app / chưa reboot)

### `API đang chậm... Demo Data dự phòng`

- Key **chưa** đọc được → sửa Secrets + reboot
- Hoặc Gemini trả lỗi khác (quota, model) → app vẫn chạy bằng demo data
- Kiểm tra sidebar: nếu key ✅ mà vẫn fallback → xem lỗi chi tiết trong `❌` dưới warning

### `Your API key was reported as leaked`

- Key đã bị Google khóa → **bắt buộc** tạo key mới (trường hợp này khác mục bạn bỏ qua)

### Handbook mẫu không tải được trên Cloud

```powershell
git add -f "TOOL/TRẠM_GỬI_TRI_THỨC_-_ĐÁNH_THỨC_TƯ_DUY.pdf"
git commit -m "Add sample handbook PDF for Streamlit"
git push
```

File ~9MB — push có thể mất vài phút.

---

## Checklist nhanh

- [ ] Push code + PDF mẫu lên GitHub  
- [ ] Main file: `TOOL/dashboard/app.py`  
- [ ] Secrets: `GEMINI_API_KEY = "..."` (TOML)  
- [ ] Reboot app  
- [ ] Sidebar: 🔑 Gemini ✅  
- [ ] Sidebar: 📖 Handbook mẫu có sẵn  
