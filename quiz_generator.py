"""Quiz generation helpers for uploaded study notes."""

from __future__ import annotations

import json
import re
from typing import Any

import google.generativeai as genai


MODEL_NAME = "gemini-flash-latest"


def _model(api_key: str) -> Any:
    if not api_key:
        raise ValueError("Add a Gemini API key to generate a quiz.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


def generate_quiz(notes: str, api_key: str) -> list[dict[str, Any]]:
    """Generate exactly five MCQs and parse the model's JSON response."""
    prompt = f"""
Create exactly 5 multiple-choice questions from the study notes below.
Return ONLY a JSON array. Each item must have:
question (string), options (array of exactly 4 strings),
answer (integer from 0 to 3), and explanation (string).
Use only information present in the notes. Keep the questions suitable for
a BTech student and avoid trick questions.

STUDY NOTES:
{notes[:24000]}
"""
    response = _model(api_key).generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    quiz = json.loads(raw)
    if not isinstance(quiz, list) or len(quiz) != 5:
        raise ValueError("Gemini returned an invalid quiz format. Please try again.")
    for item in quiz:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("question"), str)
            or not isinstance(item.get("options"), list)
            or len(item["options"]) != 4
            or not isinstance(item.get("answer"), int)
            or item["answer"] not in range(4)
        ):
            raise ValueError("Gemini returned an invalid quiz format. Please try again.")
    return quiz
