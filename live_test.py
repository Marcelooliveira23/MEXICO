import requests

base = 'http://127.0.0.1:5050'

try:
    r = requests.post(
        base + '/api/ai/chat',
        json={'query': 'AC bus tripped electrical fault ATA 24', 'scope': 'global'},
        timeout=10
    )
    d = r.json()
    rca = d.get('data', d)
    sources = rca.get('sources', {})
    print('HTTP status:', r.status_code)
    print('records=%s mel=%s aog=%s lru=%s' % (
        sources.get('records', 0),
        sources.get('mel', 0),
        sources.get('aog', 0),
        sources.get('lru', 0),
    ))
    print('confidence:', rca.get('confidence'))
    alerts = rca.get('recurrence_alerts', [])
    print('recurrence_alerts:', len(alerts))
    if alerts:
        print('top alert:', alerts[0].get('message', '')[:80])
    ctx = rca.get('context_consulted', [])
    print('context_consulted:', len(ctx))
    similar = rca.get('similar_cases', [])
    print('similar_cases:', len(similar))
    if similar:
        print('top similar score:', similar[0].get('similarity', 0))
except Exception as e:
    print('ERROR:', e)
