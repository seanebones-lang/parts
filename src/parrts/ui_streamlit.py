"""Thin Streamlit dashboard over parrts hybrid RAG.

Run:
  streamlit run src/parrts/ui_streamlit.py
  # or: ./start_demo.sh ui
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src is importable when launched via streamlit path
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

import streamlit as st

from parrts.embeddings import HashingEmbedder, resolve_embedder
from parrts.engine import PartsRAGEngine


@st.cache_resource(show_spinner="Loading hybrid RAG index…")
def get_engine() -> PartsRAGEngine:
    root = Path(os.environ.get("PARRTS_ROOT", str(_ROOT))).resolve()
    name = os.environ.get("PARRTS_EMBEDDER", "hash").lower()
    embedder = HashingEmbedder() if name == "hash" else resolve_embedder(name)
    eng = PartsRAGEngine(root=root, embedder=embedder)
    eng.ensure_ready()
    return eng


def color_emoji(color: str) -> str:
    return {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(color.lower(), "⚪")


def main() -> None:
    st.set_page_config(
        page_title="Parrts Hybrid RAG",
        page_icon="🔧",
        layout="wide",
    )
    st.title("Parrts — multi-location parts hybrid RAG")
    st.caption(
        "Dense + BM25 RRF retrieval · traffic-light policy · offline-capable (HashingEmbedder)"
    )

    eng = get_engine()
    status = eng.status()

    c1, c2, c3, c4 = st.columns(4)
    inv = status.get("inventory") or {}
    c1.metric("Locations", inv.get("locations", "—"))
    c2.metric("SKUs indexed", status.get("parts_indexed") or inv.get("total_skus") or "—")
    c3.metric("Built", "yes" if status.get("built") else "no")
    c4.metric("Embedder", status.get("embedder") or type(eng.embedder).__name__)

    with st.sidebar:
        st.header("Query options")
        location = st.selectbox(
            "Location filter",
            options=["(all)"] + list((inv.get("by_location") or {}).keys()),
        )
        top_k = st.slider("Top-k", 1, 20, 5)
        use_llm = st.checkbox("Use LLM synthesis (needs API keys)", value=False)
        use_rerank = st.checkbox("Rerank (if cross-encoder available)", value=False)
        st.divider()
        st.subheader("System")
        st.json(
            {
                "root": status.get("root"),
                "dense_backend": status.get("dense_backend"),
                "sparse_backend": status.get("sparse_backend"),
            }
        )

    q = st.text_input(
        "Parts query",
        value="brake pads for 2019 Honda Civic",
        placeholder="e.g. oil filter Toyota Camry",
    )
    go = st.button("Search", type="primary")

    if go and q.strip():
        loc = None if location == "(all)" else location
        with st.spinner("Retrieving…"):
            result = eng.query(
                text=q.strip(),
                location=loc,
                top_k=top_k,
                use_llm=use_llm,
                use_rerank=use_rerank,
            )
        data = result.to_dict()
        tl = data.get("traffic_light") or {}
        color = str(tl.get("color") or "unknown")

        st.subheader(f"{color_emoji(color)} {color.upper()} — confidence {tl.get('confidence', '—')}")
        st.write(tl.get("reason") or "")
        if tl.get("actions"):
            st.write("**Actions:** " + "; ".join(tl["actions"]))

        if data.get("answer"):
            st.info(data["answer"])

        hits = data.get("hits") or []
        if not hits:
            st.warning("No hits.")
        else:
            st.markdown("### Matches")
            for i, h in enumerate(hits, 1):
                with st.container(border=True):
                    cols = st.columns([3, 1, 1, 1])
                    cols[0].markdown(f"**{i}. {h.get('name')}**  \n`{h.get('sku')}` · {h.get('location')}")
                    cols[1].metric("Stock", h.get("stock"))
                    cols[2].metric("Price", f"${float(h.get('price') or 0):.2f}")
                    cols[3].metric("Score", f"{float(h.get('score') or 0):.3f}")
                    st.caption(h.get("description") or "")

        with st.expander("Raw JSON"):
            st.json(data)

    st.divider()
    st.caption("Legacy Streamlit pitch demos remain in repo root `dashboard.py` if needed.")


if __name__ == "__main__":
    main()
