# Trạm gửi tri thức — Demo Plan (7 ngày)

> Plan này thay thế plan production trước đây. Scope đã thu hẹp cho **demo cuộc thi cấp trường**, deadline 7 ngày (2026-04-15 → 2026-04-22).

---

## 📌 Context

**Mục tiêu:** Live demo cho judge cuộc thi cấp trường. Hệ thống phải **chạy thật end-to-end** trước mặt judge, không mock toàn bộ. UI cần **đẹp, branded**, không bị crash giữa demo.

**KHÔNG phải:** sản phẩm production để bán dài hạn. Sau khi thi xong, nếu muốn lên production → switch SQLite sang Firebase + setup cloud (1 file thay đổi). Nhưng đó là chuyện sau.

**Brand:** Trạm gửi tri thức — dự án giáo dục phi lợi nhuận, AI hỗ trợ làm handbook phương pháp học cho học sinh cấp 2 hay trì hoãn/mất tập trung.

**User skill:** zero Python — toàn bộ code do AI assistant viết, user setup môi trường + duyệt nội dung.

---

## 🎨 Brand & Visual

| | Value |
|---|---|
| Tên hiển thị | **Trạm gửi tri thức** |
| Logo | `TOOL/dashboard/assets/logo.png` (user upload) |
| Primary color | `#2C5F5C` (dark teal — núi) |
| Background | `#F5EFDC` (cream — nền logo) |
| Accent | `#E8A33D` (vàng cam — phong thư) |
| Vibe | Warm, charity-leaning, không corporate/techy |

Áp dụng: Streamlit theme, PDF handbook layout, slide thuyết trình.

---

## 🧱 Tech stack (rút gọn cho demo)

| Layer | Công nghệ | Đổi so với plan cũ |
|-------|-----------|---------------------|
| Language | Python 3.11+ | giữ |
| LLM | Gemini 2.5 Flash (free) | giữ |
| Storage | **SQLite** (file local) | ❌ Bỏ Firebase (rủi ro internet/auth giữa demo) |
| UI | Streamlit (localhost) | ❌ Bỏ Streamlit Cloud deploy |
| Image gen | Pollinations.ai (free) | giữ |
| PDF | `weasyprint` hoặc `markdown-pdf` | giữ |
| Facebook | **MOCK preview** (UI giống FB thật) | ❌ Bỏ real Graph API (cần App Review, risky) |
| Scheduling | Click button thủ công | ❌ Bỏ GitHub Actions cron |
| Logging | In-app SQLite log | ❌ Bỏ Notion |

**Tổng chi phí: $0** (tất cả miễn phí, không cần internet trừ gọi Gemini API).

---

## 📁 Cấu trúc project (cập nhật)

```
d:\GCED PROJECT\
├── Docs/
│   └── BUILD_PLAN.md              # file này
└── TOOL/
    ├── .env                        # GEMINI_API_KEY
    ├── .gitignore
    ├── requirements.txt
    ├── config.py
    ├── data/
    │   └── gced.db                 # SQLite (gitignored)
    │
    ├── agents/
    │   ├── base.py                 # ✅ đã có
    │   ├── writer.py               # ✅ đã có (+ regenerate)
    │   └── media.py                # 🆕 Day 3
    │
    ├── db/
    │   ├── schemas.py              # ✅ đã có (Pydantic)
    │   └── storage.py              # 🆕 SQLite wrapper (thay firestore_client.py)
    │
    ├── prompts/
    │   ├── writer_system.md        # ✅ đã có
    │   ├── regenerate.md           # ✅ đã có
    │   └── media_system.md         # 🆕 Day 3
    │
    ├── integrations/
    │   ├── pollinations.py         # 🆕 Day 4
    │   └── facebook_mock.py        # 🆕 Day 3 (preview UI, không call API)
    │
    ├── export/
    │   └── pdf_builder.py          # 🆕 Day 4
    │
    ├── dashboard/
    │   ├── app.py                  # ✅ đã có (cần polish + sửa import)
    │   ├── theme.py                # 🆕 brand colors, custom CSS
    │   └── assets/
    │       ├── logo.png            # 🆕 user upload
    │       └── style.css           # 🆕 Day 1
    │
    ├── scripts/
    │   ├── run_writer.py           # ✅ đã có (sửa import)
    │   └── seed_demo_data.py       # 🆕 Day 5 (backup data nếu API fail)
    │
    └── output/                     # PDF, ảnh sinh ra (gitignored)
```

---

## 🗓️ 7-Day Schedule

### Day 1 (hôm nay) — Foundation
**Mục tiêu:** Bỏ Firebase, dùng SQLite. UI có brand cơ bản. Tránh fail giữa demo.

- Tạo `db/storage.py` thay `db/firestore_client.py` — cùng interface (save_draft, list_by_status, approve_draft, reject_draft, log_approval), chỉ swap backend
- Xóa `db/firestore_client.py`, sửa imports trong `dashboard/app.py` + `scripts/run_writer.py`
- Update `requirements.txt`: bỏ `firebase-admin`, không cần thêm gì (sqlite3 built-in Python)
- Tạo `dashboard/theme.py` + `dashboard/assets/style.css` với colors `#2C5F5C` + `#F5EFDC`
- Đổi title dashboard → "Trạm gửi tri thức", add logo header
- Tạo `.streamlit/config.toml` để Streamlit dùng theme color

**Verify:** `streamlit run dashboard/app.py` → thấy UI có logo + màu cream/teal, click pending tab không crash.

---

### Day 2 — Polish UI + cleanup workflow
**Mục tiêu:** UI đẹp đủ để demo. Reject loop gọn (max 1 retry thay 3).

- Layout dashboard: 2 cột (sidebar = brand info + stats, main = drafts)
- Đổi MAX_RETRY = 1 (demo không có time cho 3 retry)
- Bỏ tab "Escalated" (không có trong demo)
- Add 1 nút "✨ Tạo chapter mới" trên header → form nhập topic → generate trực tiếp từ UI (không cần CLI)
- Add metric cards: số chapter hôm nay, tokens dùng, chapter approved
- Test reject → regenerate → approve flow đầy đủ

**Verify:** Demo full flow generate → review → approve qua UI, không cần touch terminal.

---

### Day 3 — Media Agent + Mock FB Preview
**Mục tiêu:** Sau khi approve chapter, sinh được 3-5 post FB và preview đẹp.

- `agents/media.py`: nhận chapter approved → sinh 3 post FB (carousel idea, short post, reel script) bằng Gemini Flash
- `prompts/media_system.md`: tone FB tiếng Việt, CTA cho phụ huynh
- `db/schemas.py`: thêm `PostDraft` schema (type, content, image_prompt, status)
- `db/storage.py`: thêm CRUD cho posts
- `integrations/facebook_mock.py`: render HTML giống Facebook post (avatar Trạm gửi tri thức, header, caption, fake like/comment count) → embed vào Streamlit
- Dashboard: tab "📱 Posts" — Gồm 2 phần: Chờ duyệt (Drafts) và Sẵn sàng đăng (Ready to post). User copy nội dung thủ công từ tab Sẵn sàng đăng.

**Verify:** Approve 1 chapter → vào tab Posts → có 3 post draft → approve 1 → preview hiện ra đẹp như FB thật.

---

### Day 4 — Pollinations + PDF đẹp
**Mục tiêu:** Output handbook PDF có layout sách thật, font tiếng Việt OK, ảnh minh họa từ AI.

- `integrations/pollinations.py`: gọi `https://image.pollinations.ai/prompt/{prompt}` → download PNG
- `export/pdf_builder.py`:
  - Parse `<!-- IMAGE_PROMPT: ... -->` trong markdown
  - Sinh ảnh từng prompt
  - Replace tag bằng `![alt](path)`
  - Convert markdown → HTML (template với brand colors)
  - HTML → PDF qua `weasyprint`
  - CSS: A5 page, font Be Vietnam Pro / Noto Sans Vietnamese, header/footer có logo
- Dashboard: tab Approved → button "📄 Xuất PDF" → preview PDF inline + download

**Verify:** Click "Xuất PDF" → vài chục giây sau có file PDF mở được, layout đẹp, ảnh khớp nội dung, font tiếng Việt không lỗi.

---

### Day 5 — Demo Mode + Sample Data Backup
**Mục tiêu:** Có "Demo Mode" — 1 nút chạy full pipeline cho judge. Có backup data nếu API down.

- `scripts/seed_demo_data.py`: pre-generate 2-3 chapter + posts + PDF, lưu vào DB với tag `demo=True` → nếu live demo API fail vẫn show được
- Dashboard: thêm tab "🎬 Demo Mode" — 1 page riêng:
  - Bước 1: nhập topic → generate (live)
  - Bước 2: review draft (auto-scroll, 5s)
  - Bước 3: approve → sinh post FB (live)
  - Bước 4: approve post → preview FB
  - Bước 5: xuất PDF → preview
  - Tổng thời gian: ~90s
- Add fallback: nếu Gemini call > 30s không response → switch sang sample data, hiện banner "Đang dùng demo data do API chậm"

**Verify:** Bấm "Run Demo" → 90s sau có full flow xong, không cần thao tác giữa chừng.

---

### Day 6 — End-to-end Rehearsal
**Mục tiêu:** Chạy thử 5 lần liên tiếp không lỗi. Tìm và fix mọi bug.

- Tự bạn chạy demo flow 5 lần với 5 topic khác nhau
- Ghi lại mọi điểm nghẽn (chậm, lỗi, UI confusing)
- Fix bug
- Optimize: cache Gemini response, prefetch ảnh
- Viết **demo script** (1 trang) — bạn cầm trong tay khi thuyết trình:
  - Câu mở đầu (15s)
  - Lúc nào click cái gì
  - Câu trả lời cho 5 câu hỏi judge thường hỏi
- Backup screenshot từng bước (phòng hờ máy chiếu lỗi)

**Verify:** 5 lần chạy không crash, mỗi lần dưới 2 phút.

---

### Day 7 — Dry Run + Slide
**Mục tiêu:** Sẵn sàng 100%. Slide thuyết trình xong.

- Dry run trên **đúng máy sẽ dùng để demo** (laptop, projector, mạng wifi venue nếu test được)
- Test offline mode (rút mạng → demo data vẫn show được)
- Slide 5-7 trang:
  1. Title + logo
  2. Problem (học sinh nghèo cần sách, scale là vấn đề)
  3. Solution (AI sinh handbook, người duyệt, charity model)
  4. Live demo (chuyển sang Streamlit)
  5. Tech stack + tại sao chọn (đơn giản, miễn phí, scale được)
  6. Impact metric (1 sách/tháng, X students dự kiến)
  7. Q&A / liên hệ
- Pack toàn bộ vào USB backup (code + DB + slide + screenshots)

**Verify:** Bạn tự thuyết trình full 5-7 phút, không vấp.

---

## 🎬 Demo Script (Day 6 sẽ viết chi tiết)

```
[0:00–0:30] Mở đầu
"Em xin giới thiệu Trạm gửi tri thức — dự án giáo dục phi lợi nhuận
dùng AI để sản xuất handbook phương pháp học, bán cho phụ huynh,
lợi nhuận in sách tặng học sinh nghèo."

[0:30–1:00] Live demo bắt đầu
- Mở dashboard
- Bấm "Tạo chapter mới"
- Nhập topic → Generate

[1:00–2:00] Approve flow
- Đọc draft sinh ra (~30s)
- Bấm Approve
- Tab Posts → 3 post FB sinh ra
- Approve 1 post → preview FB hiện ra

[2:00–2:30] Output cuối
- Tab Approved → bấm "Xuất PDF"
- PDF mở ra, cuộn nhanh

[2:30–5:00] Q&A
```

---

## ⚠️ Risks + Mitigations cho live demo

| Risk | Mitigation |
|------|-----------|
| Gemini API rate limit | Pre-warm cache hôm trước, có sample data backup |
| Wifi venue chậm | Dùng hotspot điện thoại, có offline demo data |
| Streamlit crash giữa demo | Mở sẵn 2 tab browser, có sẵn URL localhost |
| Pollinations down | Pre-generate ảnh từ Day 5, lưu local |
| Bị hỏi về Facebook thật | "Đã build integration, demo dùng preview cho an toàn, có video demo riêng" |
| Bị hỏi pháp lý charity | "Đang trong giai đoạn xin ĐKKD doanh nghiệp xã hội theo Luật DN 2020" |
| Quên thao tác | Cầm script in giấy, có screenshot từng bước trên USB |

---

## 📊 Trạng thái hiện tại (2026-04-15)

| Phase | Trạng thái |
|-------|-----------|
| Writer Agent | ✅ Đã có, chất lượng OK với Gemini Flash |
| Database (cần switch SQLite) | 🚧 Đang chạy code Firebase, sẽ thay |
| Dashboard (cần polish) | 🚧 UI default, chưa branded |
| Media Agent | ⏳ Chưa làm |
| FB Mock Preview | ⏳ Chưa làm |
| Pollinations + PDF | ⏳ Chưa làm |
| Demo Mode | ⏳ Chưa làm |
| Slide + script | ⏳ Chưa làm |

---

## 🚀 Next action

Day 1 bắt đầu ngay sau khi:
1. ✅ User save logo vào `TOOL/dashboard/assets/logo.png`
2. ✅ User confirm Mock FB OK (recommend Mock)

Sau đó AI assistant chạy:
- Tạo `db/storage.py` (SQLite)
- Xóa `db/firestore_client.py`
- Update imports
- Apply theme + logo
- Test full flow

---

## 📦 Sau cuộc thi (nếu muốn production)

Notes lưu trữ — KHÔNG làm trong 7 ngày này:

- Switch SQLite → Firebase (chỉ thay `db/storage.py`, schema giữ nguyên)
- Setup Facebook Graph API + App Review (~1-2 tuần)
- Deploy Streamlit Community Cloud
- GitHub Actions cron cho daily/weekly
- Notion integration cho team logging
- Analyzer Agent cho weekly insights
- Đăng ký doanh nghiệp xã hội (Luật DN 2020) hoặc partner với quỹ tự thiện
- Niche down content + xây audience phụ huynh trên Facebook
