import json


def build_messages(system_prompt: str, payload: dict):
    # Tip: if arrays are huge, trim last 60–90 points here
    msg_user = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": msg_user},
    ]

