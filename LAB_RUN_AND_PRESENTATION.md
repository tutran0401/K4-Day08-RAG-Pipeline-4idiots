# Cách chạy và thuyết trình từng phần của bài Lab RAG Pipeline

Tài liệu này dùng làm kịch bản chung cho cả nhóm khi thuyết trình. Mỗi phần gồm: **mục tiêu**, **lệnh chạy**, **kết quả cần chỉ ra** và **lời trình bày gợi ý**.

## 1. Phân công trình bày

| Thành viên | MSSV | Phần phụ trách |
|---|---|---|
| Bùi Tùng Lâm | 2A202601676 | Role 1 — Team Leader & Architect |
| Chu Tâm Vũ | 2A202601360 | Role 2 — Data & Retrieval Specialist |
| Nguyễn Đức Anh Tuấn | 2A202601618 | Role 3 — Frontend & Chatbot Developer |
| Trần Anh Tú | 2A202601674 | Role 4 — Evaluation & QA Engineer |

## 2. Chuẩn bị môi trường trước khi thuyết trình

Chạy PowerShell tại thư mục dự án:

```powershell
Set-Location "C:\Users\Tutran\OneDrive\Máy tính\VInAI\K4-Day08-RAG-Pipeline"
```

Nếu đã có virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Nếu chưa có:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Kiểm tra môi trường:

```powershell
python --version
python -m pip check
python -m pytest -q
```

Kết quả hiện tại cần đạt:

```text
41 passed
```

File `.env` dùng OpenAI cần có dạng:

```dotenv
OPENAI_API_KEY=KEY_MOI_CUA_BAN
LLM_MODEL=gpt-4o-mini
```

Không mở `.env` khi đang chia sẻ màn hình và không đưa API key thật vào slide, source code hoặc Git.

## 3. Mở đầu bài thuyết trình

### Người trình bày: Bùi Tùng Lâm

Thời lượng gợi ý: 45–60 giây.

### Nội dung trên màn hình

Mở `README.md` hoặc sơ đồ sau:

```text
Legal documents + Help-center articles
                  ↓
          Markdown chuẩn hóa
                  ↓
         Chunking + Embedding
                  ↓
     Semantic Search ─┐
                      ├→ RRF → Rerank → LLM → Answer + Citation
          BM25 ───────┘             ↘ Structural fallback
                  ↓
           Streamlit Chat UI
```

### Lời trình bày gợi ý

> Nhóm em xây dựng một RAG chatbot hỗ trợ các câu hỏi thương mại điện tử như thanh toán, đổi trả, giao hàng, quyền riêng tư và quy định người bán. Pipeline gồm 10 task, bắt đầu từ thu thập dữ liệu, chuẩn hóa, indexing, hybrid retrieval, reranking, fallback và cuối cùng là LLM generation có citation. Hệ thống được thiết kế offline-first để vẫn hoạt động khi dịch vụ bên ngoài gặp lỗi.

## 4. Task 1 — Thu thập tài liệu chính sách

### Người trình bày: Chu Tâm Vũ

### Mục tiêu

- Tạo landing zone cho tài liệu chính sách.
- Tải và kiểm tra file legal dạng PDF/DOC/DOCX.
- Không nhận file rỗng hoặc extension không hợp lệ.

### File chính

```text
src/task1_collect_legal_docs.py
data/landing/legal/
```

### Lệnh chạy

```powershell
python -m src.task1_collect_legal_docs
```

### Kết quả cần chỉ ra

- Thư mục `data/landing/legal/` hiện có 3 policy documents.
- Hàm `download_file()` kiểm tra URL, extension và kích thước file.
- Hàm `inventory()` hỗ trợ audit danh sách tài liệu.

### Lời trình bày gợi ý

> Ở Task 1, em xây dựng landing zone để lưu tài liệu chính sách gốc. Hàm download kiểm tra giao thức HTTP, phần mở rộng và kích thước nhằm tránh đưa file lỗi vào pipeline. Dự án hiện có ba tài liệu về thanh toán, trả hàng hoàn tiền và quy định người bán.

## 5. Task 2 — Crawl bài hướng dẫn và tin tức

### Người trình bày: Nguyễn Đức Anh Tuấn

### Mục tiêu

- Crawl tối thiểu 5 bài help-center.
- Lưu riêng từng bài dưới dạng JSON có metadata.
- Có fallback khi Crawl4AI không khả dụng.

### File chính

```text
src/task2_crawl_news.py
data/landing/news/
requirements-crawl.txt
```

### Lệnh chạy

```powershell
python -m src.task2_crawl_news
```

Task này cần Internet. Không nên crawl lại ngay trong live demo; hãy dùng 10 JSON snapshot đã có sẵn để tránh lỗi mạng hoặc website thay đổi.

### Kết quả cần chỉ ra

Mỗi JSON có các trường chính:

```text
url, title, crawl_date, content
```

### Lời trình bày gợi ý

> Task 2 thu thập các bài hướng dẫn thực tế. Crawler ưu tiên Crawl4AI nhưng có requests fallback, do đó pipeline không phụ thuộc duy nhất vào browser crawler. Mỗi bài được lưu thành một JSON riêng cùng URL, tiêu đề, ngày crawl và nội dung để truy xuất nguồn về sau.

## 6. Task 3 — Chuẩn hóa toàn bộ dữ liệu sang Markdown

### Người trình bày: Trần Anh Tú

### Mục tiêu

- Chuyển legal documents và news JSON sang một định dạng thống nhất.
- Giữ metadata để phục vụ filtering và citation.

### File chính

```text
src/task3_convert_markdown.py
data/standardized/legal/
data/standardized/news/
```

### Lệnh chạy

```powershell
python -m src.task3_convert_markdown
```

### Kết quả mong đợi

```text
Converted 13 documents into ...\data\standardized
```

### Lời trình bày gợi ý

> Task 3 giải quyết vấn đề dữ liệu nhiều định dạng bằng cách chuyển tất cả về Markdown. Sau bước này, pipeline có 13 tài liệu chuẩn hóa. Metadata nguồn, ngày crawl và vai trò khách hàng vẫn được giữ lại để dùng trong retrieval và citation.

### Chuyển phần

> Sau khi dữ liệu đã thống nhất, nhóm chuyển sang giai đoạn chia nhỏ tài liệu và xây dựng hai nhánh tìm kiếm.

## 7. Task 4 — Chunking, embedding và indexing

### Người trình bày: Chu Tâm Vũ

### Mục tiêu

- Đọc toàn bộ Markdown đã chuẩn hóa.
- Chia văn bản thành chunks có overlap.
- Sinh embedding và persistent index có thể tái sử dụng.

### File chính

```text
src/task4_chunking_indexing.py
data/index/chunks.json
```

### Cấu hình đang chạy

| Tham số | Giá trị |
|---|---:|
| Chunk size | 700 ký tự |
| Chunk overlap | 100 ký tự |
| Embedding mặc định | Local hashing multilingual |
| Embedding dimension | 768 |
| Backend production tùy chọn | Sentence Transformers `BAAI/bge-m3` và ChromaDB |

### Lệnh chạy

```powershell
python -m src.task4_chunking_indexing
```

### Kết quả mong đợi

```text
Loaded 13 documents; indexed 85 chunks ...
```

### Lời trình bày gợi ý

> Ở Task 4, em chia 13 tài liệu thành 85 chunks. Overlap 100 ký tự giúp nội dung nằm ở ranh giới không bị mất ngữ cảnh. Runtime mặc định dùng hashing embedding để demo ổn định và không phải tải model lớn; hệ thống cũng đã có lựa chọn sentence-transformers và ChromaDB cho môi trường production.

Không nói rằng demo mặc định đang dùng BGE-M3 hoặc ChromaDB nếu chưa bật các biến môi trường tương ứng.

## 8. Task 5 — Semantic Search

### Người trình bày: Nguyễn Đức Anh Tuấn

### Mục tiêu

- Tìm kiếm theo tương đồng ngữ nghĩa.
- Trả danh sách kết quả đã sắp xếp giảm dần theo score.
- Hỗ trợ `top_k` và metadata filter.

### File chính

```text
src/task5_semantic_search.py
```

### Lệnh chạy

```powershell
python -m src.task5_semantic_search
```

### Kết quả cần chỉ ra

Mỗi kết quả có cấu trúc:

```text
id, content, score, metadata
```

### Lời trình bày gợi ý

> Semantic Search biến query và chunks thành vector rồi tính cosine similarity. Nhánh này có khả năng tìm được đoạn liên quan dù người dùng không dùng đúng từ khóa trong tài liệu. Nhóm bổ sung một phần exact-term overlap nhỏ để hỗ trợ tốt hơn các từ như COD hoặc OTP.

## 9. Task 6 — BM25 và TF-IDF lexical search

### Người trình bày: Trần Anh Tú

### Mục tiêu

- Tìm kiếm theo từ khóa chính xác.
- Dùng BM25 làm mặc định.
- Có TF-IDF như backend bonus để so sánh.

### File chính

```text
src/task6_lexical_search.py
```

### Lệnh chạy BM25

```powershell
python -m src.task6_lexical_search
```

### Lệnh chạy TF-IDF

```powershell
$env:LEXICAL_METHOD="tfidf"
python -m src.task6_lexical_search
Remove-Item Env:LEXICAL_METHOD
```

### Lời trình bày gợi ý

> BM25 bổ sung điểm yếu của Semantic Search bằng cách ưu tiên các token xuất hiện chính xác. BM25 còn hiệu chỉnh theo độ dài tài liệu với k1 bằng 1.5 và b bằng 0.75. Pipeline có thêm TF-IDF để kiểm thử A/B, nhưng BM25 là backend lexical mặc định.

### Chuyển phần

> Hai retriever có ưu điểm khác nhau, vì vậy các task tiếp theo sẽ hợp nhất và sắp xếp lại kết quả trước khi đưa cho LLM.

## 10. Task 7 — Reranking và RRF

### Người trình bày: Chu Tâm Vũ

### Mục tiêu

- Hợp nhất kết quả Semantic Search và BM25.
- Ưu tiên tài liệu cùng xuất hiện ở nhiều ranked lists.
- Giảm kết quả trùng lặp và tăng relevance.

### File chính

```text
src/task7_reranking.py
```

Task 7 không có CLI riêng. Chạy test trực tiếp:

```powershell
python -m pytest tests/test_individual.py::TestTask7 tests/test_pipeline_quality.py::test_rrf_rewards_documents_found_by_both_rankers -q
```

### Công thức cần trình bày

```text
RRF(d) = Σ 1 / (k + rank_i(d)), với k = 60
```

### Lời trình bày gợi ý

> Task 7 dùng Reciprocal Rank Fusion để gộp hai danh sách có thang điểm khác nhau. RRF chỉ sử dụng vị trí xếp hạng nên không cần ép cosine score và BM25 score về cùng một scale. Tài liệu được cả hai retriever tìm thấy sẽ nhận điểm cộng từ cả hai phía. Sau fusion, cross-score reranker tiếp tục ưu tiên relevance và MMR có thể giảm nội dung trùng lặp.

## 11. Task 8 — PageIndex/vectorless structural fallback

### Người trình bày: Nguyễn Đức Anh Tuấn

### Mục tiêu

- Có đường dự phòng khi dense retrieval không đủ tự tin.
- Tìm theo cấu trúc document và heading.
- Không làm toàn pipeline lỗi khi không có PageIndex API.

### File chính

```text
src/task8_pageindex_vectorless.py
data/pageindex_manifest.json
```

### Lệnh chạy

```powershell
python -m src.task8_pageindex_vectorless
```

### Lời trình bày gợi ý

> Task 8 cung cấp structural fallback. Cấu hình demo chạy local theo document heading nên không cần API và vẫn trả source marker là pageindex. Remote PageIndex là chế độ opt-in, chỉ bật khi có PAGEINDEX_API_KEY và PAGEINDEX_REMOTE bằng 1. Nhờ đó demo không bị phụ thuộc dịch vụ ngoài.

Phải nói rõ nhãn `pageindex` trong demo mặc định là structural fallback local, không phải kết quả remote PageIndex API.

## 12. Task 9 — Unified retrieval pipeline

### Người trình bày: Chu Tâm Vũ

### Mục tiêu

- Nối Semantic Search và BM25 chạy song song.
- RRF fusion và reranking.
- Tự động chọn structural fallback khi dense score thấp.

### File chính

```text
src/task9_retrieval_pipeline.py
```

### Lệnh chạy

```powershell
python -m src.task9_retrieval_pipeline
```

### Luồng xử lý

```text
Query
  ├─ Semantic Search ┐
  └─ BM25 Search ────┴→ RRF → Rerank → Top-k
          Dense score < 0.16 → Structural fallback
```

### Lời trình bày gợi ý

> Task 9 là nơi kết nối retrieval thành một pipeline hoàn chỉnh. Semantic và BM25 chạy song song để giảm latency. Hệ thống dùng dense cosine score gốc với threshold 0.16 để quyết định fallback. Đây là điểm quan trọng vì RRF score thường rất nhỏ và chỉ có ý nghĩa xếp hạng, không phù hợp làm ngưỡng relevance tuyệt đối.

## 13. Task 10 — LLM generation có citation

### Người trình bày: Nguyễn Đức Anh Tuấn

### Mục tiêu

- Reorder chunks để giảm lost-in-the-middle.
- Gọi LLM với context đã gắn source.
- Bắt buộc citation và có extractive fallback.
- Hỗ trợ câu hỏi follow-up bằng conversation history.

### File chính

```text
src/task10_generation.py
```

### Lệnh kiểm tra LLM thật

```powershell
python -m src.task10_generation
```

Khi OpenAI hoạt động, kết quả phải có:

```text
Generation mode: llm
```

Khi API lỗi hoặc không có key, pipeline vẫn trả câu trả lời dựa trên chunks và chuyển sang extractive/offline mode.

### Lời trình bày gợi ý

> Task 10 nhận các chunks tốt nhất, sắp xếp lại để thông tin quan trọng nằm ở đầu và cuối context, sau đó gắn nhãn nguồn trước khi gọi LLM. Prompt yêu cầu câu trả lời phải có citation. Nếu LLM không trả citation hợp lệ hoặc API không dùng được, hệ thống chuyển sang extractive fallback thay vì bịa nội dung.

## 14. Phần Streamlit UI

### Người trình bày: Nguyễn Đức Anh Tuấn

### File chính

```text
app.py
```

### Lệnh chạy

```powershell
python -m streamlit run app.py
```

Mở:

```text
http://localhost:8501
```

### Thứ tự thao tác trên UI

1. Chỉ slider `Số đoạn bằng chứng`, mặc định là 5.
2. Chỉ bốn câu hỏi gợi ý trong sidebar.
3. Bật `Hiện query sau mở rộng`.
4. Nhập câu hỏi:

   ```text
   Shopee hỗ trợ những phương thức thanh toán nào?
   ```

5. Giải thích bốn chỉ số:
   - Retrieval source.
   - Generation mode.
   - Độ trễ.
   - Số chunks.
6. Mở `Nguồn tham khảo` để cho thấy citation, score và đoạn bằng chứng.
7. Hỏi follow-up:

   ```text
   Sau khi đã đặt hàng thì tôi có đổi phương thức đó được không?
   ```

8. Chỉ query sau mở rộng để chứng minh conversation memory.
9. Nhấn `Xóa hội thoại` trước khi chuyển phần hoặc demo lại.

### Lời trình bày gợi ý

> Giao diện không chỉ hiển thị câu trả lời mà còn cung cấp khả năng quan sát pipeline. Người dùng thấy retriever nào được chọn, LLM hay offline generation, latency và số chunks. Mỗi source card có tên tài liệu, score và đoạn bằng chứng được highlight để kiểm tra câu trả lời.

### Trạng thái UI đã kiểm tra

- Streamlit AppTest: PASS.
- Health endpoint: HTTP 200.
- End-to-end qua UI: PASS.
- Kết quả thử gần nhất: `Generation=LLM`, 5 chunks và có source expanders.

## 15. Phần Evaluation và QA

### Người trình bày: Trần Anh Tú

### File chính

```text
group_project/evaluation/golden_dataset.json
group_project/evaluation/eval_pipeline.py
group_project/evaluation/results.md
tests/test_individual.py
tests/test_pipeline_quality.py
```

### Lệnh evaluation

```powershell
python -m group_project.evaluation.eval_pipeline
```

### Lệnh test

```powershell
python -m pytest tests/test_individual.py -q
python -m pytest tests/test_pipeline_quality.py -q
python -m pytest -q
```

Kết quả hiện tại:

```text
35 passed  # test Task 1–10
6 passed   # quality tests
41 passed  # toàn bộ
```

### Bảng kết quả A/B

| Metric | Hybrid + rerank | Dense-only |
|---|---:|---:|
| Faithfulness | 1.0000 | 1.0000 |
| Answer Relevance | 0.3148 | 0.3094 |
| Context Recall | 0.8557 | 0.8715 |
| Context Precision | 0.6250 | 0.6000 |
| Average | **0.6989** | 0.6952 |

### Lời trình bày gợi ý

> Nhóm xây dựng 16 golden cases và so sánh hybrid plus rerank với dense-only. Config hybrid có average và context precision cao hơn, còn dense-only có context recall cao hơn một chút. Báo cáo mặc định dùng deterministic RAGAS-compatible proxy để có thể chạy ổn định trong CI; nhóm không trình bày đây là RAGAS LLM judge chính thức.

## 16. Lệnh chạy toàn bộ bài lab theo thứ tự

Chỉ dùng khi cần kiểm tra trước buổi demo. Không nên chạy toàn bộ trực tiếp khi đang thuyết trình vì Task 2 phụ thuộc Internet.

```powershell
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown
python -m src.task4_chunking_indexing
python -m src.task5_semantic_search
python -m src.task6_lexical_search
python -m pytest tests/test_individual.py::TestTask7 -q
python -m src.task8_pageindex_vectorless
python -m src.task9_retrieval_pipeline
python -m src.task10_generation
python -m group_project.evaluation.eval_pipeline
python -m pytest -q
python -m streamlit run app.py
```

## 17. Thứ tự live demo an toàn nhất

Để tránh mất thời gian, chỉ chạy ba lệnh sau trước lớp:

```powershell
python -m pytest -q
python -m src.task9_retrieval_pipeline
python -m streamlit run app.py
```

Các Task 1–8 nên trình bày bằng code, dữ liệu và output đã tạo sẵn. Task 10 được chứng minh trực tiếp khi UI hiện `Generation=LLM`.

## 18. Câu kết thúc

### Người trình bày: Bùi Tùng Lâm

> Nhóm đã hoàn thành toàn bộ Task 1–10 và phần bài tập nhóm. Hệ thống có 13 tài liệu chuẩn hóa, 85 chunks, hybrid retrieval, RRF reranking, structural fallback, LLM citation, conversation memory và evaluation A/B. Toàn bộ 41 automated tests đã pass và UI đã được kiểm thử end-to-end bằng OpenAI thật.

## 19. Checklist trước khi lên trình bày

- [ ] Thay API key mới nếu key cũ từng bị chia sẻ.
- [ ] Không mở `.env` khi chia sẻ màn hình.
- [ ] `python -m pytest -q` trả về `41 passed`.
- [ ] Streamlit mở được tại `http://localhost:8501`.
- [ ] Câu hỏi thử hiện `Generation=LLM` và có chunks/citations.
- [ ] Mở sẵn `group_project/evaluation/results.md`.
- [ ] Tắt thông báo ứng dụng và tab không liên quan.
- [ ] Chuẩn bị Internet hoặc hotspot dự phòng.
- [ ] Mỗi thành viên biết đúng phạm vi task của mình.
- [ ] Không crawl hoặc cài package trong lúc live demo.
