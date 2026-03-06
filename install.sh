#!/usr/bin/env bash
set -euo pipefail

# ── Environment ──────────────────────────────────────────────────────
# Avoid permission errors when uv cache dir is owned by another user.
export UV_CACHE_DIR="${UV_CACHE_DIR:-/workspace/.uv-cache}"

# Store Playwright browsers in a writable location.
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/workspace/playwright-browsers}"

# ── Install package ──────────────────────────────────────────────────
echo "==> Installing bfs-mcp via uv..."
uv tool install "bfs-mcp @ git+https://github.com/elesingp2/betfunsports-mcp.git" || {
    echo "uv tool install failed — falling back to pip"
    pip install git+https://github.com/elesingp2/betfunsports-mcp.git
}

# Ensure ~/.local/bin is on PATH for the current session and future ones.
LOCAL_BIN="$HOME/.local/bin"
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    export PATH="$LOCAL_BIN:$PATH"
    echo "export PATH=\"$LOCAL_BIN:\$PATH\"" >> "$HOME/.bashrc" 2>/dev/null || true
    echo "    Added $LOCAL_BIN to PATH"
fi

# ── Install Chromium ─────────────────────────────────────────────────
echo "==> Installing Playwright Chromium..."
playwright install chromium

# ── System libraries ─────────────────────────────────────────────────
echo "==> Checking system libraries for Chromium..."
if command -v sudo &>/dev/null && sudo -n true 2>/dev/null; then
    echo "    sudo available — running playwright install-deps"
    sudo playwright install-deps chromium 2>/dev/null || true
else
    CHROMIUM_BIN=$(find "$PLAYWRIGHT_BROWSERS_PATH" -name "chrome" -o -name "chromium" 2>/dev/null | head -1)
    if [ -n "$CHROMIUM_BIN" ]; then
        MISSING=$(ldd "$CHROMIUM_BIN" 2>/dev/null | grep "not found" | awk '{print $1}' || true)
        if [ -n "$MISSING" ]; then
            echo ""
            echo "WARNING: Chromium has missing shared libraries:"
            echo "$MISSING"
            echo ""
            echo "Without sudo, you can work around this by downloading .deb packages"
            echo "and extracting the .so files. See README.md for details."
            echo ""
            echo "Quick workaround:"
            echo "  export LD_LIBRARY_PATH=/path/to/extracted/usr/lib/x86_64-linux-gnu"
        else
            echo "    All system libraries present."
        fi
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────
echo ""
echo "==> Done. Add these to your environment (or MCP server config):"
echo ""
echo "  export PLAYWRIGHT_BROWSERS_PATH=$PLAYWRIGHT_BROWSERS_PATH"
if [ -n "${LD_LIBRARY_PATH:-}" ]; then
    echo "  export LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
fi
echo ""
echo "To verify: bfs-mcp --help"
