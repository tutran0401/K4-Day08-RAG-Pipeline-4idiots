# Project Handoff — E-commerce Support RAG

Tài liệu này là bản bàn giao nhanh để cả nhóm hiểu repository trước khi commit, review hoặc demo. Không ghi API key hay thông tin bí mật vào file này.

## 1. Trạng thái đã xác minh

Ngày kiểm tra: **2026-08-04** trên **Windows / Python 3.11.9**.

| Hạng mục | Kết quả |
|---|---|
| Cài runtime mặc định | `python -m pip install -r requirements.txt` thành công |
| Kiểm tra dependency | `python -m pip check` → không có dependency hỏng |
| Task 1 | Có 3 tài liệu policy hợp lệ |
| Task 2 | Crawl thật thành công 5 URL bài viết Shopee |
| Task 3 | Chuẩn hóa tổng cộng 13 tài liệu Markdown |
| Task 4 | Index 13 tài liệu thành 85 chunks |
| Task 5–9 | Semantic, BM25, reranking, PageIndex local và hybrid retrieval đều chạy thành công |
| Task 10 | Gọi OpenAI thành công, `Generation mode: llm` |
| Streamlit | `AppTest` render thành công, không có uncaught exception |
| Automated tests | **41 passed** |
| Evaluation | 16 golden cases; `A_hybrid_rerank` thắng |

Evaluation gần nhất:

| Metric | Hybrid + rerank | Dense-only |
|---|---:|---:|
| Faithfulness | 1.0000 | 1.0000 |
| Answer relevance | 0.3148 | 0.3094 |
| Context recall | 0.8557 | 0.8715 |
| Context precision | 0.6250 | 0.6000 |
| Average | **0.6989** | 0.6952 |

Chi tiết nằm trong `group_project/evaluation/results.md`.

## 2. Thông tin mới đồng bộ từ upstream

Repository hiện đã đồng bộ thêm ba nhóm thông tin từ upstream:

### Yêu cầu môi trường Python

- Dùng **Python 3.10 hoặc 3.11**; môi trường đã xác minh của nhóm là Python 3.11.9.
- Không khuyến nghị Python 3.12+ cho bài lab này vì một số dependency có thể rơi vào source build và yêu cầu Rust/Cargo.
- Nếu gặp lỗi `Rust/cargo is required`, ưu tiên tạo lại virtual environment bằng Python 3.11. Có thể thử `uv pip install` nếu môi trường bắt buộc dùng resolver khác.
- Crawl4AI dùng Playwright; nếu báo thiếu executable, chạy `playwright install chromium` sau khi cài gói crawler tùy chọn.

### Hướng dẫn chọn embedding provider

Upstream bổ sung hướng dẫn để nhóm cân nhắc nhiều provider. Cần phân biệt giữa **gợi ý của lab** và **backend đã được code nhóm triển khai**:

| Cấu hình | Model/dimension gợi ý | API key | Trạng thái trong code hiện tại |
|---|---|---|---|
| `local` | Hashing multilingual, 768 chiều | Không | **Đã triển khai, mặc định của nhóm** |
| `sentence_transformer` hoặc alias `sentence_transformers` | `BAAI/bge-m3`, 1024 chiều | Không | **Đã triển khai**, tải model/torch khá nặng |
| `google` | `models/text-embedding-004`, 768 chiều | `GEMINI_API_KEY` | Chỉ là **hướng dẫn upstream**, chưa có dispatch API trong code nhóm |
| `openai` | `text-embedding-3-small`, 1536 chiều | `OPENAI_API_KEY` | Chỉ là **hướng dẫn upstream**, chưa có dispatch embedding trong code nhóm |

Hai tên biến cấu hình tương thích:

```dotenv
RAG_EMBEDDING_BACKEND=sentence_transformer
RAG_EMBEDDING_MODEL=BAAI/bge-m3

# Hoặc alias theo tài liệu upstream:
# EMBEDDING_PROVIDER=sentence_transformers
```

`RAG_EMBEDDING_BACKEND` được ưu tiên nếu cả hai biến cùng tồn tại. Đổi provider/model/dimension phải rebuild index; với Chroma production cần xóa collection/index cũ trước khi chạy lại Task 4 để tránh trộn vector khác dimension.

### Danh sách chủ đề đồ án

File mới `SUGGESTED_TOPICS.md` cung cấp 9 hướng phát triển:

1. Luật lao động cho người trẻ.
2. Pháp lý khởi nghiệp và thương mại điện tử.
3. IELTS band descriptors và essay mẫu.
4. Điểm chuẩn và đề án tuyển sinh đại học.
5. Hướng dẫn du lịch thông minh.
6. Phong tục, trang phục và lễ hội truyền thống.
7. Review và tóm tắt sách.
8. Gaming meta guide.
9. Concert và festival guide.

Dự án hiện tại tiếp tục dùng miền **chính sách thương mại điện tử / hỗ trợ khách hàng**, gần với chủ đề số 2; không cần đổi corpus chỉ vì upstream bổ sung danh sách gợi ý.

## 3. Kiến trúc tổng quát

```text
Landing data
    ↓
Markdown standardization
    ↓
Chunking + local embeddings + index
    ├── Semantic search ──┐
    └── BM25 search ──────┤
                          ↓
                    RRF + reranking
                          ↓
              PageIndex structural fallback
                          ↓
          Reorder context + OpenAI generation
                          ↓
        Answer có citation + source cards trên Streamlit
```

Pipeline mặc định là offline-first: retrieval và extractive generation vẫn hoạt động khi API hoặc Internet lỗi. Khi có `OPENAI_API_KEY`, Task 10 gọi LLM thật; giao diện hiển thị `Generation: LLM` hoặc `Generation: OFFLINE`.

## 4. Phân công và nội dung từng thành viên

### Checkpoint 1 — Thu thập và chuẩn hóa dữ liệu

- Role 1 — Bùi Tùng Lâm: điều phối URL và review dữ liệu.
- Role 2 — Chu Tâm Vũ: Task 1.
- Role 3 — Nguyễn Đức Anh Tuấn: Task 2.
- Role 4 — Trần Anh Tú: Task 3 và QA.

#### Task 1 — Collect legal documents

- Code: `src/task1_collect_legal_docs.py`.
- Dữ liệu vào/ra: `data/landing/legal/`.
- Chức năng chính:
  - `setup_directory()` tạo landing zone.
  - `download_file()` tải PDF/DOC/DOCX qua HTTP(S), kiểm tra extension và kích thước.
  - `inventory()` liệt kê file để audit/demo.
- Kết quả hiện tại: 3 policy documents hợp lệ.
- Lệnh kiểm tra:

```powershell
python -m src.task1_collect_legal_docs
```

#### Task 2 — Crawl help-center articles

- Code: `src/task2_crawl_news.py`.
- Dữ liệu ra: `data/landing/news/article_01.json` đến `article_05.json`.
- Crawler ưu tiên Crawl4AI; nếu thiếu browser/package thì tự dùng `requests` fallback.
- Mỗi JSON chứa URL, title, thời gian crawl và nội dung Markdown.
- Đã sửa danh sách mặc định thành 5 URL bài viết cụ thể; không còn dùng URL trang chủ thiếu nội dung.
- Lệnh chạy:

```powershell
python -m src.task2_crawl_news
```

Task này cần Internet. Dữ liệu snapshot đã có sẵn nên các task sau vẫn chạy được khi offline.

#### Task 3 — Convert to Markdown

- Code: `src/task3_convert_markdown.py`.
- Input: `data/landing/legal/` và `data/landing/news/`.
- Output: `data/standardized/legal/` và `data/standardized/news/`.
- Giữ metadata nguồn, ngày crawl và customer role trong Markdown.
- Kết quả hiện tại: 13 file Markdown.
- Lệnh chạy:

```powershell
python -m src.task3_convert_markdown
```

Checklist trước khi bàn giao phần dữ liệu:

- Không commit file chứa cookie, token hoặc API key.
- Kiểm tra URL nguồn và metadata trong JSON/Markdown.
- Nếu crawl lại, chạy lại Task 3 và Task 4 để index không bị cũ.

### Checkpoint 2 — Indexing và hai nhánh retrieval

- Role 1 — Bùi Tùng Lâm: duyệt cấu hình chunking/index.
- Role 2 — Chu Tâm Vũ: Task 4.
- Role 3 — Nguyễn Đức Anh Tuấn: Task 5.
- Role 4 — Trần Anh Tú: Task 6 và QA.

#### Task 4 — Chunking, embeddings và indexing

- Code: `src/task4_chunking_indexing.py`.
- Input: toàn bộ `data/standardized/**/*.md`.
- Output runtime: `data/index/chunks.json` (được `.gitignore`, có thể sinh lại).
- Cấu hình mặc định:
  - Chunk size: 700 ký tự.
  - Overlap: 100 ký tự.
  - Embedding local hashing: 768 dimensions.
  - Backend đã triển khai: local hashing hoặc sentence-transformers (`BAAI/bge-m3`).
  - Google/OpenAI embedding mới là hướng dẫn mở rộng upstream, chưa được nối API trong implementation hiện tại.
  - Production tùy chọn: sentence-transformers và ChromaDB.
- Kết quả hiện tại: 13 documents, 85 chunks.
- Lệnh chạy:

```powershell
python -m src.task4_chunking_indexing
```

#### Task 5 — Semantic search

- Code: `src/task5_semantic_search.py`.
- Hàm public: `semantic_search(query, top_k, metadata_filter)`.
- Dùng cosine similarity kết hợp exact-term overlap nhỏ.
- Output chuẩn: `content`, `score`, `metadata`, `id`.
- Lệnh smoke-test:

```powershell
python -m src.task5_semantic_search
```

#### Task 6 — Lexical search

- Code: `src/task6_lexical_search.py`.
- Hàm public: `lexical_search(query, top_k, metadata_filter)`.
- Backend mặc định: BM25 với `k1=1.5`, `b=0.75`.
- Backend bonus: `LEXICAL_METHOD=tfidf`.
- Lệnh chạy:

```powershell
python -m src.task6_lexical_search
$env:LEXICAL_METHOD="tfidf"
python -m src.task6_lexical_search
Remove-Item Env:LEXICAL_METHOD
```

Checklist trước khi bàn giao retrieval:

- Luôn rebuild Task 4 sau khi corpus đổi.
- Không dùng điểm RRF làm ngưỡng relevance tuyệt đối.
- Kiểm tra kết quả cả câu hỏi tiếng Việt có dấu và không dấu.

### Checkpoint 3–4 — Reranking, fallback, pipeline và generation

- Role 1 — Bùi Tùng Lâm: duyệt kiến trúc và kết quả test.
- Role 2 — Chu Tâm Vũ: Task 7 và Task 9.
- Role 3 — Nguyễn Đức Anh Tuấn: Task 8 và Task 10.
- Role 4 — Trần Anh Tú: fallback/citation QA.

#### Task 7 — Reranking

- Code: `src/task7_reranking.py`.
- Có ba chiến lược:
  - Cross-score local để ưu tiên relevance.
  - MMR để giảm trùng lặp.
  - RRF để hợp nhất nhiều ranked lists.
- Hàm public: `rerank_cross_encoder`, `rerank_mmr`, `rerank_rrf`, `rerank`.
- Được kiểm tra trong `tests/test_individual.py` và `tests/test_pipeline_quality.py`.

#### Task 8 — PageIndex/vectorless fallback

- Code: `src/task8_pageindex_vectorless.py`.
- Mặc định dùng structural search local theo document heading, không cần API.
- Manifest: `data/pageindex_manifest.json`.
- Remote PageIndex chỉ hoạt động khi có `PAGEINDEX_API_KEY` và `PAGEINDEX_REMOTE=1`.
- Lệnh chạy:

```powershell
python -m src.task8_pageindex_vectorless
```

#### Task 9 — Unified retrieval pipeline

- Code: `src/task9_retrieval_pipeline.py`.
- Luồng xử lý:
  1. Semantic và BM25 chạy song song.
  2. RRF hợp nhất kết quả.
  3. Cross-score reranking.
  4. Fallback structural khi cosine dense gốc thấp hơn threshold.
- Hàm public: `retrieve(...)`.
- Lệnh chạy:

```powershell
python -m src.task9_retrieval_pipeline
```

#### Task 10 — Generation có citation

- Code: `src/task10_generation.py`.
- Chức năng:
  - Mở rộng follow-up query từ conversation history.
  - Reorder chunks để giảm lost-in-the-middle.
  - Gọi OpenAI/OpenRouter qua OpenAI SDK.
  - Kiểm tra citation; thiếu citation thì dùng extractive fallback.
  - Trả `generation_mode` và cảnh báo rõ ràng.
- Lệnh kiểm tra API thật:

```powershell
python -m src.task10_generation
```

Kết quả đúng khi API hoạt động phải có dòng:

```text
Generation mode: llm
```

Checklist trước khi bàn giao kiến trúc RAG:

- Không log API key.
- Kiểm tra citation của mọi câu trả lời LLM.
- Với query vô nghĩa, hệ thống phải từ chối hoặc fallback thay vì bịa.
- Giữ `temperature` thấp cho câu trả lời policy.

### Checkpoint 5–6 — UI, evaluation, QA và demo

- Role 1 — Bùi Tùng Lâm: tích hợp, điều phối và thuyết trình tổng quan.
- Role 2 — Chu Tâm Vũ: nối retrieval/generation và giải đáp kỹ thuật.
- Role 3 — Nguyễn Đức Anh Tuấn: Streamlit UI và live demo.
- Role 4 — Trần Anh Tú: evaluation, QA và báo cáo A/B.

#### Streamlit application

- Code: `app.py`.
- Có chat history, follow-up memory, suggested questions, source cards, highlight keyword và latency.
- Hiển thị riêng:
  - Retrieval source.
  - Generation mode (`LLM`, `EXTRACTIVE/OFFLINE`, `ERROR`).
  - Số chunks và latency.
- Lệnh chạy:

```powershell
streamlit run app.py
```

#### Golden dataset và evaluation

- Dataset: `group_project/evaluation/golden_dataset.json` — 16 cases.
- Pipeline: `group_project/evaluation/eval_pipeline.py`.
- Báo cáo: `group_project/evaluation/results.md`.
- So sánh:
  - Config A: hybrid + RRF + reranking.
  - Config B: dense-only, không reranking.
- Lệnh chạy mặc định, không tốn API:

```powershell
python -m group_project.evaluation.eval_pipeline
```

#### Automated QA

- `tests/test_individual.py`: kiểm tra yêu cầu Task 1–10.
- `tests/test_pipeline_quality.py`: kiểm tra chất lượng, fallback, citation và conversation flow.
- Lệnh regression bắt buộc trước commit:

```powershell
python -m pytest -q
python -m pip check
```

Checklist trước khi bàn giao UI/evaluation:

- App render không exception.
- Không hiển thị secret trong UI hoặc logs.
- Báo cáo phải ghi rõ metric mặc định là deterministic proxy, không giả là RAGAS LLM judge.
- Chạy lại evaluation khi corpus hoặc retrieval logic thay đổi.

## 5. Dependency và môi trường

### Runtime mặc định

```powershell
python -m pip install -r requirements.txt
```

Đây là môi trường đã được kiểm tra thành công cho pipeline local, OpenAI generation, Chroma tùy chọn, tests và Streamlit.

Kiểm tra đúng phiên bản Python trước khi cài:

```powershell
python --version
```

Nên dùng Python 3.10/3.11. Nếu đang ở Python 3.12+, tạo virtual environment mới bằng Python 3.11 trước khi xử lý lỗi Rust/Cargo.

### Crawl4AI tùy chọn

Task 2 đã có `requests` fallback nên không bắt buộc Crawl4AI. Nếu cần browser crawler:

```powershell
python -m pip install -r requirements-crawl.txt
```

### RAGAS LLM judge tùy chọn

RAGAS 0.1.21 dùng nhánh LangChain/OpenAI cũ, không nên cài chung với Crawl4AI mới. Tạo virtual environment riêng:

```powershell
python -m venv .venv-ragas
.\.venv-ragas\Scripts\python -m pip install -r requirements-ragas.txt
$env:RAGAS_USE_LLM="1"
.\.venv-ragas\Scripts\python -m group_project.evaluation.eval_pipeline
```

Chế độ này gọi LLM nhiều lần và có thể tốn quota. Evaluation mặc định không cần RAGAS package.

## 6. Các lỗi đã phát hiện và sửa

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| Task 2 dừng toàn bộ batch | Chỉ có 3 URL và một URL trang chủ trả nội dung quá ngắn | Thay bằng 5 URL article cụ thể |
| CLI Task 5–10 lỗi `UnicodeEncodeError` trên Windows | Console dùng code page `cp1252` | Thêm `configure_utf8_stdout()` dùng chung |
| `pip install -r requirements.txt` không resolve | Crawl4AI mới và RAGAS cũ yêu cầu hai major OpenAI/LangChain không tương thích | Tách runtime, crawler và RAGAS thành ba requirements files |
| Khó biết app có gọi API thật không | UI trước đây không hiển thị generation backend | Thêm chỉ báo `Generation: LLM/OFFLINE/ERROR` |
| Dễ hiểu nhầm embedding provider | Upstream liệt kê Google/OpenAI như hướng mở rộng nhưng code nhóm mới triển khai local/sentence-transformers | Ghi rõ ma trận provider và trạng thái implementation trong handoff/config mẫu |

## 7. Quy trình chạy lại toàn bộ

```powershell
python -m pip install -r requirements.txt
python -m src.task1_collect_legal_docs
python -m src.task2_crawl_news
python -m src.task3_convert_markdown
python -m src.task4_chunking_indexing
python -m src.task5_semantic_search
python -m src.task6_lexical_search
python -m src.task8_pageindex_vectorless
python -m src.task9_retrieval_pipeline
python -m src.task10_generation
python -m pytest -q
python -m group_project.evaluation.eval_pipeline
streamlit run app.py
```

Task 7 không có CLI riêng; chức năng Task 7 được gọi trong Task 9 và được kiểm tra bởi pytest.

## 8. Checklist trước khi commit/push

```powershell
git status --short
git diff --check
git diff --stat
python -m pytest -q
python -m group_project.evaluation.eval_pipeline
```

Kiểm tra thủ công:

1. `.env` không xuất hiện trong `git status`.
2. Không có API key thật trong README, source code hoặc báo cáo.
3. Không commit `data/index/`, `__pycache__/`, `.pytest_cache/` hoặc vector cache có thể sinh lại.
4. Review các file dữ liệu crawl mới và URL nguồn trước khi `git add`.
5. Nếu đã từng gửi key qua chat hoặc nơi công khai, thu hồi key đó và tạo key mới trước khi deploy.
6. Nếu đổi embedding backend, rebuild `data/index/chunks.json` và Chroma collection trước khi test retrieval.

## 9. Lệnh demo ngắn nhất

```powershell
python -m pytest -q
streamlit run app.py
```

Câu hỏi demo gợi ý:

1. `Shopee hỗ trợ những phương thức thanh toán nào?`
2. `Có thể đổi phương thức thanh toán sau khi đặt hàng không?`
3. `Còn COD thì sao?`
4. `Cần bằng chứng gì khi hàng bị hỏng?`
5. Một chuỗi vô nghĩa để chứng minh hệ thống fallback/từ chối thay vì hallucinate.
