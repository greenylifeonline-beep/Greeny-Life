import hashlib
import json
from pathlib import Path

RUN = Path(
    r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair"
    r"\.ai-os\reports\master-estate-census"
    r"\RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T185525Z"
)


class Dup(ValueError):
    pass


def hook_factory(found):
    def hook(pairs):
        seen = {}
        for k, v in pairs:
            if k in seen:
                found.append(k)
                raise Dup(k)
            seen[k] = v
        return seen

    return hook


def main():
    fails = []
    n = 0
    for p in sorted(RUN.rglob("*.json")):
        rel = p.relative_to(RUN).as_posix()
        found = []
        try:
            json.loads(p.read_text(encoding="utf-8"), object_pairs_hook=hook_factory(found))
            n += 1
        except Dup as e:
            fails.append((rel, "DUP", str(e)))
        except Exception as e:
            fails.append((rel, type(e).__name__, str(e)[:120]))

    lines = []
    for p in sorted(x for x in RUN.rglob("*") if x.is_file()):
        rel = p.relative_to(RUN).as_posix()
        if rel == "FILES-SHA256.txt":
            continue
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        lines.append(f"{h.hexdigest()}  {rel}")
    (RUN / "FILES-SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("JSON_STRICT_PARSE_PASS", len(fails) == 0, "parsed", n)
    print("FAILS", fails)
    print("FILES_HASHED", len(lines))


if __name__ == "__main__":
    main()
