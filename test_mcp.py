#!/usr/bin/env python3
"""Smoke test: call MCP tools directly (bypassing transport layer)."""

import asyncio
import json
import sys

sys.path.insert(0, "src")
from bfs_mcp.server import mcp
from bfs_mcp.browser import BrowserManager


async def call_tool(name: str, args: dict | None = None):
    print(f"\n{'='*60}")
    print(f"TOOL: {name}({args or {}})")
    print("=" * 60)
    try:
        result = await mcp.call_tool(name, args or {})
        for block in result:
            text = block.text if hasattr(block, "text") else str(block)
            if text.startswith("{") or text.startswith("["):
                try:
                    parsed = json.loads(text)
                    print(json.dumps(parsed, indent=2, ensure_ascii=False)[:2000])
                except json.JSONDecodeError:
                    print(text[:2000])
            elif text.startswith("data:image"):
                print(f"[screenshot: {len(text)} chars base64]")
            else:
                print(text[:2000])
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        return None


async def main():
    print("BFS MCP Server — Smoke Test")
    print("=" * 60)

    # 1. Navigate to homepage
    await call_tool("browser_navigate", {"url": "/"})

    # 2. Get state (should be unauthenticated)
    await call_tool("bfs_state")

    # 3. List sports
    await call_tool("bfs_list_sports")

    # 4. View a football coupon
    await call_tool("bfs_view_coupon", {"path": "/football/prizecoupons1X2"})

    # 5. Get forms on page
    await call_tool("browser_forms")

    # 6. Get links filtered
    await call_tool("browser_links", {"filter_pattern": "/football/"})

    # 7. Navigate to payment
    await call_tool("bfs_payment_info")

    # 8. Screenshot
    await call_tool("browser_screenshot")

    # 9. Execute JS
    await call_tool("browser_eval", {"javascript": "document.title + ' | ' + window.location.href"})

    # 10. Navigate to registration page and inspect form
    await call_tool("browser_navigate", {"url": "/fullRegistration"})
    await call_tool("browser_forms")

    print("\n\nDONE — all tools executed successfully")

    # Cleanup
    from bfs_mcp.server import bm
    await bm.stop()


if __name__ == "__main__":
    asyncio.run(main())
