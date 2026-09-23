"""A+ Study Assistant — Streamlit entry point."""

from __future__ import annotations

import os
from typing import Any

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

from auth import show_auth_screen
from database import get_messages, init_db, save_message
from quiz_generator import generate_quiz
from rag_engine import build_vector_store, extract_pdf_text, get_configured_api_key, retrieve_context


load_dotenv()
init_db()

APP_NAME = "A+ Study Assistant"
FOUNDER = "Amit Rawat"
TAGLINE = "Learn smarter, not harder."
MODEL_NAME = "gemini-flash-lite-latest"

GEMINI_API_KEY = get_configured_api_key() or "YOUR_GEMINI_API_KEY_HERE"


def has_api_key() -> bool:
    return GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE"


def model(api_key: str) -> Any:
    if not api_key:
        raise ValueError("Add your Gemini API key in the GEMINI_API_KEY environment variable.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


def generate_answer(question: str, api_key: str, context: str | None = None) -> str:
    if context:
        prompt = f"""
Answer the student's question using only the uploaded study notes below.
If the notes do not contain enough information, say so clearly and suggest
what concept the student should review. Keep the answer helpful and concise.

UPLOADED NOTES:
{context[:18000]}

STUDENT QUESTION:
{question}
"""
    else:
        prompt = f"""
You are A+ Study Assistant, a friendly and knowledgeable tutor for students at any level.

Rules for your answer:
1. ALWAYS answer in point-wise format (numbered or bulleted points). Never write one big paragraph.
2. Break complex ideas into simple, easy-to-follow steps or points.
3. If a diagram or visual structure would help, describe it using a simple text-based diagram.
4. Always include at least one clear, relatable example for every concept.
5. Use simple language first, then add technical depth if relevant.
6. Never refuse or redirect the question.

STUDENT QUESTION:
{question}
"""
    return model(api_key).generate_content(prompt).text.strip()


def summarize_notes(notes: str, api_key: str) -> str:
    prompt = f"""
Summarize these study notes in 6-8 concise, easy-to-understand bullet points.
NOTES:
{notes[:24000]}
"""
    return model(api_key).generate_content(prompt).text.strip()


def load_saved_chat() -> None:
    if "messages" not in st.session_state:
        rows = get_messages(st.session_state.username)
        st.session_state.messages = [
            {"role": row["role"], "content": row["content"], "source": row["source"]}
            for row in rows
        ]


# ---------- Sidebar navigation ----------

def show_sidebar() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "Home"

    with st.sidebar:
        st.markdown(f"## 🎓 {APP_NAME}")
        st.divider()

        nav_items = [("🏠", "Home"), ("💬", "Chat"), ("🏆", "Quiz"), ("👤", "My")]
        for icon, label in nav_items:
            active = st.session_state.page == label
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{label}",
                use_container_width=True,
                type="primary" if active else "secondary",
            ):
                st.session_state.page = label
                st.rerun()

        st.divider()
        st.write(f"Signed in as **{st.session_state.display_name}**")
        if st.session_state.get("uploaded_filename"):
            st.info(f"Notes: {st.session_state.uploaded_filename}")
        st.divider()
        if st.button("Log out", use_container_width=True):
            for key in ("authenticated", "username", "display_name", "messages", "page"):
                st.session_state.pop(key, None)
            st.rerun()


# ---------- Home dashboard ----------

CARD_STYLE = """
<div style="
    background: linear-gradient(135deg, {c1}, {c2});
    border-radius: 18px;
    padding: 20px 16px;
    min-height: 170px;
    color: white;
    box-shadow: 0 8px 20px rgba(0,0,0,0.35);
">
    <div style="font-size: 28px;">{icon}</div>
    <div style="font-size: 17px; font-weight: 700; margin-top: 8px;">{title}</div>
    <div style="font-size: 13px; opacity: 0.9; margin-top: 6px;">{desc}</div>
</div>
"""


def show_home() -> None:
    st.markdown(f"## Hello, {st.session_state.display_name} 👋")
    st.write("Your AI Study Assistant is here! Upload PDFs, ask questions, take quizzes.")
    st.write("")

    cards = [
        ("📄", "Upload PDF", "Get a clean summary and key points.", "#3b5bfd", "#7c3aed", "Quiz"),
        ("💬", "Ask Anything", "Get accurate, easy-to-understand answers.", "#0ca678", "#20c997", "Chat"),
        ("🏆", "Quiz", "Test your knowledge on any topic.", "#e8590c", "#f76707", "Quiz"),
        ("👤", "My", "View your details and settings.", "#d6336c", "#e64980", "My"),
    ]
    cols = st.columns(4)
    for col, (icon, title, desc, c1, c2, target) in zip(cols, cards):
        with col:
            st.markdown(
                CARD_STYLE.format(icon=icon, title=title, desc=desc, c1=c1, c2=c2),
                unsafe_allow_html=True,
            )
            if st.button(f"Go to {title}", key=f"card_{title}", use_container_width=True):
                st.session_state.page = target
                st.rerun()

    st.write("")
    st.divider()
    st.markdown("### Recent")
    messages = st.session_state.get("messages", [])
    if messages:
        last_user = [m for m in messages if m["role"] == "user"]
        if last_user:
            st.info(f"Last question: {last_user[-1]['content'][:80]}")
    else:
        st.caption("Nothing yet — start by asking a question or uploading a PDF.")


# ---------- Chat page ----------

def render_messages() -> None:
    messages = st.session_state.messages
    if not messages:
        with st.chat_message("assistant", avatar="📘"):
            st.markdown(
                "Hi! I'm ready to help you study. Ask me a concept question, "
                "or upload notes to chat with your PDF."
            )
        return
    last_pair = messages[-2:] if len(messages) >= 2 else messages[-1:]
    for message in last_pair:
        avatar = "📘" if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
            if message.get("source") == "notes":
                st.caption("Based on your uploaded notes")


def show_history_expander() -> None:
    messages = st.session_state.get("messages", [])
    if len(messages) <= 2:
        return
    pairs = []
    i = 0
    while i < len(messages):
        if messages[i]["role"] == "user":
            question = messages[i]
            answer = messages[i + 1] if i + 1 < len(messages) else None
            pairs.append((question, answer))
            i += 2
        else:
            i += 1
    with st.expander(f"📜 History ({len(pairs) - 1} earlier questions)"):
        for question, answer in reversed(pairs[:-1]):
            st.markdown(f"**Q:** {question['content']}")
            if answer:
                st.markdown(f"**A:** {answer['content']}")
            st.divider()


def show_chat_page() -> None:
    st.markdown("## 💬 Ask Anything")
    st.caption("Chat with your AI study assistant")
    show_history_expander()
    render_messages()
    prompt = st.chat_input("Ask a study question...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt, "source": "general"})
        save_message(st.session_state.username, "user", prompt, "general")
        with st.chat_message("user"):
            st.markdown(prompt)
        source = "notes" if st.session_state.get("vector_store") else "general"
        try:
            context = (
                retrieve_context(st.session_state.vector_store, prompt)
                if source == "notes"
                else None
            )
            with st.chat_message("assistant", avatar="📘"):
                with st.spinner("Thinking..."):
                    answer = generate_answer(prompt, GEMINI_API_KEY if has_api_key() else "", context)
                st.markdown(answer)
                if source == "notes":
                    st.caption("Based on your uploaded notes")
            st.session_state.messages.append({"role": "assistant", "content": answer, "source": source})
            save_message(st.session_state.username, "assistant", answer, source)
        except Exception as exc:
            st.error(str(exc))


# ---------- Quiz / PDF page ----------

def show_quiz_page() -> None:
    st.markdown("## 🏆 Quiz & PDF Notes")
    st.subheader("Your notes")
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"], key="notes_uploader")
    if uploaded_file is None:
        st.caption("Upload lecture notes or a textbook chapter to unlock note-based answers.")
        return

    file_signature = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.get("uploaded_signature") != file_signature:
        st.session_state.uploaded_signature = file_signature
        st.session_state.uploaded_filename = uploaded_file.name
        st.session_state.vector_store = None
        st.session_state.notes_text = ""
        try:
            pdf_bytes = uploaded_file.getvalue()
            with st.spinner("Reading your PDF and building a searchable index..."):
                notes_text = extract_pdf_text(pdf_bytes)
                vector_store, chunk_count = build_vector_store(notes_text, GEMINI_API_KEY if has_api_key() else "")
            st.session_state.notes_text = notes_text
            st.session_state.vector_store = vector_store
            st.session_state.chunk_count = chunk_count
            st.success(f"Indexed {chunk_count} note chunks.")
        except Exception as exc:
            st.session_state.notes_text = ""
            st.error(str(exc))

    if st.session_state.get("notes_text"):
        st.caption(
            f"{len(st.session_state.notes_text):,} characters extracted · "
            f"{st.session_state.get('chunk_count', 0)} searchable chunks"
        )
        summarize_col, quiz_col = st.columns(2)
        with summarize_col:
            if st.button("Summarize notes", use_container_width=True):
                try:
                    with st.spinner("Creating your summary..."):
                        st.session_state.summary = summarize_notes(st.session_state.notes_text, GEMINI_API_KEY)
                except Exception as exc:
                    st.error(str(exc))
        with quiz_col:
            if st.button("Generate quiz", use_container_width=True):
                try:
                    with st.spinner("Writing five questions..."):
                        st.session_state.quiz = generate_quiz(st.session_state.notes_text, GEMINI_API_KEY)
                except Exception as exc:
                    st.error(str(exc))

        if st.session_state.get("summary"):
            with st.expander("Notes summary", expanded=True):
                st.markdown(st.session_state.summary)
        if st.session_state.get("quiz"):
            with st.expander("5-question quiz", expanded=True):
                for index, item in enumerate(st.session_state.quiz, start=1):
                    st.markdown(f"**{index}. {item['question']}**")
                    st.radio(
                        "Choose an answer",
                        item["options"],
                        key=f"quiz_{st.session_state.uploaded_signature}_{index}",
                        label_visibility="collapsed",
                    )
                    with st.expander("Show answer"):
                        st.success(item["options"][item["answer"]])
                        if item.get("explanation"):
                            st.caption(item["explanation"])


# ---------- My page ----------

def show_my_page() -> None:
    st.markdown("## 👤 My Profile")
    st.write(f"**Name:** {st.session_state.display_name}")
    st.write(f"**Username:** {st.session_state.username}")
    st.divider()
    st.subheader("App info")
    st.write(f"**{APP_NAME}**")
    st.caption(f"Founded by {FOUNDER} · {TAGLINE}")


def run_app() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="📘", layout="wide")

    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');
        .stApp { background-color: #0a0a0f; color: #ffffff; font-family: 'Inter', sans-serif; }
        h1, h2, h3 { font-family: 'Poppins', sans-serif; font-weight: 700; color: #ffffff; }
        p, span, label, div, .stMarkdown { color: #e5e5e5; }
        .stButton>button {
            border-radius: 12px;
            font-weight: 600;
            font-family: 'Poppins', sans-serif;
        }
        [data-testid="stSidebar"] { background-color: #05050a; border-right: 1px solid #222222; }
        [data-testid="stChatMessage"] {
            background-color: #14141c;
            border-radius: 14px;
            border: 1px solid #262636;
            padding: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.get("authenticated"):
        show_auth_screen()
        return

    load_saved_chat()
    show_sidebar()

    page = st.session_state.get("page", "Home")
    if page == "Home":
        show_home()
    elif page == "Chat":
        show_chat_page()
    elif page == "Quiz":
        show_quiz_page()
    elif page == "My":
        show_my_page()


if __name__ == "__main__":
    run_app()