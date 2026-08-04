# E-commerce Support RAG Chatbot

Chatbot hỏi đáp chính sách thương mại điện tử chạy được hoàn toàn offline cho demo, đồng thời có thể dùng sentence-transformers, ChromaDB, OpenRouter và RAGAS khi cấu hình môi trường production.

## Trạng thái deliverable

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| Pipeline Task 1–10 | Hoàn thành | `python -m pytest -q` → 41 passed |
| Chatbot Streamlit | Hoàn thành | citation, source score, highlight, latency, gợi ý câu hỏi |
| Conversation memory | Hoàn thành | lịch sử được truyền vào LLM và dùng mở rộng câu hỏi nối tiếp |
| Golden dataset | Hoàn thành | 16 Q&A có expected answer/context/source/role |
| Evaluation | Hoàn thành | 4 metrics, 2 configs, worst-performer analysis |
| Báo cáo | Hoàn thành | `evaluation/results.md`, sinh lại được bằng một lệnh |

## Kiến trúc

```text
User / Streamlit
       │ query + recent conversation
       ▼
Follow-up query expansion
       │
       ├──────────────┐
       ▼              ▼
Semantic search      BM25
(dense/hash)         (lexical)
       └──────┬───────┘
              ▼
         RRF fusion
              ▼
     relevance reranking ── cosine thấp ──► structural PageIndex fallback
              │                                  │
              └──────────────────┬───────────────┘
                                 ▼
                    neighbor-aware context + reorder
                                 ▼
              OpenRouter LLM hoặc extractive generator
                                 ▼
                 Answer + inline citations + source cards
```

Các quyết định quan trọng:

- Ngưỡng fallback dùng cosine gốc của dense search, không dùng điểm RRF nhỏ và không có ý nghĩa relevance tuyệt đối.
- Embedding hashing đa ngôn ngữ là backend mặc định để demo không phụ thuộc Internet. Production có thể bật `BAAI/bge-m3`.
- BM25 dùng `k1=1.5`, `b=0.75` và chuẩn hóa dấu tiếng Việt; query expansion ánh xạ các khái niệm Việt–Anh.
- Backend bonus `LEXICAL_METHOD=tfidf` dùng trọng số `TF × log((N+1)/(df+1))+1` rồi cosine similarity. Khác BM25, TF-IDF không có term-saturation `k1` hay document-length normalization `b`; đây là baseline dễ giải thích để demo/A-B lexical.
- Generation offline chỉ trích câu từ nguồn top-ranked và luôn thêm citation; nếu không có evidence thì từ chối xác minh.

## Chạy nhanh

```powershell
python -m pip install -r requirements.txt
python -m src.task4_chunking_indexing
python -m pytest tests/test_individual.py -q
streamlit run app.py
```

Không có API key, chatbot vẫn chạy bằng encoder và generator cục bộ.

### Chạy thật với OpenRouter (khuyên dùng)

1. Đăng nhập OpenRouter và tạo API key tại `https://openrouter.ai/settings/keys`.
2. Tạo file cấu hình cục bộ:

```powershell
Copy-Item .env.example .env
```

3. Mở `.env`, thay key mẫu bằng key thật và giữ model miễn phí:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-KEY_THAT_CUA_BAN
LLM_MODEL=openrouter/free
```

4. Cài dependency, tạo index và chạy ứng dụng:

```powershell
python -m pip install -r requirements.txt
python -m src.task4_chunking_indexing
streamlit run app.py
```

Khi câu trả lời được sinh qua API, kết quả nội bộ có `generation_mode="llm"`. Nếu key sai, hết quota hoặc model tạm bận, ứng dụng hiện cảnh báo và tự chuyển sang generator trích xuất offline.

Để dùng OpenAI trực tiếp, xóa/comment `OPENROUTER_API_KEY` rồi cấu hình:

```dotenv
OPENAI_API_KEY=sk-proj-KEY_THAT_CUA_BAN
LLM_MODEL=gpt-4o-mini
```

Chỉ bật một nhà cung cấp để tránh nhầm key/model. Không gửi API key qua chat và không commit `.env`; file này đã nằm trong `.gitignore`.

Backend embedding production (tùy chọn):

```powershell
$env:RAG_EMBEDDING_BACKEND="sentence_transformer"
$env:RAG_EMBEDDING_MODEL="BAAI/bge-m3"
python -m src.task4_chunking_indexing
```

Alias tương thích với hướng dẫn upstream: `EMBEDDING_PROVIDER=sentence_transformers`. Upstream còn gợi ý Google `models/text-embedding-004` và OpenAI `text-embedding-3-small`, nhưng hai nhánh API embedding này chưa được dispatch trong implementation hiện tại; không bật chúng nếu chưa bổ sung cùng logic embed cho cả Task 4 và Task 5. Khi đổi provider/model/dimension, phải rebuild index và Chroma collection.

Chạy backend lexical TF-IDF để demo bonus:

```powershell
$env:LEXICAL_METHOD="tfidf"
python -m src.task6_lexical_search
```

## Evaluation

Chế độ mặc định dùng proxy metrics xác định, không tốn API và phù hợp CI. Báo cáo luôn ghi rõ đây không phải điểm LLM-judge.

```powershell
python -m group_project.evaluation.eval_pipeline
```

Chạy RAGAS chính thức trong virtual environment riêng khi đã có API/key và quota. Stack RAGAS 0.1.21 dùng nhánh OpenAI/LangChain cũ nên không cài chung với Crawl4AI mới:

```powershell
python -m venv .venv-ragas
.\.venv-ragas\Scripts\python -m pip install -r requirements-ragas.txt
$env:RAGAS_USE_LLM="1"
.\.venv-ragas\Scripts\python -m group_project.evaluation.eval_pipeline
```

| Metric | Ý nghĩa triển khai offline |
|---|---|
| Faithfulness | tỷ lệ token nội dung câu trả lời có trong evidence |
| Answer relevance | F1 token giữa câu trả lời và đáp án chuẩn |
| Context recall | tỷ lệ token đáp án chuẩn xuất hiện trong contexts |
| Context precision | tỷ lệ chunks đúng expected source hoặc đủ overlap |

Hai cấu hình A/B là hybrid + RRF + rerank so với dense-only không rerank. Kết quả và ba ca tệ nhất được xuất vào [results.md](evaluation/results.md).

## Phân công theo vai trò

Phân công theo module để giữ ranh giới trách nhiệm khi demo.

| Vai trò | Thành viên / MSSV | Phạm vi | Trạng thái |
|---|---|---|---|
| Data & policy | Bùi Tùng Lâm — 2A202601676 | Task 1–3, nguồn và metadata | Hoàn thành |
| Retrieval | Chu Tâm Vũ — 2A202601360 | Task 4–6, chunking/indexing, dense và BM25 | Hoàn thành |
| RAG architect | Nguyễn Đức Anh Tuấn — 2A202601618 | Task 7–10, reranking, fallback và citation | Hoàn thành |
| Product/UI & Evaluation | Trần Anh Tú — 2A202601674 | Streamlit, memory, source UX, golden dataset và A/B report | Hoàn thành |

## Checklist demo

1. Chạy test và chỉ ra `41 passed`.
2. Hỏi một câu payment/refund và mở source card để xem score + highlight.
3. Hỏi nối tiếp “Còn COD thì sao?” để demo conversation memory/query expansion.
4. Hỏi chuỗi vô nghĩa để demo từ chối hoặc structural fallback, không hallucinate.
5. Mở `results.md`, giải thích chênh lệch recall/precision giữa A và B.

## Giới hạn và an toàn

- Các file policy là snapshot giáo dục có ghi nguồn/ngày review; điều kiện trên trang/đơn trực tuyến vẫn là nguồn có thẩm quyền.
- Không đưa OTP, PIN, mật khẩu hoặc dữ liệu thẻ vào chat.
- Điểm proxy offline chỉ dùng regression/CI; không được trình bày như điểm RAGAS do LLM đánh giá.
- Khi thay corpus, index cục bộ tự rebuild theo thời gian sửa file; Chroma production cần reindex rõ ràng.
