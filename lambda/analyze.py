import json
import os

import boto3

MODEL_ID = os.environ.get("MODEL_ID", "deepseek.v3.2")
PROCESSOR_FUNCTION_NAME = os.environ.get("PROCESSOR_FUNCTION_NAME", "")

bedrock = boto3.client("bedrock-runtime")
lambda_client = boto3.client("lambda")


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_body(event):
    raw_body = event.get("body")
    if raw_body is None or event.get("isBase64Encoded"):
        return None

    try:
        return json.loads(raw_body)
    except (TypeError, json.JSONDecodeError):
        return None


def _is_thread_reply(slack_event):
    thread_ts = slack_event.get("thread_ts")
    ts = slack_event.get("ts")
    return bool(thread_ts and ts and thread_ts != ts)


def _extract_uuids_with_bedrock(text):
    prompt = (
        "Extract only UUIDs from the provided text. "
        "Return strict JSON with this exact shape: "
        '{"uuids": ["uuid-1", "uuid-2"]}. '
        "Do not include any explanation.\n\n"
        f"Text:\n{text}"
    )

    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ],
    }

    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body),
    )

    payload = json.loads(response["body"].read())
    print(f"Bedrock response payload: {json.dumps(payload)}")

    model_text = ""
    choices = payload.get("choices", [])
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message", {})
        if isinstance(message, dict):
            model_text = message.get("content", "")

    if not model_text:
        content = payload.get("content", [])
        text_chunks = [item.get("text", "") for item in content if item.get("type") == "text"]
        model_text = "\n".join(text_chunks).strip()

    if not model_text:
        return []

    try:
        parsed = json.loads(model_text)
    except json.JSONDecodeError:
        return []

    uuids = parsed.get("uuids", []) if isinstance(parsed, dict) else []
    if not isinstance(uuids, list):
        return []

    deduped = []
    seen = set()
    for value in uuids:
        if isinstance(value, str) and value not in seen:
            seen.add(value)
            deduped.append(value)

    return deduped


def _invoke_processor_async(payload):
    if not PROCESSOR_FUNCTION_NAME:
        print("PROCESSOR_FUNCTION_NAME is empty. Skipping async invoke.")
        return

    print(
        f"Invoking processor async. function={PROCESSOR_FUNCTION_NAME}, "
        f"payload={json.dumps(payload)}"
    )
    lambda_client.invoke(
        FunctionName=PROCESSOR_FUNCTION_NAME,
        InvocationType="Event",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    print("Async invoke sent successfully")


def handler(event, context):
    try:
        print(f"Analyze handler started. Event keys: {list(event.keys()) if isinstance(event, dict) else 'invalid'}")
        parsed_body = _parse_body(event)
        print(
            f"Body parsed. type={parsed_body.get('type') if isinstance(parsed_body, dict) else 'invalid_or_empty'}"
        )

        if isinstance(parsed_body, dict) and parsed_body.get("type") == "url_verification":
            print("Detected Slack url_verification request")
            return _response(
                200,
                {
                    "token": parsed_body.get("token"),
                    "challenge": parsed_body.get("challenge"),
                    "type": "url_verification",
                },
            )

        if isinstance(parsed_body, dict) and parsed_body.get("type") == "event_callback":
            print("Detected Slack event_callback")
            slack_event = parsed_body.get("event", {})
            if not isinstance(slack_event, dict):
                print("Ignoring event_callback: event is not a dict")
                return _response(200, {"ok": True})

            if slack_event.get("type") != "message":
                print(f"Ignoring event_callback: unsupported event type={slack_event.get('type')}")
                return _response(200, {"ok": True})

            if _is_thread_reply(slack_event):
                print("Ignoring event_callback: message is a thread reply")
                return _response(200, {"ok": True, "ignored": "thread_reply"})

            text = slack_event.get("text", "")
            channel = slack_event.get("channel")
            ts = slack_event.get("ts")
            thread_ts = slack_event.get("thread_ts")
            print(
                f"Message extracted. channel={channel}, ts={ts}, thread_ts={thread_ts}, "
                f"text_length={len(text) if isinstance(text, str) else 'invalid'}"
            )

            if not text or not channel or not ts:
                print("Ignoring event_callback: missing text/channel/ts")
                return _response(200, {"ok": True})

            print("Calling Bedrock to extract UUIDs")
            uuids = _extract_uuids_with_bedrock(text)
            print(f"Bedrock extracted UUID count={len(uuids)} uuids={json.dumps(uuids)}")

            processor_payload = {
                "channel": channel,
                "ts": ts,
                "thread_ts": thread_ts,
                "uuids": uuids,
            }
            _invoke_processor_async(processor_payload)
            print("Request processed with async dispatch")
            return _response(200, {"ok": True})

        print("Ignoring request: unsupported or empty payload type")
        return _response(200, {"ok": True})

    except Exception as exc:
        print(f"Error in analyze dispatcher: {exc}")
        return _response(200, {"ok": True})
