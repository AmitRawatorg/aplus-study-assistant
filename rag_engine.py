"""PDF extraction and LangChain + FAISS retrieval for uploaded study notes."""

from __future__ import annotations

import io
import os
from typing import Any

import pdfplumber
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import streamlit as st

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract readable text from every page in a PDF."""
    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text.strip())
    return "\n\n".join(pages).strip()

@st.cache_resource
def build_vector_store(text: str, api_key: str) -> tuple[FAISS, int]:
    """Split notes and create a FAISS index backed by Gemini embeddings."""
    if not text.strip():
        raise ValueError("No readable text was found in this PDF.")
    if not api_key:
        raise ValueError("Add a Gemini API key before indexing notes.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=180,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    documents = [Document(page_content=chunk) for chunk in splitter.split_text(text)]
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key,
    )
    return FAISS.from_documents(documents, embeddings), len(documents)


def retrieve_context(vector_store: FAISS, question: str, k: int = 4) -> str:
    documents = vector_store.similarity_search(question, k=k)
    return "\n\n---\n\n".join(document.page_content for document in documents)


def get_configured_api_key() -> str:
    """Read the key from the environment; the placeholder makes setup obvious."""
    return os.getenv("GEMINI_API_KEY", "").strip()
