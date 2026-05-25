import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

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
