import json
import os
import urllib.error
import urllib.parse
import urllib.request

FIND_ENDPOINT_BASE = os.environ.get(
    "FIND_ENDPOINT_BASE",
    "https://gkgspoul29.execute-api.us-east-1.amazonaws.com/hom/find",
)

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")

def _find_terminal(uuid_value):
    url = f"{FIND_ENDPOINT_BASE}?terminal={urllib.parse.quote(uuid_value)}"
    print(f"Calling find endpoint for UUID {uuid_value}: {url}")
    req = urllib.request.Request(url, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            print(f"Find response status for {uuid_value}: {resp.status}")
            if resp.status != 200:
                return None
            return json.loads(body)
    except urllib.error.HTTPError as http_error:
        print(f"Terminal not found for {uuid_value}: status={http_error.code}")
        return None
    except Exception as exc:
        print(f"Error calling /find for {uuid_value}: {exc}")
        return None


def _build_thread_message(found_results, not_found):
    lines: list[str] = []

    if found_results:
        lines.append(f"*Resultados encontrados ({len(found_results)})*")
        for uuid_value, data in found_results:
            value = data.get("value", "-") if isinstance(data, dict) else "-"
            description = data.get("description", "-") if isinstance(data, dict) else "-"
            location = data.get("location", "-") if isinstance(data, dict) else "-"
            address = data.get("address", "-") if isinstance(data, dict) else "-"
            lines.append(f"• *UUID:* `{uuid_value}`")
            lines.append(f"  • Valor: {value}")
            lines.append(f"  • Descricao: {description}")
            lines.append(f"  • Localizacao: {location}")
            lines.append(f"  • Endereco: {address}")

            if isinstance(data, dict):
                extra_fields = {
                    key: value
                    for key, value in data.items()
                    if key not in {"terminal", "value", "description", "location", "address"}
                }
                if extra_fields:
                    lines.append(
                        f"  • Campos extras: `{json.dumps(extra_fields, ensure_ascii=False)}`"
                    )
            lines.append("")

    if not_found:
        lines.append(f"*Nao encontrados ({len(not_found)})*")
        for uuid_value in not_found:
            lines.append(f"• `{uuid_value}`")
        lines.append("")

    if not lines:
        return "Nao encontrei UUIDs validos na mensagem."

    return "\n".join(lines).strip()


def _post_thread_message(channel, thread_ts, text):
    if not SLACK_BOT_TOKEN:
        print("SLACK_BOT_TOKEN is empty. Skipping Slack message.")
        return

    payload = {
        "channel": channel,
        "thread_ts": thread_ts,
        "text": text,
    }
    print(
        f"Posting Slack thread message to channel={channel}, thread_ts={thread_ts}, "
        f"text_length={len(text)}"
    )

    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
        print(f"Slack post response: {body}")


def handler(event, context):
    try:
        if not isinstance(event, dict):
            print("Invalid processor payload: not a dict")
            return {"ok": True}

        print(f"Processor event payload: {json.dumps(event)}")
        channel = event.get("channel")
        ts = event.get("ts")
        thread_ts = event.get("thread_ts")
        uuids = event.get("uuids", [])
        print(f"Parsed channel={channel}, ts={ts}, thread_ts={thread_ts}, uuids_count={len(uuids) if isinstance(uuids, list) else 'invalid'}")

        if not channel or not ts:
            print("Missing channel/ts in processor payload")
            return {"ok": True}

        if not isinstance(uuids, list):
            uuids = []
            print("UUID list is invalid, forcing empty list")

        target_thread_ts = thread_ts if thread_ts else ts
        print(f"Target thread_ts for reply: {target_thread_ts}")

        found_results = []
        not_found = []

        for uuid_value in uuids:
            if not isinstance(uuid_value, str) or not uuid_value:
                print(f"Skipping invalid UUID value: {uuid_value}")
                continue

            result = _find_terminal(uuid_value)
            if result is None:
                not_found.append(uuid_value)
                print(f"UUID not found: {uuid_value}")
            else:
                found_results.append((uuid_value, result))
                print(f"UUID found: {uuid_value}")

        message = _build_thread_message(found_results, not_found)
        print(
            f"Built message with found={len(found_results)} and not_found={len(not_found)}"
        )
        _post_thread_message(channel, target_thread_ts, message)
        print("Slack thread message posted successfully")

        return {"ok": True}
    except Exception as exc:
        print(f"Error in analyze processor: {exc}")
        return {"ok": True}
