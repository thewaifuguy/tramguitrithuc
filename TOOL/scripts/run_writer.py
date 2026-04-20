"""CLI entry to generate a chapter and save it to Firestore as a pending draft.

Usage:
    python scripts/run_writer.py --topic "Pomodoro cho học sinh hay trì hoãn"
    python scripts/run_writer.py --topic "..." --outline "1. ... 2. ..."
    python scripts/run_writer.py --topic "..." --no-firestore  # save locally only
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Force UTF-8 on Windows terminals so Vietnamese chars don't crash
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Make parent dir importable when running as script
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from agents.writer import WriterAgent
from db.schemas import ChapterDraft


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a handbook chapter draft")
    parser.add_argument("--topic", required=True, help="Chủ đề chapter (tiếng Việt)")
    parser.add_argument("--outline", default=None, help="Outline gợi ý (optional)")
    parser.add_argument(
        "--no-firestore",
        action="store_true",
        help="Skip Firestore save (useful before Firebase is set up)",
    )
    args = parser.parse_args()

    print(f"[writer] Generating chapter for: {args.topic!r}")
    print(f"[writer] Model: {config.WRITER_MODEL}")

    agent = WriterAgent()
    out = agent.generate_chapter(topic=args.topic, outline=args.outline)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_topic = "".join(c if c.isalnum() else "-" for c in args.topic.lower())[:40]
    local_path = config.OUTPUT_DIR / f"chapter-{timestamp}-{safe_topic}.md"
    local_path.write_text(out.content_md, encoding="utf-8")

    word_count = len(out.content_md.split())
    print(f"[writer] ✓ Generated. {word_count} words, {len(out.image_prompts)} image prompts.")
    print(f"[writer] Tokens: in={out.input_tokens}, out={out.output_tokens}")
    print(f"[writer] Saved locally: {local_path}")

    if args.no_firestore:
        print("[writer] Skipped Firestore (--no-firestore).")
        return

    from db.storage import save_draft

    draft = ChapterDraft(
        topic=out.topic,
        content_md=out.content_md,
        image_prompts=out.image_prompts,
        input_tokens=out.input_tokens,
        output_tokens=out.output_tokens,
    )
    draft_id = save_draft(draft)
    print(f"[writer] Saved to Firestore, draft id: {draft_id}")
    print(f"[writer] Open dashboard (streamlit run dashboard/app.py) to review.")


if __name__ == "__main__":
    main()
