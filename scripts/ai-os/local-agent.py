from __future__ import annotations

import argparse
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()

OLLAMA = "http://localhost:11434/api/generate"


def read_file(path: Path, max_chars: int = 20000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return text[:max_chars]


def call_model(model: str, prompt: str) -> dict:
    native = ROOT / "_raios-a17-native-cortex"
    if str(native) not in sys.path:
        sys.path.insert(0, str(native))
    from ccee.config import FailClosed
    from ccee.ollama_runtime import OllamaRuntimeManager

    manager = OllamaRuntimeManager(base_url=OLLAMA.rsplit("/api/generate", 1)[0])
    try:
        result = manager.generate(prompt, model=model)
    except FailClosed as exc:
        raise SystemExit(f"OLLAMA_FAIL_CLOSED:{exc}") from exc
    return {"response": result.get("response") or "", "eval_count": None, "proposal_only": True}


def build_context() -> str:

    files = [
        ".ai-os/CORE-CONTRACT.md",
        ".ai-os/MASTER-PLAN.md",
        ".ai-os/state/CURRENT-STATE.json",
        ".ai-os/state/TASKS.json",
        ".ai-os/state/LOCKS.json",

        "migration/OLD-TO-CODEX-MAP.md",
        "migration/CAPABILITY-MATRIX.md",
        "migration/BRAIN-INVENTORY.md",
        "migration/RUNTIME-GAPS.md",
        "migration/MIGRATION-WAVES.md",
        "migration/GL-001-EVIDENCE.md",
    ]

    parts = []

    for rel in files:

        path = ROOT / rel

        if path.exists():

            parts.append(
                f"\n===== {rel} =====\n"
                + read_file(path)
            )

    return "\n".join(parts)


def main():

    p = argparse.ArgumentParser()

    p.add_argument(
        "--task",
        required=True
    )

    p.add_argument(
        "--model",
        default="deepseek-r1:1.5b"
    )

    p.add_argument(
        "--output",
        required=True
    )

    args = p.parse_args()

    context = build_context()

    prompt = f"""
You are RAIOS LOCAL INTELLIGENCE.

Privacy:
LOCAL_ONLY.

You are NOT the final authority.

You may analyze.
You may classify.
You may propose.
You may identify conflicts.

You must NOT invent repository facts.

TASK:

{args.task}

SHARED VERIFIED CONTEXT:

{context}

Return exactly these sections:

VERIFIED FACTS
UNPROVEN
RISKS
RECOMMENDATIONS
DEPENDENCIES
NEXT SAFE STEP

Never claim something is verified unless supported by supplied evidence.
"""

    start = datetime.now()

    response = call_model(
        args.model,
        prompt
    )

    elapsed = (
        datetime.now() - start
    ).total_seconds()

    out = Path(args.output)

    out.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    report = (
        "# RAIOS Local Intelligence Result\n\n"
        f"Model: {args.model}\n\n"
        f"Elapsed: {elapsed:.2f} sec\n\n"
        + response.get("response", "")
        + "\n"
    )

    out.write_text(
        report,
        encoding="utf-8"
    )

    print(out)
    print(
        "eval_count:",
        response.get("eval_count")
    )


if __name__ == "__main__":
    main()