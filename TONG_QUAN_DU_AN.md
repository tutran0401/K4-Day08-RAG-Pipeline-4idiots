# Tổng quan dự án E-commerce Support RAG

> Tài liệu nhập môn dành cho người mới clone repo. Đọc file này trước, sau đó mới đi vào `README.md`, `LAB_GUIDE.md` hoặc từng file trong `src/`.

## 1. Dự án này giải quyết bài toán gì?

Dự án xây dựng một chatbot RAG trả lời câu hỏi bằng tiếng Việt về:

- thanh toán;
- đổi trả và hoàn tiền;
- theo dõi đơn hàng;
- quyền riêng tư;
- quy định đăng bán dành cho người bán.

RAG là viết tắt của **Retrieval-Augmented Generation**. Thay vì để mô hình ngôn ngữ trả lời hoàn toàn bằng kiến thức đã học, hệ thống sẽ:

1. tìm các đoạn tài liệu liên quan đến câu hỏi;
2. đưa các đoạn đó vào context;
3. sinh hoặc trích xuất câu trả lời;
4. gắn tên nguồn vào câu trả lời để người dùng kiểm tra.

Mục tiêu quan trọng nhất của repo không chỉ là có chatbot, mà là minh họa đầy đủ pipeline từ **thu thập dữ liệu → chuẩn hóa → chia đoạn → lập chỉ mục → truy xuất → xếp hạng → sinh câu trả lời có citation → đánh giá**.

## 2. Bức tranh tổng thể

```text
Nguồn chính sách / bài hỗ trợ
          │
          ▼
data/landing                 Dữ liệu thô: DOC, JSON...
          │
          │ Task 3: chuyển đổi
          ▼
data/standardized            Tài liệu Markdown đã chuẩn hóa
          │
          │ Task 4: chunk + embedding + index
          ▼
data/index/chunks.json        Chỉ mục cục bộ
          │
          ├──────────────────────────────┐
          ▼                              ▼
Task 5: semantic search          Task 6: BM25 lexical search
          │                              │
          └──────────────┬───────────────┘
                         ▼
                 Task 7: RRF + rerank
                         │
        dense score thấp │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
       Kết quả hybrid        Task 8: structural/PageIndex fallback
              └──────────┬──────────┘
                         ▼
                 Task 10: generation
                  + citation + từ chối
                         │
                         ▼
                    app.py / Streamlit
```

Lưu ý về code thực tế: quyết định fallback được thực hiện bằng **điểm semantic gốc trước khi RRF và rerank**. Đây là chủ ý đúng vì điểm RRF chỉ thể hiện thứ hạng, không phải độ liên quan tuyệt đối.

## 3. Hai luồng cần phân biệt

### 3.1. Luồng chuẩn bị dữ liệu — thường chỉ chạy khi dữ liệu thay đổi

```text
Task 1 + Task 2 → Task 3 → Task 4
```

- Task 1 thu thập file chính sách vào `data/landing/legal/`.
- Task 2 crawl bài hỗ trợ vào `data/landing/news/`.
- Task 3 chuyển dữ liệu thô thành Markdown trong `data/standardized/`.
- Task 4 chia Markdown thành các chunk, tạo embedding và lưu index.

Không cần chạy lại bốn bước này cho mỗi câu hỏi. Khi chỉ chạy chatbot, hệ thống sẽ dùng index đã có. Nếu Markdown mới hơn index, `load_or_build_index()` có thể tự tạo lại index cục bộ.

### 3.2. Luồng xử lý một câu hỏi — chạy mỗi lần người dùng chat

```text
app.py
  └─ generate_with_citation()                  Task 10
       ├─ expand_follow_up_query()
       ├─ retrieve()                           Task 9
       │    ├─ semantic_search()               Task 5
       │    ├─ lexical_search()                Task 6
       │    ├─ rerank_rrf()                    Task 7
       │    ├─ rerank_cross_encoder()          Task 7
       │    └─ pageindex_search() nếu cần      Task 8
       ├─ reorder_for_llm()
       ├─ format_context()
       └─ LLM hoặc _extractive_answer()
```

Đây là chuỗi hàm quan trọng nhất để debug. Nếu giao diện có lỗi, hãy lần từ `app.py` xuống Task 10 rồi Task 9 thay vì đọc ngẫu nhiên cả repo.

## 4. Vai trò của từng task

| Task | File chính | Input | Output / trách nhiệm |
|---|---|---|---|
| 1 | `src/task1_collect_legal_docs.py` | URL file PDF/DOC/DOCX | Tải tài liệu vào `data/landing/legal/`, kiểm tra đuôi file và kích thước |
| 2 | `src/task2_crawl_news.py` | URL bài hỗ trợ | JSON gồm URL, tiêu đề, thời gian crawl và nội dung Markdown |
| 3 | `src/task3_convert_markdown.py` | File thô trong `data/landing/` | Markdown trong `data/standardized/` |
| 4 | `src/task4_chunking_indexing.py` | Markdown chuẩn hóa | Chunk, embedding và `data/index/chunks.json`; Chroma là tùy chọn |
| 5 | `src/task5_semantic_search.py` | Query + index | Các chunk gần nhau về ý nghĩa, xếp theo cosine/overlap |
| 6 | `src/task6_lexical_search.py` | Query + index | Các chunk khớp từ khóa bằng BM25; TF-IDF là backend tùy chọn |
| 7 | `src/task7_reranking.py` | Các danh sách ứng viên | Gộp bằng RRF và chấm lại độ liên quan; có thêm MMR |
| 8 | `src/task8_pageindex_vectorless.py` | Query + cây heading/tài liệu | Fallback structural chạy local; PageIndex API là tùy chọn opt-in |
| 9 | `src/task9_retrieval_pipeline.py` | Query | Điều phối dense, sparse, fusion, rerank và fallback |
| 10 | `src/task10_generation.py` | Query + chunks | Mở rộng câu hỏi nối tiếp, tạo context, trả lời có citation |

### Những tên gọi dễ gây hiểu nhầm

- `rerank_cross_encoder()` hiện là reranker heuristic chạy local dựa trên keyword overlap và điểm retrieval cũ; nó giữ giao diện của cross-encoder nhưng **không tải một cross-encoder thật**.
- Task 8 mặc định là tìm kiếm theo cấu trúc heading chạy local, lấy cảm hứng từ PageIndex. Chỉ gọi dịch vụ PageIndex thật khi có key và `PAGEINDEX_REMOTE=1`.
- `VECTOR_STORE = "chromadb"` mô tả backend production, nhưng đường chạy mặc định vẫn đọc `data/index/chunks.json`. Chroma chỉ được ghi khi `RAG_USE_CHROMA=1`.
- Embedding mặc định là hashing 768 chiều chạy offline, không phải BGE-M3. BGE-M3 chỉ dùng khi bật backend `sentence_transformer`.

## 5. Dữ liệu đi qua hệ thống như thế nào?

### Landing zone

`data/landing/` giữ dữ liệu gần với nguồn ban đầu nhất:

- `legal/`: các snapshot chính sách dạng DOC;
- `news/`: các record JSON từ trang hỗ trợ.

Không nên sửa nội dung ở đây chỉ để “làm đẹp” cho chatbot. Nếu cần làm sạch, thực hiện ở bước convert/chunk để vẫn giữ được dữ liệu gốc phục vụ kiểm tra.

### Standardized zone

`data/standardized/` chứa Markdown đã chuẩn hóa. Đây là nguồn đầu vào thật sự của retrieval pipeline. Metadata như `source`, `path`, `type`, `customer_role` được gắn hoặc suy luận từ tài liệu ở bước index.

### Chunk và index

Task 4 đang dùng:

- `CHUNK_SIZE = 700` ký tự;
- `CHUNK_OVERLAP = 100` ký tự;
- ưu tiên cắt ở đoạn văn, câu, dòng hoặc khoảng trắng;
- embedding mặc định `local-hashing-multilingual-v1`, 768 chiều;
- ID dạng `tên_file::chunk_index`.

Overlap giúp câu nằm sát biên chunk không bị mất hoàn toàn. Đổi embedding model, số chiều hoặc cách chunk thì nên chạy lại Task 4 để toàn bộ index nhất quán.

### Hình dạng một kết quả retrieval

Các module retrieval thống nhất trả về gần giống cấu trúc sau:

```python
{
    "content": "Đoạn bằng chứng...",
    "score": 0.73,
    "metadata": {
        "source": "payment_methods_policy.md",
        "path": "legal/payment_methods_policy.md",
        "type": "legal",
        "customer_role": "buyer",
        "chunk_index": 2
    },
    "source": "hybrid"  # hoặc "pageindex"
}
```

`metadata.source` là tên tài liệu dùng làm citation. Trường `source` ở cấp ngoài cho biết kết quả đến từ nhánh retrieval nào.

## 6. Retrieval hoạt động ra sao?

### Semantic search — tìm theo ý nghĩa

Task 5 biến query thành embedding rồi so cosine với embedding của từng chunk. Điểm cuối còn có một phần nhỏ keyword overlap:

```text
semantic_score = 0.82 × cosine + 0.18 × keyword_overlap
```

Điểm được giữ trong khoảng `[0, 1]`, vì vậy có thể dùng để quyết định query có đủ liên quan với kho dữ liệu hay không.

### Lexical search — tìm theo từ khóa

Task 6 mặc định dùng BM25 với `k1=1.5`, `b=0.75`. BM25 hữu ích khi query chứa tên gọi, cụm từ hoặc từ khóa xuất hiện trực tiếp trong tài liệu. Hàm tokenize có chuẩn hóa dấu và mở rộng một số từ đồng nghĩa Việt–Anh.

### Hybrid search — kết hợp hai góc nhìn

Task 9 chạy semantic và BM25 song song, mỗi nhánh lấy tối đa `top_k × 3` ứng viên. Sau đó:

1. kiểm tra semantic top-1 có thấp hơn `SCORE_THRESHOLD = 0.16` không;
2. nếu thấp, thử structural/PageIndex fallback;
3. nếu không fallback, gộp hai bảng xếp hạng bằng Reciprocal Rank Fusion (RRF);
4. chấm lại ứng viên bằng reranker local;
5. trả về `top_k` kết quả.

RRF ưu tiên tài liệu xuất hiện ở vị trí cao trong một hoặc cả hai danh sách. Không so ngưỡng relevance với điểm RRF vì top-1 RRF thường chỉ khoảng `1/(60+1)` cho mỗi danh sách.

## 7. Generation và chống hallucination

Task 10 có hai chế độ:

### Có API key

Nếu `.env` có `OPENROUTER_API_KEY` hoặc `OPENAI_API_KEY`, hệ thống gọi LLM với:

- system prompt yêu cầu chỉ dùng context;
- citation dạng `[tên nguồn]` cho từng khẳng định;
- `temperature = 0.2` để giảm tính ngẫu nhiên;
- tối đa bốn message gần nhất làm conversation history.

Nếu LLM trả lời không có citation hoặc API lỗi, hệ thống tự chuyển về chế độ extractive.

### Không có API key

Chatbot vẫn chạy. `_extractive_answer()` chọn một hoặc hai câu liên quan nhất từ nguồn top-ranked rồi gắn citation. Nếu không có bằng chứng phù hợp, hệ thống trả:

> Tôi không thể xác minh thông tin này từ nguồn hiện có.

Vì vậy API key giúp câu trả lời tự nhiên hơn, nhưng không phải điều kiện bắt buộc để demo pipeline.

### Câu hỏi nối tiếp

Với câu ngắn như “Còn COD thì sao?”, `expand_follow_up_query()` nối câu hỏi user trước đó vào query retrieval. Streamlit giữ lịch sử trong `st.session_state`; đây là memory trong phạm vi phiên trình duyệt, không phải database hội thoại lâu dài.

## 8. Giao diện Streamlit

`app.py` chỉ làm tầng trình bày và quản lý session; logic RAG nằm trong `src/`.

Giao diện cung cấp:

- khung chat và câu hỏi gợi ý;
- chọn số chunk bằng `top_k`;
- lịch sử hội thoại;
- query sau khi mở rộng ở chế độ debug;
- retrieval source, generation mode, độ trễ và số chunk;
- source cards, score, loại người dùng và đoạn evidence có highlight.

Quy tắc kiến trúc nên giữ: không nhét thuật toán retrieval mới trực tiếp vào `app.py`. Hãy sửa module tương ứng trong `src/`, để UI, test và evaluation cùng dùng một logic.

## 9. Cách chạy từ bản clone mới

### Bước 1 — tạo môi trường và cài dependency

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn script kích hoạt, có thể gọi trực tiếp `.\.venv\Scripts\python.exe` thay cho `python` trong các lệnh tiếp theo.

### Bước 2 — tạo lại index

```powershell
python -m src.task4_chunking_indexing
```

Lệnh này đọc toàn bộ `data/standardized/**/*.md`, chia chunk, tạo embedding và ghi index cục bộ.

### Bước 3 — chạy test baseline

```powershell
python -m pytest -q
```

Tại thời điểm tạo tài liệu này, kết quả trên repo hiện tại là:

```text
41 passed
```

### Bước 4 — chạy chatbot

```powershell
python -m streamlit run app.py
```

Mở URL local Streamlit in ra trên terminal, thường là `http://localhost:8501`.

### Bước 5 — chạy evaluation offline

```powershell
python -m group_project.evaluation.eval_pipeline
```

Script dùng 16 câu hỏi trong `group_project/evaluation/golden_dataset.json`, so sánh:

- Config A: hybrid + RRF + rerank;
- Config B: dense-only, không rerank.

Kết quả được ghi vào `group_project/evaluation/results.md`. Điểm mặc định là proxy xác định để regression/CI, không phải điểm LLM judge chính thức của RAGAS.

## 10. Cấu hình tùy chọn

Copy file mẫu nếu muốn dùng dịch vụ/model ngoài:

```powershell
Copy-Item .env.example .env
```

| Biến | Ý nghĩa |
|---|---|
| `OPENROUTER_API_KEY` | Sinh câu trả lời qua OpenRouter |
| `OPENAI_API_KEY` | Sinh câu trả lời qua OpenAI nếu không dùng OpenRouter |
| `LLM_MODEL` | Model generation |
| `RAG_EMBEDDING_BACKEND=sentence_transformer` | Dùng Sentence Transformers thay hashing local |
| `RAG_EMBEDDING_MODEL=BAAI/bge-m3` | Model embedding production mặc định được gợi ý |
| `LEXICAL_METHOD=tfidf` | Đổi BM25 sang TF-IDF |
| `RAG_USE_CHROMA=1` | Ghi thêm index vào ChromaDB |
| `PAGEINDEX_API_KEY` + `PAGEINDEX_REMOTE=1` | Bật upload/retrieval PageIndex thật; có thể dùng quota |
| `RAGAS_USE_LLM=1` | Chạy RAGAS LLM judge trong môi trường riêng |

Không commit `.env` và không đưa API key, OTP, PIN hoặc thông tin thẻ vào chat/log.

`GEMINI_API_KEY` và `JINA_API_KEY` có trong file cấu hình mẫu nhưng code hiện tại chưa có nhánh gọi Gemini generation hoặc Jina reranking. Không nên hiểu việc khai báo biến là tính năng đã được kết nối.

## 11. Cấu trúc thư mục nên nhớ

```text
.
├── app.py                         Streamlit UI
├── src/                           Pipeline Task 1–10
├── data/
│   ├── landing/                   Dữ liệu thô
│   ├── standardized/              Markdown dùng để index
│   ├── index/chunks.json          Index local, được sinh tự động
│   └── pageindex_manifest.json    Manifest cho fallback/PageIndex
├── tests/                         Test chức năng và chất lượng
├── group_project/evaluation/      Golden dataset, script eval, báo cáo
├── requirements.txt               Môi trường chạy chính
├── requirements-crawl.txt         Crawl4AI tùy chọn
├── requirements-ragas.txt         RAGAS legacy, nên cài ở venv riêng
├── README.md                      Đặc tả đầy đủ của bài lab
├── PROJECT_HANDOFF.md             Bàn giao và phân công
└── TONG_QUAN_DU_AN.md             File bạn đang đọc
```

Tại thời điểm kiểm tra repo:

- 4 file thô trong `data/landing/legal/`;
- 11 file thô trong `data/landing/news/`;
- 3 Markdown legal và 10 Markdown news trong `data/standardized/`;
- 85 chunks trong index local;
- 16 trường hợp trong golden dataset;
- 41 test đang pass.

Số lượng có thể thay đổi sau khi crawl, convert hoặc bổ sung tài liệu.

## 12. Nên đọc code theo thứ tự nào?

Nếu mục tiêu là hiểu nhanh chatbot đang chạy:

1. `app.py` — xem UI gọi entry point nào;
2. `src/task10_generation.py` — hiểu output cuối, citation và fallback offline;
3. `src/task9_retrieval_pipeline.py` — hiểu bộ điều phối retrieval;
4. `src/task5_semantic_search.py` và `src/task6_lexical_search.py`;
5. `src/task7_reranking.py` và `src/task8_pageindex_vectorless.py`;
6. `src/task4_chunking_indexing.py` — hiểu index được tạo ra sao;
7. Task 1–3 — hiểu nguồn gốc dữ liệu;
8. `tests/` và `group_project/evaluation/` — hiểu tiêu chí đúng và chất lượng.

Nếu mục tiêu là học RAG theo trình tự xây dựng, hãy đọc Task 1 → Task 10 theo số thứ tự.

## 13. Debug theo triệu chứng

| Triệu chứng | Nơi kiểm tra đầu tiên |
|---|---|
| Không thấy tài liệu | `data/standardized/`, rồi `load_documents()` ở Task 4 |
| Index cũ hoặc score lạ sau khi đổi model | Chạy lại `python -m src.task4_chunking_indexing` |
| Tìm đúng từ khóa nhưng semantic kém | Task 5, embedding backend và dimension |
| BM25 không ra kết quả | Task 6, `tokenize()` và `LEXICAL_METHOD` |
| Kết quả đúng bị tụt hạng | Task 7 và danh sách dense/sparse trước RRF |
| Query lạc đề vẫn trả lời | `SCORE_THRESHOLD` ở Task 9 và logic từ chối ở Task 10 |
| Citation sai nguồn | `metadata.source`, `format_context()` và `_extractive_answer()` |
| Follow-up mất ngữ cảnh | history trong `app.py` và `expand_follow_up_query()` |
| API lỗi nhưng app vẫn chạy extractive | Đây là fallback có chủ ý; xem `generation_warning` |
| PageIndex remote không chạy | Cần key, manifest có `doc_id`, `PAGEINDEX_REMOTE=1` và file PDF phù hợp |

Một cách kiểm tra theo tầng:

```powershell
python -m src.task4_chunking_indexing
python -m src.task5_semantic_search
python -m src.task6_lexical_search
python -m src.task8_pageindex_vectorless
python -m src.task9_retrieval_pipeline
python -m src.task10_generation
python -m pytest -q
```

Khi tầng thấp chạy đúng mới chuyển lên Streamlit, vì UI thường chỉ phản ánh lỗi phát sinh từ pipeline bên dưới.

## 14. Evaluation đang đo gì?

Evaluation offline có bốn metric:

- **Faithfulness**: câu trả lời có được evidence hỗ trợ không;
- **Answer relevance**: câu trả lời có gần expected answer không;
- **Context recall**: retriever lấy được bao nhiêu nội dung cần thiết;
- **Context precision**: trong các chunk lấy ra, bao nhiêu chunk hữu ích/đúng nguồn.

Test và evaluation có vai trò khác nhau:

- `pytest` kiểm tra code, interface, dữ liệu và các invariant có hoạt động không;
- evaluation đo chất lượng câu trả lời/retrieval trên golden dataset;
- UI demo kiểm tra trải nghiệm người dùng và cách hiển thị evidence.

Một pipeline có thể pass toàn bộ unit test nhưng chất lượng retrieval vẫn chưa tốt, vì vậy sau thay đổi thuật toán nên chạy cả test và evaluation A/B.

## 15. Các giới hạn hiện tại

- Corpus là snapshot phục vụ học tập, không phải nguồn chính sách cập nhật theo thời gian thực.
- Embedding hashing mặc định ưu tiên khả năng chạy offline hơn chất lượng semantic production.
- Reranker local chưa phải cross-encoder neural thật.
- PageIndex mặc định là structural fallback local; remote phải bật rõ ràng.
- Generator extractive có thể trả lời hơi cứng và chỉ ưu tiên nguồn top-ranked.
- Conversation memory chỉ sống trong session Streamlit.
- Proxy evaluation phù hợp CI, không thay thế đánh giá bằng người dùng hoặc LLM judge chính thức.
- Index tự kiểm tra thời gian sửa tài liệu, nhưng không tự nhận biết mọi thay đổi cấu hình model/chunk. Sau khi đổi các cấu hình đó, hãy chủ động chạy lại Task 4.

## 16. Phân công theo thành viên và checkpoint

Phần này trả lời câu hỏi: **“Sau mỗi checkpoint, mỗi thành viên đã tạo ra gì, phải hiểu phần nào và bàn giao gì cho người tiếp theo?”** Ma trận dưới đây lấy theo `PROJECT_HANDOFF.md`; phần phân công tổng quát trong các README có thể viết ngắn hơn nên không dùng thay cho bảng checkpoint này.

### Bản đồ ownership nhanh

| Thành viên | Role xuyên suốt | Phần chịu trách nhiệm chính |
|---|---|---|
| **Bùi Tùng Lâm** — `2A202601676` | Role 1 — Team Leader & Architect | Điều phối, duyệt kiến trúc, review tích hợp, kiểm tra kết quả và thuyết trình tổng quan |
| **Chu Tâm Vũ** — `2A202601360` | Role 2 — Data & Retrieval Specialist | Task 1, Task 4, Task 7, Task 9 và nối retrieval với generation |
| **Nguyễn Đức Anh Tuấn** — `2A202601618` | Role 3 — Frontend & Chatbot Developer | Task 2, Task 5, Task 8, Task 10, Streamlit UI và live demo |
| **Trần Anh Tú** — `2A202601674` | Role 4 — Evaluation & QA Engineer | Task 3, Task 6, QA fallback/citation, golden dataset và báo cáo A/B |

Các role không có nghĩa là một người làm một mình toàn bộ hệ thống. Người phụ trách là **owner** của kết quả và là người giải thích phần đó khi review/demo; các thành viên còn lại vẫn cần hiểu input, output và điểm tích hợp.

### Checkpoint 1 — Thu thập và chuẩn hóa dữ liệu

**Mục tiêu:** biến nguồn chính sách/bài hỗ trợ thành Markdown sạch, có metadata và có thể đưa vào index.

| Người | Việc phải làm | File/thư mục cần nắm | Bàn giao cuối checkpoint |
|---|---|---|---|
| Bùi Tùng Lâm | Điều phối URL, thống nhất phạm vi dữ liệu, review nguồn và metadata | `data/SOURCES.md`, `data/landing/`, `src/task1_collect_legal_docs.py`, `src/task2_crawl_news.py` | Danh sách nguồn hợp lệ, quy ước tên file, xác nhận corpus đủ chủ đề |
| Chu Tâm Vũ | **Task 1:** thu thập tối thiểu 3 policy legal | `src/task1_collect_legal_docs.py`, `data/landing/legal/` | File policy gốc, inventory tên/kích thước và URL có thể kiểm tra |
| Nguyễn Đức Anh Tuấn | **Task 2:** crawl tối thiểu 5 bài help-center | `src/task2_crawl_news.py`, `data/landing/news/` | JSON có `url`, `title`, `date_crawled`, `content_markdown` |
| Trần Anh Tú | **Task 3 + QA:** convert legal/news sang Markdown và kiểm tra metadata | `src/task3_convert_markdown.py`, `data/standardized/` | 13 Markdown đọc được, không rỗng, giữ source/date/customer role |

**Điều kiện chuyển checkpoint:** `data/standardized/legal/` và `data/standardized/news/` có nội dung; không commit cookie, token hoặc API key. Nếu crawl lại sau này, phải chạy lại Task 3 và Task 4.

### Checkpoint 2 — Indexing và hai nhánh retrieval

**Mục tiêu:** từ Markdown tạo index dùng được cho tìm kiếm theo ý nghĩa và theo từ khóa.

| Người | Việc phải làm | File cần nắm | Bàn giao cuối checkpoint |
|---|---|---|---|
| Bùi Tùng Lâm | Duyệt quyết định chunk size, overlap, embedding backend và cách rebuild | `src/task4_chunking_indexing.py` | Cấu hình được review; thống nhất không dùng điểm RRF làm relevance threshold |
| Chu Tâm Vũ | **Task 4:** load → chunk → embed → persist index | `src/task4_chunking_indexing.py`, `data/index/chunks.json` | 13 tài liệu thành khoảng 85 chunks, schema chunk/metadata ổn định |
| Nguyễn Đức Anh Tuấn | **Task 5:** semantic search bằng cosine + overlap | `src/task5_semantic_search.py`, `src/retrieval_utils.py` | `semantic_search()` trả list sorted, có `content`, `score`, `metadata`, `id` |
| Trần Anh Tú | **Task 6 + QA:** BM25, kiểm tra query có dấu/không dấu và keyword match | `src/task6_lexical_search.py`, `tests/` | `lexical_search()` trả đúng schema, score giảm dần, không crash khi query lạ |

**Điều kiện chuyển checkpoint:** chạy Task 4 sau mọi thay đổi corpus; kiểm tra semantic/BM25 trên câu hỏi payment, refund, order tracking và cả biến thể tiếng Việt không dấu.

### Checkpoint 3–4 — Reranking, fallback, pipeline và generation

**Mục tiêu:** nối hai retriever thành một pipeline hoàn chỉnh, có fallback khi confidence thấp và có câu trả lời grounded.

| Người | Việc phải làm | File cần nắm | Bàn giao cuối checkpoint |
|---|---|---|---|
| Bùi Tùng Lâm | Duyệt kiến trúc, review flow và kết quả test/invariant | `src/task9_retrieval_pipeline.py`, `tests/` | Xác nhận luồng hybrid → fallback → generation đúng với thiết kế |
| Chu Tâm Vũ | **Task 7 + Task 9:** RRF/rerank và unified retrieval | `src/task7_reranking.py`, `src/task9_retrieval_pipeline.py` | `retrieve()` chạy dense/sparse, fallback theo dense score gốc, trả tối đa `top_k` |
| Nguyễn Đức Anh Tuấn | **Task 8 + Task 10:** structural/PageIndex fallback và generation/citation | `src/task8_pageindex_vectorless.py`, `src/task10_generation.py` | Có kết quả `source=pageindex` khi fallback; generation có citation hoặc từ chối xác minh |
| Trần Anh Tú | QA fallback, citation, source metadata và câu hỏi lạc domain | `tests/test_pipeline_quality.py`, `src/task10_generation.py` | Danh sách case pass/fail, phát hiện citation sai hoặc hallucination |

**Điều kiện chuyển checkpoint:** `retrieve()` không nhầm điểm RRF với semantic threshold; query vô nghĩa không làm pipeline crash; output generation có `answer`, `sources`, `retrieval_source`, `generation_mode`.

### Checkpoint 5–6 — UI, evaluation, QA và demo

**Mục tiêu:** biến pipeline thành sản phẩm nhóm có thể demo và có số liệu so sánh.

| Người | Việc phải làm | File cần nắm | Bàn giao cuối checkpoint |
|---|---|---|---|
| Bùi Tùng Lâm | Tích hợp, điều phối branch/công việc, review cuối và thuyết trình tổng quan | `README.md`, `PROJECT_HANDOFF.md`, toàn bộ pipeline | Bản chạy thống nhất, câu chuyện kiến trúc và checklist trình bày |
| Chu Tâm Vũ | Nối retrieval với generation, giải đáp các quyết định kỹ thuật | `src/task9_retrieval_pipeline.py`, `src/task10_generation.py` | Demo kỹ thuật: semantic/BM25/RRF/fallback và lý do chọn threshold |
| Nguyễn Đức Anh Tuấn | Streamlit UI, conversation memory, source cards và live demo | `app.py`, `src/task10_generation.py` | UI hiển thị answer, source, score, highlight, latency và follow-up query |
| Trần Anh Tú | Evaluation, QA cuối, golden dataset và báo cáo A/B | `group_project/evaluation/`, `tests/`, `results.md` | 16 golden cases, 4 metrics, so sánh hybrid vs dense-only, worst performers |

**Điều kiện hoàn thành:** `python -m pytest -q` đạt `41 passed`; Streamlit mở được; demo có citation/source cards; `python -m group_project.evaluation.eval_pipeline` sinh được báo cáo.

### Sau mỗi checkpoint, thành viên cần cập nhật gì?

Mỗi owner nên ghi ngắn gọn vào handoff/commit hoặc tin nhắn nhóm theo mẫu:

```text
[Checkpoint N] [Tên] — hoàn thành phần ...
Files chính: ...
Input/output: ...
Đã kiểm tra bằng: ... (lệnh + kết quả)
Rủi ro/việc cần người kế tiếp: ...
```

Ví dụ sau Checkpoint 2:

```text
[Checkpoint 2] Chu Tâm Vũ — Task 4 hoàn thành
Files chính: src/task4_chunking_indexing.py, data/index/chunks.json
Output: 13 docs → 85 chunks, chunk_size=700, overlap=100, hashing embedding 768d
Đã kiểm tra bằng: python -m src.task4_chunking_indexing; pytest -q
Bàn giao: Nguyễn Đức Anh Tuấn dùng schema chunk này cho semantic_search; Trần Anh Tú dùng cùng index để test BM25.
```

### Ai cần đọc phần nào để nắm bắt nhanh?

- **Bùi Tùng Lâm:** đọc các mục 2, 3, 6, 9 và bảng checkpoint để nói được toàn bộ flow và các điểm quyết định.
- **Chu Tâm Vũ:** đọc mục 5–6, Task 4–7–9 và cách threshold/fusion hoạt động.
- **Nguyễn Đức Anh Tuấn:** đọc mục 7–8, Task 2–5–8–10 và cách UI truyền history vào generation.
- **Trần Anh Tú:** đọc mục 9, 14, `tests/` và `group_project/evaluation/` để biết cách chứng minh pipeline đúng/chưa tốt.
- **Cả nhóm:** phải biết schema kết quả retrieval, cách chạy test, cách fallback và nơi xem source citation.

## 17. Khi giao AI sửa dự án, nên mô tả yêu cầu thế nào?

Nên nêu rõ tầng cần thay đổi và tiêu chí kiểm tra. Ví dụ:

> Cải thiện Task 6 để tokenizer xử lý cụm “trả hàng hoàn tiền” tốt hơn. Không sửa UI. Giữ nguyên schema kết quả. Chạy pytest và evaluation A/B, báo lại metric thay đổi.

Hoặc:

> Thay reranker heuristic ở Task 7 bằng cross-encoder local, nhưng phải có fallback offline. Không làm mất citation, không đổi API của `retrieve()`, và bổ sung test.

Những ràng buộc nên nhắc AI:

- giữ nguyên schema `content`, `score`, `metadata`, `source`;
- không đưa logic retrieval vào `app.py`;
- không commit secret hoặc dữ liệu nhạy cảm;
- không gọi API/upload ngoài hệ thống nếu chưa được cho phép;
- chạy `python -m pytest -q` sau thay đổi;
- chạy evaluation nếu thay retrieval, rerank hoặc generation;
- giải thích ảnh hưởng đến chế độ offline và production.

## 18. Tóm tắt trong một phút

- `data/standardized/` là kho kiến thức thực tế của chatbot.
- Task 4 biến tài liệu thành index gồm các chunk và embedding.
- Task 5 tìm theo ý nghĩa; Task 6 tìm theo từ khóa.
- Task 7 gộp và xếp hạng; Task 8 là fallback theo cấu trúc/PageIndex.
- Task 9 là entry point retrieval.
- Task 10 tạo câu trả lời có citation và fallback extractive.
- `app.py` chỉ là UI gọi Task 10.
- Không có API key vẫn chạy được.
- `pytest` xác nhận chức năng; evaluation A/B mới phản ánh chất lượng.

Sau file này, hai tài liệu nên đọc tiếp là `group_project/README.md` để hiểu sản phẩm đã hoàn thiện và `PROJECT_HANDOFF.md` để hiểu quyết định kỹ thuật, phân công và cách bàn giao.
