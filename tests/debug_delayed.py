import httpx
import json

c = httpx.Client(timeout=10, trust_env=False)

# Fresh reset
r = c.post("http://127.0.0.1:8000/reset", json={})
d = r.json()
obs = d.get("observation", d)
blocks = obs.get("memory_blocks", [])
print(f"After reset: {len(blocks)} blocks")
print(f"Block IDs: {[b['block_id'] for b in blocks]}")
print(f"Block types: {[b['block_type'] for b in blocks]}")

# Try evicting block 0
r2 = c.post("http://127.0.0.1:8000/step", json={"action": {"target_block_id": 0, "tactic": "evict"}})
d2 = r2.json()
obs2 = d2.get("observation", {})
print(f"\nEvict block 0: status={r2.status_code}")
print(f"  done={d2.get('done')}")
print(f"  reward={d2.get('reward')}")
print(f"  message={obs2.get('message', '')[:200]}")
print(f"  blocks after: {len(obs2.get('memory_blocks', []))}")

# Now run 6 retains
for i in range(7):
    cur_blocks = obs2.get("memory_blocks", [])
    if not cur_blocks:
        print(f"  Step {i+2}: No blocks left")
        break
    if d2.get("done"):
        print(f"  Step {i+2}: Episode done, need reset")
        break
    bid = cur_blocks[0]["block_id"]
    r3 = c.post("http://127.0.0.1:8000/step", json={"action": {"target_block_id": bid, "tactic": "retain"}})
    d3 = r3.json()
    obs3 = d3.get("observation", {})
    msg = obs3.get("message", "")
    print(f"  Step {i+2}: msg={msg[:120]}")
    if "HALLUCINATION" in msg:
        print(f"  >> HALLUCINATION EVENT DETECTED!")
        break
    d2 = d3
    obs2 = obs3
