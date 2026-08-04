# Hướng dẫn demo RAG Pipeline

Tài liệu dùng cho buổi demo ngày **04/08/2026**. Chạy lệnh từ thư mục gốc của dự án.

## 1. Trạng thái đã xác minh trước buổi demo

| Hạng mục | Kết quả |
|---|---|
| Toàn bộ automated tests | **41 passed** |
| Streamlit AppTest | PASS: có sidebar, 1 chat input, 5 button và 1 slider |
| Streamlit health check | **HTTP 200** tại `/_stcore/health` |
| Kiểm thử UI end-to-end | PASS |
| Retrieval trong lần kiểm thử | `pageindex` structural fallback |
| Generation trong lần kiểm thử | **LLM** qua OpenAI |
| Nguồn trả về | 5 chunks, có source/citation expanders |
| Độ trễ tham khảo | Khoảng 4–6 giây, phụ thuộc mạng và OpenAI |

Câu hỏi end-to-end đã thử thành công:

```text
Tôi theo dõi hành trình đơn hàng ở đâu?
```

Kết quả kiểm thử ghi nhận: `Retrieval=pageindex`, `Generation=LLM`, độ trễ `5.55s`, `Chunks=5`.

## 2. Khởi động nhanh trước khi trình chiếu

### Terminal 1 — kiểm tra dự án

```powershell
Set-Location "C:\Users\Tutran\OneDrive\Máy tính\VInAI\K4-Day08-RAG-Pipeline"
.\.venv\Scripts\Activate.ps1
python --version
python -m pytest -q
```

Kết quả mong đợi:

```text
41 passed
```

Nếu chưa có `.venv`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Kiểm tra cấu hình LLM

File `.env` cần có cấu hình tương tự dưới đây, nhưng không được chiếu hoặc đọc API key trước lớp:

```dotenv
OPENAI_API_KEY=KEY_MOI_CUA_BAN
LLM_MODEL=gpt-4o-mini
```

API key từng gửi qua chat hoặc nơi công khai cần được thu hồi và thay bằng key mới trước khi demo. Tuyệt đối không commit `.env`.

### Build lại index khi cần

```powershell
python -m src.task4_chunking_indexing
```

Index mặc định được sinh tự động nên có thể bỏ qua bước này nếu không thay dữ liệu.

### Terminal 2 — chạy giao diện

```powershell
python -m streamlit run app.py
```

Mở trình duyệt tại:

```text
http://localhost:8501
```

Nếu cổng 8501 đang bận:

```powershell
python -m streamlit run app.py --server.port 8502
```

## 3. Kịch bản demo đề xuất trong 7 phút

### 0:00–0:40 — Giới thiệu bài toán

> Nhóm xây dựng chatbot hỗ trợ thương mại điện tử. Hệ thống chỉ trả lời dựa trên tập tài liệu chính sách và bài hướng dẫn đã thu thập, đồng thời hiển thị nguồn để người dùng kiểm chứng.

Nêu ba điểm chính:

1. Kết hợp Semantic Search và BM25 thay vì chỉ dùng một retriever.
2. Gộp thứ hạng bằng RRF, có reranking và structural fallback.
3. LLM sinh câu trả lời có citation; khi API lỗi vẫn có offline extractive fallback.

### 0:40–1:30 — Trình bày pipeline

```text
Raw legal/news
    → Markdown chuẩn hóa
    → Chunking + indexing
    → Semantic Search ┐
                      ├→ RRF → Rerank → LLM + Citation
    → BM25 Search ────┘             ↘ Structural fallback
```

Giải thích ngắn:

- Semantic Search tìm đoạn tương đồng về ý nghĩa.
- BM25 mạnh với từ khóa chính xác như COD, OTP hoặc tên chính sách.
- RRF cộng thứ hạng của hai danh sách với `k=60`.
- Pipeline dùng điểm dense gốc và threshold `0.16` để quyết định fallback, không dùng nhầm điểm RRF.

### 1:30–4:30 — Live demo Streamlit

1. Giới thiệu sidebar:
   - Slider `Số đoạn bằng chứng`, mặc định 5.
   - Toggle hiển thị query sau mở rộng.
   - Các câu hỏi gợi ý.
   - Nút xóa hội thoại.
2. Hỏi câu đầu tiên:

   ```text
   Shopee hỗ trợ những phương thức thanh toán nào?
   ```

3. Chỉ vào bốn chỉ số dưới câu trả lời:
   - `Retrieval`: nhánh truy xuất được sử dụng.
   - `Generation`: nên hiện `LLM` khi OpenAI hoạt động.
   - `Độ trễ`: thời gian xử lý truy vấn.
   - `Số chunks`: số đoạn bằng chứng được đưa vào context.
4. Mở `Nguồn tham khảo` và chỉ ra:
   - Tên file nguồn.
   - Loại retrieval và score.
   - Đoạn bằng chứng có highlight từ khóa.
5. Hỏi follow-up để demo conversation memory:

   ```text
   Sau khi đã đặt hàng thì tôi có đổi phương thức đó được không?
   ```

6. Bật `Hiện query sau mở rộng` để giải thích hệ thống ghép ngữ cảnh hội thoại vào truy vấn follow-up.

### 4:30–5:30 — Demo một nghiệp vụ khác

Chọn một câu trong sidebar:

```text
Cần bằng chứng gì khi hàng bị hỏng?
```

Kết quả mong đợi phải đề cập ảnh/video của kiện hàng, nhãn vận chuyển, bao bì, sản phẩm và vị trí hư hỏng; nguồn phù hợp là `refund_evidence_guide.md`.

### 5:30–6:20 — Trình bày evaluation

Dataset có **16 golden cases**, so sánh:

- Config A: Hybrid + RRF + reranking + structural fallback.
- Config B: Dense-only.

| Metric | Config A | Config B |
|---|---:|---:|
| Faithfulness | 1.0000 | 1.0000 |
| Answer Relevance | 0.3148 | 0.3094 |
| Context Recall | 0.8557 | 0.8715 |
| Context Precision | 0.6250 | 0.6000 |
| Average | **0.6989** | 0.6952 |

Kết luận đúng để trình bày: Config A có macro average và context precision cao hơn; Config B có context recall nhỉnh hơn. Đây là **RAGAS-compatible deterministic proxy**, không phải điểm từ RAGAS LLM judge chính thức.

### 6:20–7:00 — Tổng kết

> Hệ thống đã hoàn thành Task 1–10, giao diện nhóm, evaluation và automated QA. Điểm mạnh là kết hợp nhiều retrieval strategy, citation có thể mở kiểm tra, conversation memory và khả năng tiếp tục trả lời bằng chế độ offline khi dịch vụ LLM không khả dụng.

## 4. Bộ câu hỏi demo an toàn

| Câu hỏi | Nguồn mong đợi |
|---|---|
| Shopee hỗ trợ những phương thức thanh toán nào? | `payment_methods_policy.md` |
| Có thể đổi phương thức thanh toán sau khi đã đặt hàng không? | `change_payment_guide.md` |
| Cần chuẩn bị bằng chứng gì khi yêu cầu hoàn tiền vì hàng bị hỏng? | `refund_evidence_guide.md` |
| Tôi theo dõi hành trình đơn hàng ở đâu? | `order_tracking_guide.md` |
| Người bán không được đăng bán những sản phẩm nào? | `seller_listing_privacy_policy.md` |
| Tôi có nên cung cấp OTP cho nhân viên hỗ trợ để nhận hoàn tiền không? | `account_privacy_guide.md` |

Không dùng câu hỏi ngoài tập dữ liệu ngay ở đầu demo. Chỉ demo câu hỏi ngoài domain khi còn thời gian và đã giải thích trước về fallback.

## 5. Phân vai khi thuyết trình

| Thành viên | GitHub | Nội dung trình bày |
|---|---|---|
| Bùi Tùng Lâm — 2A202601676 | `buitunglam308work-stack` | Role 1 — Team Leader & Architect: điều phối, review và thuyết trình tổng quan |
| Chu Tâm Vũ — 2A202601360 | `ctz1310204` | Role 2 — Data & Retrieval: Task 1, 4, 7, 9 và giải đáp kỹ thuật |
| Nguyễn Đức Anh Tuấn — 2A202601618 | `nt15032` | Role 3 — Frontend & Chatbot: Task 2, 5, 8, 10 và live demo UI |
| Trần Anh Tú — 2A202601674 | `tutran0401` | Role 4 — Evaluation & QA: Task 3, 6, citation QA và báo cáo A/B |

Mỗi người nên nói khoảng 60–90 giây; Nguyễn Đức Anh Tuấn thao tác UI trong lúc các thành viên còn lại giải thích phần mình phụ trách.

## 6. Các câu hỏi phản biện dễ gặp

### Vì sao dùng Hybrid Retrieval?

Semantic Search tìm tương đồng ngữ nghĩa, còn BM25 giữ độ chính xác với từ khóa. RRF hợp nhất hai thứ hạng mà không cần chuẩn hóa hai thang điểm khác nhau.

### Vì sao RRF dùng `k=60`?

Đây là smoothing constant phổ biến giúp giảm ảnh hưởng quá lớn của một vị trí đứng đầu đơn lẻ và làm việc tốt khi hợp nhất nhiều ranked list.

### Khi nào hệ thống fallback?

Khi điểm dense tốt nhất thấp hơn `0.16`, pipeline chuyển sang tìm kiếm cấu trúc theo tài liệu/heading. Nhãn `pageindex` trong cấu hình demo mặc định là structural fallback local; nhóm chưa tuyên bố đó là PageIndex remote API.

### Nếu OpenAI bị lỗi thì sao?

Pipeline không dừng. Nó chuyển sang extractive generation dựa trên các chunks đã truy xuất và UI hiển thị `Generation=OFFLINE`. Trong demo bình thường, nếu key và Internet hoạt động thì UI hiển thị `Generation=LLM`.

### ChromaDB và BGE-M3 đã dùng chưa?

Runtime mặc định đang dùng persistent JSON index và hashing embedding để chạy ổn định offline. ChromaDB và `BAAI/bge-m3` là backend production tùy chọn qua biến môi trường, không nên nói rằng demo mặc định đang dùng chúng.

### Evaluation có phải RAGAS chính thức không?

Không. Báo cáo mặc định là deterministic proxy tương thích bốn nhóm metric của RAGAS để chạy lặp lại trong CI. RAGAS LLM judge là chế độ opt-in và cần môi trường/phí API riêng.

## 7. Xử lý sự cố trong lúc demo

| Hiện tượng | Cách xử lý nhanh |
|---|---|
| `Generation=OFFLINE` | Kiểm tra key mới trong `.env` và Internet; vẫn có thể tiếp tục demo fallback offline |
| OpenAI trả 401 | Key sai/đã thu hồi; thay key mới rồi khởi động lại Streamlit |
| OpenAI trả 429 | Hết quota/rate limit; giải thích cơ chế offline fallback và tiếp tục |
| Không có chunks | Chạy `python -m src.task4_chunking_indexing`, rồi restart app |
| Cổng 8501 bị chiếm | Chạy với `--server.port 8502` |
| UI giữ hội thoại cũ | Nhấn `Xóa hội thoại` trong sidebar |
| Console Windows lỗi tiếng Việt | Chạy `$env:PYTHONIOENCODING="utf-8"` trước lệnh Python |
| Mạng chậm | Dùng câu hỏi đã chuẩn bị; chờ spinner, không gửi lặp nhiều lần |

## 8. Checklist 10 phút trước giờ demo

- [ ] Đổi API key mới nếu key cũ từng bị chia sẻ.
- [ ] Đảm bảo `.env` không được mở trên màn hình trình chiếu.
- [ ] Chạy `python -m pytest -q` và thấy `41 passed`.
- [ ] Chạy Streamlit và mở sẵn `http://localhost:8501`.
- [ ] Thử đúng một câu hỏi, kiểm tra `Generation=LLM`.
- [ ] Mở thử source expander và kiểm tra có citation/chunks.
- [ ] Xóa lịch sử chat trước khi bắt đầu chính thức.
- [ ] Mở sẵn `group_project/evaluation/results.md` ở tab khác.
- [ ] Chuẩn bị hotspot dự phòng.
- [ ] Không chạy crawl, cài package hoặc RAGAS LLM judge trong lúc demo.

## 9. Lệnh khôi phục nhanh nhất

```powershell
Set-Location "C:\Users\Tutran\OneDrive\Máy tính\VInAI\K4-Day08-RAG-Pipeline"
.\.venv\Scripts\Activate.ps1
python -m src.task4_chunking_indexing
python -m pytest -q
python -m streamlit run app.py
```
