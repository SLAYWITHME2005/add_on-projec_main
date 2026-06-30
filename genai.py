import os
import re
import sys
from typing import List, Tuple, Dict, Any

try:
    import openai
except Exception:
    openai = None


class GenAI:
    """
    College FAQ Answer Generator

    - Uses OpenAI if API key is available.
    - Otherwise returns the best FAQ answer directly.
    """

    def __init__(self):
        self.provider = None

        key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")

        if key and openai is not None:
            try:
                openai.api_key = key
                self.provider = "openai"
            except Exception as e:
                print("OpenAI configuration failed:", e, file=sys.stderr)

    def _score_contexts(
        self,
        query: str,
        contexts: List[Dict[str, Any]]
    ) -> List[Tuple[float, Dict[str, Any]]]:

        q_tokens = set(re.findall(r"\w+", query.lower()))

        scored = []

        for c in contexts:

            if "score" in c:
                score = float(c["score"])

            else:
                text = (
                    c.get("question", "")
                    + " "
                    + c.get("answer", "")
                ).lower()

                score = float(
                    sum(
                        1
                        for token in q_tokens
                        if token in text
                    )
                )

            scored.append((score, c))

        scored.sort(reverse=True, key=lambda x: x[0])

        return scored

    def get_answer(
        self,
        query: str,
        contexts: List[Dict[str, Any]],
        temperature: float = 0.0,
        top_k: int = 1,
    ) -> Tuple[str, List[int]]:

        if not contexts:
            return (
                "Sorry, I couldn't find an answer to your question.",
                [],
            )

        ranked = self._score_contexts(query, contexts)

        best_score, best = ranked[0]

        source_ids = [int(best["id"])]

        if self.provider == "openai":

            prompt = f"""
You are a helpful College FAQ Assistant.

Answer ONLY using the information below.

Question:
{best["question"]}

Answer:
{best["answer"]}

User:
{query}
"""

            try:

                response = openai.ChatCompletion.create(
                    model=os.getenv(
                        "OPENAI_MODEL",
                        "gpt-4o-mini",
                    ),
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        },
                    ],
                    temperature=temperature,
                    max_tokens=300,
                )

                answer = response["choices"][0]["message"]["content"].strip()

                return answer, source_ids

            except Exception as e:
                print(e)

        # Fallback (No OpenAI Key)

        return best["answer"], source_ids