import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import app as app_module
from game_state import GameStateManager


class ExplodingAI:
    def available(self):
        return True

    def __getattr__(self, name):
        raise AssertionError(f"next day click must not call AI method: {name}")


def test_next_day_uses_local_fallback_without_sync_ai():
    state = GameStateManager()
    state.day_ended = True

    result = asyncio.run(state.async_advance_to_next_day(ExplodingAI(), []))

    assert result["success"] is True
    assert result["fallback"] is True
    assert state.day == 2
    assert state.active_customer is not None


def test_next_day_consumes_prewarmed_roster():
    state = GameStateManager()
    state.day_ended = True
    prewarmed = [state.generate_random_customer() for _ in range(state.total_customers_today)]

    result = asyncio.run(state.async_advance_to_next_day(ExplodingAI(), prewarmed))

    assert result["success"] is True
    assert result["prewarmed"] is True
    assert state.day == 2
    assert state.active_customer is not None


def test_await_get_next_day_prewarm_waits_for_running_task():
    player_id = 999_001
    source_day = 3
    app_module.day_prewarm_cache.pop(player_id, None)
    app_module.day_prewarm_tasks.pop(player_id, None)
    app_module.day_prewarm_generations[player_id] = 0

    async def run_case():
        prewarmed: list = []

        async def slow_prewarm():
            await asyncio.sleep(0.05)
            state = GameStateManager()
            state.day = source_day
            prewarmed.extend([state.generate_random_customer() for _ in range(2)])
            app_module.day_prewarm_cache[player_id] = {
                "source_day": source_day,
                "target_day": source_day + 1,
                "signature": "test",
                "customers": prewarmed,
            }

        task = asyncio.create_task(slow_prewarm())
        app_module.day_prewarm_tasks[player_id] = task
        consumed = await app_module.await_get_next_day_prewarm(player_id, source_day, wait_timeout=2.0)
        assert len(consumed) == 2
        assert task.done()

    asyncio.run(run_case())
