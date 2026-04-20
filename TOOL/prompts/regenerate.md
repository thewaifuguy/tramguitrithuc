# Regenerate instruction (appended to Writer user message when retry)

Bản chapter trước đã bị reviewer **reject**. Lý do reject:

**Mã lỗi:** {reason_code}
**Diễn giải:** {reason_label}
**Ghi chú của reviewer:** {note}

---

Bản cũ (KHÔNG copy nguyên xi, chỉ dùng để biết lỗi nằm ở đâu):

```
{previous_content}
```

---

## Yêu cầu viết lại
1. Viết lại **toàn bộ** chapter, fix đúng lỗi đã nêu.
2. Giữ nguyên **cấu trúc heading** và **cùng topic**.
3. Nếu lỗi là `too_generic` hoặc `missing_examples` → thêm nhiều ví dụ thực tế học sinh VN (tên trường, môn học, tình huống cụ thể).
4. Nếu lỗi là `too_long` → cắt bớt ý phụ, giữ core insight, < 2500 từ.
5. Nếu lỗi là `too_short` → mở rộng các section ngắn, thêm ví dụ + bài tập, > 2200 từ.
6. Nếu lỗi là `wrong_tone` → đọc lại yêu cầu xưng hô "cậu"/"bố mẹ", tone không giáo điều.
7. Nếu lỗi là `factual_error` → xóa số liệu/tên người không chắc chắn, thay bằng cách nói chung chung.
8. Nếu lỗi là `boring_hook` → viết mở bài mới hoàn toàn, bắt đầu bằng 1 tình huống CỤ THỂ.
9. Nếu lỗi là `bad_structure` → bám sát cấu trúc heading trong system prompt.

Output vẫn là markdown thuần, có 2-4 tag `<!-- IMAGE_PROMPT: ... -->`. Không giải thích ngoài lề.
