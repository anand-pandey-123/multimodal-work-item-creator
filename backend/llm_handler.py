import base64, json, re, os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def encode_image(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def safe_parse_json(raw: str) -> dict:
    """Strips markdown fences and parses JSON safely."""
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse LLM output: {raw[:200]}")




def quick_analysis(image_bytes_list: list[bytes] | None, user_description: str) -> dict:
    """
    Pass 1 — identify affected area.
    If no images provided, derive from text description only.
    """
    if not image_bytes_list:
        # Text-only path — no vision model needed
        prompt = f"""
        Based on this description: "{user_description}"
        Return ONLY this JSON:
        {{
            "affected_area": "one phrase describing what feature or area this relates to",
            "error_keywords": ["keyword1", "keyword2", "keyword3"]
        }}
        """
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",   # text model, faster + cheaper
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.1
        )
        return safe_parse_json(res.choices[0].message.content)

    # Vision path — send all images in one call
    content = []

    # Add all images first
    for i, image_bytes in enumerate(image_bytes_list):
        b64 = encode_image(image_bytes)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })

    # Then the prompt
    image_note = f"You are given {len(image_bytes_list)} screenshot(s). Analyze all of them together." if len(image_bytes_list) > 1 else ""
    content.append({"type": "text", "text": f"""
        {image_note}
        User description: "{user_description}"
        Return ONLY this JSON:
        {{
            "affected_area": "one phrase describing what feature or area is shown",
            "error_keywords": ["keyword1", "keyword2", "keyword3"]
        }}
    """})

    res = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": content}],
        max_tokens=150,
        temperature=0.1
    )
    return safe_parse_json(res.choices[0].message.content)


def full_analysis(image_bytes_list: list[bytes] | None, full_prompt: str) -> dict:
    """
    Pass 2 — full work item generation.
    Handles 0, 1, or multiple images.
    """
    if not image_bytes_list:
        # Text-only — use fast text model
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=1000,
            temperature=0.2
        )
        return safe_parse_json(res.choices[0].message.content)

    # Build content array: all images first, then prompt text
    content = []
    for image_bytes in image_bytes_list:
        b64 = encode_image(image_bytes)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"}
        })
    content.append({"type": "text", "text": full_prompt})

    res = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{"role": "user", "content": content}],
        max_tokens=1000,
        temperature=0.2
    )
    return safe_parse_json(res.choices[0].message.content)