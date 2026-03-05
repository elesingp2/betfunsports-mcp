"""
Demo: full autonomous betting loop — login → scan coupons → place Wooden-room bet.

Usage:
    python3 test_bfs.py [email] [password]

If no arguments are given, credentials are loaded from ~/.bfs-mcp/credentials.json
(auto-saved after the first successful bfs_login).
"""

import asyncio
import json
import sys

from bfs_mcp.browser import BFSBrowser
from bfs_mcp import notify


def _get_credentials() -> tuple[str, str]:
    if len(sys.argv) == 3:
        return sys.argv[1], sys.argv[2]
    creds = BFSBrowser.load_credentials()
    if creds:
        return creds["email"], creds["password"]
    print("No saved credentials. Pass email and password as arguments:")
    print("  python3 test_bfs.py your@email.com YourPassword")
    sys.exit(1)


async def main() -> None:
    email, password = _get_credentials()
    b = BFSBrowser()
    await b.start()

    # ── 1. Auth check ────────────────────────────────────────────────
    print("\n══ 1. Auth status ══")
    await b.goto("/")
    state = await b.state()
    print(json.dumps(state.to_dict(), indent=2, ensure_ascii=False))

    if not state.authenticated:
        print("\n══ 2. Login ══")
        result = await b.login(email, password)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        notify.on_login(email, result)
        if not result.get("authenticated"):
            print("❌ Login failed"); await b.stop(); return
    else:
        print(f"✅ Logged in as {state.username}  |  BFS: {state.balance_bfs}  |  EUR: {state.balance_eur}")
        notify.on_login(email, state.to_dict())

    # ── 2. Scan homepage for coupons with numeric IDs ────────────────
    print("\n══ 3. Scan coupons ══")
    await b.goto("/")
    links = await b.page.evaluate("""() => {
        const seen = new Set(), out = [];
        document.querySelectorAll('a[href]').forEach(a => {
            const h = a.getAttribute('href') || '';
            if (h.startsWith('/') && /\\/\\d+$/.test(h) && !seen.has(h)) {
                seen.add(h);
                out.push({ path: h, label: a.textContent.trim().replace(/\\s+/g,' ').slice(0,80) });
            }
        });
        return out;
    }""")
    print(f"Found {len(links)} coupon link(s):")
    for ln in links:
        print(f"  {ln['path']}  →  {ln['label']}")

    # ── 3. Find first coupon with an open bet form ───────────────────
    open_path, open_details = None, None
    for ln in links[:20]:
        print(f"\n  Checking {ln['path']} …")
        try:
            details = await b.bet_info(ln["path"])
        except Exception as exc:
            print(f"    skip ({exc})")
            continue
        if not details.get("error") and details.get("events") and details.get("rooms"):
            open_path, open_details = ln["path"], details
            print(f"  ✅ Open — events={len(details['events'])}, rooms={len(details['rooms'])}")
            break
        else:
            print(f"  ⏭  {details.get('error', 'no events/rooms')}")

    # ── 4. Place a bet ───────────────────────────────────────────────
    if open_path and open_details:
        events, rooms = open_details["events"], open_details["rooms"]
        print(f"\n══ 4. Place bet ══")
        print(f"Coupon : {open_path}")
        print(f"Title  : {open_details.get('title','')}")
        for e in events:
            print(f"  event {e['eventId']}  outcomes: {e['outcomes']}")
        for r in rooms:
            print(f"  room  {r['label']}  stake={r['currentStake']}")

        first_event = events[0]
        eid = first_event["eventId"]
        outcomes = first_event.get("outcomes") or [{"code": "8", "label": "1 (home)"}]
        oc = outcomes[0]["code"]
        label = outcomes[0].get("label", oc)
        print(f"\n→ Selecting outcome {label} (code {oc}) for event {eid}")
        print("→ Wooden room, stake 1 BFS (free)")

        result = await b.place_bet(open_path, {eid: oc}, room_index=0, stake="1")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        notify.on_bet(result, open_path)
    else:
        print("\nℹ️  No open bet forms found at this time.")

    # ── 5. Active bets ───────────────────────────────────────────────
    print("\n══ 5. Active bets ══")
    await asyncio.sleep(2)
    try:
        print(await b.active_bets())
    except Exception as e:
        print(f"(skipped: {e})")

    # ── 6. Bet history ───────────────────────────────────────────────
    print("\n══ 6. Bet history ══")
    await asyncio.sleep(1)
    try:
        print((await b.bet_history())[:3000])
    except Exception as e:
        print(f"(skipped: {e})")

    await b.stop()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
