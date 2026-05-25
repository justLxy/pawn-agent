#!/usr/bin/env python3
"""Seed or reset NPC pawn shop accounts and market listings."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import init_db
from npc_market_service import full_seed_npc_shops


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed NPC pawn shops for the player market.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear active NPC listings and rebuild inventory before seeding.",
    )
    args = parser.parse_args()
    init_db()
    summary = full_seed_npc_shops(reset=args.reset)
    players = summary.get("players", {})
    listings = summary.get("listings", {})
    print(f"Seeded {len(players)} NPC shops.")
    for key, player_id in players.items():
        count = len(listings.get(key, []))
        print(f"  {key}: player_id={player_id}, new_listings={count}")


if __name__ == "__main__":
    main()
