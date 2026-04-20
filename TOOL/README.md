# GCED Tool

Hệ thống 3 AI agent cho dự án GCED. Xem [BUILD_PLAN.md](../Docs/BUILD_PLAN.md) để hiểu roadmap đầy đủ.

## Trạng thái hiện tại

- **Phase 1** ✅ — Writer Agent sinh chapter markdown
- **Phase 2** 🚧 — Firebase lưu draft + Streamlit dashboard approve/reject/regenerate

## Setup lần đầu

### 1. Tạo virtual environment

```powershell
cd "d:\GCED PROJECT\TOOL"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Cài dependencies

```powershell
pip install -r requirements.txt
```

### 3. Setup Gemini API key (Phase 1)

- Lấy key từ https://aistudio.google.com/ → "Get API key"
- Paste vào file `.env`, dòng `GEMINI_API_KEY=`

### 4. Setup Firebase (Phase 2)

1. Vào https://console.firebase.google.com/
2. **Add project** → đặt tên (ví dụ: `gced-prod`) → tắt Google Analytics (không cần) → Create
3. Sidebar trái → **Build → Firestore Database** → **Create database** → **Start in production mode** → chọn region `asia-southeast1` (Singapore, gần VN nhất) → Enable
4. Sidebar trái → ⚙️ **Project settings** → tab **Service accounts** → **Generate new private key** → tải file JSON về
5. Đổi tên file JSON thành `firebase-key.json`, copy vào `d:\GCED PROJECT\TOOL\`
6. Mở Firestore Console → tab **Rules** → tạm thời cho phép read/write (test mode):
   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /{document=**} {
         allow read, write: if true;
       }
     }
   }
   ```
   ⚠️ Rules này mở hoàn toàn, chỉ dùng cho MVP local. Sau này khi deploy cloud sẽ siết lại.

## Chạy

### Sinh 1 chapter mới (lưu vào Firestore)

```powershell
python scripts/run_writer.py --topic "Pomodoro cho học sinh hay trì hoãn"
```

### Sinh chapter nhưng KHÔNG lưu Firestore (test Phase 1)

```powershell
python scripts/run_writer.py --topic "..." --no-firestore
```

### Mở dashboard duyệt bài

```powershell
streamlit run dashboard/app.py
```

Dashboard mở tại http://localhost:8501. Có 4 tab: Pending / Approved / Rejected / Escalated.

## Flow Phase 2

1. Chạy `run_writer.py` → draft xuất hiện ở tab **Pending**
2. Vào dashboard, đọc draft
3. Bấm **Approve** → chapter chuyển qua tab Approved, sẵn sàng cho Phase 3 (PDF export)
4. Bấm **Reject** → chọn lý do (dropdown) + ghi chú → Writer tự regenerate → draft mới xuất hiện ở Pending
5. Nếu reject 3 lần cùng chapter → chuyển qua **Escalated**, cần xử lý thủ công

## Cấu trúc project

```
TOOL/
├── .env                   # API keys (KHÔNG commit)
├── firebase-key.json      # Firebase service account (KHÔNG commit)
├── requirements.txt
├── config.py              # model names, paths, env loader
│
├── agents/
│   ├── base.py            # BaseAgent wrap LiteLLM
│   └── writer.py          # Writer Agent + regenerate
│
├── db/
│   ├── schemas.py         # Pydantic: ChapterDraft, RejectReason, ...
│   └── firestore_client.py # Firebase CRUD
│
├── dashboard/
│   └── app.py             # Streamlit UI (tab pending/approved/rejected/escalated)
│
├── prompts/
│   ├── writer_system.md
│   └── regenerate.md
│
├── scripts/
│   └── run_writer.py
│
└── output/                # Local markdown backup (gitignored)
```

## Troubleshooting

**403 PERMISSION_DENIED khi gọi Gemini**
→ Máy có sẵn `GEMINI_API_KEY` cũ trong env hệ thống. Đã fix bằng `load_dotenv(override=True)` trong `config.py`.

**Unicode error trên terminal Windows**
→ Đã fix trong `scripts/run_writer.py` bằng `sys.stdout.reconfigure(encoding="utf-8")`.

**"Firebase key not found"**
→ Tải service account JSON, đổi tên thành `firebase-key.json`, copy vào TOOL folder.

**Streamlit cache issue**
→ Refresh browser hoặc bấm "Rerun" trong Streamlit toolbar.

## Checklist Phase 2

- [ ] Tạo Firebase project + enable Firestore
- [ ] Download `firebase-key.json` vào TOOL folder
- [ ] Cài `pip install -r requirements.txt` (có firebase-admin + streamlit)
- [ ] Chạy `python scripts/run_writer.py --topic "..."` → verify có doc mới trong Firestore Console
- [ ] Chạy `streamlit run dashboard/app.py` → thấy draft ở tab Pending
- [ ] Test reject với 1 lý do → verify draft mới xuất hiện
- [ ] Test reject 3 lần liên tiếp cùng chapter → verify escalate
- [ ] Test approve → verify chuyển qua tab Approved
