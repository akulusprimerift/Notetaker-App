"""Short-lived local text extraction process. No file writes or model/provider calls."""
import json
import sys
from .materials import extract, MAX_BYTES


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES: raise ValueError('size')
        pages = extract('upload'+sys.argv[1], raw)
        sys.stdout.buffer.write(json.dumps(pages, ensure_ascii=True).encode('ascii'))
    except Exception:
        # Do not echo parser exceptions, document content or filesystem details.
        raise SystemExit(1) from None


if __name__ == '__main__': main()
