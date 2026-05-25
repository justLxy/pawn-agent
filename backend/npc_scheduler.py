import asyncio
import logging
import os
from typing import Optional

from npc_market_config import NPC_MARKET_ENABLED, NPC_MARKET_TICK_HOURS
from npc_market_service import ensure_npc_players, full_seed_npc_shops, refresh_all_npc_presence, run_npc_tick

logger = logging.getLogger("npc_market")

_market_task: Optional[asyncio.Task] = None
_presence_task: Optional[asyncio.Task] = None


async def _npc_market_loop() -> None:
    interval = max(1.0, NPC_MARKET_TICK_HOURS * 3600)
    await asyncio.sleep(15)
    while True:
        try:
            result = await asyncio.to_thread(run_npc_tick)
            logger.info("NPC market tick: %s", result)
        except Exception:
            logger.exception("NPC market tick failed")
        await asyncio.sleep(interval)


async def _npc_presence_loop() -> None:
    """更频繁地刷新 NPC 在线/离线，营造真人挂线节奏。"""
    from npc_market_service import _presence_refresh_interval_sec

    interval = _presence_refresh_interval_sec()
    await asyncio.sleep(45)
    while True:
        try:
            player_map = await asyncio.to_thread(ensure_npc_players)
            presence = await asyncio.to_thread(refresh_all_npc_presence, player_map)
            online_count = sum(1 for online in presence.values() if online)
            logger.info("NPC presence refresh: %s/%s online", online_count, len(presence))
        except Exception:
            logger.exception("NPC presence refresh failed")
        await asyncio.sleep(interval)


def start_npc_scheduler() -> None:
    global _market_task, _presence_task
    if not NPC_MARKET_ENABLED:
        return
    loop = asyncio.get_event_loop()
    if not _market_task or _market_task.done():
        _market_task = loop.create_task(_npc_market_loop())
    if not _presence_task or _presence_task.done():
        _presence_task = loop.create_task(_npc_presence_loop())


async def startup_npc_market() -> None:
    if not NPC_MARKET_ENABLED:
        return
    auto_seed = os.getenv("NPC_MARKET_AUTO_SEED", "1").strip().lower() in ("1", "true", "yes")
    if auto_seed:
        try:
            summary = await asyncio.to_thread(full_seed_npc_shops, False)
            logger.info("NPC market auto-seed: %s players", len(summary.get("players", {})))
        except Exception:
            logger.exception("NPC market auto-seed failed")

    run_tick_on_startup = os.getenv("NPC_MARKET_STARTUP_TICK", "1").strip().lower() in ("1", "true", "yes")
    if run_tick_on_startup:
        try:
            tick_result = await asyncio.to_thread(run_npc_tick)
            logger.info("NPC market startup tick: %s", tick_result)
        except Exception:
            logger.exception("NPC market startup tick failed")

    start_npc_scheduler()
