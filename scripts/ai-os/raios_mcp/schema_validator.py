"""Isolated, disposable validator; schema regex CPU cannot block the gateway."""
import json
import sys


def main() -> int:
    from jsonschema import Draft202012Validator
    try:
        # Parent sends at most one configured provider frame; this fixed ceiling
        # also protects direct invocation of this private worker entrypoint.
        raw = sys.stdin.buffer.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            return 1
        payload = json.loads(raw)
        Draft202012Validator.check_schema(payload['schema'])
        Draft202012Validator(payload['schema']).validate(payload['arguments'])
        return 0
    except Exception:
        # Never print provider schemas, arguments or validation exceptions.
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
