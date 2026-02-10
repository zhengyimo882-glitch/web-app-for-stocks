import sys
import os
import json
import time
from typing import Literal

# Simple startup log to make it obvious where this module is loaded from.
# This is mainly for debugging import/path issues during development.
print("[sentiment_service] LOADED FROM:", os.path.abspath(__file__), flush=True)

# Manually resolving project root so that local modules can be imported
# when this file is executed from different working directories.
# This is a bit of a beginner-friendly approach, but very explicit and reliable.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Core data + visualization logic lives in a separate module.
# This file acts more like a lightweight service / adapter layer.
from marketviews_sentiment_panel_finalized import get_data_to_draw, draw_sentiment_panel


# Very small in-memory cache.
# Intentionally kept simple instead of using a formal caching library
# to make the behavior fully transparent.
_CACHE = {
    "timestamp": 0,
    "positive": None,
    "negative": None
}

# Cache expiration time (seconds).
# Chosen as a balance between freshness and avoiding unnecessary recomputation.
CACHE_TTL_SECONDS = 30 * 60  # 30 minutes


def _cache_valid() -> bool:
    """
    Check whether the cached data is still usable.

    This intentionally uses a timestamp comparison instead of more advanced
    cache invalidation logic to keep the behavior easy to reason about.
    """
    return (time.time() - _CACHE["timestamp"]) < CACHE_TTL_SECONDS


def _rebuild_cache(debug: bool):
    """
    Fully rebuild the sentiment cache.

    This function is intentionally written as a single, explicit pipeline
    (fetch -> draw -> parse -> store) to keep the data flow obvious.
    """
    # Fetch processed sentiment data grouped by sector
    top_5_each_sector, low_5_each_sector = get_data_to_draw(debug=debug)

    # Generate visualization JSON (Plotly-style) for both sentiment directions
    fig_pos_json, fig_neg_json = draw_sentiment_panel(
        top_5_each_sector,
        low_5_each_sector
    )

    # Convert JSON strings into Python dicts once,
    # so downstream consumers don't need to parse repeatedly.
    _CACHE["positive"] = json.loads(fig_pos_json)
    _CACHE["negative"] = json.loads(fig_neg_json)

    # Record rebuild time for TTL-based cache validation
    _CACHE["timestamp"] = time.time()


def build_treemap_data(debug=False):
    """
    Return raw DataFrame-style data (top_df, low_df).

    This function exists mainly for debugging, inspection,
    or future reuse outside of visualization rendering.
    """
    top_df, low_df = get_data_to_draw(debug=debug)
    return top_df, low_df


def build_treemap_json(
    mode: Literal["positive", "negative"],
    debug: bool = True
) -> dict:
    """
    Return cached treemap JSON for the requested sentiment mode.

    Cache is rebuilt lazily to avoid unnecessary computation,
    which is sufficient for the expected request frequency.
    """
    if not _cache_valid():
        print("[CACHE] Rebuilding sentiment cache...", flush=True)
        _rebuild_cache(debug)
    else:
        print("[CACHE] Using cached sentiment data", flush=True)

    # Mode is intentionally restricted via Literal
    # to prevent accidental misuse by callers.
    return _CACHE[mode]