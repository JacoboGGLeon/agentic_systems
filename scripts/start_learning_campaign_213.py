"""Create the separately authorized learning campaign; never reset a ledger."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    from agentic_systems_studio.environment import load_studio_environment
    from agentic_systems_studio.routes import values, configured
    load_studio_environment(ROOT / '.env')
    previous = ROOT / '.tmp/campaign213-final/live-budget.json'
    target = ROOT / '.tmp/campaign213-learning/live-budget.json'
    if target.exists():
        raise FileExistsError('An allocation exists; it must never be reset')
    routes = {}
    for provider in ('openai-runtime', 'ollama-runtime', 'bedrock-runtime'):
        options = values(provider)
        assert configured(provider), provider
        endpoint = options['endpoint'] or ('https://api.openai.com/v1' if provider == 'openai-runtime'
            else 'https://bedrock-runtime.' + options['region'] + '.amazonaws.com')
        routes[provider] = {'model': options['model'], 'endpoint': endpoint,
                           'input_usd_per_million': 5, 'output_usd_per_million': 20}
    payload = {'schema_version': 'agentic_systems.campaign-213-budget.v1', 'campaign': '213-learning',
        'authorization': 'User selected Nueva campaña: USD 10 y 300 llamadas for tutorials, examples and Studio, 2026-10-22',
        'created_at': datetime.now(timezone.utc).isoformat(), 'limits': {'usd': 10, 'requests': 300},
        'routes': routes, 'attempts': [], 'previous_campaign_sha256': hashlib.sha256(previous.read_bytes()).hexdigest(),
        'reservation_note': 'Conservative reservation, not billed cost. Includes failures, retries, evaluators and Ollama; transport hooks persist until workers finish.'}
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({k: payload[k] for k in ('campaign', 'limits', 'routes', 'previous_campaign_sha256')}))


if __name__ == '__main__':
    main()
