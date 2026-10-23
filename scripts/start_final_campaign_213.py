"""Create exactly the separate allocation explicitly authorized for final 2.1.3 validation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    previous = ROOT / '.tmp/campaign213/live-budget.json'
    old = json.loads(previous.read_text(encoding='utf-8'))
    target = ROOT / '.tmp/campaign213-final/live-budget.json'
    if target.exists():
        raise FileExistsError('An allocation exists; it must never be reset')
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {'schema_version': 'agentic_systems.campaign-213-budget.v1', 'campaign': '213-final',
        'authorization': 'User explicitly selected Nueva campaña final: USD 10 y 300 llamadas in this task on 2026-10-22',
        'created_at': datetime.now(timezone.utc).isoformat(), 'limits': {'usd': 10, 'requests': 300},
        'routes': old['routes'], 'attempts': [], 'previous_campaign_sha256': hashlib.sha256(previous.read_bytes()).hexdigest(),
        'reservation_note': 'USD5/M input + USD20/M output, UTF-8 bytes + 4096 framing, full output limit and 25% margin. Not billed cost.'}
    target.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'campaign': '213-final', 'limits': payload['limits'], 'previous_attempts_preserved': len(old['attempts'])}))


if __name__ == '__main__':
    main()
