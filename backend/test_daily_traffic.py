import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from game_state import GameStateManager


def _make_state(total: int = 3) -> GameStateManager:
    state = GameStateManager(initialize=False)
    state.total_customers_today = total
    state.customers_served_today = 0
    state.customers_finished_ids = []
    state.active_customer = state.generate_random_customer()
    state.daily_customer_queue = [state.generate_random_customer() for _ in range(total - 1)]
    for customer in state.daily_customer_queue:
        customer.role = "seller"
        customer.generation_source = "local"
    return state


def test_apply_queue_refill_does_not_grow_queue():
    state = _make_state(total=3)
    extras = [state.generate_random_customer() for _ in range(4)]
    for customer in extras:
        customer.generation_source = "ai"

    applied = state.apply_queue_refill(extras)

    assert applied == 2
    assert len(state.daily_customer_queue) == 2
    assert all(getattr(customer, "generation_source", "") == "ai" for customer in state.daily_customer_queue)


def test_select_next_customer_stops_at_daily_total():
    state = _make_state(total=3)
    state.active_customer.session_closed = "deal"

    assert state.select_next_customer() is True
    assert state.customers_served_today == 1
    assert len(state.customers_finished_ids) == 1
    assert state.active_customer is not None

    state.active_customer.session_closed = "deal"
    assert state.select_next_customer() is True
    assert state.customers_served_today == 2

    state.active_customer.session_closed = "deal"
    assert state.select_next_customer() is False
    assert state.customers_served_today == 3
    assert state.active_customer is None
    assert state.daily_customer_queue == []


def test_double_dismiss_same_customer_counts_once():
    state = _make_state(total=3)
    departing_id = state.active_customer.customer_id
    state.active_customer.session_closed = "deal"

    assert state.select_next_customer() is True
    assert state.customers_served_today == 1
    assert departing_id in state.customers_finished_ids

    state.active_customer.session_closed = "deal"
    state.active_customer.customer_id = departing_id
    assert state.select_next_customer() is True
    assert state.customers_served_today == 1
    assert state.active_customer is not None


def test_sanitize_legacy_inflated_counter():
    state = GameStateManager(initialize=False)
    state.total_customers_today = 9
    state.customers_served_today = 19
    state.customers_finished_ids = []
    state.active_customer = state.generate_random_customer()
    state.daily_customer_queue = [state.generate_random_customer() for _ in range(5)]

    state._sanitize_daily_traffic()

    assert state.customers_served_today == 9
    assert state.customers_seen_today() == 9
    assert state.active_customer is None
    assert state.daily_customer_queue == []
