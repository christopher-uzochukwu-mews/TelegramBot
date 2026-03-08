"""Optional briefings for assignments: OpenAI when available, else use details from schedule."""
import re
from typing import Any

from config import OPENAI_API_KEY

# Max length for manual-details "briefing" when no API (keeps messages readable in Telegram)
MAX_DETAILS_BRIEFING_LEN = 480


def _details_as_briefing(details: str) -> str:
    """Use schedule 'details' as briefing text when no API: first 1–2 sentences, capped length."""
    if not details or not details.strip():
        return ""
    text = details.strip()
    sentences = re.split(r"(?<=[.!?])\s+", text, maxsplit=2)
    out = sentences[0]
    if len(sentences) > 1:
        out += " " + sentences[1]
    if len(out) <= MAX_DETAILS_BRIEFING_LEN:
        return out.strip()
    # Truncate: prefer cutting at last sentence end before limit, else at last word
    capped = out[: MAX_DETAILS_BRIEFING_LEN - 3]
    last_sent = max(capped.rfind("."), capped.rfind("!"), capped.rfind("?"))
    if last_sent > MAX_DETAILS_BRIEFING_LEN // 2:
        out = out[: last_sent + 1].strip()
    else:
        out = capped.rsplit(" ", 1)[0] + "..."
    return out.strip()


def get_assignment_briefing(event: dict[str, Any]) -> str | None:
    """Return a short briefing for an assignment: from OpenAI if key set, else from event 'details'."""
    title = event.get("title", "")
    course = event.get("course", "")
    details = event.get("details", "")
    time_note = event.get("time_note", "")

    if OPENAI_API_KEY:
        prompt = (
            "You are a helpful MBA study assistant. In 2–4 short sentences, explain what this "
            "assignment is and what the student should focus on. Be clear and encouraging. "
            "Do not use bullet points or markdown.\n\n"
            f"Course: {course}\nTitle: {title}\nWhen: {time_note}\n"
        )
        if details:
            prompt += f"Details: {details}\n"
        prompt += "\nBriefing:"
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
            )
            text = (r.choices[0].message.content or "").strip()
            if text:
                return text
        except Exception:
            pass

    # No API or API failed: use schedule "details" as briefing if present
    if details:
        return _details_as_briefing(details)
    return None
