# Ma trận checkpoint, role và commit

Tài liệu này là nguồn đối chiếu giữa `checkpoint_timer.html`, người phụ trách và lịch sử Git.

## Ánh xạ role

| Role | Thành viên | GitHub |
|---|---|---|
| Role 1 — Team Leader & Architect | Bùi Tùng Lâm — 2A202601676 | `buitunglam308work-stack` |
| Role 2 — Data & Retrieval Specialist | Chu Tâm Vũ — 2A202601360 | `ctz1310204` |
| Role 3 — Frontend & Chatbot Developer | Nguyễn Đức Anh Tuấn — 2A202601618 | `nt15032` |
| Role 4 — Evaluation & QA Engineer | Trần Anh Tú — 2A202601674 | `tutran0401` |

## Checkpoint 0 — Setup môi trường

| Role | Công việc |
|---|---|
| Role 1 | Khởi tạo project, duyệt cấu trúc và cấu hình chung |
| Role 2 | Kiểm tra dependency cho data/indexing |
| Role 3 | Kiểm tra API config và runtime chatbot |
| Role 4 | Kiểm tra Streamlit, pytest và quy tắc bảo vệ secret |

## Checkpoint 1 — Thu thập và chuẩn hóa dữ liệu

| Role | Công việc |
|---|---|
| Role 1 | Phân chia URL, kiểm tra dữ liệu sau convert |
| Role 2 | Task 1 — thu thập legal documents |
| Role 3 | Task 2 — crawl help-center articles |
| Role 4 | Task 3 — convert toàn bộ sang Markdown và QA |

## Checkpoint 2 — Indexing và retrieval cơ bản

| Role | Công việc |
|---|---|
| Role 1 | Duyệt cấu hình chunking, embedding và index |
| Role 2 | Task 4 — chunking và indexing |
| Role 3 | Task 5 — semantic search |
| Role 4 | Task 6 — BM25/TF-IDF và QA |

## Checkpoint 3 — Reranking và fallback

| Role | Công việc |
|---|---|
| Role 1 | Duyệt công thức RRF và `k=60` |
| Role 2 | Task 7 — RRF, MMR và relevance reranking |
| Role 3 | Task 8 — PageIndex/structural fallback |
| Role 4 | Test query ngoài domain và fallback quality |

## Checkpoint 4 — Pipeline và generation

| Role | Công việc |
|---|---|
| Role 1 | Duyệt 35 test Task 1–10 và kiến trúc tích hợp |
| Role 2 | Task 9 — unified retrieval pipeline |
| Role 3 | Task 10 — LLM generation có citation |
| Role 4 | Citation, hallucination và fallback QA |

## Checkpoint 5 — Bài tập nhóm

| Role | Công việc |
|---|---|
| Role 1 | Tích hợp các module vào ứng dụng nhóm |
| Role 2 | Nối retrieval/generation vào `app.py` |
| Role 3 | Hoàn thiện Streamlit Chatbot UI |
| Role 4 | Golden dataset, evaluation A/B và quality tests |

## Checkpoint 6 — Demo và bàn giao

| Role | Công việc |
|---|---|
| Role 1 | Tổng quan kiến trúc, điều phối và handoff |
| Role 2 | Giải đáp kỹ thuật data/retrieval |
| Role 3 | Live demo Streamlit |
| Role 4 | Báo cáo evaluation, QA và kết quả A/B |

Mỗi checkpoint có bốn commit theo thứ tự Role 1 → Role 4. Commit review/setup không sinh thay đổi file được tạo có chủ đích bằng `--allow-empty`; commit code chứa đúng file theo phạm vi role.
