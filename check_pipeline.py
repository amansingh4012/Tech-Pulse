"""Verify pipeline articles with timestamps."""
import requests, json

# Check pipeline status
r = requests.get("http://localhost:8000/api/v1/pipeline/status")
status = r.json()
print("=" * 60)
print("  PIPELINE STATUS")
print("=" * 60)
print(f"  Running:      {status['is_running']}")
print(f"  Queue size:   {status['queue_size']}")
print(f"  Generated:    {status['stats']['articles_generated']}")
print(f"  Pruned:       {status['stats']['articles_pruned']}")
print(f"  Last tick:    {status['stats']['last_tick_at']}")
print(f"  Last source:  {status['stats']['last_source_scraped']}")
print()

# Check health
r = requests.get("http://localhost:8000/api/v1/pipeline/health")
health = r.json()
print(f"  Health:       {health['status']}")
print()

# Check articles with timestamps
r = requests.get("http://localhost:8000/api/v1/articles?page_size=10")
data = r.json()
print(f"  Total articles in DB: {data['total']}")
print()
print("  LATEST ARTICLES (with generated_at timestamp):")
print("  " + "-" * 56)
for a in data["articles"]:
    gen = a.get("generated_at", "N/A")
    print(f"  [{a['id']:>3}] {a['source']:<16} | {gen} | {a['title'][:40]}")

print()
print("  " + "-" * 56)

# Stats
r = requests.get("http://localhost:8000/api/v1/stats")
stats = r.json()
print(f"\n  By Source: {json.dumps(stats['by_source'], indent=4)}")
