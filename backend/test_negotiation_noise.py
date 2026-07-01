"""谈判隐藏保留价扰动 + 关键词递减：防止精确压极限价与刷证据词。"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from game_state import Customer, Item
from negotiation_engine import _initial_state
from negotiation_economics import should_auto_accept_negotiation


def _seller(current_offer=8000, limit_price=5500):
    item = Item("测试古物", "Historical", "Good", False, 8000, 9000, "旧物")
    return Customer(
        name="老陈", trait="hardball", role="seller", item=item,
        current_offer=current_offer, limit_price=limit_price,
        shop_level=1, marketer_active=False,
        shop_level_for_case=1, appraisal_room_for_case=1,
    )


def test_reserve_noise_is_seeded_and_bounded():
    seen = set()
    for _ in range(50):
        c = _seller()
        st = _initial_state(c)
        noise = st["reserve_noise"]
        assert -0.06 <= noise <= 0.06
        seen.add(noise)
    # 扰动应有随机性，而非恒为 0（否则又变回可解）
    assert len(seen) > 5


def test_positive_noise_raises_seller_threshold():
    # 卖家：正扰动抬高保留价阈值，原本刚好够的出价会被拒
    limit_price = 5000
    relief_offer = int(limit_price * (1 - (0.015 * 5 + 0.01 * 3)))  # 恰在无扰动阈值
    # 无扰动：接受
    assert should_auto_accept_negotiation(
        "seller", relief_offer, 8000, limit_price, "counter", 5, 3, reserve_noise=0.0
    )
    # 正扰动：同样的出价被拒（压极限价翻车）
    assert not should_auto_accept_negotiation(
        "seller", relief_offer, 8000, limit_price, "counter", 5, 3, reserve_noise=0.05
    )


def test_meeting_or_beating_ask_still_accepts_regardless_of_noise():
    # 出价 >= 要价时无论扰动都成交（不影响爽快成交）
    assert should_auto_accept_negotiation(
        "seller", 8000, 8000, 5000, "counter", 1, 1, reserve_noise=0.06
    )
