import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from env_loader import load_env_file

load_env_file()

from ai_client import AIClient
from auth import _public_player, count_online_players, current_player, delete_player_account, login_player, logout_player, recover_usernames_by_password, register_player
from player_cosmetics import merge_cosmetics_into_player
from shop_service import (
    create_manual_order,
    fulfill_order,
    get_catalog,
    list_admin_pending_orders,
    list_player_orders,
    list_public_sponsors,
    require_shop_admin,
    require_shop_admin_or_secret,
    submit_payment,
    update_profile_cosmetics,
)
from database import init_db
from game_state import GameStateManager
from online_services import (
    buy_listing,
    buy_showcase_item,
    buyer_respond_offer,
    create_offer,
    delete_guestbook,
    bootstrap_new_player_state_async,
    ensure_player_state,
    get_hot_showcases,
    get_leaderboard,
    get_market_listings,
    get_my_listings,
    get_my_offers,
    get_player_showcase,
    get_trade_logs,
    import_state as import_cloud_state,
    list_item,
    post_guestbook,
    reset_player_data,
    respond_offer,
    load_state,
    save_state,
    set_showcase_price,
    toggle_showcase_like,
    unlist_item,
    update_listing_price,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="当铺代理人 API (Pawnshop Agent API)")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "https://game.lvxy.cc,http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_client = AIClient()
day_prewarm_cache: Dict[int, Dict[str, Any]] = {}
day_prewarm_tasks: Dict[int, asyncio.Task] = {}
day_prewarm_task_metadata: Dict[int, Dict[str, Any]] = {}
day_prewarm_generations: Dict[int, int] = {}
queue_refill_cache: Dict[int, Dict[str, Any]] = {}
queue_refill_tasks: Dict[int, asyncio.Task] = {}
queue_refill_generations: Dict[int, int] = {}
PREWARM_GENERATION_TIMEOUT = 75.0
NEXT_DAY_PREWARM_WAIT = 180.0


def next_day_prewarm_signature(state: GameStateManager) -> str:
    """Track only state that materially changes tomorrow's generated roster."""
    saleable_inventory = [
        {
            "id": getattr(item, "id", ""),
            "status": getattr(item, "status", ""),
            "market_value": int(getattr(item, "market_value", 0) or 0),
            "showcase_price": getattr(item, "showcase_price", None),
        }
        for item in getattr(state, "inventory", [])
        if getattr(item, "status", "") in {"stored", "displayed"}
    ]
    customer_memory = [
        {
            "id": customer_id,
            "relationship_level": record.get("relationship_level"),
            "times_seen": record.get("times_seen"),
            "satisfaction": record.get("satisfaction"),
            "last_seen_day": record.get("last_seen_day"),
        }
        for customer_id, record in sorted(getattr(state, "customer_registry", {}).items())
    ]
    payload = {
        "day": int(state.day),
        "shop_level": int(state.shop_level),
        "facilities": dict(sorted(state.facilities.items())),
        "staff": dict(sorted(state.staff.items())),
        "reputation": int(state.reputation),
        "economy_index": round(float(state.economy_index), 4),
        "economic_pressure": state.economic_pressure,
        "market_trends": dict(sorted(state.market_trends.items())),
        "inventory": saleable_inventory,
        "customer_memory": customer_memory,
    }
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


async def generate_prewarmed_pending_event(event_state: GameStateManager) -> Optional[Dict[str, Any]]:
    if event_state.day_ended or event_state.pending_event:
        return None
    event = event_state._generate_pending_event()
    if not event:
        return None
    try:
        ai_event = event_state._normalize_ai_event(
            await ai_client.generate_random_event(
                {
                    "shop_level": event_state.shop_level,
                    "cash": event_state.cash,
                    "day": event_state.day,
                    "reputation": event_state.reputation,
                    "economy_index": event_state.economy_index,
                    "economic_pressure": event_state.economic_pressure,
                    "money_supply_score": event_state.money_supply_score,
                }
            )
        )
        if ai_event:
            return await event_state._enrich_ai_event_item(ai_client, ai_event)
    except Exception as exc:
        logger.warning("Prewarmed event generation failed: %s", exc)
    return event


async def generate_next_day_prewarm(player_id: int, source_day: int, generation: int, signature: str, state_snapshot: Dict[str, Any]) -> None:
    try:
        event_state = GameStateManager.from_dict(state_snapshot)
        preview_state = GameStateManager.from_dict(state_snapshot)
        if int(preview_state.day) != source_day:
            return
        preview_state.day += 1
        preview_state.initialize_day()
        result = await preview_state.async_initialize_day_with_fallback(ai_client, timeout=PREWARM_GENERATION_TIMEOUT)

        customers = ([preview_state.active_customer] if preview_state.active_customer else []) + list(preview_state.daily_customer_queue)
        if not customers or day_prewarm_generations.get(player_id) != generation:
            if result.get("fallback") is True:
                logger.info("Day prewarm empty for player %s day %s: %s", player_id, source_day + 1, result.get("reason"))
            return

        day_prewarm_cache[player_id] = {
            "source_day": source_day,
            "target_day": source_day + 1,
            "signature": signature,
            "customers": customers,
            "partial": result.get("fallback") in (True, "partial"),
            "fallback": bool(result.get("fallback") is True),
            "reason": result.get("reason"),
            "pending_event": None,
            "event_ready": False,
        }
        logger.info(
            "Prewarmed %s customers for player %s day %s (partial=%s, fallback=%s)",
            len(customers),
            player_id,
            source_day + 1,
            result.get("fallback") == "partial",
            result.get("fallback") is True,
        )
        event = await generate_prewarmed_pending_event(event_state)
        cached = day_prewarm_cache.get(player_id)
        if cached and day_prewarm_generations.get(player_id) == generation and cached.get("source_day") == source_day:
            cached["pending_event"] = event
            cached["event_ready"] = True
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("Next day prewarm failed for player %s: %s", player_id, exc)


def _prewarm_cache_ready(player_id: int, source_day: int) -> Optional[List[Any]]:
    cached = day_prewarm_cache.get(player_id)
    if not cached:
        return None
    if cached.get("source_day") != source_day or cached.get("target_day") != source_day + 1:
        return None
    customers = list(cached.get("customers") or [])
    return customers if customers else None


def get_next_day_prewarm(player_id: int, source_day: int) -> List[Any]:
    """Return cached prewarm only; does not wait (kept for tests)."""
    ready = _prewarm_cache_ready(player_id, source_day)
    if ready is not None:
        return consume_next_day_prewarm(player_id, source_day)
    return []


async def await_get_next_day_prewarm(player_id: int, source_day: int, wait_timeout: float = NEXT_DAY_PREWARM_WAIT) -> List[Any]:
    """Wait for in-flight prewarm before opening the next day."""
    ready = _prewarm_cache_ready(player_id, source_day)
    if ready is not None:
        return consume_next_day_prewarm(player_id, source_day)

    running_task = day_prewarm_tasks.get(player_id)
    if running_task and not running_task.done():
        try:
            await asyncio.wait_for(asyncio.shield(running_task), timeout=wait_timeout)
        except asyncio.TimeoutError:
            logger.info("Next day prewarm wait timed out for player %s (day %s)", player_id, source_day)
        except Exception as exc:
            logger.warning("Next day prewarm wait failed for player %s: %s", player_id, exc)

    ready = _prewarm_cache_ready(player_id, source_day)
    if ready is not None:
        return consume_next_day_prewarm(player_id, source_day)

    running_task = day_prewarm_tasks.pop(player_id, None)
    day_prewarm_task_metadata.pop(player_id, None)
    if running_task and not running_task.done():
        running_task.cancel()
        day_prewarm_generations[player_id] = day_prewarm_generations.get(player_id, 0) + 1
        logger.info("Next day prewarm unavailable for player %s; using local fallback.", player_id)
    return []


async def generate_queue_refill(player_id: int, day: int, generation: int, state_snapshot: Dict[str, Any]) -> None:
    try:
        preview_state = GameStateManager.from_dict(state_snapshot)
        if int(preview_state.day) != day:
            return
        batch_size = preview_state.queue_refill_batch_size()
        if batch_size <= 0:
            return

        customers: List[Any] = []
        for _ in range(batch_size):
            if queue_refill_generations.get(player_id) != generation:
                return
            seller = await preview_state.generate_ai_seller_customer(ai_client)
            if seller:
                customers.append(seller)

        if not customers or queue_refill_generations.get(player_id) != generation:
            return

        queue_refill_cache[player_id] = {"day": day, "customers": customers}
        logger.info("Queue refill prepared %s AI sellers for player %s day %s", len(customers), player_id, day)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("Queue refill failed for player %s: %s", player_id, exc)


def finish_queue_refill_task(player_id: int, task: asyncio.Task) -> None:
    if queue_refill_tasks.get(player_id) is task:
        queue_refill_tasks.pop(player_id, None)
    if task.cancelled():
        return
    error = task.exception()
    if error:
        logger.warning("Queue refill task failed for player %s: %s", player_id, error)


def apply_pending_queue_refill(player_id: int, state: GameStateManager) -> int:
    cached = queue_refill_cache.pop(player_id, None)
    if not cached:
        return 0
    if int(cached.get("day", 0)) != int(state.day):
        return 0
    customers = cached.get("customers") or []
    if not customers:
        return 0
    return state.apply_queue_refill(customers)


def schedule_queue_refill(player: Dict[str, Any], state: GameStateManager) -> None:
    if not bool(getattr(ai_client, "available", lambda: False)()):
        return
    if state.pending_event or state.day_ended:
        return
    if state.queue_refill_batch_size() <= 0:
        return
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return

    player_id = int(player["id"])
    day = int(state.day)
    cached = queue_refill_cache.get(player_id)
    if cached and int(cached.get("day", 0)) == day and cached.get("customers"):
        return

    running_task = queue_refill_tasks.get(player_id)
    if running_task and not running_task.done():
        return

    generation = queue_refill_generations.get(player_id, 0) + 1
    queue_refill_generations[player_id] = generation
    state_snapshot = state.to_dict()
    task = asyncio.create_task(generate_queue_refill(player_id, day, generation, state_snapshot))
    queue_refill_tasks[player_id] = task
    task.add_done_callback(lambda completed_task, pid=player_id: finish_queue_refill_task(pid, completed_task))


def finish_prewarm_task(player_id: int, task: asyncio.Task) -> None:
    if day_prewarm_tasks.get(player_id) is task:
        day_prewarm_tasks.pop(player_id, None)
        day_prewarm_task_metadata.pop(player_id, None)
    if task.cancelled():
        return
    error = task.exception()
    if error:
        logger.warning("Next day prewarm task failed for player %s: %s", player_id, error)


def schedule_next_day_prewarm(player: Dict[str, Any], state: GameStateManager, force: bool = False) -> None:
    if not bool(getattr(ai_client, "available", lambda: False)()):
        return
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return

    player_id = int(player["id"])
    source_day = int(state.day)
    target_day = source_day + 1
    signature = next_day_prewarm_signature(state)

    cached = day_prewarm_cache.get(player_id)
    if cached and cached.get("source_day") == source_day and cached.get("target_day") == target_day:
        if state.day_ended and not force and cached.get("customers"):
            return
        if not force and cached.get("signature") == signature and cached.get("customers"):
            return
        day_prewarm_cache.pop(player_id, None)

    if force:
        running_task = day_prewarm_tasks.get(player_id)
        if running_task and not running_task.done():
            running_task.cancel()

    running_task = day_prewarm_tasks.get(player_id)
    if running_task and not running_task.done() and not force:
        metadata = day_prewarm_task_metadata.get(player_id, {})
        if metadata.get("source_day") == source_day and metadata.get("signature") == signature:
            return
        running_task.cancel()
        day_prewarm_tasks.pop(player_id, None)
        day_prewarm_task_metadata.pop(player_id, None)

    generation = day_prewarm_generations.get(player_id, 0) + 1
    day_prewarm_generations[player_id] = generation
    state_snapshot = state.to_dict()
    task = asyncio.create_task(generate_next_day_prewarm(player_id, source_day, generation, signature, state_snapshot))
    day_prewarm_tasks[player_id] = task
    day_prewarm_task_metadata[player_id] = {"source_day": source_day, "target_day": target_day, "signature": signature}
    task.add_done_callback(lambda completed_task, pid=player_id: finish_prewarm_task(pid, completed_task))


def consume_next_day_prewarm(player_id: int, source_day: int) -> List[Any]:
    target_day = source_day + 1
    cached = day_prewarm_cache.pop(player_id, None)
    day_prewarm_generations[player_id] = day_prewarm_generations.get(player_id, 0) + 1

    running_task = day_prewarm_tasks.pop(player_id, None)
    day_prewarm_task_metadata.pop(player_id, None)
    if running_task and not running_task.done():
        running_task.cancel()

    if not cached:
        return []
    if cached.get("source_day") != source_day or cached.get("target_day") != target_day:
        return []
    return list(cached.get("customers") or [])


def apply_prewarmed_pending_event(player_id: int, state: GameStateManager) -> bool:
    cached = day_prewarm_cache.get(player_id)
    if not cached or cached.get("source_day") != int(state.day):
        return False
    event = cached.get("pending_event")
    if not event or not state.pending_event:
        return False
    state.pending_event = event
    if state.daily_summary.get("events") and state.daily_summary["events"][-1].startswith("待处理事件："):
        state.daily_summary["events"][-1] = f"待处理事件：{event['title']}。"
    return True


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API error on %s %s", request.method, request.url.path)
    headers = {}
    origin = request.headers.get("origin")
    if origin and ("*" in allowed_origins or origin in allowed_origins):
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin",
        }
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后再试。"}, headers=headers)


class AuthRequest(BaseModel):
    username: str
    password: str
    shop_name: Optional[str] = None


class RecoverUsernameRequest(BaseModel):
    password: str


class OfferRequest(BaseModel):
    message: str
    player_offer: Optional[int] = None


class HireRequest(BaseModel):
    staff_type: str


class FireRequest(BaseModel):
    staff_type: str


class ItemRequest(BaseModel):
    item_id: str
    method: Optional[str] = None


class AppraiseRequest(BaseModel):
    method: Optional[str] = "standard"


class CaseInvestigateRequest(BaseModel):
    action: str
    method: Optional[str] = "standard"


class FacilityRequest(BaseModel):
    facility: str


class AmountRequest(BaseModel):
    amount: int


class EventChoiceRequest(BaseModel):
    choice_id: str


class ImportStateRequest(BaseModel):
    state: Dict[str, Any]


class MarketListRequest(BaseModel):
    item_id: str
    price: int


class MarketListingRequest(BaseModel):
    listing_id: str


class MarketPriceRequest(BaseModel):
    listing_id: str
    price: int


class ShowcasePriceRequest(BaseModel):
    item_id: str
    price: Optional[int] = None


class ShowcaseBuyRequest(BaseModel):
    owner_id: int
    item_id: str


class MarketOfferRequest(BaseModel):
    listing_id: str
    price: int


class MarketOfferActionRequest(BaseModel):
    offer_id: str
    action: str
    counter_price: Optional[int] = None
    price: Optional[int] = None


class ShowcaseLikeRequest(BaseModel):
    owner_id: int


class ShowcaseGuestbookRequest(BaseModel):
    owner_id: int
    content: str


async def get_engine(player: Dict[str, Any]) -> GameStateManager:
    state = await ensure_player_state(player, ai_client)
    apply_pending_queue_refill(int(player["id"]), state)
    if state.reconcile_daily_traffic():
        save_state(player["id"], state)
    return state


def commit_state(player: Dict[str, Any], state: GameStateManager) -> Dict[str, Any]:
    state.shop_name = state.shop_name or player["shop_name"]
    apply_pending_queue_refill(int(player["id"]), state)
    state.reconcile_daily_traffic()
    save_state(player["id"], state)
    schedule_queue_refill(player, state)
    schedule_next_day_prewarm(player, state, force=state.day_ended)
    return state.to_dict()


def state_response(player: Dict[str, Any], state: GameStateManager, result_key: str, result: Dict[str, Any]):
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {result_key: result, "state": commit_state(player, state)}


def format_offer_change_narration(
    role: str,
    previous_offer: int,
    new_offer: int,
    player_offer: Optional[int] = None,
) -> str:
    price_term = "要价" if role == "seller" else "出价"
    if new_offer > previous_offer:
        direction = "抬至"
    elif new_offer < previous_offer:
        direction = "降至"
    else:
        direction = "维持于"
    line = f"对方将{price_term}{direction} ${new_offer:,}。"
    if player_offer is not None and player_offer > 0:
        if role == "seller":
            line += f" 你已出价 ${player_offer:,}。"
        else:
            line += f" 你的要价 ${player_offer:,}。"
    return line


def terminal_negotiation_dialogue(
    customer: Any,
    accepted: bool,
    walk_out: bool,
    new_offer: int,
    player_offer: Optional[int] = None,
) -> str:
    if accepted:
        if customer.role == "seller":
            return f"{customer.name}盯着柜台沉默片刻，终于把手从货上挪开：「行，${new_offer:,}，这件东西归你。咱们就按这个价办。」"
        return f"{customer.name}看了看柜台里的货，点头道：「行，${new_offer:,} 我认了。帮我包起来，这笔买卖就这么定。」"
    if walk_out:
        if customer.role == "seller":
            return f"{customer.name}把东西重新收回怀里，语气冷了下来：「这个价没法谈，我还是去别家问问。」"
        return f"{customer.name}摇了摇头，往门口退了一步：「这价我接不住，今天就先算了。」"
    if customer.role == "seller":
        if player_offer is not None and player_offer >= new_offer:
            return (
                f"{customer.name}沉吟片刻，把货往柜台推了推："
                f"「${player_offer:,} 是不低，但我还想再磨一磨。少于 ${new_offer:,} 我仍不卖。」"
            )
        return f"{customer.name}皱着眉把货往自己身边挪了挪：「这个价太低，做不了。要谈，至少得看见 ${new_offer:,} 的诚意。」"
    if player_offer is not None and player_offer <= new_offer:
        return (
            f"{customer.name}按住钱夹，摇了摇头："
            f"「${player_offer:,} 还是偏高。若你愿意降到 ${new_offer:,}，我可以继续谈。」"
        )
    return f"{customer.name}按住钱夹，仍没有点头：「这个价我还不能接。若你愿意松到 ${new_offer:,}，我可以继续听。」"


def _dialogue_claims_deal_without_accept(text: str) -> bool:
    """Detect AI falsely claiming a deal while economics say otherwise."""
    if re.search(r"(?<![肯])定了(?=[。！？」』\s]|$)", text):
        return True
    deal_markers = ("成交了", "就成交", "成交吧", "归你了", "说定了", "就这么定了", "那就定了", "我认了", "拿去", "成交")
    if any(marker in text for marker in deal_markers):
        return True
    if "包起来" in text and re.search(r"(帮你|给你|成交|拿走|要了)", text):
        return True
    return False


def normalize_negotiation_dialogue(
    customer: Any,
    dialogue: str,
    accepted: bool,
    walk_out: bool,
    new_offer: int,
    intent: str = "persuade",
    has_price_offer: bool = False,
    player_offer: Optional[int] = None,
    force_terminal: bool = False,
) -> str:
    from game_state import customer_dialogue_conflicts_role
    from negotiation_economics import dialogue_contradicts_economics

    text = (dialogue or "").strip()
    refusal_markers = ["太低", "太高", "不够", "做不了", "没法", "不能", "不卖", "不买", "再添", "加一点", "去别家", "算了"]
    if accepted or walk_out:
        return terminal_negotiation_dialogue(customer, accepted, walk_out, new_offer, player_offer)
    if force_terminal or not text or customer_dialogue_conflicts_role(text, customer.role):
        return terminal_negotiation_dialogue(customer, False, False, new_offer, player_offer)
    if intent in ("question", "persuade") and not has_price_offer:
        return text
    if _dialogue_claims_deal_without_accept(text):
        return terminal_negotiation_dialogue(customer, False, False, new_offer, player_offer)
    if dialogue_contradicts_economics(
        customer.role, text, player_offer, new_offer, int(customer.current_offer)
    ):
        return terminal_negotiation_dialogue(customer, False, False, new_offer, player_offer)
    if any(marker in text for marker in refusal_markers):
        return text
    return text


def prepare_negotiation_ai_response(
    state: GameStateManager,
    customer: Any,
    ai_response: Dict[str, Any],
    player_offer: Optional[int],
    intent: str,
) -> tuple[Dict[str, Any], bool]:
    from negotiation_economics import reconcile_negotiation_economics

    reconciled = reconcile_negotiation_economics(
        customer,
        ai_response,
        player_offer,
        intent,
        negotiation_level=state.skills["negotiation"]["level"],
        charm_level=state.skills["charm"]["level"],
    )
    force_terminal = bool(reconciled.pop("_force_terminal_dialogue", False))
    return reconciled, force_terminal


async def negotiation_ai_response(
    state: GameStateManager,
    customer: Any,
    player_message: str,
    player_offer: Optional[int],
    intent: str,
) -> Dict[str, Any]:
    economy_context = {
        "economy_index": state.economy_index,
        "economic_pressure": state.economic_pressure,
        "market_trend": state.market_trends.get(customer.item.category, 1.0),
    }
    customer_memory = {
        "relationship_cn": customer.to_dict().get("relationship_cn"),
        "visit_count": customer.visit_count,
        "last_deal_summary": customer.last_deal_summary,
    }
    return await ai_client.generate_negotiation(
        customer_name=customer.name,
        trait=customer.trait,
        trait_desc=customer.to_dict()["trait_desc"],
        role=customer.role,
        item_name=customer.item.name,
        item_category=customer.item.category,
        item_condition=customer.item.condition,
        is_fake=customer.item.is_fake,
        actual_value=customer.item.actual_value,
        limit_price=customer.limit_price,
        current_offer=customer.current_offer,
        player_message=player_message,
        player_offer=player_offer,
        intent=intent,
        patience=customer.patience,
        negotiation_level=state.skills["negotiation"]["level"],
        charm_level=state.skills["charm"]["level"],
        dialogue_history=customer.dialogue_history,
        economy_context=economy_context,
        customer_memory=customer_memory,
        customer_context=customer.negotiation_context(),
    )


def is_stale_negotiation_finalize(state: GameStateManager, stream_customer_id: str) -> bool:
    customer = state.active_customer
    if not customer:
        return True
    if customer.customer_id != stream_customer_id:
        return True
    if customer.session_closed:
        return True
    return False


def build_stale_negotiation_payload(player: Dict[str, Any], state: GameStateManager) -> Dict[str, Any]:
    return {
        "negotiation": {
            "stale": True,
            "patience_change": 0,
            "remaining_patience": state.active_customer.patience if state.active_customer else 0,
            "new_offer": state.active_customer.current_offer if state.active_customer else 0,
            "accepted": False,
            "walk_out": False,
        },
        "deal_completed": False,
        "walk_out_completed": False,
        "stale": True,
        "state": commit_state(player, state),
    }


def apply_negotiation_outcome(
    player: Dict[str, Any],
    state: GameStateManager,
    ai_response: Dict[str, Any],
    player_offer: Optional[int],
    intent: str,
) -> Dict[str, Any]:
    customer = state.active_customer
    if not customer:
        raise HTTPException(status_code=400, detail="现在没有正在谈判的顾客。")
    disk_state = load_state(int(player["id"]))
    if is_stale_negotiation_finalize(disk_state, customer.customer_id):
        return build_stale_negotiation_payload(player, disk_state)
    ai_response, force_terminal = prepare_negotiation_ai_response(
        state, customer, ai_response, player_offer, intent
    )
    dialogue = ai_response["dialogue"]
    patience_change = int(ai_response["patience_change"])
    accepted = bool(ai_response["accepted"])
    walk_out = bool(ai_response["walk_out"])
    previous_offer = customer.current_offer
    if accepted:
        from negotiation_economics import negotiation_deal_price

        patience_change = max(0, patience_change)
        new_offer = negotiation_deal_price(customer.role, player_offer, previous_offer)
        ai_response["new_offer"] = new_offer
    else:
        new_offer = int(ai_response["new_offer"])
    previous_patience = customer.patience
    customer.patience = max(0, customer.patience + patience_change)
    if customer.patience == 0:
        walk_out = True
    dialogue = normalize_negotiation_dialogue(
        customer,
        dialogue,
        accepted,
        walk_out,
        new_offer,
        intent=intent,
        has_price_offer=player_offer is not None,
        player_offer=player_offer,
        force_terminal=force_terminal,
    )
    if not accepted and not walk_out and new_offer != previous_offer:
        customer.dialogue_history.append({
            "role": "narrator",
            "content": format_offer_change_narration(
                customer.role, previous_offer, new_offer, player_offer
            ),
        })
    if patience_change < 0:
        customer.dialogue_history.append({
            "role": "narrator",
            "content": f"对方耐心下降，还剩 {customer.patience} 点。",
        })
    elif patience_change > 0 and previous_patience < customer.patience:
        customer.dialogue_history.append({
            "role": "narrator",
            "content": f"你的话起了作用，对方耐心回升至 {customer.patience} 点。",
        })
    customer.dialogue_history.append({"role": "customer", "content": dialogue})
    customer.current_offer = new_offer
    state.add_skill_xp("negotiation", 12)
    if intent in ["persuade", "question"]:
        state.add_skill_xp("charm", 8)

    negotiation_summary = {
        "dialogue": dialogue,
        "patience_change": patience_change,
        "remaining_patience": customer.patience,
        "new_offer": new_offer,
        "accepted": accepted,
        "walk_out": walk_out,
        "parsed_offer": ai_response.get("parsed_offer", player_offer),
        "intent": intent,
    }

    if accepted:
        deal_result = state.deal()
        if "error" in deal_result:
            raise HTTPException(status_code=400, detail=deal_result["error"])
        return {"negotiation": negotiation_summary, "deal_completed": True, "deal_result": deal_result, "state": commit_state(player, state)}
    if walk_out:
        state._record_customer_outcome(customer, "walk_out")
        state._check_achievements("walk_out")
        customer.session_closed = "walk_out"
        customer.deal_summary = "顾客离开了当铺，这笔买卖没有谈成，声誉 -2。"
        return {"negotiation": negotiation_summary, "deal_completed": False, "walk_out_completed": True, "state": commit_state(player, state)}
    return {"negotiation": negotiation_summary, "deal_completed": False, "walk_out_completed": False, "state": commit_state(player, state)}


@app.get("/api/online/count")
def online_count():
    online = count_online_players()
    return {"online": online, "message": f"当前 {online} 人在线"}


@app.post("/api/auth/register")
async def register(req: AuthRequest):
    auth = register_player(req.username, req.password, req.shop_name or req.username)
    state = await bootstrap_new_player_state_async(auth["player"]["id"], auth["player"]["shop_name"], ai_client)
    schedule_queue_refill(auth["player"], state)
    schedule_next_day_prewarm(auth["player"], state)
    return auth


@app.post("/api/auth/recover_username")
async def recover_username(req: RecoverUsernameRequest):
    usernames = recover_usernames_by_password(req.password)
    if not usernames:
        return {
            "usernames": [],
            "count": 0,
            "message": "未找到使用该密码的账号，请确认密码是否输入正确。",
        }
    if len(usernames) == 1:
        message = f"找到 1 个账号：{usernames[0]}"
    else:
        joined = "、".join(usernames)
        message = f"找到 {len(usernames)} 个使用该密码的账号：{joined}"
    return {"usernames": usernames, "count": len(usernames), "message": message}


@app.post("/api/auth/login")
async def login(req: AuthRequest):
    auth = login_player(req.username, req.password)
    state = await ensure_player_state(auth["player"], ai_client)
    schedule_next_day_prewarm(auth["player"], state)
    return auth


@app.post("/api/auth/logout")
def logout(player: Dict[str, Any] = Depends(current_player)):
    logout_player(player["id"])
    return {"success": True}


@app.delete("/api/auth/account")
def delete_account(player: Dict[str, Any] = Depends(current_player)):
    delete_player_account(player["id"])
    return {"success": True, "message": "账号已注销。"}


@app.get("/api/auth/me")
def me(player: Dict[str, Any] = Depends(current_player)):
    return {"player": player}


class ShopOrderRequest(BaseModel):
    product_id: str


class ShopSubmitRequest(BaseModel):
    order_id: str
    payer_note: Optional[str] = None


class ShopFulfillRequest(BaseModel):
    order_id: Optional[str] = None
    order_no: Optional[str] = None


class ProfileCosmeticsRequest(BaseModel):
    shop_emblem: Optional[str] = None
    showcase_tagline: Optional[str] = None


@app.get("/api/shop/catalog")
def shop_catalog():
    return {"products": get_catalog()}


@app.get("/api/shop/sponsors")
def shop_sponsors():
    return {"sponsors": list_public_sponsors()}


@app.get("/api/shop/orders")
def shop_orders(player: Dict[str, Any] = Depends(current_player)):
    return {"orders": list_player_orders(player["id"])}


@app.post("/api/shop/create_order")
def shop_create_order(req: ShopOrderRequest, player: Dict[str, Any] = Depends(current_player)):
    return create_manual_order(player["id"], req.product_id)


@app.post("/api/shop/submit_payment")
def shop_submit_payment(req: ShopSubmitRequest, player: Dict[str, Any] = Depends(current_player)):
    return submit_payment(player["id"], req.order_id, req.payer_note)


@app.get("/api/shop/admin/queue")
def shop_admin_queue(player: Dict[str, Any] = Depends(current_player)):
    require_shop_admin(player)
    return {"orders": list_admin_pending_orders()}


@app.post("/api/shop/admin/fulfill")
def shop_admin_fulfill(
    req: ShopFulfillRequest,
    player: Dict[str, Any] = Depends(current_player),
    x_shop_admin_secret: Optional[str] = Header(None, alias="X-Shop-Admin-Secret"),
):
    require_shop_admin_or_secret(player, x_shop_admin_secret)
    return fulfill_order(req.order_id, req.order_no)


@app.patch("/api/profile/cosmetics")
def profile_cosmetics(req: ProfileCosmeticsRequest, player: Dict[str, Any] = Depends(current_player)):
    cosmetics = update_profile_cosmetics(player["id"], req.shop_emblem, req.showcase_tagline)
    from database import get_connection

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM players WHERE id = ?", (player["id"],)).fetchone()
    return {"cosmetics": cosmetics, "player": merge_cosmetics_into_player(_public_player(row), row)}


@app.get("/api/state")
async def get_state(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    apply_pending_queue_refill(int(player["id"]), state)
    save_state(player["id"], state)
    schedule_queue_refill(player, state)
    schedule_next_day_prewarm(player, state)
    return state.to_dict()


@app.get("/api/cloud/state")
async def cloud_state(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    apply_pending_queue_refill(int(player["id"]), state)
    save_state(player["id"], state)
    schedule_queue_refill(player, state)
    schedule_next_day_prewarm(player, state)
    return state.to_dict()


@app.post("/api/cloud/state")
def save_cloud_state(req: ImportStateRequest, player: Dict[str, Any] = Depends(current_player)):
    state = import_cloud_state(player["id"], req.state, player["shop_name"])
    return state.to_dict()


@app.post("/api/cloud/import_local")
def import_local_state(req: ImportStateRequest, player: Dict[str, Any] = Depends(current_player)):
    state = import_cloud_state(player["id"], req.state, player["shop_name"])
    return state.to_dict()


@app.post("/api/import_state")
def import_state(req: ImportStateRequest, player: Dict[str, Any] = Depends(current_player)):
    state = import_cloud_state(player["id"], req.state, player["shop_name"])
    return state.to_dict()


@app.post("/api/restart")
async def restart_game(player: Dict[str, Any] = Depends(current_player)):
    state = GameStateManager()
    state.shop_name = player["shop_name"]
    await state.async_initialize_day_with_fallback(ai_client)
    state = reset_player_data(player["id"], player["shop_name"], state)
    schedule_next_day_prewarm(player, state)
    return state.to_dict()


@app.post("/api/negotiate")
async def negotiate(req: OfferRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    state.ensure_active_customer_target()
    if not state.active_customer:
        raise HTTPException(status_code=400, detail="现在没有正在谈判的顾客。")
    if state.day_ended:
        raise HTTPException(status_code=400, detail="今天营业已结束，请等明天开门。")
    if state.active_customer.session_closed:
        raise HTTPException(status_code=400, detail="请先送离当前顾客。")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="请输入谈判内容。")

    customer = state.active_customer
    parsed = await ai_client.parse_player_negotiation(req.message, req.player_offer)
    player_offer = parsed.get("offer")
    intent = parsed.get("intent", "persuade")
    if player_offer is not None and player_offer <= 0:
        raise HTTPException(status_code=400, detail="报价必须大于0元！")
    if customer.role == "seller" and player_offer is not None and player_offer > state.cash:
        raise HTTPException(status_code=400, detail=f"现金不足，你当前最多只能出 ${state.cash}。")

    player_message = req.message.strip()
    customer.dialogue_history.append({"role": "player", "content": player_message})
    ai_response = await negotiation_ai_response(state, customer, player_message, player_offer, intent)
    return apply_negotiation_outcome(player, state, ai_response, player_offer, intent)


@app.post("/api/negotiate/stream")
async def negotiate_stream(req: OfferRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    state.ensure_active_customer_target()
    if not state.active_customer:
        raise HTTPException(status_code=400, detail="现在没有正在谈判的顾客。")
    if state.day_ended:
        raise HTTPException(status_code=400, detail="今天营业已结束，请等明天开门。")
    if state.active_customer.session_closed:
        raise HTTPException(status_code=400, detail="请先送离当前顾客。")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="请输入谈判内容。")

    customer = state.active_customer
    parsed = await ai_client.parse_player_negotiation(req.message, req.player_offer)
    player_offer = parsed.get("offer")
    intent = parsed.get("intent", "persuade")
    if player_offer is not None and player_offer <= 0:
        raise HTTPException(status_code=400, detail="报价必须大于0元！")
    if customer.role == "seller" and player_offer is not None and player_offer > state.cash:
        raise HTTPException(status_code=400, detail=f"现金不足，你当前最多只能出 ${state.cash}。")

    player_message = req.message.strip()
    customer.dialogue_history.append({"role": "player", "content": player_message})
    economy_context = {
        "economy_index": state.economy_index,
        "economic_pressure": state.economic_pressure,
        "market_trend": state.market_trends.get(customer.item.category, 1.0),
    }
    customer_memory = {
        "relationship_cn": customer.to_dict().get("relationship_cn"),
        "visit_count": customer.visit_count,
        "last_deal_summary": customer.last_deal_summary,
    }
    customer_context = customer.negotiation_context()
    previous_offer = customer.current_offer
    ai_response = await negotiation_ai_response(state, customer, player_message, player_offer, intent)
    ai_response, force_terminal = prepare_negotiation_ai_response(
        state, customer, ai_response, player_offer, intent
    )
    stream_customer_id = customer.customer_id

    async def stream():
        def line(payload: Dict[str, Any]) -> str:
            return json.dumps(payload, ensure_ascii=False) + "\n"

        yield line({"type": "start"})
        streamed_dialogue = ""
        if force_terminal or bool(ai_response["accepted"]) or bool(ai_response["walk_out"]):
            streamed_dialogue = normalize_negotiation_dialogue(
                customer,
                str(ai_response.get("dialogue") or ""),
                bool(ai_response["accepted"]),
                bool(ai_response["walk_out"]),
                int(ai_response["new_offer"]),
                intent=intent,
                has_price_offer=player_offer is not None,
                player_offer=player_offer,
                force_terminal=force_terminal,
            )
            yield line({"type": "chunk", "content": streamed_dialogue})
        else:
            try:
                async for chunk in ai_client.stream_negotiation_dialogue(
                    customer_name=customer.name,
                    trait_desc=customer.to_dict()["trait_desc"],
                    role=customer.role,
                    item_name=customer.item.name,
                    player_message=player_message,
                    new_offer=int(ai_response["new_offer"]),
                    accepted=bool(ai_response["accepted"]),
                    walk_out=bool(ai_response["walk_out"]),
                    dialogue_history=customer.dialogue_history,
                    economy_context=economy_context,
                    customer_memory=customer_memory,
                    customer_context=customer_context,
                    intent=intent,
                    patience_change=int(ai_response.get("patience_change", 0)),
                    previous_offer=previous_offer,
                ):
                    streamed_dialogue += chunk
                    yield line({"type": "chunk", "content": chunk})
            except Exception as exc:
                logger.warning("Negotiation dialogue stream failed: %s", exc)

            if not streamed_dialogue.strip():
                streamed_dialogue = str(ai_response.get("dialogue") or "嗯，我再想想这个价。")
                for index in range(0, len(streamed_dialogue), 8):
                    yield line({"type": "chunk", "content": streamed_dialogue[index:index + 8]})

        ai_response["dialogue"] = streamed_dialogue.strip()[:480]
        try:
            fresh_state = await ensure_player_state(player, ai_client)
            if is_stale_negotiation_finalize(fresh_state, stream_customer_id):
                payload = build_stale_negotiation_payload(player, fresh_state)
                yield line({"type": "final", "payload": payload})
                return
            payload = apply_negotiation_outcome(player, state, ai_response, player_offer, intent)
        except HTTPException as exc:
            logger.warning("Negotiation stream finalization failed: %s", exc.detail)
            yield line({"type": "error", "detail": exc.detail})
            return
        except Exception as exc:
            logger.exception("Negotiation stream finalization failed")
            yield line({"type": "error", "detail": f"谈判结算失败：{exc}"})
            return
        yield line({"type": "final", "payload": payload})

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/api/deal")
async def finalize_deal(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    if state.active_customer and state.active_customer.session_closed:
        raise HTTPException(status_code=400, detail="请先送离当前顾客。")
    return state_response(player, state, "deal_result", state.deal())


@app.post("/api/reject")
async def reject_customer(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "result", state.reject())


@app.post("/api/dismiss_customer")
async def dismiss_customer(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "result", state.dismiss_customer())


@app.post("/api/appraise")
async def appraise_item(req: Optional[AppraiseRequest] = None, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "appraise_result", await state.async_appraise_active_item(ai_client, (req.method if req else "standard") or "standard"))


@app.post("/api/case/investigate")
async def investigate_case(req: CaseInvestigateRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(
        player,
        state,
        "investigation_result",
        await state.async_investigate_case(ai_client, req.action, req.method or "standard"),
    )


class AppraiseInventoryRequest(BaseModel):
    item_id: str
    method: str = "standard"


@app.post("/api/appraise_inventory")
async def appraise_inventory_item(req: AppraiseInventoryRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "appraise_result", await state.async_appraise_inventory_item(ai_client, req.item_id, req.method))


@app.post("/api/display")
async def display_item(req: ItemRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "display_result", state.display_item(req.item_id))


@app.post("/api/undisplay")
async def undisplay_item(req: ItemRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "display_result", state.undisplay_item(req.item_id))


@app.post("/api/repair")
async def repair_item(req: ItemRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "repair_result", state.start_repair(req.item_id, req.method or "standard"))


@app.post("/api/sell")
async def sell_item(req: ItemRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "sell_result", state.sell_item(req.item_id))


@app.post("/api/hire")
async def hire_employee(req: HireRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "hire_result", state.hire_staff(req.staff_type))


@app.post("/api/fire")
async def fire_employee(req: FireRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "fire_result", state.fire_staff(req.staff_type))


@app.post("/api/upgrade")
async def upgrade_shop(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "upgrade_result", state.upgrade_shop())


@app.post("/api/upgrade_facility")
async def upgrade_facility(req: FacilityRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "upgrade_result", state.upgrade_facility(req.facility))


@app.post("/api/loan/borrow")
async def borrow_loan(req: AmountRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "loan_result", state.borrow_loan(req.amount))


@app.post("/api/loan/repay")
async def repay_loan(req: AmountRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "loan_result", state.repay_loan(req.amount))


@app.post("/api/event/choice")
async def choose_event(req: EventChoiceRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "event_result", state.resolve_event(req.choice_id))


@app.post("/api/end_day")
async def end_day(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    summary = state.end_day()
    if "error" in summary:
        raise HTTPException(status_code=400, detail=summary["error"])
    if state.pending_event:
        apply_prewarmed_pending_event(int(player["id"]), state)
    return {"summary": summary, "state": commit_state(player, state)}


@app.post("/api/next_day")
async def next_day(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    if not state.day_ended:
        raise HTTPException(status_code=400, detail="请先点击营业结算结束今天的营业！")
    if state.pending_event:
        raise HTTPException(status_code=400, detail="还有未处理的随机事件，请先做出选择。")
    prewarmed_customers = await await_get_next_day_prewarm(int(player["id"]), int(state.day))
    result = await state.async_advance_to_next_day(ai_client, prewarmed_customers)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {
        "result": {
            "success": True,
            "message": result.get("message", "新的一天开始了。"),
            "prewarmed": bool(result.get("prewarmed", False)),
            "fallback": bool(result.get("fallback", False)),
        },
        "state": commit_state(player, state),
    }


@app.get("/api/leaderboard")
def leaderboard(board_type: str = Query("assets", alias="type"), player: Dict[str, Any] = Depends(current_player)):
    return get_leaderboard(board_type, player["id"])


@app.get("/api/market/listings")
def market_listings(
    search: str = "",
    rarity: str = "",
    category: str = "",
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    sort: str = "newest",
    player: Dict[str, Any] = Depends(current_player),
):
    _ = player
    return {"listings": get_market_listings(search, rarity, category, min_price, max_price, sort)}


@app.get("/api/market/mine")
def my_market_listings(player: Dict[str, Any] = Depends(current_player)):
    return {"listings": get_my_listings(player["id"])}


@app.post("/api/market/list")
def market_list(req: MarketListRequest, player: Dict[str, Any] = Depends(current_player)):
    result = list_item(player["id"], req.item_id, req.price)
    state = load_state_for_response(player)
    return {"market_result": result, "state": state.to_dict(), "listings": get_my_listings(player["id"])}


@app.post("/api/market/unlist")
def market_unlist(req: MarketListingRequest, player: Dict[str, Any] = Depends(current_player)):
    result = unlist_item(player["id"], req.listing_id)
    state = load_state_for_response(player)
    return {"market_result": result, "state": state.to_dict(), "listings": get_my_listings(player["id"])}


@app.post("/api/market/update_price")
def market_update_price(req: MarketPriceRequest, player: Dict[str, Any] = Depends(current_player)):
    result = update_listing_price(player["id"], req.listing_id, req.price)
    return {"market_result": result, "listings": get_my_listings(player["id"])}


@app.post("/api/market/buy")
def market_buy(req: MarketListingRequest, player: Dict[str, Any] = Depends(current_player)):
    result = buy_listing(player["id"], req.listing_id)
    state = load_state_for_response(player)
    return {"market_result": result, "state": state.to_dict()}


@app.get("/api/market/trades")
def market_trades(player: Dict[str, Any] = Depends(current_player)):
    return {"trades": get_trade_logs(player["id"])}


@app.post("/api/market/offer")
def market_offer(req: MarketOfferRequest, player: Dict[str, Any] = Depends(current_player)):
    result = create_offer(player["id"], req.listing_id, req.price)
    return {"market_result": result, "offers": get_my_offers(player["id"])}


@app.post("/api/market/offer/respond")
def market_offer_respond(req: MarketOfferActionRequest, player: Dict[str, Any] = Depends(current_player)):
    result = respond_offer(player["id"], req.offer_id, req.action, req.counter_price)
    state = load_state_for_response(player) if req.action == "accept" else None
    payload: Dict[str, Any] = {"market_result": result, "offers": get_my_offers(player["id"])}
    if state is not None:
        payload["state"] = state.to_dict()
    return payload


@app.post("/api/market/offer/buyer_respond")
def market_offer_buyer_respond(req: MarketOfferActionRequest, player: Dict[str, Any] = Depends(current_player)):
    result = buyer_respond_offer(player["id"], req.offer_id, req.action, req.price)
    state = load_state_for_response(player) if req.action == "accept" else None
    payload: Dict[str, Any] = {"market_result": result, "offers": get_my_offers(player["id"])}
    if state is not None:
        payload["state"] = state.to_dict()
    return payload


@app.get("/api/market/offers")
def market_offers(player: Dict[str, Any] = Depends(current_player)):
    return get_my_offers(player["id"])


@app.get("/api/showcase/hot")
def showcase_hot(limit: int = Query(20, ge=1, le=50), player: Dict[str, Any] = Depends(current_player)):
    _ = player
    return {"entries": get_hot_showcases(limit)}


@app.get("/api/showcase/{owner_id}")
def player_showcase(owner_id: int, player: Dict[str, Any] = Depends(current_player)):
    return get_player_showcase(player["id"], owner_id)


@app.post("/api/showcase/price")
def showcase_price(req: ShowcasePriceRequest, player: Dict[str, Any] = Depends(current_player)):
    result = set_showcase_price(player["id"], req.item_id, req.price)
    state = load_state_for_response(player)
    return {"showcase_result": result, "state": state.to_dict()}


@app.post("/api/showcase/buy")
def showcase_buy(req: ShowcaseBuyRequest, player: Dict[str, Any] = Depends(current_player)):
    result = buy_showcase_item(player["id"], req.owner_id, req.item_id)
    state = load_state_for_response(player)
    showcase = get_player_showcase(player["id"], req.owner_id)
    return {"showcase_result": result, "state": state.to_dict(), "showcase": showcase}


@app.post("/api/showcase/like")
def showcase_like(req: ShowcaseLikeRequest, player: Dict[str, Any] = Depends(current_player)):
    result = toggle_showcase_like(player["id"], req.owner_id)
    showcase = get_player_showcase(player["id"], req.owner_id)
    return {"showcase_result": result, "showcase": showcase}


@app.post("/api/showcase/guestbook")
def showcase_guestbook(req: ShowcaseGuestbookRequest, player: Dict[str, Any] = Depends(current_player)):
    result = post_guestbook(player["id"], req.owner_id, req.content)
    showcase = get_player_showcase(player["id"], req.owner_id)
    return {"showcase_result": result, "showcase": showcase}


@app.delete("/api/showcase/guestbook/{message_id}")
def showcase_guestbook_delete(message_id: int, player: Dict[str, Any] = Depends(current_player)):
    result = delete_guestbook(player["id"], message_id)
    showcase = get_player_showcase(player["id"], player["id"])
    return {"showcase_result": result, "showcase": showcase}


def load_state_for_response(player: Dict[str, Any]) -> GameStateManager:
    from online_services import load_state

    return load_state(player["id"])


@app.on_event("startup")
async def startup_event():
    init_db()
    from npc_scheduler import startup_npc_market

    await startup_npc_market()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
