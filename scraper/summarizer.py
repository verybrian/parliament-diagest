import os
import json
import logging
import textwrap
import google.generativeai as genai

log = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"

PROMPT_TEMPLATE = textwrap.dedent("""
    You are a legal analyst summarizing Kenyan parliamentary bills for ordinary citizens.
    Your job is to read the extracted text of a bill and return a concise, plain-English
    summary in JSON format.

    The JSON must have exactly these 7 fields:

    {{
        "title": "Full official title of the bill",
        "date": "Date the bill was published or introduced, as it appears in the document",
        "endorser": "Name and title of the person who signed/endorsed the bill",
        "argument": "1-2 sentences on the problem or situation this bill is responding to",
        "proposal": "1-2 sentences on what the bill proposes to do about it",
        "who_is_affected": "1-2 sentences on who will be impacted — citizens, businesses, county governments, etc.",
        "key_changes": [
            "Specific change 1",
            "Specific change 2",
            "..."
        ]
    }}

    Rules:
    - Use plain English — no legal jargon. Write as if explaining to a friend.
    - Keep each field brief. The whole summary should fit comfortably in an email.
    - key_changes should be 3-6 bullet points maximum, each one sentence.
    - If a field cannot be determined from the text, use null.
    - Return ONLY the JSON object. No markdown, no code fences, no explanation.

    Bill text:
    {text}
""")


def summarize(extracted: dict) -> dict:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL)

    prompt = PROMPT_TEMPLATE.format(text=extracted["text"])
    log.info("Sending %d characters to Gemini (%s)...", len(extracted["text"]), MODEL)

    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )

    raw = response.text.strip()
    log.info("Gemini responded with %d characters", len(raw))

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        summary = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("Gemini returned non-JSON output:\n%s", raw)
        raise ValueError(f"Could not parse Gemini response as JSON: {e}") from e

    for field in ["title", "date", "endorser", "argument", "proposal", "who_is_affected", "key_changes"]:
        summary.setdefault(field, None)

    log.info("Summary parsed — title: %s", summary.get("title"))
    return summary