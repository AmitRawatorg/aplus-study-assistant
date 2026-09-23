# A+ Study Assistant

A Streamlit study companion for BTech students with Gemini tutoring, PDF note retrieval, summaries, quizzes, and local chat history.

## Run & Operate

- `streamlit run app.py --server.port 5000` — run the study assistant
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- Streamlit and Python 3.13
- Google Gemini via `google-generativeai`
- PDF extraction via `pdfplumber`
- LangChain text splitting, Gemini embeddings, and FAISS retrieval
- Local SQLite persistence

## Where things live

- `app.py` — Streamlit UI and Gemini chat flow
- `auth.py` — local login/signup using `streamlit-authenticator` password hashing
- `database.py` — SQLite users and chat history
- `rag_engine.py` — PDF text extraction and FAISS note retrieval
- `quiz_generator.py` — Gemini quiz generation and JSON validation
- `.env.example` — Gemini API key setup placeholder

## Architecture decisions

- User accounts and chat history remain local in `.study_assistant/study_assistant.db`.
- Uploaded PDFs are indexed in Streamlit session state, so note content is not persisted to disk.
- Gemini API access is configured through `GEMINI_API_KEY`; the code includes a visible placeholder rather than a secret.

## Product

- Students can create an account, sign in, ask general study questions, upload notes, search their notes with RAG, summarize PDFs, generate five-question quizzes, and return to prior chat history.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- PDF indexing and Gemini actions require a configured `GEMINI_API_KEY`.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
