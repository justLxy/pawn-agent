import logging
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from env_loader import load_env_file

load_env_file()

from ai_client import AIClient
from auth import current_player, login_player, logout_player, register_player
from database import init_db
from game_state import GameStateManager
from online_services import (
    buy_listing,
    buy_showcase_item,
    ensure_player_state,
    get_leaderboard,
    get_market_listings,
    get_my_listings,
    get_player_showcase,
    get_trade_logs,
    import_state as import_cloud_state,
    list_item,
    reset_player_data,
    save_state,
    set_showcase_price,
    unlist_item,
    update_listing_price,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="当铺代理人 API (Pawnshop Agent API)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_client = AIClient()


class AuthRequest(BaseModel):
    username: str
    password: str
    shop_name: Optional[str] = None


class OfferRequest(BaseModel):
    message: str
    player_offer: Optional[int] = None


class HireRequest(BaseModel):
    staff_type: str


class FireRequest(BaseModel):
    staff_type: str


class ItemRequest(BaseModel):
    item_id: str


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


async def get_engine(player: Dict[str, Any]) -> GameStateManager:
    return await ensure_player_state(player, ai_client)


def commit_state(player: Dict[str, Any], state: GameStateManager) -> Dict[str, Any]:
    state.shop_name = state.shop_name or player["shop_name"]
    save_state(player["id"], state)
    return state.to_dict()


def state_response(player: Dict[str, Any], state: GameStateManager, result_key: str, result: Dict[str, Any]):
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {result_key: result, "state": commit_state(player, state)}


@app.post("/api/auth/register")
async def register(req: AuthRequest):
    auth = register_player(req.username, req.password, req.shop_name or req.username)
    state = GameStateManager()
    state.shop_name = auth["player"]["shop_name"]
    await state.async_initialize_day(ai_client)
    save_state(auth["player"]["id"], state)
    return auth


@app.post("/api/auth/login")
async def login(req: AuthRequest):
    auth = login_player(req.username, req.password)
    await ensure_player_state(auth["player"], ai_client)
    return auth


@app.post("/api/auth/logout")
def logout(player: Dict[str, Any] = Depends(current_player)):
    logout_player(player["id"])
    return {"success": True}


@app.get("/api/auth/me")
def me(player: Dict[str, Any] = Depends(current_player)):
    return {"player": player}


@app.get("/api/state")
async def get_state(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state.to_dict()


@app.get("/api/cloud/state")
async def cloud_state(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
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
    state = reset_player_data(player["id"], player["shop_name"])
    return state.to_dict()


@app.post("/api/negotiate")
async def negotiate(req: OfferRequest, player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    if not state.active_customer:
        raise HTTPException(status_code=400, detail="现在没有正在谈判的顾客。")
    if state.day_ended:
        raise HTTPException(status_code=400, detail="今天营业已结束，请等明天开门。")
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

    customer.dialogue_history.append({"role": "player", "content": req.message.strip()})
    ai_response = await ai_client.generate_negotiation(
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
        player_message=req.message.strip(),
        player_offer=player_offer,
        intent=intent,
        patience=customer.patience,
        negotiation_level=state.skills["negotiation"]["level"],
        charm_level=state.skills["charm"]["level"],
        dialogue_history=customer.dialogue_history,
    )

    dialogue = ai_response["dialogue"]
    new_offer = int(ai_response["new_offer"])
    patience_change = int(ai_response["patience_change"])
    accepted = bool(ai_response["accepted"])
    walk_out = bool(ai_response["walk_out"])
    effective_offer = ai_response.get("parsed_offer", player_offer)
    if effective_offer is not None:
        effective_offer = int(effective_offer)
        skill_relief = 0.015 * state.skills["negotiation"]["level"] + 0.01 * state.skills["charm"]["level"]
        if customer.role == "seller":
            rule_accepted = effective_offer >= int(customer.limit_price * (1 - skill_relief))
        else:
            rule_accepted = effective_offer <= int(customer.limit_price * (1 + skill_relief))
        if rule_accepted:
            accepted = True
            walk_out = False
            new_offer = effective_offer
            patience_change = max(0, patience_change)

    customer.patience = max(0, customer.patience + patience_change)
    if customer.patience == 0:
        walk_out = True
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
        return {"negotiation": negotiation_summary, "deal_completed": True, "deal_result": deal_result, "state": commit_state(player, state)}
    if walk_out:
        state.select_next_customer()
        return {"negotiation": negotiation_summary, "deal_completed": False, "walk_out_completed": True, "state": commit_state(player, state)}
    return {"negotiation": negotiation_summary, "deal_completed": False, "walk_out_completed": False, "state": commit_state(player, state)}


@app.post("/api/deal")
async def finalize_deal(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "deal_result", state.deal())


@app.post("/api/reject")
async def reject_customer(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "result", state.reject())


@app.post("/api/appraise")
async def appraise_item(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    return state_response(player, state, "appraise_result", state.appraise_active_item())


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
    return state_response(player, state, "repair_result", state.start_repair(req.item_id))


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
    return {"summary": summary, "state": commit_state(player, state)}


@app.post("/api/next_day")
async def next_day(player: Dict[str, Any] = Depends(current_player)):
    state = await get_engine(player)
    if not state.day_ended:
        raise HTTPException(status_code=400, detail="请先点击营业结算结束今天的营业！")
    if state.pending_event:
        raise HTTPException(status_code=400, detail="还有未处理的随机事件，请先做出选择。")
    result = await state.async_advance_to_next_day(ai_client)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return commit_state(player, state)


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


def load_state_for_response(player: Dict[str, Any]) -> GameStateManager:
    from online_services import load_state

    return load_state(player["id"])


@app.on_event("startup")
async def startup_event():
    init_db()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
