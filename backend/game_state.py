import random
import time
import uuid
from copy import deepcopy
from urllib.parse import quote
from typing import Any, Dict, List, Optional


ITEM_TEMPLATES = {
    "Pop Culture": [
        {"name": "初代宝可梦喷火龙闪卡", "mint_val": 1500, "good_val": 800, "poor_val": 300, "fake_rate": 0.15, "desc": "1999年第一版无阴影喷火龙卡片，极具收藏价值。"},
        {"name": "迈克尔·杰克逊亲笔签名手套", "mint_val": 5000, "good_val": 2500, "poor_val": 1000, "fake_rate": 0.25, "desc": "镶满亮片的白色礼服手套，带有天王本人的亲笔签名。"},
        {"name": "乔丹1998年总决赛亲穿球衣", "mint_val": 12000, "good_val": 6000, "poor_val": 2500, "fake_rate": 0.30, "desc": "芝加哥公牛队经典的23号红色球衣，相传是总决赛第二场亲穿。"},
        {"name": "《星球大战》1977年原版未拆封黑武士手办", "mint_val": 3500, "good_val": 1800, "poor_val": 600, "fake_rate": 0.10, "desc": "Kenner公司生产的初代3.75英寸黑武士，吸塑卡保存完好。"},
        {"name": "任天堂红白机(FC)未拆封原装机", "mint_val": 2500, "good_val": 1200, "poor_val": 500, "fake_rate": 0.08, "desc": "极其罕见的全新未拆封原装FC日版红白机。"},
    ],
    "Art": [
        {"name": "徐悲鸿《八骏图》精细摹本", "mint_val": 8000, "good_val": 4000, "poor_val": 1500, "fake_rate": 0.45, "desc": "水墨奔马图摹本，画工极佳，宣纸微泛黄，有鉴赏家伪印。"},
        {"name": "现代主义抽象派油画《无题》", "mint_val": 3000, "good_val": 1500, "poor_val": 700, "fake_rate": 0.20, "desc": "不知名现代画家的油画作品，色彩强烈，构图张扬。"},
        {"name": "张大千泼彩山水画仿作", "mint_val": 15000, "good_val": 7000, "poor_val": 3000, "fake_rate": 0.50, "desc": "青绿泼彩设色，气势磅礴。墨韵生动，极难分辨真伪。"},
        {"name": "毕加索签名的限量陶瓷盘子", "mint_val": 9000, "good_val": 4500, "poor_val": 2000, "fake_rate": 0.35, "desc": "1950年代马杜拉陶艺工坊制作，盘底印有毕加索专属签名。"},
        {"name": "齐白石风格《虾趣图》", "mint_val": 5500, "good_val": 2800, "poor_val": 1100, "fake_rate": 0.40, "desc": "展现出墨虾灵动多姿的身态，落款和印章十分考究。"},
    ],
    "Jewelry": [
        {"name": "18K金镶3克拉天然红宝石戒指", "mint_val": 6000, "good_val": 3500, "poor_val": 1800, "fake_rate": 0.15, "desc": "主石为鸽血红宝石，周边微镶碎钻，工艺精湛，色泽艳丽。"},
        {"name": "维多利亚时期古董祖母绿项链", "mint_val": 10000, "good_val": 5500, "poor_val": 2500, "fake_rate": 0.20, "desc": "典型的19世纪维多利亚时期复古设计，主石祖母绿内含物天然。"},
        {"name": "大溪地黑珍珠耳环", "mint_val": 4000, "good_val": 2200, "poor_val": 1000, "fake_rate": 0.10, "desc": "两颗直径14mm的黑珍珠，带有迷人的孔雀绿金属光泽。"},
        {"name": "冰种阳绿翡翠手镯", "mint_val": 20000, "good_val": 10000, "poor_val": 4000, "fake_rate": 0.40, "desc": "玉质细腻，质地冰润，带有一抹极其鲜艳的阳绿。"},
        {"name": "百达翡丽1970年代古董金表", "mint_val": 15000, "good_val": 8500, "poor_val": 4000, "fake_rate": 0.25, "desc": "手动上链机械机芯，18K黄金表壳，运行走时依然精准。"},
    ],
    "Antiquities": [
        {"name": "清乾隆粉彩缠枝花卉纹瓷瓶", "mint_val": 18000, "good_val": 9000, "poor_val": 4000, "fake_rate": 0.55, "desc": "大清乾隆年制款，胎质细密，釉色莹润，掐丝精细。"},
        {"name": "战国时期青铜错金带钩", "mint_val": 12000, "good_val": 6000, "poor_val": 2500, "fake_rate": 0.40, "desc": "青铜锈迹斑驳，但错金纹路依然清晰，具有极高的史学研究价值。"},
        {"name": "明代黄花梨官皮箱", "mint_val": 15000, "good_val": 8000, "poor_val": 3500, "fake_rate": 0.30, "desc": "色泽金黄温润，纹理如行云流水。金属锁扣配件为原装。"},
        {"name": "唐代三彩马", "mint_val": 25000, "good_val": 12000, "poor_val": 5000, "fake_rate": 0.50, "desc": "釉色斑斓，马身丰满。底盘有细微土腥味，造型昂扬。"},
        {"name": "宋代建窑兔毫盏", "mint_val": 10000, "good_val": 5000, "poor_val": 2000, "fake_rate": 0.45, "desc": "盏壁兔毫纹细密清晰，折射出铁锈红色的金属光泽。"},
    ],
    "Historical": [
        {"name": "二战时期密码机 Enigma 残件", "mint_val": 30000, "good_val": 15000, "poor_val": 6000, "fake_rate": 0.10, "desc": "德国军用转子密码机，转子及部分外壳完好，铭牌可辨。"},
        {"name": "泰坦尼克号头等舱船票存根", "mint_val": 8000, "good_val": 4000, "poor_val": 1800, "fake_rate": 0.20, "desc": "白星航运印制的硬纸船票，印有1912年4月出航时间及编号。"},
        {"name": "19世纪法国拿破仑军官佩剑", "mint_val": 14000, "good_val": 7000, "poor_val": 3000, "fake_rate": 0.25, "desc": "精钢剑身，配有烫金帝国鹰徽及真皮剑鞘，护手雕花华丽。"},
        {"name": "阿波罗11号登月任务签名徽章", "mint_val": 11000, "good_val": 5000, "poor_val": 2000, "fake_rate": 0.15, "desc": "登月舱纪念金属徽章，配有阿姆斯特朗及奥尔德林的签名墨迹。"},
        {"name": "18世纪西班牙沉船“双柱”银币", "mint_val": 3500, "good_val": 1800, "poor_val": 800, "fake_rate": 0.15, "desc": "来自于著名的沉船遗迹，银币表面有海底珊瑚和氧化碳酸盐附着。"},
    ],
}

CUSTOMER_NAMES = [
    "张伟", "王芳", "李杰", "刘洋", "陈静", "杨光", "赵军", "黄燕", "周超", "吴磊",
    "徐丽", "孙敏", "胡涛", "朱玲", "高飞", "林杰", "何平", "郭辉", "马莉", "罗刚",
    "艾米莉", "老莫", "王大锤", "安娜", "钱老板", "九叔", "珍妮花", "小帅", "苏富比常客",
]

CUSTOMER_TRAITS = {
    "hardball": {"name_cn": "强硬", "desc": "坚持自己的价格，喜欢压迫式谈判。"},
    "eager": {"name_cn": "急切", "desc": "急于完成交易，价格合适时容易让步。"},
    "hesitant": {"name_cn": "犹豫", "desc": "缺乏安全感，需要被说服才愿意成交。"},
    "fraud": {"name_cn": "欺诈", "desc": "话术油滑，可能隐瞒物品缺陷或真伪。"},
    "expert": {"name_cn": "专家", "desc": "眼光毒辣，对价值和真伪非常敏感。"},
}

STAFF_TYPES = {
    "appraiser": {"name_cn": "鉴定师", "hire_cost": 800, "daily_salary": 100, "desc": "提高鉴定准确度，并降低专业鉴定费用。"},
    "restorer": {"name_cn": "修复师", "hire_cost": 1000, "daily_salary": 120, "desc": "有概率缩短修复工时，并降低修复失败风险。"},
    "marketer": {"name_cn": "宣传员", "hire_cost": 600, "daily_salary": 80, "desc": "提高每日客流，并吸引更高价值顾客。"},
    "guard": {"name_cn": "保安", "hire_cost": 500, "daily_salary": 60, "desc": "降低抢劫、盗窃和纠纷带来的损失。"},
}

SKILL_INFO = {
    "negotiation": {"name_cn": "谈判", "desc": "改善让步幅度和顾客耐心。"},
    "appraisal": {"name_cn": "鉴定", "desc": "提高估值准确度和识别赝品概率。"},
    "restoration": {"name_cn": "修复", "desc": "降低修复成本并提高修复质量。"},
    "charm": {"name_cn": "魅力", "desc": "改善顾客初始态度和耐心。"},
    "commerce": {"name_cn": "商业", "desc": "降低运营成本并提高出售收益。"},
}

FACILITY_INFO = {
    "showcase": {"name_cn": "展示柜", "base_cost": 1600, "desc": "增加可展示物品数量，并提高展示商品售价。"},
    "security": {"name_cn": "安全系统", "base_cost": 1400, "desc": "降低盗窃和法律纠纷损失。"},
    "appraisal_room": {"name_cn": "鉴定室", "base_cost": 1800, "desc": "降低鉴定费用，提高鉴定质量。"},
    "restoration_workshop": {"name_cn": "修复工坊", "base_cost": 2000, "desc": "降低修复费用，提高修复成功率。"},
    "storefront": {"name_cn": "店面", "base_cost": 2200, "desc": "提高客流和高稀有度物品出现率。"},
}

SHOP_UPGRADE_COSTS = {
    2: {"cost": 5000, "desc": "中型当铺：每日顾客流量增加，解锁古董与历史遗物中高级商品。"},
    3: {"cost": 15000, "desc": "豪华当铺：每日顾客流量大幅增加，吸引超高价值艺术品卖家。"},
    4: {"cost": 40000, "desc": "典当行财阀：解锁专属拍卖行信息，顾客上门质量提升。"},
    5: {"cost": 100000, "desc": "世纪大掌柜：极高声誉，解锁神级传说遗物。"},
}

RARITY_INFO = {
    "common": {"name_cn": "普通", "multiplier": 1.0},
    "rare": {"name_cn": "稀有", "multiplier": 1.6},
    "epic": {"name_cn": "史诗", "multiplier": 2.6},
    "legendary": {"name_cn": "传奇", "multiplier": 4.2},
}

CONDITION_UPGRADE = {"Poor": "Good", "Good": "Mint"}
CONDITION_MULTIPLIER = {"Poor": 0.72, "Good": 1.0, "Mint": 1.35}

APPRAISAL_METHODS = {
    "visual": {"name_cn": "目测初鉴", "cost_multiplier": 0.65, "accuracy_bonus": -0.10, "xp": 20, "desc": "速度快、费用最低，适合低价值物品；对高仿赝品不够稳。"},
    "standard": {"name_cn": "标准鉴定", "cost_multiplier": 1.15, "accuracy_bonus": 0.0, "xp": 35, "desc": "检查材质、工艺和市场记录，适合大多数交易。"},
    "forensic": {"name_cn": "深度鉴定", "cost_multiplier": 2.45, "accuracy_bonus": 0.14, "xp": 60, "desc": "显微痕迹、来源链和多项检测一起做，贵但最可靠。"},
}

REPAIR_METHODS = {
    "conservative": {"name_cn": "保守修复", "cost_multiplier": 0.85, "hours_delta": 1, "success_bonus": 0.10, "xp": 25, "desc": "少动原貌，耗时略长，失败风险低。"},
    "standard": {"name_cn": "标准修复", "cost_multiplier": 1.0, "hours_delta": 0, "success_bonus": 0.0, "xp": 25, "desc": "按常规工序处理，成本和速度均衡。"},
    "premium": {"name_cn": "高阶修复", "cost_multiplier": 1.55, "hours_delta": -1, "success_bonus": 0.14, "xp": 40, "desc": "使用更好的材料和工艺，费用高但更快更稳。"},
}


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def skill_template() -> Dict[str, Dict[str, int]]:
    return {key: {"level": 1, "xp": 0} for key in SKILL_INFO}


def facility_template() -> Dict[str, int]:
    return {key: 1 for key in FACILITY_INFO}


def customer_avatar_url(name: str, trait: str) -> str:
    seed = quote(f"{name}-{trait}", safe="")
    return f"https://api.dicebear.com/9.x/adventurer/svg?seed={seed}&radius=50&backgroundColor=1b1f26"


class Item:
    def __init__(
        self,
        name: str,
        category: str,
        condition: str,
        is_fake: bool,
        actual_value: int,
        description: str,
        rarity: str = "common",
        story: Optional[str] = None,
        hidden_attrs: Optional[List[str]] = None,
        repair_difficulty: int = 1,
        market_value: Optional[int] = None,
        item_id: Optional[str] = None,
        acquired_at: Optional[int] = None,
        last_trade_at: Optional[int] = None,
        showcase_price: Optional[int] = None,
        era: Optional[str] = None,
        damage_report: Optional[str] = None,
        special_effects: Optional[List[str]] = None,
        authentication_tips: Optional[List[str]] = None,
    ):
        self.id = item_id or str(uuid.uuid4())[:8]
        self.name = name
        self.category = category
        self.condition = condition
        self.is_fake = is_fake
        self.actual_value = max(1, int(actual_value))
        self.market_value = max(1, int(market_value if market_value is not None else actual_value))
        self.description = description
        self.rarity = rarity if rarity in RARITY_INFO else "common"
        self.story = story or f"{name} 的来历仍有些扑朔迷离，等待进一步鉴定。"
        self.hidden_attrs = hidden_attrs or []
        self.era = era or "年代不明"
        self.damage_report = damage_report or f"{condition} 成色，细节仍需专业检查。"
        self.special_effects = special_effects or []
        self.authentication_tips = authentication_tips or []
        self.repair_difficulty = clamp(int(repair_difficulty), 1, 5)

        self.appraised_value: Optional[int] = None
        self.is_appraised_fake: Optional[bool] = None
        self.appraisal_notes: List[str] = []
        self.purchase_price: Optional[int] = None
        self.selling_price: Optional[int] = None
        self.status = "stored"
        self.repair_finishes_at: Optional[float] = None
        self.repair_success_bonus = 0.0
        self.display_slot: Optional[int] = None
        self.acquired_at = int(acquired_at if acquired_at is not None else time.time())
        self.last_trade_at = last_trade_at
        self.showcase_price = showcase_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "condition": self.condition,
            "is_fake": self.is_fake,
            "actual_value": self.actual_value,
            "market_value": self.market_value,
            "appraised_value": self.appraised_value,
            "is_appraised_fake": self.is_appraised_fake,
            "appraisal_notes": self.appraisal_notes,
            "purchase_price": self.purchase_price,
            "selling_price": self.selling_price,
            "status": self.status,
            "description": self.description,
            "rarity": self.rarity,
            "rarity_cn": RARITY_INFO[self.rarity]["name_cn"],
            "story": self.story,
            "hidden_attrs": self.hidden_attrs,
            "era": self.era,
            "damage_report": self.damage_report,
            "special_effects": self.special_effects,
            "authentication_tips": self.authentication_tips,
            "repair_difficulty": self.repair_difficulty,
            "repair_finishes_at": self.repair_finishes_at,
            "repair_success_bonus": self.repair_success_bonus,
            "display_slot": self.display_slot,
            "acquired_at": self.acquired_at,
            "last_trade_at": self.last_trade_at,
            "showcase_price": self.showcase_price,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        item = cls(
            name=data.get("name", "未知物品"),
            category=data.get("category", "Misc"),
            condition=data.get("condition", "Good"),
            is_fake=bool(data.get("is_fake", False)),
            actual_value=int(data.get("actual_value", 100)),
            market_value=int(data.get("market_value", data.get("actual_value", 100))),
            description=data.get("description", ""),
            rarity=data.get("rarity", "common"),
            story=data.get("story"),
            hidden_attrs=list(data.get("hidden_attrs", [])),
            repair_difficulty=int(data.get("repair_difficulty", 1)),
            item_id=data.get("id"),
            acquired_at=data.get("acquired_at"),
            last_trade_at=data.get("last_trade_at"),
            showcase_price=data.get("showcase_price"),
            era=data.get("era"),
            damage_report=data.get("damage_report"),
            special_effects=list(data.get("special_effects", [])),
            authentication_tips=list(data.get("authentication_tips", [])),
        )
        item.appraised_value = data.get("appraised_value")
        item.is_appraised_fake = data.get("is_appraised_fake")
        item.appraisal_notes = list(data.get("appraisal_notes", []))
        item.purchase_price = data.get("purchase_price")
        item.selling_price = data.get("selling_price")
        item.status = data.get("status", "stored")
        item.repair_success_bonus = float(data.get("repair_success_bonus", 0.0))
        finishes_at = data.get("repair_finishes_at")
        if finishes_at is not None:
            item.repair_finishes_at = float(finishes_at)
        elif item.status == "repairing":
            legacy_days = int(data.get("repair_days_remaining", 0))
            legacy_hours = max(1, min(6, legacy_days if legacy_days > 0 else 1))
            item.repair_finishes_at = time.time() + legacy_hours * 3600
        else:
            item.repair_finishes_at = None
        item.display_slot = data.get("display_slot")
        return item


class Customer:
    def __init__(
        self,
        name: str,
        trait: str,
        role: str,
        item: Item,
        shop_level: int,
        marketer_active: bool,
        age: Optional[int] = None,
        appearance: Optional[str] = None,
        backstory: Optional[str] = None,
        fraud_intent: Optional[bool] = None,
        avatar_url: Optional[str] = None,
        dialogue_history: Optional[List[Dict[str, str]]] = None,
        patience: Optional[int] = None,
        current_offer: Optional[int] = None,
        initial_offer: Optional[int] = None,
        limit_price: Optional[int] = None,
        transaction_prefs: Optional[List[str]] = None,
        persuasion_points: Optional[List[str]] = None,
    ):
        self.name = name
        self.trait = trait if trait in CUSTOMER_TRAITS else "hesitant"
        self.role = role if role in ["seller", "buyer"] else "seller"
        self.item = item
        self.age = age or random.randint(22, 72)
        self.appearance = appearance or random.choice(["穿着旧呢大衣", "拎着磨旧皮箱", "戴着金边眼镜", "神色匆忙", "衣着体面"])
        self.backstory = backstory or self._default_backstory()
        self.fraud_intent = bool(fraud_intent if fraud_intent is not None else (item.is_fake and self.trait in ["fraud", "hardball"]))
        self.transaction_prefs = transaction_prefs or self._default_transaction_prefs()
        self.persuasion_points = persuasion_points or self._default_persuasion_points()
        self.avatar_url = avatar_url or customer_avatar_url(self.name, self.trait)
        self.dialogue_history = dialogue_history or []

        base_patience = 5 + (1 if marketer_active else 0) + (1 if shop_level >= 3 else 0)
        if self.trait == "hardball":
            base_patience -= 1
        elif self.trait in ["eager", "hesitant"]:
            base_patience += 1
        self.patience = clamp(int(patience if patience is not None else base_patience), 1, 7)

        calculated_limit, calculated_offer = self._calculate_prices()
        self.limit_price = int(limit_price if limit_price is not None else calculated_limit)
        self.current_offer = int(current_offer if current_offer is not None else calculated_offer)
        self.initial_offer = int(initial_offer if initial_offer is not None else self.current_offer)

    def _default_backstory(self) -> str:
        if self.role == "seller":
            return f"{self.name} 说这件 {self.item.name} 是家里旧物，急需换成现金。"
        return f"{self.name} 最近在搜罗 {self.item.category} 藏品，听说你的铺子里有门道。"

    def _default_transaction_prefs(self) -> List[str]:
        if self.trait == "eager":
            return ["希望尽快成交", "更看重现金到手速度"]
        if self.trait == "hardball":
            return ["不喜欢被明显压价", "需要看到专业依据"]
        if self.trait == "fraud":
            return ["回避细节追问", "偏好快速成交"]
        return ["愿意听取来源与行情分析", "对礼貌沟通更有耐心"]

    def _default_persuasion_points(self) -> List[str]:
        points = {
            "hardball": ["用市场行情说服", "强调长期合作"],
            "eager": ["承诺立即付款", "减少流程拖延"],
            "hesitant": ["解释鉴定依据", "给出安全感"],
            "fraud": ["追问来源细节", "提出专业鉴定"],
            "expert": ["引用成色和稀缺度", "尊重对方专业判断"],
        }
        return points.get(self.trait, ["保持礼貌", "给出合理理由"])

    def _calculate_prices(self) -> tuple[int, int]:
        perceived_value = self.item.market_value
        if self.item.is_fake and self.role == "seller":
            perceived_value = max(self.item.market_value, self.item.actual_value * 7)

        if self.role == "seller":
            ratios = {
                "hardball": (0.88, 1.42),
                "eager": (0.58, 1.12),
                "hesitant": (0.68, 1.22),
                "fraud": (0.82, 1.55),
                "expert": (0.80, 1.25),
            }
        else:
            ratios = {
                "hardball": (0.85, 0.50),
                "eager": (1.18, 0.78),
                "hesitant": (1.05, 0.68),
                "fraud": (0.78, 0.45),
                "expert": (1.05, 0.82),
            }
            perceived_value = self.item.actual_value

        limit_ratio, start_ratio = ratios[self.trait]
        return max(5, int(perceived_value * limit_ratio)), max(10, int(perceived_value * start_ratio))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trait": self.trait,
            "trait_cn": CUSTOMER_TRAITS[self.trait]["name_cn"],
            "trait_desc": CUSTOMER_TRAITS[self.trait]["desc"],
            "role": self.role,
            "item": self.item.to_dict(),
            "age": self.age,
            "appearance": self.appearance,
            "backstory": self.backstory,
            "fraud_intent": self.fraud_intent,
            "transaction_prefs": self.transaction_prefs,
            "persuasion_points": self.persuasion_points,
            "avatar_url": self.avatar_url,
            "patience": self.patience,
            "current_offer": self.current_offer,
            "initial_offer": self.initial_offer,
            "limit_price": self.limit_price,
            "dialogue_history": self.dialogue_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Customer":
        return cls(
            name=data.get("name", "无名顾客"),
            trait=data.get("trait", "hesitant"),
            role=data.get("role", "seller"),
            item=Item.from_dict(data.get("item", {})),
            shop_level=1,
            marketer_active=False,
            age=data.get("age"),
            appearance=data.get("appearance"),
            backstory=data.get("backstory"),
            fraud_intent=data.get("fraud_intent"),
            avatar_url=data.get("avatar_url"),
            dialogue_history=list(data.get("dialogue_history", [])),
            patience=data.get("patience"),
            current_offer=data.get("current_offer"),
            initial_offer=data.get("initial_offer"),
            limit_price=data.get("limit_price"),
            transaction_prefs=list(data.get("transaction_prefs") or []),
            persuasion_points=list(data.get("persuasion_points") or []),
        )


class GameStateManager:
    def __init__(self, initialize: bool = True):
        self.cash = 10000
        self.day = 1
        self.shop_level = 1
        self.inventory: List[Item] = []
        self.sold_items: List[Item] = []
        self.transaction_log: List[Dict[str, Any]] = []
        self.staff: Dict[str, bool] = {key: False for key in STAFF_TYPES}
        self.skills = skill_template()
        self.facilities = facility_template()
        self.loan = {"principal": 0, "interest_rate": 0.02}
        self.tax = {"next_due_day": 7, "rate": 0.08, "last_paid": 0}
        self.market_trends: Dict[str, float] = {category: 1.0 for category in ITEM_TEMPLATES}
        self.pending_event: Optional[Dict[str, Any]] = None
        self.shop_name = "无名当铺"
        self.reputation = 100
        self.total_profit = 0
        self.successful_trades = 0
        self.positive_reviews = 0
        self.ranking_badge: Optional[str] = None
        self.ranking_reward_bonus = 0
        self.active_customer: Optional[Customer] = None
        self.daily_customer_queue: List[Customer] = []
        self.customers_served_today = 0
        self.total_customers_today = 3
        self.daily_summary: Dict[str, Any] = {}
        self.day_ended = False

        if initialize:
            self.initialize_day()

    def initialize_day(self):
        self.day_ended = False
        self.customers_served_today = 0
        self.active_customer = None
        base_traffic = 2 + self.shop_level + self.facilities["storefront"] // 2
        if self.staff["marketer"]:
            base_traffic += random.randint(1, 2)
        self.total_customers_today = max(2, base_traffic)
        self.daily_customer_queue = []
        self.daily_summary = {
            "day": self.day,
            "revenue": 0,
            "salaries": 0,
            "upgrades": 0,
            "operating_cost": 0,
            "loan_interest": 0,
            "tax": 0,
            "events": [],
            "starting_cash": self.cash,
            "ending_cash": self.cash,
            "net_profit": 0,
        }
        self._refresh_market_trends()

    async def async_initialize_day(self, ai_client):
        import asyncio

        self.daily_customer_queue = []
        tasks = [self.generate_random_customer_async(ai_client) for _ in range(self.total_customers_today)]
        self.daily_customer_queue.extend(await asyncio.gather(*tasks))
        self.active_customer = self.daily_customer_queue.pop(0) if self.daily_customer_queue else None

    def initialize_day_fast(self):
        """Initialize a playable day immediately with local templates."""
        self.daily_customer_queue = [self.generate_random_customer() for _ in range(self.total_customers_today)]
        self.active_customer = self.daily_customer_queue.pop(0) if self.daily_customer_queue else None

    def generate_random_customer(self) -> Customer:
        name = random.choice(CUSTOMER_NAMES)
        trait = random.choice(list(CUSTOMER_TRAITS.keys()))
        saleable_items = [i for i in self.inventory if i.status in ["stored", "displayed"]]
        role = "buyer" if saleable_items and random.random() < 0.45 else "seller"

        if role == "seller":
            category = random.choice(list(ITEM_TEMPLATES.keys()))
            template = random.choice(ITEM_TEMPLATES[category])
            item = self._generate_item_from_template(template, category)
        else:
            displayed = [i for i in saleable_items if i.status == "displayed"]
            item = random.choice(displayed or saleable_items)

        customer = Customer(name=name, trait=trait, role=role, item=item, shop_level=self.shop_level, marketer_active=self.staff["marketer"])
        customer.patience = clamp(customer.patience + self.skills["charm"]["level"] // 2, 1, 8)
        return customer

    async def async_advance_to_next_day(self, ai_client):
        import asyncio

        if self.pending_event:
            return {"error": "还有未处理的随机事件，请先做出选择。"}
        self.day += 1
        self.initialize_day()
        try:
            await asyncio.wait_for(self.async_initialize_day(ai_client), timeout=3.0)
            return {"success": True, "message": "新的一天开始了。"}
        except Exception:
            self.initialize_day_fast()
            return {"success": True, "message": "新的一天开始了。AI 预生成较慢，已先用本地顾客开门。", "fallback": True}

    def _refresh_market_trends(self):
        for category in ITEM_TEMPLATES:
            drift = random.uniform(-0.12, 0.14)
            self.market_trends[category] = round(clamp(int((1.0 + drift) * 100), 78, 135) / 100, 2)

    def _choose_rarity(self) -> str:
        boost = self.shop_level + self.facilities["storefront"] + (1 if self.staff["marketer"] else 0)
        weights = {
            "common": max(35, 78 - boost * 5),
            "rare": 18 + boost * 3,
            "epic": 3 + boost,
            "legendary": max(1, boost - 2),
        }
        return random.choices(list(weights.keys()), weights=list(weights.values()), k=1)[0]

    def _generate_item_from_template(self, template: Dict[str, Any], category: str, ai_item: Optional[Dict[str, Any]] = None) -> Item:
        ai_item = ai_item or {}
        condition = random.choices(["Poor", "Good", "Mint"], weights=[35, 45, 20], k=1)[0]
        raw_value = template["mint_val"] if condition == "Mint" else template["good_val"] if condition == "Good" else template["poor_val"]
        rarity = self._choose_rarity()
        value = int(raw_value * RARITY_INFO[rarity]["multiplier"] * random.uniform(0.85, 1.16))
        is_fake = random.random() < template["fake_rate"]
        if is_fake:
            value = max(15, int(value * random.uniform(0.10, 0.22)))
        market_value = int(value * self.market_trends.get(category, 1.0))
        hidden_attrs = ai_item.get("hidden_attrs") if isinstance(ai_item.get("hidden_attrs"), list) else random.sample(
            ["有隐蔽修补痕迹", "附带可疑来源传闻", "材质检测点较多", "可能存在名人关联", "同类市场近期波动明显"],
            k=random.randint(1, 2),
        )
        desc = str(ai_item.get("desc") or template["desc"])
        story = str(ai_item.get("story") or f"{desc} 据说几经转手，上一任藏家留下了含糊的来源说明。")
        return Item(
            name=str(ai_item.get("name") or template["name"]),
            category=category,
            condition=condition,
            is_fake=is_fake,
            actual_value=value,
            market_value=market_value,
            description=desc,
            rarity=rarity,
            story=story,
            hidden_attrs=[str(value) for value in hidden_attrs],
            era=str(ai_item.get("era") or random.choice(["民国时期", "20世纪末", "清末民初", "近现代", "年代仍待考证"])),
            damage_report=str(ai_item.get("damage_report") or f"{condition} 成色，局部磨损与包浆需要进一步确认。"),
            special_effects=[str(value) for value in (ai_item.get("special_effects") if isinstance(ai_item.get("special_effects"), list) else ["适合展示吸引收藏客"])],
            authentication_tips=[str(value) for value in (ai_item.get("authentication_tips") if isinstance(ai_item.get("authentication_tips"), list) else ["观察材质老化", "核对款识与来源"])],
            repair_difficulty=random.randint(1, 5),
        )

    async def generate_random_customer_async(self, ai_client) -> Customer:
        name = await ai_client.generate_random_content("customer_name") or random.choice(CUSTOMER_NAMES)
        trait = random.choice(list(CUSTOMER_TRAITS.keys()))

        saleable_items = [i for i in self.inventory if i.status in ["stored", "displayed"]]
        role = "buyer" if saleable_items and random.random() < 0.45 else "seller"

        if role == "seller":
            category = random.choice(list(ITEM_TEMPLATES.keys()))
            template = random.choice(ITEM_TEMPLATES[category])
            preview_condition = random.choice(["Poor", "Good", "Mint"])
            preview_rarity = self._choose_rarity()
            ai_item = await ai_client.generate_deep_item(category, preview_rarity, preview_condition, template["good_val"])
            if not ai_item:
                ai_item = await ai_client.generate_item_details(category)
            item = self._generate_item_from_template(template, category, ai_item)
        else:
            displayed = [i for i in saleable_items if i.status == "displayed"]
            item = random.choice(displayed or saleable_items)

        profile = await ai_client.generate_customer_profile(role, trait, item.name, item.category)
        customer = Customer(
            name=str(profile.get("name") or name),
            trait=trait,
            role=role,
            item=item,
            shop_level=self.shop_level,
            marketer_active=self.staff["marketer"],
            age=profile.get("age"),
            appearance=profile.get("appearance"),
            backstory=profile.get("backstory"),
            fraud_intent=profile.get("fraud_intent"),
            transaction_prefs=[str(value) for value in profile.get("transaction_prefs", [])] if isinstance(profile.get("transaction_prefs"), list) else None,
            persuasion_points=[str(value) for value in profile.get("persuasion_points", [])] if isinstance(profile.get("persuasion_points"), list) else None,
        )
        charm_bonus = self.skills["charm"]["level"] // 2
        customer.patience = clamp(customer.patience + charm_bonus, 1, 8)
        return customer

    def select_next_customer(self) -> bool:
        self.customers_served_today += 1
        if self.daily_customer_queue:
            self.active_customer = self.daily_customer_queue.pop(0)
            return True
        self.active_customer = None
        return False

    def add_skill_xp(self, skill: str, amount: int):
        if skill not in self.skills:
            return
        data = self.skills[skill]
        data["xp"] += max(0, amount)
        while data["level"] < 10 and data["xp"] >= data["level"] * 100:
            data["xp"] -= data["level"] * 100
            data["level"] += 1

    def appraise_active_item(self, method: str = "standard", ai_notes: Optional[List[str]] = None) -> Dict[str, Any]:
        if not self.active_customer:
            return {"error": "当前没有顾客。"}
        method_info = APPRAISAL_METHODS.get(method, APPRAISAL_METHODS["standard"])
        item = self.active_customer.item
        facility_level = self.facilities["appraisal_room"]
        skill_level = self.skills["appraisal"]["level"]
        base_cost = max(120, int(item.market_value * 0.06))
        discount = 0.08 * (facility_level - 1) + (0.35 if self.staff["appraiser"] else 0)
        cost = max(80, int(base_cost * method_info["cost_multiplier"] * (1 - min(0.65, discount))))
        if self.cash < cost:
            return {"error": f"鉴定资金不足，需要 ${cost}。"}

        self.cash -= cost
        self.daily_summary["upgrades"] += cost
        accuracy = min(0.98, max(0.35, 0.65 + skill_level * 0.035 + facility_level * 0.04 + (0.15 if self.staff["appraiser"] else 0) + method_info["accuracy_bonus"]))
        detects_fake = item.is_fake and random.random() < accuracy
        item.is_appraised_fake = detects_fake if item.is_fake else False
        error_margin = max(0.03, 0.24 - skill_level * 0.015 - facility_level * 0.02 - max(0, method_info["accuracy_bonus"]))
        item.appraised_value = max(10, int(item.actual_value * random.uniform(1 - error_margin, 1 + error_margin)))
        fallback_notes = [
            f"鉴定方法：{method_info['name_cn']}。{method_info['desc']}",
            f"观察成色：{item.condition}，修复难度 {item.repair_difficulty}/5。",
            f"市场趋势系数：{self.market_trends.get(item.category, 1.0):.2f}。",
            f"年代线索：{item.era}；损坏记录：{item.damage_report}",
            "鉴定结论仍受技能和设备影响。" if item.is_fake and not detects_fake else "关键鉴定点已记录。",
        ]
        item.appraisal_notes = ai_notes or fallback_notes
        self.add_skill_xp("appraisal", int(method_info["xp"]))
        return {"success": True, "cost": cost, "method": method, "method_name": method_info["name_cn"], "is_fake": item.is_appraised_fake, "appraised_value": item.appraised_value, "notes": item.appraisal_notes}

    async def async_appraise_active_item(self, ai_client, method: str = "standard") -> Dict[str, Any]:
        result = self.appraise_active_item(method)
        if "error" in result or not self.active_customer:
            return result
        item = self.active_customer.item
        ai_notes = await ai_client.generate_appraisal_notes(item.to_dict(), method, bool(result["is_fake"]), int(result["appraised_value"]))
        if ai_notes:
            item.appraisal_notes = ai_notes
            result["notes"] = ai_notes
        return result

    def get_item(self, item_id: str) -> Optional[Item]:
        return next((item for item in self.inventory if item.id == item_id), None)

    def active_buyer_wants_item(self, item_id: str) -> bool:
        return bool(
            self.active_customer
            and self.active_customer.role == "buyer"
            and self.active_customer.item.id == item_id
        )

    def display_capacity(self) -> int:
        return 2 + self.facilities["showcase"] * 2

    def display_item(self, item_id: str) -> Dict[str, Any]:
        item = self.get_item(item_id)
        if not item:
            return {"error": "未找到该物品。"}
        if item.status not in ["stored", "displayed"]:
            return {"error": "该物品当前不能展示。"}
        displayed = [i for i in self.inventory if i.status == "displayed"]
        if item.status != "displayed" and len(displayed) >= self.display_capacity():
            return {"error": "展示柜已满，请升级展示柜或下架其他物品。"}
        item.status = "displayed"
        item.display_slot = displayed.index(item) + 1 if item in displayed else len(displayed) + 1
        return {"success": True, "message": f"【{item.name}】已摆入展示柜。"}

    def undisplay_item(self, item_id: str) -> Dict[str, Any]:
        item = self.get_item(item_id)
        if not item:
            return {"error": "未找到该物品。"}
        if item.status != "displayed":
            return {"error": "该物品并未展示。"}
        item.status = "stored"
        item.display_slot = None
        item.showcase_price = None
        return {"success": True, "message": f"【{item.name}】已收入仓库。"}

    def start_repair(self, item_id: str, method: str = "standard", ai_notes: Optional[List[str]] = None) -> Dict[str, Any]:
        item = self.get_item(item_id)
        if not item:
            return {"error": "未找到该物品。"}
        if item.status not in ["stored", "displayed"]:
            return {"error": "该物品当前不能修复。"}
        if item.condition == "Mint":
            return {"error": "该物品已经是最佳成色。"}

        method_info = REPAIR_METHODS.get(method, REPAIR_METHODS["standard"])
        facility_level = self.facilities["restoration_workshop"]
        skill_level = self.skills["restoration"]["level"]
        cost = max(60, int(item.market_value * (0.08 + item.repair_difficulty * 0.015) * (1 - 0.05 * (facility_level - 1) - 0.03 * (skill_level - 1))))
        if self.staff["restorer"]:
            cost = int(cost * 0.75)
        cost = max(30, int(cost * method_info["cost_multiplier"]))
        if self.cash < cost:
            return {"error": f"修复资金不足，需要 ${cost}。"}

        self.cash -= cost
        item.status = "repairing"
        item.display_slot = None
        repair_hours = self._repair_duration_hours(item, facility_level, method_info)
        if self.staff["restorer"] and random.random() < 0.35:
            repair_hours = max(1, repair_hours - 1)
        item.repair_finishes_at = time.time() + repair_hours * 3600
        item.repair_success_bonus = float(method_info["success_bonus"])
        notes = ai_notes or [
            f"修复方案：{method_info['name_cn']}。{method_info['desc']}",
            f"损坏记录：{item.damage_report}",
            f"预计 {repair_hours} 小时完成，工坊等级 Lv.{facility_level}。",
        ]
        item.appraisal_notes = list(item.appraisal_notes) + notes
        self.daily_summary["upgrades"] += cost
        self.add_skill_xp("restoration", int(method_info["xp"]))
        return {
            "success": True,
            "message": f"【{item.name}】已按【{method_info['name_cn']}】送入修复工坊，预计 {repair_hours} 小时完成。",
            "cost": cost,
            "method": method,
            "method_name": method_info["name_cn"],
            "repair_hours": repair_hours,
            "notes": notes,
        }

    async def async_start_repair(self, ai_client, item_id: str, method: str = "standard") -> Dict[str, Any]:
        item = self.get_item(item_id)
        if not item:
            return {"error": "未找到该物品。"}
        method_info = REPAIR_METHODS.get(method, REPAIR_METHODS["standard"])
        facility_level = self.facilities["restoration_workshop"]
        skill_level = self.skills["restoration"]["level"]
        preview_cost = max(60, int(item.market_value * (0.08 + item.repair_difficulty * 0.015) * (1 - 0.05 * (facility_level - 1) - 0.03 * (skill_level - 1))))
        if self.staff["restorer"]:
            preview_cost = int(preview_cost * 0.75)
        preview_cost = max(30, int(preview_cost * method_info["cost_multiplier"]))
        preview_hours = self._repair_duration_hours(item, facility_level, method_info)
        ai_notes = await ai_client.generate_repair_notes(item.to_dict(), method, preview_hours, preview_cost)
        return self.start_repair(item_id, method, ai_notes)

    def sell_item(self, item_id: str) -> Dict[str, Any]:
        item = self.get_item(item_id)
        if not item:
            return {"error": "未找到该物品。"}
        if item.status not in ["stored", "displayed"]:
            return {"error": "该物品当前不能直接出售。"}

        active_buyer_waiting = self.active_buyer_wants_item(item_id)
        active_buyer_name = self.active_customer.name if active_buyer_waiting and self.active_customer else ""
        commerce = self.skills["commerce"]["level"]
        showcase_bonus = 0.04 * self.facilities["showcase"] if item.status == "displayed" else 0
        rarity_bonus = {"common": 0.0, "rare": 0.06, "epic": 0.12, "legendary": 0.2}[item.rarity]
        multiplier = random.uniform(0.72, 0.92) + commerce * 0.025 + showcase_bonus + rarity_bonus
        price = max(10, int(item.market_value * multiplier))
        self.cash += price
        item.selling_price = price
        item.status = "sold"
        item.display_slot = None
        item.showcase_price = None
        self.inventory = [i for i in self.inventory if i.id != item_id]
        self.sold_items.append(item)
        self.daily_summary["revenue"] += price
        self.transaction_log.append({"day": self.day, "type": "direct_sell", "item": item.name, "amount": price})
        self.add_skill_xp("commerce", 35)
        message = f"你通过渠道卖出了【{item.name}】，收入 ${price}。"
        if active_buyer_waiting:
            self.select_next_customer()
            message += f" {active_buyer_name}看中的货已经售出，只好离开店里。"
        return {"success": True, "message": message, "price": price}

    def deal(self) -> Dict[str, Any]:
        if not self.active_customer:
            return {"error": "当前没有正在谈判的顾客。"}
        customer = self.active_customer
        item = customer.item
        price = customer.current_offer

        if customer.role == "seller":
            if self.cash < price:
                return {"error": "资金余额不足，无法完成这笔交易。"}
            self.cash -= price
            item.purchase_price = price
            item.acquired_at = int(time.time())
            item.status = "stored"
            self.inventory.append(item)
            self.daily_summary["revenue"] -= price
            message = "交易成功！你买下了该物品。"
            tx_type = "buy"
        else:
            inventory_item = self.get_item(item.id)
            if not inventory_item or inventory_item.status not in ["stored", "displayed"]:
                return {"error": "这件物品已不在店内，无法继续出售给顾客。"}
            item = inventory_item
            self.cash += price
            item.selling_price = price
            item.status = "sold"
            item.display_slot = None
            item.showcase_price = None
            self.inventory = [i for i in self.inventory if i.id != item.id]
            self.sold_items.append(item)
            self.daily_summary["revenue"] += price
            message = "交易成功！你卖出了该物品。"
            tx_type = "sell"

        dialogue = "合作愉快，这笔买卖就这么定了！"
        customer.dialogue_history.append({"role": "customer", "content": dialogue})
        self.transaction_log.append({"day": self.day, "type": tx_type, "item": item.name, "amount": -price if tx_type == "buy" else price})
        self.add_skill_xp("negotiation", 25)
        self.successful_trades += 1
        self.positive_reviews += 1 if random.random() < 0.75 else 0
        self.reputation += 1
        if tx_type == "sell":
            self.add_skill_xp("commerce", 20)
        self.select_next_customer()
        return {"success": True, "message": message, "price_transacted": price, "dialogue": dialogue}

    def reject(self) -> Dict[str, Any]:
        if not self.active_customer:
            return {"error": "没有活跃的顾客。"}
        self.select_next_customer()
        return {"success": True, "message": "已拒绝交易。下一位顾客！"}

    def hire_staff(self, staff_type: str) -> Dict[str, Any]:
        if staff_type not in STAFF_TYPES:
            return {"error": "未知的职员类型。"}
        if self.staff[staff_type]:
            return {"error": "你已经雇佣了该岗位的员工！"}
        cost = STAFF_TYPES[staff_type]["hire_cost"]
        if self.cash < cost:
            return {"error": f"招聘资金不足，需要花费 ${cost}。"}
        self.cash -= cost
        self.staff[staff_type] = True
        self.daily_summary["upgrades"] += cost
        return {"success": True, "message": f"成功雇佣了一名【{STAFF_TYPES[staff_type]['name_cn']}】！"}

    def fire_staff(self, staff_type: str) -> Dict[str, Any]:
        if staff_type not in self.staff:
            return {"error": "未知的职员类型。"}
        if not self.staff[staff_type]:
            return {"error": "你没有雇佣这个岗位的员工。"}
        self.staff[staff_type] = False
        return {"success": True, "message": f"已解雇【{STAFF_TYPES[staff_type]['name_cn']}】。"}

    def upgrade_shop(self) -> Dict[str, Any]:
        next_lvl = self.shop_level + 1
        if next_lvl > 5:
            return {"error": "你的店铺等级已达到上限！"}
        cost = SHOP_UPGRADE_COSTS[next_lvl]["cost"]
        if self.cash < cost:
            return {"error": f"店铺升级资金不足，需要 ${cost}。"}
        self.cash -= cost
        self.shop_level = next_lvl
        self.daily_summary["upgrades"] += cost
        return {"success": True, "message": f"店铺升级成功！当前等级：Lv.{self.shop_level} ({SHOP_UPGRADE_COSTS[next_lvl]['desc']})"}

    def facility_upgrade_cost(self, facility: str) -> Optional[int]:
        if facility not in FACILITY_INFO:
            return None
        level = self.facilities[facility]
        if level >= 5:
            return None
        return int(FACILITY_INFO[facility]["base_cost"] * (level ** 1.65))

    def upgrade_facility(self, facility: str) -> Dict[str, Any]:
        if facility not in FACILITY_INFO:
            return {"error": "未知设施类型。"}
        cost = self.facility_upgrade_cost(facility)
        if cost is None:
            return {"error": "该设施已达到最高等级。"}
        if self.cash < cost:
            return {"error": f"资金不足，需要 ${cost}。"}
        self.cash -= cost
        self.facilities[facility] += 1
        self.daily_summary["upgrades"] += cost
        return {"success": True, "message": f"【{FACILITY_INFO[facility]['name_cn']}】升级到 Lv.{self.facilities[facility]}。"}

    def borrow_loan(self, amount: int) -> Dict[str, Any]:
        amount = int(amount)
        max_principal = 20000 + self.shop_level * 8000
        if amount <= 0:
            return {"error": "借款金额必须大于 0。"}
        if self.loan["principal"] + amount > max_principal:
            return {"error": f"贷款额度不足，当前最高可欠 ${max_principal}。"}
        self.loan["principal"] += amount
        self.cash += amount
        return {"success": True, "message": f"银行放款 ${amount}，每日利息按 {self.loan['interest_rate'] * 100:.1f}% 计。"}

    def repay_loan(self, amount: int) -> Dict[str, Any]:
        amount = min(int(amount), self.loan["principal"])
        if amount <= 0:
            return {"error": "没有可偿还的贷款。"}
        if self.cash < amount:
            return {"error": "现金不足，无法还款。"}
        self.cash -= amount
        self.loan["principal"] -= amount
        return {"success": True, "message": f"已偿还贷款 ${amount}。"}

    def _repair_duration_hours(self, item: Item, facility_level: int, method_info: Dict[str, Any]) -> int:
        hours_delta = int(method_info.get("hours_delta", method_info.get("days_delta", 0)))
        return max(1, min(6, item.repair_difficulty - facility_level // 2 + hours_delta))

    def process_due_repairs(self) -> List[str]:
        return self._process_repairs()

    def _process_repairs(self) -> List[str]:
        events: List[str] = []
        now = time.time()
        for item in list(self.inventory):
            if item.status != "repairing":
                continue
            finishes_at = getattr(item, "repair_finishes_at", None)
            if not finishes_at or now < finishes_at:
                continue
            success_chance = min(0.97, 0.55 + self.skills["restoration"]["level"] * 0.035 + self.facilities["restoration_workshop"] * 0.06 + (0.12 if self.staff["restorer"] else 0) + float(getattr(item, "repair_success_bonus", 0.0)))
            old_condition = item.condition
            if random.random() < success_chance:
                item.condition = CONDITION_UPGRADE.get(item.condition, item.condition)
                item.actual_value = int(item.actual_value * (1.45 if item.condition == "Good" else 1.7))
                item.market_value = int(item.market_value * (1.35 if item.condition == "Good" else 1.55))
                events.append(f"修复完成：【{item.name}】成色从 {old_condition} 提升到 {item.condition}。")
                self.add_skill_xp("restoration", 40)
            else:
                item.actual_value = max(10, int(item.actual_value * 0.92))
                events.append(f"修复意外：【{item.name}】修复失败，价值略有受损。")
            item.status = "stored"
            item.repair_finishes_at = None
            item.repair_success_bonus = 0.0
        return events

    def _generate_pending_event(self) -> Optional[Dict[str, Any]]:
        if random.random() > 0.42:
            return None
        event_type = random.choice(["theft", "scam", "celebrity", "market", "legal", "staff"])
        if event_type == "theft":
            return {
                "id": str(uuid.uuid4())[:8],
                "title": "夜间异响",
                "description": "打烊后有人在后门徘徊，似乎盯上了你的仓库。",
                "choices": [
                    {"id": "guard", "label": "让保安和安全系统处理", "effect": "安全等级越高，损失越低。"},
                    {"id": "cash", "label": "花钱请街坊巡夜", "effect": "支付一笔费用，但基本避免损失。"},
                ],
            }
        if event_type == "scam":
            return {
                "id": str(uuid.uuid4())[:8],
                "title": "可疑典当",
                "description": "一名顾客留下了过于完美的来源故事，但票据编号和物品磨损对不上。",
                "choices": [
                    {"id": "inspect", "label": "追加鉴定并追问来源", "effect": "花费少量现金，可能避免诈骗并获得鉴定经验。"},
                    {"id": "decline", "label": "直接谢绝这笔买卖", "effect": "稳妥避险，但可能错过机会。"},
                ],
            }
        if event_type == "celebrity":
            return {
                "id": str(uuid.uuid4())[:8],
                "title": "名人来访",
                "description": "一位低调的收藏节目主持人想来店里拍摄一段素材。",
                "choices": [
                    {"id": "host", "label": "热情接待", "effect": "可能提高声望和现金收入。"},
                    {"id": "private", "label": "保持低调", "effect": "获得少量稳定收益。"},
                ],
            }
        if event_type == "market":
            return {
                "id": str(uuid.uuid4())[:8],
                "title": "市场风向变化",
                "description": "拍卖圈传出新消息，某一类藏品可能短期升温。",
                "choices": [
                    {"id": "follow", "label": "跟进市场热点", "effect": "随机分类市场系数上升。"},
                    {"id": "ignore", "label": "维持稳健经营", "effect": "获得商业经验。"},
                ],
            }
        if event_type == "legal":
            return {
                "id": str(uuid.uuid4())[:8],
                "title": "来源质疑",
                "description": "有人质疑你的一件藏品来源不清，需要尽快处理。",
                "choices": [
                    {"id": "lawyer", "label": "请律师和鉴定师处理", "effect": "花费较高，但风险更低。"},
                    {"id": "settle", "label": "私下和解", "effect": "花费中等，可能影响声望。"},
                ],
            }
        return {
            "id": str(uuid.uuid4())[:8],
            "title": "员工小问题",
            "description": "店员之间因为排班和提成产生了争执。",
            "choices": [
                {"id": "bonus", "label": "发放小额奖金", "effect": "花费现金，提升团队稳定。"},
                {"id": "talk", "label": "亲自调解", "effect": "获得魅力经验。"},
            ],
        }

    def _normalize_ai_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not event or not isinstance(event.get("choices"), list):
            return None
        choices = []
        for index, choice in enumerate(event["choices"][:2]):
            if not isinstance(choice, dict):
                continue
            choices.append(
                {
                    "id": str(choice.get("id") or f"choice_{index + 1}"),
                    "label": str(choice.get("label") or "谨慎处理"),
                    "effect": str(choice.get("effect") or "结果取决于当铺当前状态。"),
                    "cash_delta": int(choice.get("cash_delta") or 0),
                    "reputation_delta": int(choice.get("reputation_delta") or 0),
                    "skill": choice.get("skill") if choice.get("skill") in SKILL_INFO else None,
                    "skill_xp": int(choice.get("skill_xp") or 0),
                }
            )
        if len(choices) < 2:
            return None
        return {
            "id": str(uuid.uuid4())[:8],
            "title": str(event.get("title") or "突发事件"),
            "description": str(event.get("description") or "当铺里发生了一件需要你判断的事。"),
            "type": str(event.get("type") or "ai"),
            "ai_generated": True,
            "choices": choices,
        }

    async def async_end_day(self, ai_client) -> Dict[str, Any]:
        summary = self.end_day()
        if "error" in summary:
            return summary
        if self.pending_event:
            ai_event = self._normalize_ai_event(
                await ai_client.generate_random_event(
                    {
                        "shop_level": self.shop_level,
                        "cash": self.cash,
                        "day": self.day,
                        "reputation": self.reputation,
                    }
                )
            )
            if ai_event:
                self.pending_event = ai_event
                if self.daily_summary["events"] and self.daily_summary["events"][-1].startswith("待处理事件："):
                    self.daily_summary["events"][-1] = f"待处理事件：{ai_event['title']}。"
        return self.daily_summary

    def resolve_event(self, choice_id: str) -> Dict[str, Any]:
        if not self.pending_event:
            return {"error": "当前没有待处理事件。"}
        event = self.pending_event
        title = event["title"]
        message = ""
        if event.get("ai_generated"):
            choice = next((item for item in event.get("choices", []) if item.get("id") == choice_id), None)
            if not choice:
                return {"error": "未知的事件选择。"}
            cash_delta = int(choice.get("cash_delta") or 0)
            reputation_delta = int(choice.get("reputation_delta") or 0)
            self.cash += cash_delta
            self.reputation += reputation_delta
            if cash_delta > 0:
                self.daily_summary["revenue"] += cash_delta
            skill = choice.get("skill")
            if skill in SKILL_INFO:
                self.add_skill_xp(skill, int(choice.get("skill_xp") or 0))
            message = f"{choice.get('label')}：{choice.get('effect')}"
            if cash_delta:
                message += f"，现金{'+' if cash_delta > 0 else ''}${cash_delta}"
            if reputation_delta:
                message += f"，声誉{'+' if reputation_delta > 0 else ''}{reputation_delta}"
            self.daily_summary["events"].append(f"{title}：{message}")
            self.pending_event = None
            self.daily_summary["ending_cash"] = self.cash
            self.daily_summary["net_profit"] = self.cash - self.daily_summary.get("starting_cash", self.cash)
            return {"success": True, "message": message}
        if title == "夜间异响":
            if choice_id == "guard":
                mitigation = self.facilities["security"] + (2 if self.staff["guard"] else 0)
                loss = max(0, random.randint(700, 1800) - mitigation * 350)
                self.cash -= loss
                message = "安全系统拦下了窃贼，没有损失。" if loss == 0 else f"窃贼被赶走，但仍造成 ${loss} 损失。"
            else:
                loss = random.randint(250, 650)
                self.cash -= loss
                message = f"街坊帮忙巡夜，支付了 ${loss} 茶水钱。"
        elif title == "可疑典当":
            if choice_id == "inspect":
                cost = random.randint(120, 360)
                self.cash -= cost
                self.add_skill_xp("appraisal", 45)
                if random.random() < 0.65 + self.skills["appraisal"]["level"] * 0.03:
                    self.reputation += 2
                    message = f"你识破了伪造来源，支出 ${cost}，声誉提升。"
                else:
                    message = f"追加鉴定没有找到实锤，但你支出 ${cost} 稳住了风险。"
            else:
                self.add_skill_xp("negotiation", 20)
                message = "你礼貌谢绝了这笔可疑交易，没有留下风险。"
        elif title == "名人来访":
            gain = random.randint(500, 1800) if choice_id == "host" else random.randint(250, 700)
            self.cash += gain
            self.daily_summary["revenue"] += gain
            self.add_skill_xp("charm", 45 if choice_id == "host" else 20)
            message = f"来访带来口碑与收入，获得 ${gain}。"
        elif title == "市场风向变化":
            if choice_id == "follow":
                category = random.choice(list(self.market_trends.keys()))
                self.market_trends[category] = round(min(1.5, self.market_trends[category] + 0.18), 2)
                message = f"{category} 类藏品热度上升，市场系数提高。"
            else:
                self.add_skill_xp("commerce", 45)
                message = "你稳住节奏，商业判断更成熟了。"
        elif title == "来源质疑":
            security = self.facilities["security"]
            loss = random.randint(500, 1500) if choice_id == "lawyer" else random.randint(300, 1000)
            loss = max(100, loss - security * 80)
            self.cash -= loss
            self.add_skill_xp("appraisal", 30)
            message = f"纠纷得到处理，花费 ${loss}。"
        else:
            if choice_id == "bonus":
                cost = random.randint(180, 420)
                self.cash -= cost
                message = f"奖金平息了争执，支出 ${cost}。"
            else:
                self.add_skill_xp("charm", 35)
                message = "你亲自调解，员工关系恢复平稳。"
        self.daily_summary["events"].append(f"{title}：{message}")
        self.pending_event = None
        self.daily_summary["ending_cash"] = self.cash
        self.daily_summary["net_profit"] = self.cash - self.daily_summary.get("starting_cash", self.cash)
        return {"success": True, "message": message}

    def end_day(self) -> Dict[str, Any]:
        if self.day_ended:
            return {"error": "今天已经结算过了！"}
        self.day_ended = True

        salary_total = sum(STAFF_TYPES[s]["daily_salary"] for s, active in self.staff.items() if active)
        commerce_discount = min(0.25, (self.skills["commerce"]["level"] - 1) * 0.025)
        operating_cost = int((260 + self.shop_level * 90 + sum(self.facilities.values()) * 18) * (1 - commerce_discount))
        interest = int(self.loan["principal"] * self.loan["interest_rate"]) if self.loan["principal"] else 0
        tax_due = 0
        if self.day >= self.tax["next_due_day"]:
            taxable = max(0, self.cash - self.daily_summary["starting_cash"])
            tax_due = int(taxable * self.tax["rate"])
            self.tax["last_paid"] = tax_due
            self.tax["next_due_day"] = self.day + 7

        self.cash -= salary_total + operating_cost + interest + tax_due
        self.daily_summary["salaries"] = salary_total
        self.daily_summary["operating_cost"] = operating_cost
        self.daily_summary["loan_interest"] = interest
        self.daily_summary["tax"] = tax_due

        for event in self._process_repairs():
            self.daily_summary["events"].append(event)

        if not self.pending_event:
            self.pending_event = self._generate_pending_event()
            if self.pending_event:
                self.daily_summary["events"].append(f"待处理事件：{self.pending_event['title']}。")

        self.daily_summary["ending_cash"] = self.cash
        self.daily_summary["net_profit"] = self.cash - self.daily_summary["starting_cash"]
        if self.daily_summary["net_profit"] > 0:
            self.total_profit += self.daily_summary["net_profit"]
        return self.daily_summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash": self.cash,
            "day": self.day,
            "shop_level": self.shop_level,
            "inventory": [i.to_dict() for i in self.inventory],
            "sold_items": [i.to_dict() for i in self.sold_items],
            "transaction_log": self.transaction_log[-120:],
            "staff": self.staff,
            "skills": self.skills,
            "skill_info": SKILL_INFO,
            "facilities": self.facilities,
            "facility_info": self.facility_info_for_state(),
            "loan": self.loan,
            "tax": self.tax,
            "market_trends": self.market_trends,
            "pending_event": self.pending_event,
            "shop_name": self.shop_name,
            "reputation": self.reputation,
            "total_profit": self.total_profit,
            "successful_trades": self.successful_trades,
            "positive_reviews": self.positive_reviews,
            "ranking_badge": self.ranking_badge,
            "ranking_reward_bonus": self.ranking_reward_bonus,
            "active_customer": self.active_customer.to_dict() if self.active_customer else None,
            "daily_customer_queue": [c.to_dict() for c in self.daily_customer_queue],
            "customers_served_today": self.customers_served_today,
            "total_customers_today": self.total_customers_today,
            "day_ended": self.day_ended,
            "daily_summary": self.daily_summary,
            "display_capacity": self.display_capacity(),
            "shop_upgrade_cost": SHOP_UPGRADE_COSTS.get(self.shop_level + 1, {}).get("cost", None),
            "shop_upgrade_desc": SHOP_UPGRADE_COSTS.get(self.shop_level + 1, {}).get("desc", None),
            "staff_info": STAFF_TYPES,
            "appraisal_methods": APPRAISAL_METHODS,
            "repair_methods": REPAIR_METHODS,
        }

    def facility_info_for_state(self) -> Dict[str, Dict[str, Any]]:
        info = deepcopy(FACILITY_INFO)
        for key in info:
            info[key]["level"] = self.facilities[key]
            info[key]["upgrade_cost"] = self.facility_upgrade_cost(key)
        return info

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameStateManager":
        state = cls(initialize=False)
        state.cash = int(data.get("cash", 10000))
        state.day = int(data.get("day", 1))
        state.shop_level = int(data.get("shop_level", 1))
        state.inventory = [Item.from_dict(item) for item in data.get("inventory", [])]
        state.sold_items = [Item.from_dict(item) for item in data.get("sold_items", [])]
        state.transaction_log = list(data.get("transaction_log", []))
        state.staff = {key: bool(data.get("staff", {}).get(key, False)) for key in STAFF_TYPES}
        state.skills = skill_template()
        for key, value in data.get("skills", {}).items():
            if key in state.skills:
                state.skills[key] = {"level": int(value.get("level", 1)), "xp": int(value.get("xp", 0))}
        state.facilities = facility_template()
        for key, value in data.get("facilities", {}).items():
            if key in state.facilities:
                state.facilities[key] = clamp(int(value), 1, 5)
        state.loan = {"principal": int(data.get("loan", {}).get("principal", 0)), "interest_rate": float(data.get("loan", {}).get("interest_rate", 0.02))}
        state.tax = {
            "next_due_day": int(data.get("tax", {}).get("next_due_day", 7)),
            "rate": float(data.get("tax", {}).get("rate", 0.08)),
            "last_paid": int(data.get("tax", {}).get("last_paid", 0)),
        }
        state.market_trends = {category: float(data.get("market_trends", {}).get(category, 1.0)) for category in ITEM_TEMPLATES}
        state.pending_event = data.get("pending_event")
        state.shop_name = data.get("shop_name", "无名当铺")
        state.reputation = int(data.get("reputation", 100))
        state.total_profit = int(data.get("total_profit", 0))
        state.successful_trades = int(data.get("successful_trades", 0))
        state.positive_reviews = int(data.get("positive_reviews", 0))
        state.ranking_badge = data.get("ranking_badge")
        state.ranking_reward_bonus = int(data.get("ranking_reward_bonus", 0))
        state.active_customer = Customer.from_dict(data["active_customer"]) if data.get("active_customer") else None
        state.daily_customer_queue = [Customer.from_dict(customer) for customer in data.get("daily_customer_queue", [])]
        state.customers_served_today = int(data.get("customers_served_today", 0))
        state.total_customers_today = int(data.get("total_customers_today", max(3, len(state.daily_customer_queue))))
        state.day_ended = bool(data.get("day_ended", False))
        state.daily_summary = data.get("daily_summary") or {
            "day": state.day,
            "revenue": 0,
            "salaries": 0,
            "upgrades": 0,
            "operating_cost": 0,
            "loan_interest": 0,
            "tax": 0,
            "events": [],
            "starting_cash": state.cash,
            "ending_cash": state.cash,
            "net_profit": 0,
        }
        return state
