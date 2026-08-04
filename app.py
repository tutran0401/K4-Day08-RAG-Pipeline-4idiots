"""Streamlit UI for the e-commerce support RAG pipeline."""

from __future__ import annotations

import html
import os
import re
import time

import streamlit as st

from src.task10_generation import generate_with_citation

st.set_page_config(page_title="E-commerce Support RAG", page_icon="🛒", layout="wide")

st.markdown(
    """
    <style>
      .block-container {max-width: 1120px; padding-top: 1.5rem;}
      .hero {padding: 1.25rem 1.5rem; border-radius: 18px; background: linear-gradient(120deg,#0f766e,#2563eb); color:white; margin-bottom:1rem;}
      .hero h1 {margin:0; font-size:1.8rem;} .hero p {margin:.4rem 0 0; opacity:.9;}
      mark {background:#fef08a; color:#422006; padding:0 .12rem; border-radius:.2rem;}
      .source-card {border:1px solid rgba(128,128,128,.25); border-radius:12px; padding:.8rem; margin:.5rem 0;}
    </style>
    <div class="hero"><h1>🛒 E-commerce Support RAG</h1>
    <p>Hybrid Semantic + BM25 · RRF reranking · structural fallback · grounded citations</p></div>
    """,
    unsafe_allow_html=True,
)


def _highlight(text: str, query: str) -> str:
    escaped = html.escape(text)
    terms = sorted({word for word in re.findall(r"\w+", query, re.UNICODE) if len(word) >= 4}, key=len, reverse=True)
    for term in terms[:12]:
        escaped = re.sub(f"(?i)({re.escape(html.escape(term))})", r"<mark>\1</mark>", escaped)
    return escaped.replace("\n", "<br>")


def render_sources(sources: list[dict], query: str) -> None:
    if not sources:
        st.info("Không có nguồn phù hợp được truy xuất.")
        return
    for index, source in enumerate(sources, 1):
        metadata = source.get("metadata") or {}
        name = metadata.get("source", "Unknown")
        role = metadata.get("customer_role", "both")
        section = metadata.get("section")
        score = float(source.get("score", 0))
        st.markdown(
            f"<div class='source-card'><b>[{index}] {html.escape(name)}</b> · "
            f"<code>{html.escape(source.get('source', 'hybrid'))}</code> · score <code>{score:.4f}</code> · "
            f"role <code>{html.escape(str(role))}</code>"
            + (f"<br><small>Section: {html.escape(str(section))}</small>" if section else "")
            + "</div>",
            unsafe_allow_html=True,
        )
        with st.expander("Xem đoạn bằng chứng và highlight từ khóa"):
            st.markdown(_highlight(source.get("content", ""), query), unsafe_allow_html=True)


if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

with st.sidebar:
    st.header("Thiết lập")
    top_k = st.slider("Số đoạn bằng chứng", 3, 8, 5, help="Nhiều đoạn tăng recall nhưng có thể giảm precision.")
    lexical_method = st.radio(
        "Lexical search",
        options=["bm25", "tfidf"],
        format_func=lambda v: "BM25" if v == "bm25" else "TF-IDF",
        horizontal=True,
        help="Thuật toán cho nhánh sparse retrieval trong hybrid search: BM25 (bão hoà tần suất từ, "
        "chuẩn hoá độ dài) hoặc TF-IDF cosine (mô hình vector space cổ điển).",
    )
    show_debug = st.toggle("Hiện query sau mở rộng", value=False)
    if st.button("🗑️ Xóa hội thoại", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    st.divider()
    st.subheader("Câu hỏi gợi ý")
    suggestions = [
        "Có thể đổi phương thức thanh toán sau khi đặt hàng không?",
        "Cần bằng chứng gì khi hàng bị hỏng?",
        "Người bán không được đăng sản phẩm nào?",
        "Tôi theo dõi hành trình đơn hàng ở đâu?",
    ]
    for index, suggestion in enumerate(suggestions):
        if st.button(suggestion, key=f"suggestion-{index}", use_container_width=True):
            st.session_state.pending_query = suggestion
            st.rerun()
    st.divider()
    st.caption("🔒 Không gửi mật khẩu, PIN, OTP hoặc dữ liệu thẻ vào khung chat.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            columns = st.columns(4)
            columns[0].caption(f"Nguồn: {message.get('retrieval_source', 'none')}")
            columns[1].caption(f"Generation: {message.get('generation_mode', 'offline').upper()}")
            columns[2].caption(f"Độ trễ: {message.get('latency', 0):.2f}s")
            columns[3].caption(f"Chunks: {len(message.get('sources', []))}")
            st.caption(f"Lexical: {message.get('lexical_method', 'bm25').upper()}")
            with st.expander(f"📚 Nguồn tham khảo ({len(message.get('sources', []))})"):
                render_sources(message.get("sources", []), message.get("query", ""))

query = st.chat_input("Hỏi về thanh toán, trả hàng, giao hàng, quyền riêng tư hoặc quy định người bán…")
query = query or st.session_state.pending_query
if query:
    st.session_state.pending_query = None
    history = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        started = time.perf_counter()
        with st.spinner("Đang truy xuất và kiểm tra bằng chứng…"):
            try:
                os.environ["LEXICAL_METHOD"] = lexical_method
                result = generate_with_citation(query, top_k=top_k, conversation_history=history)
                answer = result["answer"]
                sources = result.get("sources", [])
                retrieval_source = result.get("retrieval_source", "none")
                generation_mode = result.get("generation_mode", "offline")
            except Exception as exc:
                answer = f"Không thể hoàn tất truy vấn: `{type(exc).__name__}: {exc}`"
                sources, retrieval_source, generation_mode = [], "error", "error"
                result = {"effective_query": query}
        latency = time.perf_counter() - started
        st.markdown(answer)
        if show_debug and result.get("effective_query") != query:
            st.caption(f"Query sau mở rộng: {result['effective_query']}")
        if result.get("generation_warning"):
            st.caption(result["generation_warning"])
        metrics = st.columns(4)
        metrics[0].metric("Retrieval", retrieval_source)
        metrics[1].metric("Generation", generation_mode.upper())
        metrics[2].metric("Độ trễ", f"{latency:.2f}s")
        metrics[3].metric("Số chunks", len(sources))
        st.caption(f"Lexical search: {lexical_method.upper()}")
        with st.expander(f"📚 Nguồn tham khảo ({len(sources)})", expanded=True):
            render_sources(sources, query)
    st.session_state.messages.append({
        "role": "assistant", "content": answer, "sources": sources, "query": query,
        "retrieval_source": retrieval_source, "generation_mode": generation_mode, "latency": latency,
        "lexical_method": lexical_method,
    })
