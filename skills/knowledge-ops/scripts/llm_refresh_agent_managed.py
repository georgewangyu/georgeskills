#!/usr/bin/env python3
"""
Headless LLM-driven refresh for LLM-wiki topic pages.

This script keeps the current deterministic input gathering from
`refresh_agent_managed.py`, but replaces keyword-based topic matching with an
LLM classification and routing pass.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from refresh_agent_managed import (
    AGENT_MANAGED_DIR,
    CANDIDATES_DIR,
    PRIVATE_REPO_ROOT,
    append_unique_bullets,
    changed_files_for_date,
    conversation_note_signal,
    ensure_dir,
    evidence_texts_for_page,
    load_topic_pages,
    parse_frontmatter_header,
    section_bullets,
    source_seed_paths_for_page,
    split_frontmatter,
    summary_path_for_date,
    summary_signal,
    upsert_level2_section,
    write_candidates,
)


DEFAULT_PROVIDER = "gemini"
DEFAULT_MODEL = "gemini-2.5-flash"
MAX_SIGNAL_TEXT = 700
MAX_FILE_COUNT = 40
MAX_TOPICS = 24
MAX_EXISTING_BULLETS = 6
RETRYABLE_HTTP_CODES = {429, 500, 503}


@dataclass
class SignalRecord:
    signal_id: str
    section: str
    text: str
    source_ref: str
    origin: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Headless LLM refresh for LLM-wiki topic pages.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, choices=["gemini"], help="LLM provider")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--apply", action="store_true", help="Apply LLM topic updates directly to topic pages.")
    parser.add_argument("--print-payload", action="store_true", help="Print the final candidate payload to stdout.")
    parser.add_argument("--print-prompt", action="store_true", help="Print the assembled prompt input instead of only writing candidates.")
    parser.add_argument("--max-signals", type=int, default=60, help="Max number of signals sent to the model.")
    parser.add_argument("--max-topic-updates", type=int, default=8, help="Hard cap on topic updates applied from model output.")
    return parser.parse_args()


def trim_text(text: str, *, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def collect_signals(date_text: str, *, max_signals: int) -> tuple[list[SignalRecord], Path, list[Path]]:
    summary_signals, summary_path = summary_signal(date_text)
    note_signals, note_paths = conversation_note_signal(date_text)
    records: list[SignalRecord] = []

    ordered = [("summary", signal) for signal in summary_signals] + [("conversation_note", signal) for signal in note_signals]
    for idx, (origin, signal) in enumerate(ordered[:max_signals], start=1):
        records.append(
            SignalRecord(
                signal_id=f"S{idx}",
                section=str(signal["section"]),
                text=trim_text(str(signal["text"]), limit=MAX_SIGNAL_TEXT),
                source_ref=str(signal["source_ref"]),
                origin=origin,
            )
        )
    return records, summary_path, note_paths


def topic_context(topic: Any) -> dict[str, Any]:
    path = Path(topic.path)
    text = path.read_text(encoding="utf-8")
    header = parse_frontmatter_header(text)
    description = None
    for line in header.splitlines():
        if line.startswith("description:"):
            description = line.split(":", 1)[1].strip().strip('"')
            break
    return {
        "topic_slug": topic.slug,
        "topic_title": topic.title,
        "page_path": path.relative_to(AGENT_MANAGED_DIR).as_posix(),
        "description": description or "",
        "keywords": topic.keywords[:16],
        "source_seed_paths": source_seed_paths_for_page(path)[:10],
        "current_summary_bullets": [b.removeprefix("- ").strip() for b in section_bullets(text, "Summary")[:3]],
        "current_understanding_bullets": [b.removeprefix("- ").strip() for b in section_bullets(text, "Current Understanding")[:4]],
        "important_evidence_bullets": [b.removeprefix("- ").strip() for b in section_bullets(text, "Important Evidence")[:MAX_EXISTING_BULLETS]],
    }


def response_schema() -> dict[str, Any]:
    nullable_string = {"type": ["string", "null"]}
    return {
        "type": "object",
        "properties": {
            "run_summary": {"type": "string"},
            "topic_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic_slug": {"type": "string"},
                        "confidence": {"type": "integer"},
                        "why": {"type": "string"},
                        "signal_ids": {"type": "array", "items": {"type": "string"}},
                        "changed_files": {"type": "array", "items": {"type": "string"}},
                        "summary_bullets": {"type": "array", "items": {"type": "string"}},
                        "current_understanding_bullets": {"type": "array", "items": {"type": "string"}},
                        "important_evidence_bullets": {"type": "array", "items": {"type": "string"}},
                        "source_map_bullets": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "topic_slug",
                        "confidence",
                        "why",
                        "signal_ids",
                        "changed_files",
                        "summary_bullets",
                        "current_understanding_bullets",
                        "important_evidence_bullets",
                        "source_map_bullets",
                    ],
                },
            },
            "memory_candidates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string"},
                        "summary": {"type": "string"},
                        "source_ref": {"type": "string"},
                        "topic_slug": nullable_string,
                    },
                    "required": ["kind", "summary", "source_ref", "topic_slug"],
                },
            },
            "new_topic_suggestions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "why": {"type": "string"},
                        "signal_ids": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title", "why", "signal_ids"],
                },
            },
            "journal_only_signal_ids": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "run_summary",
            "topic_updates",
            "memory_candidates",
            "new_topic_suggestions",
            "journal_only_signal_ids",
        ],
    }


def build_model_input(date_text: str, signals: list[SignalRecord], topics: list[Any], changed_files: list[str]) -> dict[str, Any]:
    return {
        "date": date_text,
        "signals": [asdict(signal) for signal in signals],
        "changed_files": changed_files[:MAX_FILE_COUNT],
        "topics": [topic_context(topic) for topic in topics[:MAX_TOPICS]],
    }


def system_instruction() -> str:
    return (
        "You are maintaining a private markdown wiki that compounds knowledge over time. "
        "Route new daily signals into the smallest correct set of topic-page updates. "
        "Prefer high-signal rewrites over generic summaries. "
        "Do not invent facts. Only use explicit information from the provided signals, changed files, and existing topic context. "
        "If a signal does not belong in the wiki yet, leave it as journal-only. "
        "Summary bullets should be concise and durable. "
        "Current-understanding bullets should explain what materially changed or became clearer. "
        "Important-evidence bullets should be grounded and cite concrete source refs via the provided signal IDs/source refs. "
        "Source-map bullets should be markdown bullets that start with `- ` and point to concrete file refs."
    )


def user_prompt(model_input: dict[str, Any], *, max_topic_updates: int) -> str:
    instructions = {
        "task": "Categorize the day's human work semantically and decide what should update the maintained wiki.",
        "rules": [
            f"Return at most {max_topic_updates} topic updates.",
            "Only update an existing topic if there is real new signal for it.",
            "Use confidence 0-100. Confidence below 60 means the topic probably should not be updated.",
            "Every topic update must reference the signal_ids that justify it.",
            "If changed_files strengthen the route, include only the relevant ones.",
            "Do not duplicate evidence bullets already present unless the new wording is materially better.",
            "If no existing topic fits, put the idea in new_topic_suggestions instead of forcing it into the wrong topic.",
            "memory_candidates should classify durable items using kinds like decision, pattern, commitment, person_update, project_update, or durable_fact.",
            "journal_only_signal_ids should contain signal ids that are useful chronologically but do not deserve canonical wiki updates right now.",
        ],
        "input": model_input,
    }
    return json.dumps(instructions, indent=2)


def gemini_api_key() -> str | None:
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return None


def gemini_generate_json(
    *,
    api_key: str,
    model: str,
    prompt: str,
    schema: dict[str, Any],
    max_attempts: int = 4,
) -> dict[str, Any]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "system_instruction": {
            "parts": [{"text": system_instruction()}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
            "temperature": 0.2,
        },
    }
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "x-goog-api-client": "georgeskills-knowledge-ops/0.1",
        },
        method="POST",
    )
    body = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body = response.read().decode("utf-8")
                break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code in RETRYABLE_HTTP_CODES and attempt < max_attempts:
                time.sleep(min(2 ** (attempt - 1), 8))
                continue
            raise RuntimeError(f"Gemini API error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_attempts:
                time.sleep(min(2 ** (attempt - 1), 8))
                continue
            raise RuntimeError(f"Gemini API request failed: {exc}") from exc

    if body is None:
        raise RuntimeError("Gemini API request failed after retries.")

    parsed = json.loads(body)
    candidates = parsed.get("candidates") or []
    if not candidates:
        raise RuntimeError(f"Gemini API returned no candidates: {body}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text.strip():
        raise RuntimeError(f"Gemini API returned empty text: {body}")
    return json.loads(text)


def run_model(*, provider: str, model: str, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
    if provider != "gemini":
        raise RuntimeError(f"Unsupported provider: {provider}")
    api_key = gemini_api_key()
    if not api_key:
        raise RuntimeError(
            "Missing Gemini API key. Set GEMINI_API_KEY, GOOGLE_API_KEY, or GOOGLE_GENERATIVE_AI_API_KEY to run headless LLM refresh."
        )
    return gemini_generate_json(api_key=api_key, model=model, prompt=prompt, schema=schema)


def replace_section_with_bullets(text: str, title: str, bullets: list[str]) -> str:
    normalized = []
    for bullet in bullets:
        stripped = bullet.strip()
        if not stripped:
            continue
        normalized.append(f"- {stripped.removeprefix('- ').strip()}")
    body = "\n".join(normalized) if normalized else "- Not logged yet."
    return upsert_level2_section(text, title, body)


def apply_topic_update(update: dict[str, Any]) -> bool:
    topic_pages = {topic.slug: topic for topic in load_topic_pages()}
    slug = str(update["topic_slug"])
    topic = topic_pages.get(slug)
    if topic is None:
        return False

    path = Path(topic.path)
    text = path.read_text(encoding="utf-8")
    updated = replace_section_with_bullets(text, "Summary", list(update.get("summary_bullets", [])))
    updated = replace_section_with_bullets(updated, "Current Understanding", list(update.get("current_understanding_bullets", [])))
    updated = append_unique_bullets(updated, "Important Evidence", list(update.get("important_evidence_bullets", [])))
    updated = append_unique_bullets(updated, "Source Map", list(update.get("source_map_bullets", [])))

    if updated == text:
        return False
    path.write_text(updated.rstrip("\n") + "\n", encoding="utf-8")
    return True


def log_llm_apply(date_text: str, applied_slugs: list[str], provider: str, model: str) -> None:
    log_path = AGENT_MANAGED_DIR / "log.md"
    if not log_path.exists():
        return
    lines = [
        f"## [{date_text}] llm-auto-apply | Headless LLM Wiki Refresh",
        f"- Applied LLM updates to {len(applied_slugs)} canonical pages via `{provider}` / `{model}`.",
    ]
    for slug in applied_slugs:
        lines.append(f"  - `{slug}`")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n" + "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    date_text = args.date.strip().lower()
    if date_text == "today":
        date_text = date.today().isoformat()

    signals, summary_path, note_paths = collect_signals(date_text, max_signals=args.max_signals)
    topics = load_topic_pages()
    changed_files = changed_files_for_date(date_text)
    model_input = build_model_input(date_text, signals, topics, changed_files)
    prompt = user_prompt(model_input, max_topic_updates=args.max_topic_updates)

    if args.print_prompt:
        print(prompt)

    model_output = run_model(
        provider=args.provider,
        model=args.model,
        prompt=prompt,
        schema=response_schema(),
    )

    payload = {
        "date": date_text,
        "mode": "llm_refresh_agent_managed",
        "provider": args.provider,
        "model": args.model,
        "summary_path": summary_path.relative_to(PRIVATE_REPO_ROOT).as_posix(),
        "conversation_note_paths": [path.relative_to(PRIVATE_REPO_ROOT).as_posix() for path in note_paths],
        "signal_count": len(signals),
        "changed_file_count": len(changed_files),
        "input": model_input,
        "llm_output": model_output,
    }

    ensure_dir(CANDIDATES_DIR)
    candidate_path = CANDIDATES_DIR / f"{date_text}.llm.json"
    candidate_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # Preserve the existing date-level candidate path too so the artifact is easy to find.
    write_candidates(
        date_text,
        {
            "date": date_text,
            "mode": "llm_refresh_agent_managed",
            "provider": args.provider,
            "model": args.model,
            "signal_count": len(signals),
            "changed_file_count": len(changed_files),
            "run_summary": model_output.get("run_summary", ""),
            "topic_updates": model_output.get("topic_updates", []),
            "memory_candidates": model_output.get("memory_candidates", []),
            "new_topic_suggestions": model_output.get("new_topic_suggestions", []),
            "journal_only_signal_ids": model_output.get("journal_only_signal_ids", []),
        },
    )

    print(f"llm LLM wiki candidates [{date_text}]: {candidate_path}")

    applied_slugs: list[str] = []
    if args.apply:
        for update in list(model_output.get("topic_updates", []))[: args.max_topic_updates]:
            confidence = int(update.get("confidence", 0))
            if confidence < 60:
                continue
            if apply_topic_update(update):
                applied_slugs.append(str(update["topic_slug"]))
        if applied_slugs:
            log_llm_apply(date_text, applied_slugs, args.provider, args.model)

    if applied_slugs:
        print("applied llm updates:")
        for slug in applied_slugs:
            print(f"- {slug}")
    else:
        print("applied llm updates: none")

    if args.print_payload:
        print(json.dumps(payload, indent=2))

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
