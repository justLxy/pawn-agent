#!/usr/bin/env python3
"""Run one NPC market maintenance tick (for cron)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import init_db
from npc_market_service import run_npc_tick


def main() -> None:
    init_db()
    result = run_npc_tick()
    print(result)


if __name__ == "__main__":
    main()
