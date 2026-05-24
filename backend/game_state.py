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
    "restorer": {"name_cn": "修复师", "hire_cost": 1000, "daily_salary": 120, "desc": "每日推进修复进度，并降低修复失败风险。"},
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

ECONOMY_INDEX_MIN = 0.72
ECONOMY_INDEX_MAX = 1.85

RARITY_VALUE_DRIFT = {
    "common": -0.012,
    "rare": -0.004,
    "epic": 0.002,
    "legendary": 0.006,
}

CONDITION_VALUE_DRIFT = {
    "Poor": -0.010,
    "Good": 0.0,
    "Mint": 0.002,
}

AI_DAY_GENERATION_TIMEOUT = 30.0
EVENT_BASE_CHANCE = 0.62
EVENT_GUARANTEE_AFTER_QUIET_DAYS = 1

RARITY_HOLDING_RATE = {
    "common": 0.0012,
    "rare": 0.0016,
    "epic": 0.0021,
    "legendary": 0.0028,
}

LOCAL_EVENT_TEMPLATES = [
    {
        "type": "theft",
        "title": "夜间异响",
        "description": "打烊后有人在后门徘徊，似乎盯上了你的仓库。",
        "choices": [
            {"id": "guard", "label": "让保安和安全系统处理", "effect": "安全等级越高，损失越低。", "outcome": {"cash_delta": [-1800, -700], "mitigate_by": {"facility": "security", "staff": "guard", "per_level": 350, "staff_bonus": 700, "min_loss": 0}}},
            {"id": "cash", "label": "花钱请街坊巡夜", "effect": "支付一笔费用，但基本避免损失。", "outcome": {"cash_delta": [-650, -250], "skill": "charm", "skill_xp": 15}},
        ],
    },
    {
        "type": "scam",
        "title": "可疑典当",
        "description": "一名顾客留下了过于完美的来源故事，但票据编号和物品磨损对不上。",
        "choices": [
            {"id": "inspect", "label": "追加鉴定并追问来源", "effect": "花费少量现金，可能避免诈骗并获得鉴定经验。", "outcome": {"cash_delta": [-360, -120], "reputation_delta": 2, "skill": "appraisal", "skill_xp": 45}},
            {"id": "decline", "label": "直接谢绝这笔买卖", "effect": "稳妥避险，但可能错过机会。", "outcome": {"skill": "negotiation", "skill_xp": 20}},
        ],
    },
    {
        "type": "celebrity",
        "title": "名人来访",
        "description": "一位低调的收藏节目主持人想来店里拍摄一段素材。",
        "choices": [
            {"id": "host", "label": "热情接待", "effect": "可能提高声望和现金收入。", "outcome": {"cash_delta": [500, 1800], "reputation_delta": 2, "skill": "charm", "skill_xp": 45}},
            {"id": "private", "label": "保持低调", "effect": "获得少量稳定收益。", "outcome": {"cash_delta": [250, 700], "skill": "charm", "skill_xp": 20}},
        ],
    },
    {
        "type": "market",
        "title": "市场风向变化",
        "description": "拍卖圈传出新消息，某一类藏品可能短期升温。",
        "choices": [
            {"id": "follow", "label": "跟进市场热点", "effect": "随机分类市场系数上升。", "outcome": {"market_shift": 0.18, "skill": "commerce", "skill_xp": 20}},
            {"id": "ignore", "label": "维持稳健经营", "effect": "获得商业经验。", "outcome": {"skill": "commerce", "skill_xp": 45}},
        ],
    },
    {
        "type": "legal",
        "title": "来源质疑",
        "description": "有人质疑你的一件藏品来源不清，需要尽快处理。",
        "choices": [
            {"id": "lawyer", "label": "请律师和鉴定师处理", "effect": "花费较高，但风险更低。", "outcome": {"cash_delta": [-1500, -500], "mitigate_by": {"facility": "security", "per_level": 80, "min_loss": 100}, "skill": "appraisal", "skill_xp": 30}},
            {"id": "settle", "label": "私下和解", "effect": "花费中等，可能影响声望。", "outcome": {"cash_delta": [-1000, -300], "reputation_delta": -1, "skill": "negotiation", "skill_xp": 25}},
        ],
    },
    {
        "type": "staff",
        "title": "员工小问题",
        "description": "店员之间因为排班和提成产生了争执。",
        "choices": [
            {"id": "bonus", "label": "发放小额奖金", "effect": "花费现金，提升团队稳定。", "outcome": {"cash_delta": [-420, -180], "reputation_delta": 1}},
            {"id": "talk", "label": "亲自调解", "effect": "获得魅力经验。", "outcome": {"skill": "charm", "skill_xp": 35}},
        ],
    },
    {
        "type": "rare_item",
        "title": "巷口传闻",
        "description": "旧货圈有人提到一批来路清楚的老物件，消息只在今晚有效。",
        "choices": [
            {"id": "tip", "label": "付线人费追消息", "effect": "花钱换市场机会，商业经验提升。", "outcome": {"cash_delta": [-900, -300], "market_shift": 0.12, "skill": "commerce", "skill_xp": 35}},
            {"id": "wait", "label": "等消息自然发酵", "effect": "不冒进，保留现金。", "outcome": {"skill": "appraisal", "skill_xp": 15}},
        ],
    },
    {
        "type": "restoration",
        "title": "修复师来信",
        "description": "一位手艺人愿意短期接你的活，但材料费需要你先垫付。",
        "choices": [
            {"id": "hire_day", "label": "请他临时坐镇", "effect": "支出材料费，修复经验提升。", "outcome": {"cash_delta": [-800, -280], "skill": "restoration", "skill_xp": 55}},
            {"id": "consult", "label": "只买一份修复建议", "effect": "花费较少，获得少量经验。", "outcome": {"cash_delta": [-260, -90], "skill": "restoration", "skill_xp": 25}},
        ],
    },
    {
        "type": "appraisal",
        "title": "鉴定讲座",
        "description": "城里的拍卖行临时开放一场内部讲座，名额有限。",
        "choices": [
            {"id": "attend", "label": "关门半日去听课", "effect": "支付费用，鉴定能力成长明显。", "outcome": {"cash_delta": [-520, -180], "skill": "appraisal", "skill_xp": 60}},
            {"id": "notes", "label": "托熟人带讲义", "effect": "收益较低但不耽误经营。", "outcome": {"cash_delta": [-180, -60], "skill": "appraisal", "skill_xp": 25}},
        ],
    },
    {
        "type": "customer",
        "title": "老客介绍",
        "description": "一位熟客给你介绍了潜在买家，对方很看重店铺口碑。",
        "choices": [
            {"id": "receive", "label": "亲自接待并备茶", "effect": "小额花费换取声望与魅力经验。", "outcome": {"cash_delta": [-220, -80], "reputation_delta": 2, "skill": "charm", "skill_xp": 35}},
            {"id": "schedule", "label": "约到明天详谈", "effect": "稳住关系，获得谈判经验。", "outcome": {"reputation_delta": 1, "skill": "negotiation", "skill_xp": 25}},
        ],
    },
    {
        "type": "finance",
        "title": "银行经理电话",
        "description": "银行经理提醒你近期利率可能调整，问你是否要重谈授信。",
        "choices": [
            {"id": "renegotiate", "label": "主动重谈授信", "effect": "花时间沟通，商业经验提升。", "outcome": {"skill": "commerce", "skill_xp": 45, "reputation_delta": 1}},
            {"id": "ignore_bank", "label": "暂时不理会", "effect": "避免额外牵扯，保持现状。", "outcome": {"skill": "negotiation", "skill_xp": 10}},
        ],
    },
    {
        "type": "weather",
        "title": "暴雨压街",
        "description": "突如其来的暴雨让客流变少，但也有人急着把东西换成现金。",
        "choices": [
            {"id": "open_late", "label": "延长营业等急客", "effect": "增加收入机会，但有额外成本。", "outcome": {"cash_delta": [-320, 900], "skill": "negotiation", "skill_xp": 30}},
            {"id": "close_early", "label": "提前打烊整理库存", "effect": "稳妥经营，获得商业经验。", "outcome": {"skill": "commerce", "skill_xp": 25}},
        ],
    },
]


def _achievement_defs() -> Dict[str, Dict[str, Any]]:
    definitions: Dict[str, Dict[str, Any]] = {}

    def add(achievement_id: str, category: str, name: str, desc: str, metric: str, target: int, reward: Optional[Dict[str, Any]] = None, hidden: bool = False):
        definitions[achievement_id] = {
            "id": achievement_id,
            "category": category,
            "name": name,
            "desc": desc,
            "metric": metric,
            "target": target,
            "reward": reward or {},
            "hidden": hidden,
        }

    for target, name in [(20000, "现金流转"), (50000, "金库初成"), (100000, "六位数掌柜"), (250000, "城中富户"), (1000000, "百万富翁")]:
        add(f"cash_{target}", "经营", name, f"现金达到 ${target:,}。", "cash", target, {"reputation": 1})
    for target, name in [(5000, "第一桶金"), (25000, "稳定盈利"), (100000, "利润机器"), (500000, "财源滚滚"), (1000000, "当铺财阀")]:
        add(f"profit_{target}", "经营", name, f"累计正向利润达到 ${target:,}。", "total_profit", target, {"cash": min(5000, target // 50)})
    for target, name in [(1, "开张大吉"), (10, "熟练掌柜"), (50, "百炼柜台"), (100, "交易百次"), (300, "谈遍全城")]:
        add(f"trades_{target}", "交易", name, f"成功完成 {target} 笔交易。", "successful_trades", target, {"reputation": 1})
    for target, name in [(5, "好评初现"), (25, "街坊称赞"), (100, "口碑名店")]:
        add(f"reviews_{target}", "声誉", name, f"获得 {target} 次正面评价。", "positive_reviews", target, {"reputation": 2})
    for target, name in [(120, "小有名气"), (160, "信誉店铺"), (220, "金字招牌"), (320, "名满旧街"), (500, "传奇声望")]:
        add(f"reputation_{target}", "声誉", name, f"声誉达到 {target}。", "reputation", target, {"cash": target * 5})
    for target, name in [(7, "撑过首周"), (30, "月度经营"), (100, "百日老店"), (365, "一年掌柜")]:
        add(f"days_{target}", "经营", name, f"经营到第 {target} 天。", "day", target, {"reputation": 2})
    for target, name in [(1, "传说入库"), (5, "传奇收藏家"), (10, "镇店之宝库")]:
        add(f"legendary_{target}", "收藏", name, f"累计拥有或售出 {target} 件传奇物品。", "legendary_total", target, {"reputation": 3})
    for target, name in [(3, "史诗眼光"), (10, "高端藏家"), (25, "珍品经纪人")]:
        add(f"epic_{target}", "收藏", name, f"累计拥有或售出 {target} 件史诗物品。", "epic_total", target, {"cash": target * 200})
    for target, name in [(10, "仓库渐满"), (25, "藏品周转"), (50, "满仓经营")]:
        add(f"inventory_{target}", "库存", name, f"库存达到 {target} 件。", "inventory_count", target, {"reputation": 1})
    for target, name in [(5, "橱窗有人气"), (10, "展柜经理")]:
        add(f"displayed_{target}", "库存", name, f"同时展示 {target} 件物品。", "displayed_count", target, {"cash": target * 120})
    for target, name in [(1, "第一次鉴定"), (25, "鉴定常客"), (100, "鉴定专家")]:
        add(f"appraisals_{target}", "鉴定", name, f"完成 {target} 次鉴定。", "appraisals", target, {"skill_xp": {"appraisal": 60}})
    for target, name in [(1, "识破骗局"), (10, "反诈掌柜"), (30, "火眼金睛")]:
        add(f"fakes_{target}", "鉴定", name, f"识破 {target} 次欺诈或赝品。", "fakes_detected", target, {"reputation": 2})
    for target, name in [(1, "修好第一件"), (20, "修复熟手"), (75, "修复大师")]:
        add(f"repairs_{target}", "修复", name, f"完成 {target} 次成功修复。", "repairs_completed", target, {"skill_xp": {"restoration": 60}})
    for target, name in [(2, "门面升级"), (3, "豪华当铺"), (5, "世纪大掌柜")]:
        add(f"shop_level_{target}", "升级", name, f"当铺等级达到 Lv.{target}。", "shop_level", target, {"reputation": target})
    for target, name in [(3, "入门专精"), (6, "技能老练"), (10, "单项宗师")]:
        add(f"max_skill_{target}", "技能", name, f"任意技能达到 Lv.{target}。", "max_skill_level", target, {"cash": target * 300})
    for target, name in [(3, "全面发展"), (5, "全能掌柜"), (10, "五艺俱全")]:
        add(f"all_skills_{target}", "技能", name, f"全部技能达到 Lv.{target}。", "all_skill_min", target, {"reputation": target})
    for target, name in [(2, "设施起步"), (3, "店铺成型"), (5, "满级设施")]:
        add(f"all_facilities_{target}", "升级", name, f"全部设施达到 Lv.{target}。", "all_facility_min", target, {"cash": target * 600})
    for target, name in [(5, "熟面孔"), (20, "客源簿"), (50, "旧街人脉")]:
        add(f"customers_{target}", "顾客", name, f"记录 {target} 位顾客关系。", "customer_records", target, {"reputation": 1})
    for target, name in [(1, "第一位回头客"), (10, "忠实客群")]:
        add(f"loyal_{target}", "顾客", name, f"拥有 {target} 位忠实顾客。", "loyal_customers", target, {"reputation": 3})
    for target, name in [(1, "旧客回访"), (15, "老客成交"), (50, "回头生意")]:
        add(f"returning_deals_{target}", "顾客", name, f"与回头客完成 {target} 笔交易。", "returning_customer_deals", target, {"cash": target * 150})
    for target, name in [(1000, "仓储压力"), (10000, "库存税感")]:
        add(f"holding_cost_{target}", "经济", name, f"累计支付持有成本 ${target:,}。", "holding_cost_paid", target, {"skill_xp": {"commerce": 50}})
    for target, name in [(1000, "等到涨价"), (25000, "价值投资")]:
        add(f"value_gain_{target}", "经济", name, f"靠持有与展示累计增值 ${target:,}。", "value_gain_from_holding", target, {"reputation": 2})
    add("negative_reviews_1", "风险", "第一次差评", "收到一次负面评价。", "negative_reviews", 1, {"skill_xp": {"charm": 40}}, hidden=True)

    return definitions


ACHIEVEMENT_DEFS = _achievement_defs()

APPRAISAL_METHODS = {
    "visual": {"name_cn": "目测初鉴", "cost_multiplier": 0.8, "accuracy_bonus": -0.20, "value_margin": 0.48, "xp": 20, "desc": "速度快、费用较低，只能给出粗略区间；对高仿赝品不够稳。"},
    "standard": {"name_cn": "标准鉴定", "cost_multiplier": 1.45, "accuracy_bonus": -0.02, "value_margin": 0.30, "xp": 35, "desc": "检查材质、工艺和市场记录，适合大多数交易，但仍保留误差。"},
    "forensic": {"name_cn": "深度鉴定", "cost_multiplier": 3.2, "accuracy_bonus": 0.16, "value_margin": 0.16, "xp": 60, "desc": "显微痕迹、来源链和多项检测一起做，费用高但风险最低。"},
}

REPAIR_METHODS = {
    "conservative": {"name_cn": "保守修复", "cost_multiplier": 0.85, "days_delta": 1, "success_bonus": 0.10, "xp": 25, "desc": "少动原貌，耗时略长，失败风险低。"},
    "standard": {"name_cn": "标准修复", "cost_multiplier": 1.0, "days_delta": 0, "success_bonus": 0.0, "xp": 25, "desc": "按常规工序处理，成本和速度均衡。"},
    "premium": {"name_cn": "高阶修复", "cost_multiplier": 1.55, "days_delta": -1, "success_bonus": 0.14, "xp": 40, "desc": "使用更好的材料和工艺，费用高但更快更稳。"},
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
        acquired_day: Optional[int] = None,
        last_value_update_day: Optional[int] = None,
        base_value_at_purchase: Optional[int] = None,
        value_history: Optional[List[Dict[str, Any]]] = None,
        holding_cost_paid: int = 0,
        value_trend_note: Optional[str] = None,
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
        self.appraised_value_low: Optional[int] = None
        self.appraised_value_high: Optional[int] = None
        self.is_appraised_fake: Optional[bool] = None
        self.appraisal_confidence: Optional[int] = None
        self.appraisal_verdict: Optional[str] = None
        self.appraisal_notes: List[str] = []
        self.purchase_price: Optional[int] = None
        self.selling_price: Optional[int] = None
        self.status = "stored"
        self.repair_days_remaining = 0
        self.repair_success_bonus = 0.0
        self.display_slot: Optional[int] = None
        self.acquired_at = int(acquired_at if acquired_at is not None else time.time())
        self.acquired_day = int(acquired_day) if acquired_day is not None else 1
        self.last_value_update_day = int(last_value_update_day) if last_value_update_day is not None else self.acquired_day
        self.base_value_at_purchase = int(base_value_at_purchase) if base_value_at_purchase is not None else self.market_value
        self.value_history = value_history or []
        self.holding_cost_paid = int(holding_cost_paid or 0)
        self.value_trend_note = value_trend_note or "尚未经历库存时间价值结算。"
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
            "appraised_value_low": self.appraised_value_low,
            "appraised_value_high": self.appraised_value_high,
            "is_appraised_fake": self.is_appraised_fake,
            "appraisal_confidence": self.appraisal_confidence,
            "appraisal_verdict": self.appraisal_verdict,
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
            "repair_days_remaining": self.repair_days_remaining,
            "repair_success_bonus": self.repair_success_bonus,
            "display_slot": self.display_slot,
            "acquired_at": self.acquired_at,
            "acquired_day": self.acquired_day,
            "last_value_update_day": self.last_value_update_day,
            "base_value_at_purchase": self.base_value_at_purchase,
            "value_history": self.value_history[-12:],
            "holding_cost_paid": self.holding_cost_paid,
            "value_trend_note": self.value_trend_note,
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
            acquired_day=data.get("acquired_day"),
            last_value_update_day=data.get("last_value_update_day"),
            base_value_at_purchase=data.get("base_value_at_purchase"),
            value_history=list(data.get("value_history", [])),
            holding_cost_paid=int(data.get("holding_cost_paid", 0)),
            value_trend_note=data.get("value_trend_note"),
            last_trade_at=data.get("last_trade_at"),
            showcase_price=data.get("showcase_price"),
            era=data.get("era"),
            damage_report=data.get("damage_report"),
            special_effects=list(data.get("special_effects", [])),
            authentication_tips=list(data.get("authentication_tips", [])),
        )
        item.appraised_value = data.get("appraised_value")
        item.appraised_value_low = data.get("appraised_value_low")
        item.appraised_value_high = data.get("appraised_value_high")
        item.is_appraised_fake = data.get("is_appraised_fake")
        item.appraisal_confidence = data.get("appraisal_confidence")
        item.appraisal_verdict = data.get("appraisal_verdict")
        item.appraisal_notes = list(data.get("appraisal_notes", []))
        item.purchase_price = data.get("purchase_price")
        item.selling_price = data.get("selling_price")
        item.status = data.get("status", "stored")
        item.repair_days_remaining = int(data.get("repair_days_remaining", 0))
        item.repair_success_bonus = float(data.get("repair_success_bonus", 0.0))
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
        customer_id: Optional[str] = None,
        is_returning: bool = False,
        visit_count: int = 1,
        relationship_level: Optional[str] = None,
        last_deal_summary: Optional[str] = None,
        satisfaction: int = 50,
        referred_by: Optional[str] = None,
    ):
        self.customer_id = customer_id or str(uuid.uuid4())[:10]
        self.name = name
        self.trait = trait if trait in CUSTOMER_TRAITS else "hesitant"
        self.role = role if role in ["seller", "buyer"] else "seller"
        self.item = item
        self.is_returning = bool(is_returning)
        self.visit_count = max(1, int(visit_count or 1))
        self.satisfaction = clamp(int(satisfaction), 0, 100)
        self.relationship_level = relationship_level or self._relationship_from_satisfaction(self.satisfaction, self.visit_count)
        self.last_deal_summary = last_deal_summary
        self.referred_by = referred_by
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
        if self.is_returning:
            base_patience += 1
        if self.relationship_level in ["loyal", "vip"]:
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
        if self.relationship_level in ["loyal", "vip"]:
            if self.role == "seller":
                limit_ratio *= 0.96
                start_ratio *= 0.94
            else:
                limit_ratio *= 1.05
                start_ratio *= 1.04
        elif self.is_returning:
            if self.role == "seller":
                limit_ratio *= 0.98
                start_ratio *= 0.97
            else:
                limit_ratio *= 1.02
                start_ratio *= 1.02
        return max(5, int(perceived_value * limit_ratio)), max(10, int(perceived_value * start_ratio))

    @staticmethod
    def _relationship_from_satisfaction(satisfaction: int, visit_count: int) -> str:
        if satisfaction >= 88 and visit_count >= 3:
            return "vip"
        if satisfaction >= 76 and visit_count >= 2:
            return "loyal"
        if satisfaction >= 58 or visit_count >= 2:
            return "familiar"
        if satisfaction <= 28:
            return "strained"
        return "new"

    def retarget_item(self, item: Item, note: Optional[str] = None):
        self.item = item
        calculated_limit, calculated_offer = self._calculate_prices()
        self.limit_price = calculated_limit
        self.current_offer = calculated_offer
        self.initial_offer = calculated_offer
        if self.role == "buyer":
            self.backstory = f"{self.name} 转而对店里的 {item.name} 产生兴趣，想听听你的报价。"
        if note:
            self.dialogue_history.append({"role": "customer", "content": note})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
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
            "is_returning": self.is_returning,
            "visit_count": self.visit_count,
            "relationship_level": self.relationship_level,
            "relationship_cn": {
                "new": "新客",
                "familiar": "熟客",
                "loyal": "忠实顾客",
                "vip": "贵宾",
                "strained": "关系紧张",
            }.get(self.relationship_level, "新客"),
            "last_deal_summary": self.last_deal_summary,
            "satisfaction": self.satisfaction,
            "referred_by": self.referred_by,
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
            customer_id=data.get("customer_id"),
            is_returning=bool(data.get("is_returning", False)),
            visit_count=int(data.get("visit_count", 1)),
            relationship_level=data.get("relationship_level"),
            last_deal_summary=data.get("last_deal_summary"),
            satisfaction=int(data.get("satisfaction", 50)),
            referred_by=data.get("referred_by"),
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
        self.economy_index = 1.0
        self.inflation_rate = 0.0
        self.money_supply_score = 10000
        self.economic_pressure = "stable"
        self.economy_history: List[Dict[str, Any]] = []
        self.pending_event: Optional[Dict[str, Any]] = None
        self.shop_name = "无名当铺"
        self.reputation = 100
        self.total_profit = 0
        self.successful_trades = 0
        self.positive_reviews = 0
        self.customer_registry: Dict[str, Dict[str, Any]] = {}
        self.customer_codex: Dict[str, Dict[str, Any]] = {}
        self.item_codex: Dict[str, Dict[str, Any]] = {}
        self.achievements: Dict[str, Dict[str, Any]] = {}
        self.achievement_unlocks: List[Dict[str, Any]] = []
        self.achievement_stats: Dict[str, int] = {
            "appraisals": 0,
            "fakes_detected": 0,
            "repairs_completed": 0,
            "repair_failures": 0,
            "returning_customer_deals": 0,
            "negative_reviews": 0,
            "holding_cost_paid": 0,
            "value_gain_from_holding": 0,
            "highest_cash": self.cash,
            "highest_inventory_value": 0,
            "total_customers_seen": 0,
            "referrals_generated": 0,
        }
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
            "holding_cost": 0,
            "economy_index": self.economy_index,
            "inflation_rate": self.inflation_rate,
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
        self._inject_relationship_customers()
        self._rebalance_buyer_targets()
        self.achievement_stats["total_customers_seen"] = int(self.achievement_stats.get("total_customers_seen", 0)) + len(self.daily_customer_queue)
        self.active_customer = self.daily_customer_queue.pop(0) if self.daily_customer_queue else None
        self._record_daily_customer_codex()

    async def async_initialize_day_with_fallback(self, ai_client, timeout: float = AI_DAY_GENERATION_TIMEOUT) -> Dict[str, Any]:
        import asyncio

        ai_available = bool(getattr(ai_client, "available", lambda: False)())
        if not ai_available:
            self.initialize_day_fast()
            return {"success": True, "fallback": True, "reason": "ai_unavailable"}

        try:
            await asyncio.wait_for(self.async_initialize_day(ai_client), timeout=timeout)
            return {"success": True, "fallback": False}
        except Exception:
            self.initialize_day_fast()
            return {"success": True, "fallback": True, "reason": "ai_timeout_or_error"}

    def initialize_day_fast(self):
        """Initialize a playable day immediately with local templates."""
        self.daily_customer_queue = [self.generate_random_customer() for _ in range(self.total_customers_today)]
        self._inject_relationship_customers()
        self._rebalance_buyer_targets()
        self.achievement_stats["total_customers_seen"] = int(self.achievement_stats.get("total_customers_seen", 0)) + len(self.daily_customer_queue)
        self.active_customer = self.daily_customer_queue.pop(0) if self.daily_customer_queue else None
        self._record_daily_customer_codex()

    def generate_random_customer(self) -> Customer:
        name = random.choice(CUSTOMER_NAMES)
        trait = random.choice(list(CUSTOMER_TRAITS.keys()))
        saleable_items = self._saleable_items()
        role = "buyer" if saleable_items and random.random() < 0.45 else "seller"

        if role == "seller":
            return self._generate_local_seller_customer(name, trait)
        else:
            item = self._choose_saleable_item() or random.choice(saleable_items)

        customer = Customer(name=name, trait=trait, role=role, item=item, shop_level=self.shop_level, marketer_active=self.staff["marketer"])
        customer.patience = clamp(customer.patience + self.skills["charm"]["level"] // 2, 1, 8)
        return customer

    def _saleable_items(self, exclude_ids: Optional[set[str]] = None) -> List[Item]:
        exclude_ids = exclude_ids or set()
        return [item for item in self.inventory if item.status in ["stored", "displayed"] and item.id not in exclude_ids]

    def _is_saleable_item(self, item_id: str) -> bool:
        item = self.get_item(item_id)
        return bool(item and item.status in ["stored", "displayed"])

    def _choose_saleable_item(self, exclude_ids: Optional[set[str]] = None, target_counts: Optional[Dict[str, int]] = None) -> Optional[Item]:
        saleable_items = self._saleable_items(exclude_ids)
        if not saleable_items:
            return None
        displayed = [item for item in saleable_items if item.status == "displayed"]
        pool = displayed or saleable_items
        if target_counts is None:
            return random.choice(pool)
        return min(pool, key=lambda item: (target_counts.get(item.id, 0), 0 if item.status == "displayed" else 1, item.market_value))

    def _generate_local_seller_customer(self, name: Optional[str] = None, trait: Optional[str] = None) -> Customer:
        category = random.choice(list(ITEM_TEMPLATES.keys()))
        template = random.choice(ITEM_TEMPLATES[category])
        item = self._generate_item_from_template(template, category)
        customer = Customer(
            name=name or random.choice(CUSTOMER_NAMES),
            trait=trait or random.choice(list(CUSTOMER_TRAITS.keys())),
            role="seller",
            item=item,
            shop_level=self.shop_level,
            marketer_active=self.staff["marketer"],
        )
        customer.patience = clamp(customer.patience + self.skills["charm"]["level"] // 2, 1, 8)
        return customer

    def _relationship_cn(self, level: str) -> str:
        return {
            "new": "新客",
            "familiar": "熟客",
            "loyal": "忠实顾客",
            "vip": "贵宾",
            "strained": "关系紧张",
        }.get(level, "新客")

    def _customer_record(self, customer: Customer) -> Dict[str, Any]:
        return {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "trait": customer.trait,
            "age": customer.age,
            "appearance": customer.appearance,
            "avatar_url": customer.avatar_url,
            "visit_count": customer.visit_count,
            "last_visit_day": self.day,
            "satisfaction": customer.satisfaction,
            "relationship_level": customer.relationship_level,
            "last_deal_summary": customer.last_deal_summary,
            "positive_deals": 0,
            "negative_deals": 0,
            "referrals_generated": 0,
        }

    def _record_item_encounter(self, item: Item, source: str = "unknown"):
        existing = self.item_codex.get(item.id, {})
        sources = list(existing.get("sources", []))
        if source not in sources:
            sources.append(source)
        first_seen_day = int(existing.get("first_seen_day", self.day))
        entry = {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "category_cn": item.category,
            "condition": item.condition,
            "rarity": item.rarity,
            "rarity_cn": RARITY_INFO[item.rarity]["name_cn"],
            "era": item.era,
            "description": item.description,
            "story": item.story,
            "market_value": item.market_value,
            "appraised_value": item.appraised_value,
            "appraisal_verdict": item.appraisal_verdict,
            "appraisal_confidence": item.appraisal_confidence,
            "is_appraised_fake": item.is_appraised_fake,
            "status": item.status,
            "first_seen_day": first_seen_day,
            "last_seen_day": self.day,
            "times_seen": int(existing.get("times_seen", 0)) + 1,
            "sources": sources[-8:],
            "owned": any(owned.id == item.id for owned in self.inventory),
            "sold": any(sold.id == item.id for sold in self.sold_items),
            "purchase_price": item.purchase_price,
            "selling_price": item.selling_price,
            "value_trend_note": item.value_trend_note,
            "special_effects": item.special_effects[:3],
            "authentication_tips": item.authentication_tips[:3],
        }
        self.item_codex[item.id] = entry

    def _record_customer_encounter(self, customer: Customer, source: str = "visit"):
        existing = self.customer_codex.get(customer.customer_id, {})
        sources = list(existing.get("sources", []))
        if source not in sources:
            sources.append(source)
        first_seen_day = int(existing.get("first_seen_day", self.day))
        entry = {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "trait": customer.trait,
            "trait_cn": CUSTOMER_TRAITS[customer.trait]["name_cn"],
            "trait_desc": CUSTOMER_TRAITS[customer.trait]["desc"],
            "role": customer.role,
            "age": customer.age,
            "appearance": customer.appearance,
            "backstory": customer.backstory,
            "avatar_url": customer.avatar_url,
            "transaction_prefs": customer.transaction_prefs[:4],
            "persuasion_points": customer.persuasion_points[:4],
            "is_returning": customer.is_returning,
            "visit_count": customer.visit_count,
            "relationship_level": customer.relationship_level,
            "relationship_cn": customer.to_dict().get("relationship_cn", "新客"),
            "satisfaction": customer.satisfaction,
            "last_deal_summary": customer.last_deal_summary,
            "referred_by": customer.referred_by,
            "first_seen_day": first_seen_day,
            "last_seen_day": self.day,
            "times_seen": int(existing.get("times_seen", 0)) + 1,
            "sources": sources[-8:],
            "last_item_id": customer.item.id,
            "last_item_name": customer.item.name,
        }
        self.customer_codex[customer.customer_id] = entry
        self._record_item_encounter(customer.item, f"customer:{customer.name}")

    def _record_daily_customer_codex(self):
        for customer in ([self.active_customer] if self.active_customer else []) + list(self.daily_customer_queue):
            self._record_customer_encounter(customer, "daily_queue")

    def _generate_customer_from_record(self, record: Dict[str, Any], referred_by: Optional[str] = None) -> Customer:
        saleable_items = self._saleable_items()
        role = "buyer" if saleable_items and random.random() < 0.52 else "seller"
        if role == "seller":
            category = random.choice(list(ITEM_TEMPLATES.keys()))
            template = random.choice(ITEM_TEMPLATES[category])
            item = self._generate_item_from_template(template, category)
            quality_bonus = 1.08 + min(0.18, int(record.get("visit_count", 1)) * 0.025)
            item.market_value = int(item.market_value * quality_bonus)
            item.actual_value = int(item.actual_value * quality_bonus)
            item.hidden_attrs = list(dict.fromkeys(item.hidden_attrs + ["回头客带来的更优质来源"]))
        else:
            item = self._choose_saleable_item() or random.choice(saleable_items)
        visit_count = int(record.get("visit_count", 1)) + 1
        satisfaction = int(record.get("satisfaction", 55))
        relationship_level = Customer._relationship_from_satisfaction(satisfaction, visit_count)
        backstory = (
            f"{record.get('name', '熟客')} 又回到店里，提起上次交易：{record.get('last_deal_summary') or '还记得你这里办事利落'}。"
            if not referred_by
            else f"{record.get('name', '熟客')} 推荐来的朋友，听说你的铺子讲规矩，想先试一笔。"
        )
        customer = Customer(
            name=str(record.get("name") or random.choice(CUSTOMER_NAMES)),
            trait=str(record.get("trait") or random.choice(list(CUSTOMER_TRAITS.keys()))),
            role=role,
            item=item,
            shop_level=self.shop_level,
            marketer_active=self.staff["marketer"],
            age=record.get("age"),
            appearance=record.get("appearance"),
            backstory=backstory,
            avatar_url=record.get("avatar_url"),
            customer_id=str(record.get("customer_id") or str(uuid.uuid4())[:10]),
            is_returning=not bool(referred_by),
            visit_count=visit_count,
            relationship_level=relationship_level,
            last_deal_summary=record.get("last_deal_summary"),
            satisfaction=satisfaction,
            referred_by=referred_by,
        )
        customer.patience = clamp(customer.patience + self.skills["charm"]["level"] // 2, 1, 8)
        return customer

    def _inject_relationship_customers(self):
        if not self.daily_customer_queue:
            return
        candidates = []
        for record in self.customer_registry.values():
            if self.day - int(record.get("last_visit_day", 0)) < 2:
                continue
            satisfaction = int(record.get("satisfaction", 50))
            if satisfaction < 58:
                continue
            base_chance = 0.30 if satisfaction >= 70 else 0.14
            base_chance += min(0.08, (self.reputation - 100) / 1000)
            base_chance += min(0.06, self.skills["charm"]["level"] * 0.006)
            if record.get("relationship_level") == "vip":
                base_chance += 0.08
            if random.random() < base_chance:
                candidates.append(record)
        random.shuffle(candidates)
        slots = min(len(candidates), max(1, self.total_customers_today // 3))
        for index, record in enumerate(candidates[:slots]):
            self.daily_customer_queue[index % len(self.daily_customer_queue)] = self._generate_customer_from_record(record)

        loyal_records = [record for record in self.customer_registry.values() if record.get("relationship_level") in ["loyal", "vip"]]
        if loyal_records and random.random() < 0.18 + (0.07 if self.staff["marketer"] else 0):
            source = random.choice(loyal_records)
            insert_at = min(len(self.daily_customer_queue) - 1, slots)
            referred = self._generate_customer_from_record(source, referred_by=str(source.get("customer_id")))
            referred.name = random.choice(CUSTOMER_NAMES)
            referred.customer_id = str(uuid.uuid4())[:10]
            referred.is_returning = False
            referred.visit_count = 1
            self.daily_customer_queue[insert_at] = referred
            source["referrals_generated"] = int(source.get("referrals_generated", 0)) + 1
            self.achievement_stats["referrals_generated"] = int(self.achievement_stats.get("referrals_generated", 0)) + 1

    def _record_customer_outcome(self, customer: Customer, outcome: str, price: Optional[int] = None, item: Optional[Item] = None):
        record = self.customer_registry.get(customer.customer_id) or self._customer_record(customer)
        record["visit_count"] = max(int(record.get("visit_count", 0)), customer.visit_count)
        record["last_visit_day"] = self.day
        delta = 0
        if outcome == "deal":
            delta = 14 if customer.role == "seller" else 12
            record["positive_deals"] = int(record.get("positive_deals", 0)) + 1
            if customer.is_returning:
                self.achievement_stats["returning_customer_deals"] = int(self.achievement_stats.get("returning_customer_deals", 0)) + 1
        elif outcome == "reject":
            delta = -8
        elif outcome == "walk_out":
            delta = -14
        elif outcome == "fraud_detected":
            delta = -22
            record["negative_deals"] = int(record.get("negative_deals", 0)) + 1
        satisfaction = clamp(int(record.get("satisfaction", customer.satisfaction)) + delta, 0, 100)
        record["satisfaction"] = satisfaction
        record["relationship_level"] = Customer._relationship_from_satisfaction(satisfaction, int(record.get("visit_count", 1)))
        if price is not None and item is not None:
            verb = "卖给你" if customer.role == "seller" else "从你这里买走"
            record["last_deal_summary"] = f"第 {self.day} 天以 ${price} {verb}【{item.name}】"
        record["name"] = customer.name
        record["trait"] = customer.trait
        record["age"] = customer.age
        record["appearance"] = customer.appearance
        record["avatar_url"] = customer.avatar_url
        self.customer_registry[customer.customer_id] = record
        customer.satisfaction = satisfaction
        customer.relationship_level = record["relationship_level"]
        customer.last_deal_summary = record.get("last_deal_summary")
        self._record_customer_encounter(customer, outcome)
        if outcome in ["reject", "walk_out"] and random.random() < 0.10:
            self.reputation -= 1
            self.achievement_stats["negative_reviews"] = int(self.achievement_stats.get("negative_reviews", 0)) + 1
            if self.daily_summary:
                self.daily_summary["events"].append(f"{customer.name} 留下一条负面评价，声誉 -1。")

    def _retarget_buyer(self, customer: Customer, unavailable_item_id: Optional[str] = None, target_counts: Optional[Dict[str, int]] = None, announce: bool = True) -> bool:
        if customer.role != "buyer":
            return True
        exclude_ids = {unavailable_item_id} if unavailable_item_id else set()
        item = self._choose_saleable_item(exclude_ids, target_counts)
        if not item:
            return False
        if customer.item.id == item.id and self._is_saleable_item(item.id):
            if target_counts is not None:
                target_counts[item.id] = target_counts.get(item.id, 0) + 1
            return True
        note = f"刚才那件已经不合适了，我再看看这件【{item.name}】。" if announce else None
        customer.retarget_item(item, note)
        self._record_customer_encounter(customer, "retarget")
        if target_counts is not None:
            target_counts[item.id] = target_counts.get(item.id, 0) + 1
        return True

    def _rebalance_buyer_targets(self):
        saleable_items = self._saleable_items()
        if not saleable_items:
            self.daily_customer_queue = [
                self._generate_local_seller_customer(customer.name, customer.trait) if customer.role == "buyer" else customer
                for customer in self.daily_customer_queue
            ]
            return
        buyer_slots = max(1, len(saleable_items) * 2)
        buyer_count = 0
        target_counts: Dict[str, int] = {}
        for index, customer in enumerate(list(self.daily_customer_queue)):
            if customer.role != "buyer":
                continue
            if buyer_count >= buyer_slots:
                self.daily_customer_queue[index] = self._generate_local_seller_customer(customer.name, customer.trait)
                continue
            if self._retarget_buyer(customer, target_counts=target_counts, announce=False):
                buyer_count += 1
            else:
                self.daily_customer_queue[index] = self._generate_local_seller_customer(customer.name, customer.trait)

    def _repair_buyer_queue_after_item_removed(self, item_id: str):
        target_counts: Dict[str, int] = {}
        if self.active_customer and self.active_customer.role == "buyer" and self._is_saleable_item(self.active_customer.item.id):
            target_counts[self.active_customer.item.id] = target_counts.get(self.active_customer.item.id, 0) + 1
        for index, customer in enumerate(list(self.daily_customer_queue)):
            if customer.role != "buyer":
                continue
            if customer.item.id != item_id and self._is_saleable_item(customer.item.id):
                target_counts[customer.item.id] = target_counts.get(customer.item.id, 0) + 1
                continue
            if not self._retarget_buyer(customer, item_id, target_counts):
                self.daily_customer_queue[index] = self._generate_local_seller_customer(customer.name, customer.trait)

    def ensure_active_customer_target(self):
        if not self.active_customer or self.active_customer.role != "buyer":
            return
        if self._is_saleable_item(self.active_customer.item.id):
            return
        old_name = self.active_customer.name
        old_trait = self.active_customer.trait
        if not self._retarget_buyer(self.active_customer, self.active_customer.item.id):
            self.active_customer = self._generate_local_seller_customer(old_name, old_trait)

    async def async_advance_to_next_day(self, ai_client):
        if self.pending_event:
            return {"error": "还有未处理的随机事件，请先做出选择。"}
        self.day += 1
        self.initialize_day()
        result = await self.async_initialize_day_with_fallback(ai_client)
        if not result.get("fallback"):
            return {"success": True, "message": "新的一天开始了。"}
        if result.get("reason") == "ai_unavailable":
            return {"success": True, "message": "新的一天开始了。未检测到 AI 配置，已用本地顾客开门。", "fallback": True}
        return {"success": True, "message": "新的一天开始了。AI 预生成较慢，已先用本地顾客开门。", "fallback": True}

    def _refresh_market_trends(self):
        for category in ITEM_TEMPLATES:
            macro_bias = (self.economy_index - 1.0) * 0.10
            drift = random.uniform(-0.12, 0.14) + macro_bias
            self.market_trends[category] = round(clamp(int((1.0 + drift) * 100), 72, 150) / 100, 2)

    def _inventory_value(self) -> int:
        return int(sum(item.market_value for item in self.inventory if item.status != "sold"))

    def _achievement_metric(self, metric: str) -> int:
        rarity_totals = {"common": 0, "rare": 0, "epic": 0, "legendary": 0}
        for item in self.inventory + self.sold_items:
            rarity_totals[item.rarity] = rarity_totals.get(item.rarity, 0) + 1
        if metric == "cash":
            return int(self.cash)
        if metric == "total_profit":
            return int(self.total_profit)
        if metric == "successful_trades":
            return int(self.successful_trades)
        if metric == "positive_reviews":
            return int(self.positive_reviews)
        if metric == "reputation":
            return int(self.reputation)
        if metric == "day":
            return int(self.day)
        if metric == "inventory_count":
            return len([item for item in self.inventory if item.status != "sold"])
        if metric == "displayed_count":
            return len([item for item in self.inventory if item.status == "displayed"])
        if metric == "legendary_total":
            return rarity_totals.get("legendary", 0)
        if metric == "epic_total":
            return rarity_totals.get("epic", 0)
        if metric == "shop_level":
            return int(self.shop_level)
        if metric == "max_skill_level":
            return max((value["level"] for value in self.skills.values()), default=1)
        if metric == "all_skill_min":
            return min((value["level"] for value in self.skills.values()), default=1)
        if metric == "all_facility_min":
            return min(self.facilities.values()) if self.facilities else 1
        if metric == "customer_records":
            return len(self.customer_registry)
        if metric == "loyal_customers":
            return len([record for record in self.customer_registry.values() if record.get("relationship_level") in ["loyal", "vip"]])
        return int(self.achievement_stats.get(metric, 0))

    def _update_achievement_stats(self):
        self.achievement_stats["highest_cash"] = max(int(self.achievement_stats.get("highest_cash", 0)), int(self.cash))
        self.achievement_stats["highest_inventory_value"] = max(int(self.achievement_stats.get("highest_inventory_value", 0)), self._inventory_value())
        self.achievement_stats["total_customers_seen"] = max(
            int(self.achievement_stats.get("total_customers_seen", 0)),
            self.customers_served_today + len(self.customer_registry),
        )

    def _apply_achievement_reward(self, reward: Dict[str, Any]):
        cash_reward = int(reward.get("cash") or 0)
        reputation_reward = int(reward.get("reputation") or 0)
        if cash_reward:
            self.cash += cash_reward
            if self.daily_summary:
                self.daily_summary["revenue"] = self.daily_summary.get("revenue", 0) + cash_reward
        if reputation_reward:
            self.reputation += reputation_reward
        skill_rewards = reward.get("skill_xp") if isinstance(reward.get("skill_xp"), dict) else {}
        for skill, amount in skill_rewards.items():
            self.add_skill_xp(skill, int(amount))

    def _check_achievements(self, event_type: str = "", context: Optional[Dict[str, Any]] = None):
        _ = event_type, context
        self._update_achievement_stats()
        for achievement_id, definition in ACHIEVEMENT_DEFS.items():
            current = self.achievements.get(achievement_id, {})
            progress = self._achievement_metric(definition["metric"])
            unlocked = bool(current.get("unlocked"))
            if not unlocked and progress >= int(definition["target"]):
                unlocked = True
                self._apply_achievement_reward(definition.get("reward", {}))
                unlock = {
                    "id": achievement_id,
                    "name": definition["name"],
                    "category": definition["category"],
                    "day": self.day,
                    "reward": definition.get("reward", {}),
                }
                self.achievement_unlocks.append(unlock)
                self.achievement_unlocks = self.achievement_unlocks[-12:]
            self.achievements[achievement_id] = {
                "id": achievement_id,
                "progress": min(progress, int(definition["target"])),
                "target": int(definition["target"]),
                "unlocked": unlocked,
                "unlocked_day": current.get("unlocked_day") or (self.day if unlocked else None),
            }

    def achievement_list(self) -> List[Dict[str, Any]]:
        self._update_achievement_stats()
        items: List[Dict[str, Any]] = []
        for achievement_id, definition in ACHIEVEMENT_DEFS.items():
            progress = self._achievement_metric(definition["metric"])
            state = self.achievements.get(achievement_id, {})
            unlocked = bool(state.get("unlocked")) or progress >= int(definition["target"])
            hidden = bool(definition.get("hidden")) and not unlocked
            items.append(
                {
                    **definition,
                    "name": "隐藏成就" if hidden else definition["name"],
                    "desc": "继续经营以揭开这个目标。" if hidden else definition["desc"],
                    "progress": min(progress, int(definition["target"])),
                    "unlocked": unlocked,
                    "unlocked_day": state.get("unlocked_day"),
                }
            )
        return items

    def _apply_economy_tick(self) -> Dict[str, Any]:
        previous = float(self.economy_index)
        assets = max(0, int(self.cash) + self._inventory_value())
        self.money_supply_score = assets + int(self.loan.get("principal", 0) * 0.45) + self.successful_trades * 180
        wealth_pressure = min(0.018, max(0.0, (assets - 35000) / 900000))
        time_pressure = min(0.010, self.day / 30000)
        debt_drag = min(0.010, self.loan.get("principal", 0) / 700000)
        random_drift = random.uniform(-0.006, 0.008)
        daily_change = random_drift + wealth_pressure + time_pressure - debt_drag
        self.economy_index = round(max(ECONOMY_INDEX_MIN, min(ECONOMY_INDEX_MAX, previous * (1 + daily_change))), 3)
        self.inflation_rate = round(self.economy_index - previous, 4)
        if self.inflation_rate > 0.012:
            self.economic_pressure = "inflation"
        elif self.inflation_rate < -0.008:
            self.economic_pressure = "deflation"
        else:
            self.economic_pressure = "stable"
        entry = {
            "day": self.day,
            "economy_index": self.economy_index,
            "inflation_rate": self.inflation_rate,
            "pressure": self.economic_pressure,
            "money_supply_score": self.money_supply_score,
        }
        self.economy_history.append(entry)
        self.economy_history = self.economy_history[-30:]
        return entry

    def _apply_inventory_value_tick(self) -> Dict[str, Any]:
        total_holding_cost = 0
        total_value_delta = 0
        changed_items = 0
        security_discount = min(0.35, (self.facilities["security"] - 1) * 0.04)
        commerce_discount = min(0.20, (self.skills["commerce"]["level"] - 1) * 0.025)
        for item in self.inventory:
            if item.status not in ["stored", "displayed", "repairing"]:
                continue
            last_day = int(getattr(item, "last_value_update_day", getattr(item, "acquired_day", self.day)) or self.day)
            days_elapsed = max(0, self.day - last_day)
            if days_elapsed <= 0:
                continue
            old_value = int(item.market_value)
            trend = float(self.market_trends.get(item.category, 1.0))
            rarity_drift = RARITY_VALUE_DRIFT.get(item.rarity, -0.006)
            condition_drift = CONDITION_VALUE_DRIFT.get(item.condition, 0.0)
            display_drift = 0.004 + self.facilities["showcase"] * 0.001 if item.status == "displayed" else 0.0
            repair_drag = -0.004 if item.status == "repairing" else 0.0
            market_drift = (trend - 1.0) * 0.08
            macro_drift = (self.economy_index - 1.0) * 0.006
            daily_rate = max(-0.035, min(0.032, rarity_drift + condition_drift + display_drift + repair_drag + market_drift + macro_drift))
            new_value = max(10, int(old_value * ((1 + daily_rate) ** days_elapsed)))
            value_delta = new_value - old_value
            storage_rate = RARITY_HOLDING_RATE.get(item.rarity, 0.0014)
            if item.status == "displayed":
                storage_rate += 0.0008
            if item.status == "repairing":
                storage_rate += 0.0005
            storage_rate *= max(0.45, 1 - security_discount - commerce_discount)
            holding_cost = max(days_elapsed * 2, int(old_value * storage_rate * days_elapsed))
            item.market_value = new_value
            item.holding_cost_paid = int(getattr(item, "holding_cost_paid", 0)) + holding_cost
            item.last_value_update_day = self.day
            item.value_trend_note = (
                f"{days_elapsed} 天内{'增值' if value_delta >= 0 else '折价'} ${abs(value_delta)}，"
                f"持有成本 ${holding_cost}，市场系数 {trend:.2f}x。"
            )
            item.value_history = (getattr(item, "value_history", []) or []) + [
                {"day": self.day, "market_value": new_value, "delta": value_delta, "holding_cost": holding_cost}
            ]
            item.value_history = item.value_history[-12:]
            self._record_item_encounter(item, "value_tick")
            total_holding_cost += holding_cost
            total_value_delta += value_delta
            changed_items += 1
        if total_holding_cost:
            self.cash -= total_holding_cost
            self.achievement_stats["holding_cost_paid"] = int(self.achievement_stats.get("holding_cost_paid", 0)) + total_holding_cost
        if total_value_delta > 0:
            self.achievement_stats["value_gain_from_holding"] = int(self.achievement_stats.get("value_gain_from_holding", 0)) + total_value_delta
        return {"holding_cost": total_holding_cost, "value_delta": total_value_delta, "changed_items": changed_items}

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
        value = int(raw_value * RARITY_INFO[rarity]["multiplier"] * self.economy_index * random.uniform(0.85, 1.16))
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
            acquired_day=self.day,
            last_value_update_day=self.day,
            base_value_at_purchase=market_value,
        )

    async def generate_random_customer_async(self, ai_client) -> Customer:
        name = await ai_client.generate_random_content("customer_name") or random.choice(CUSTOMER_NAMES)
        trait = random.choice(list(CUSTOMER_TRAITS.keys()))

        saleable_items = self._saleable_items()
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

        profile = await ai_client.generate_customer_profile(
            role,
            trait,
            item.name,
            item.category,
            {
                "economy_index": self.economy_index,
                "economic_pressure": self.economic_pressure,
                "market_trend": self.market_trends.get(item.category, 1.0),
                "reputation": self.reputation,
            },
        )
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
            if self.active_customer.role == "buyer" and not self._is_saleable_item(self.active_customer.item.id):
                if not self._retarget_buyer(self.active_customer, self.active_customer.item.id):
                    self.active_customer = self._generate_local_seller_customer(self.active_customer.name, self.active_customer.trait)
            if self.active_customer:
                self._record_customer_encounter(self.active_customer, "served")
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
        base_cost = max(160, int(item.market_value * 0.08 * self.economy_index))
        discount = 0.08 * (facility_level - 1) + (0.35 if self.staff["appraiser"] else 0)
        cost = max(120, int(base_cost * method_info["cost_multiplier"] * (1 - min(0.45, discount))))
        if self.cash < cost:
            return {"error": f"鉴定资金不足，需要 ${cost}。"}

        self.cash -= cost
        self.daily_summary["upgrades"] += cost
        accuracy = min(0.92, max(0.25, 0.45 + skill_level * 0.035 + facility_level * 0.04 + (0.12 if self.staff["appraiser"] else 0) + method_info["accuracy_bonus"]))
        detects_fake = item.is_fake and random.random() < accuracy
        item.is_appraised_fake = detects_fake if item.is_fake else False
        error_margin = max(0.06, float(method_info["value_margin"]) - (skill_level - 1) * 0.015 - (facility_level - 1) * 0.02 - (0.04 if self.staff["appraiser"] else 0))
        estimate_noise = random.uniform(-error_margin * 0.75, error_margin * 0.75)
        item.appraised_value = max(10, int(item.actual_value * (1 + estimate_noise)))
        item.appraised_value_low = max(10, int(item.appraised_value * (1 - error_margin)))
        item.appraised_value_high = max(item.appraised_value_low + 1, int(item.appraised_value * (1 + error_margin)))
        item.appraisal_confidence = int(accuracy * 100)
        item.appraisal_verdict = "发现明显作伪" if detects_fake else "未见明显作伪"
        fallback_notes = [
            f"鉴定方法：{method_info['name_cn']}。{method_info['desc']}",
            f"观察成色：{item.condition}，修复难度 {item.repair_difficulty}/5。",
            f"市场趋势系数：{self.market_trends.get(item.category, 1.0):.2f}。",
            f"年代线索：{item.era}；损坏记录：{item.damage_report}",
            f"估值区间约 ${item.appraised_value_low} - ${item.appraised_value_high}，结论可信度约 {item.appraisal_confidence}%。",
            "未发现作伪不等于保真，仍可能存在高仿或来源风险。" if not detects_fake else "关键作伪疑点已记录，建议谨慎压价或拒绝。",
        ]
        item.appraisal_notes = ai_notes or fallback_notes
        self.add_skill_xp("appraisal", int(method_info["xp"]))
        self.achievement_stats["appraisals"] = int(self.achievement_stats.get("appraisals", 0)) + 1
        if detects_fake:
            self.achievement_stats["fakes_detected"] = int(self.achievement_stats.get("fakes_detected", 0)) + 1
            self._record_customer_outcome(self.active_customer, "fraud_detected")
        self._record_item_encounter(item, "appraisal")
        self._check_achievements("appraise", {"method": method, "detected_fake": detects_fake})
        return {
            "success": True,
            "cost": cost,
            "method": method,
            "method_name": method_info["name_cn"],
            "is_fake": item.is_appraised_fake,
            "verdict": item.appraisal_verdict,
            "confidence": item.appraisal_confidence,
            "appraised_value": item.appraised_value,
            "appraised_value_low": item.appraised_value_low,
            "appraised_value_high": item.appraised_value_high,
            "notes": item.appraisal_notes,
        }

    async def async_appraise_active_item(self, ai_client, method: str = "standard") -> Dict[str, Any]:
        result = self.appraise_active_item(method)
        if "error" in result or not self.active_customer:
            return result
        item = self.active_customer.item
        appraisal_item = item.to_dict()
        appraisal_item.pop("actual_value", None)
        appraisal_item.pop("is_fake", None)
        appraisal_item.pop("appraised_value", None)
        appraisal_item.pop("appraised_value_low", None)
        appraisal_item.pop("appraised_value_high", None)
        appraisal_item.pop("is_appraised_fake", None)
        ai_notes = await ai_client.generate_appraisal_notes(
            appraisal_item,
            method,
            str(result.get("verdict") or "未见明显作伪"),
            int(result.get("confidence") or 0),
            int(result.get("appraised_value_low") or result.get("appraised_value") or 0),
            int(result.get("appraised_value_high") or result.get("appraised_value") or 0),
        )
        if ai_notes:
            item.appraisal_notes = ai_notes
            result["notes"] = ai_notes
        return result

    def appraise_inventory_item(self, item_id: str, method: str = "standard", ai_notes: Optional[List[str]] = None) -> Dict[str, Any]:
        item = self.get_item(item_id)
        if not item:
            return {"error": "物品未在仓库中找到。"}
        if item.is_appraised_fake is not None:
            return {"error": "物品已经鉴定过了。"}
        method_info = APPRAISAL_METHODS.get(method, APPRAISAL_METHODS["standard"])
        facility_level = self.facilities["appraisal_room"]
        skill_level = self.skills["appraisal"]["level"]
        base_cost = max(160, int(item.market_value * 0.08 * self.economy_index))
        discount = 0.08 * (facility_level - 1) + (0.35 if self.staff["appraiser"] else 0)
        cost = max(120, int(base_cost * method_info["cost_multiplier"] * (1 - min(0.45, discount))))
        if self.cash < cost:
            return {"error": f"鉴定资金不足，需要 ${cost}。"}

        self.cash -= cost
        self.daily_summary["upgrades"] += cost
        accuracy = min(0.92, max(0.25, 0.45 + skill_level * 0.035 + facility_level * 0.04 + (0.12 if self.staff["appraiser"] else 0) + method_info["accuracy_bonus"]))
        detects_fake = item.is_fake and random.random() < accuracy
        item.is_appraised_fake = detects_fake if item.is_fake else False
        error_margin = max(0.06, float(method_info["value_margin"]) - (skill_level - 1) * 0.015 - (facility_level - 1) * 0.02 - (0.04 if self.staff["appraiser"] else 0))
        estimate_noise = random.uniform(-error_margin * 0.75, error_margin * 0.75)
        item.appraised_value = max(10, int(item.actual_value * (1 + estimate_noise)))
        item.appraised_value_low = max(10, int(item.appraised_value * (1 - error_margin)))
        item.appraised_value_high = max(item.appraised_value_low + 1, int(item.appraised_value * (1 + error_margin)))
        item.appraisal_confidence = int(accuracy * 100)
        item.appraisal_verdict = "发现明显作伪" if detects_fake else "未见明显作伪"
        fallback_notes = [
            f"鉴定方法：{method_info['name_cn']}。{method_info['desc']}",
            f"观察成色：{item.condition}，修复难度 {item.repair_difficulty}/5。",
            f"市场趋势系数：{self.market_trends.get(item.category, 1.0):.2f}。",
            f"年代线索：{item.era}；损坏记录：{item.damage_report}",
            f"估值区间约 ${item.appraised_value_low} - ${item.appraised_value_high}，结论可信度约 {item.appraisal_confidence}%。",
        ]
        item.appraisal_notes = ai_notes if ai_notes else fallback_notes

        self.add_skill_xp("appraisal", method_info["xp"])
        self._record_transaction("appraisal_fee", item, -cost)
        self._check_achievements("appraise", {"method": method, "detected_fake": detects_fake})
        return {
            "cost": cost,
            "method_name": method_info["name_cn"],
            "is_fake": item.is_appraised_fake,
            "verdict": item.appraisal_verdict,
            "confidence": item.appraisal_confidence,
            "appraised_value": item.appraised_value,
            "appraised_value_low": item.appraised_value_low,
            "appraised_value_high": item.appraised_value_high,
            "notes": item.appraisal_notes,
        }

    async def async_appraise_inventory_item(self, ai_client, item_id: str, method: str = "standard") -> Dict[str, Any]:
        result = self.appraise_inventory_item(item_id, method)
        if "error" in result:
            return result
        item = self.get_item(item_id)
        if not item:
            return result
        appraisal_item = item.to_dict()
        appraisal_item.pop("actual_value", None)
        appraisal_item.pop("is_fake", None)
        appraisal_item.pop("appraised_value", None)
        appraisal_item.pop("appraised_value_low", None)
        appraisal_item.pop("appraised_value_high", None)
        appraisal_item.pop("is_appraised_fake", None)
        ai_notes = await ai_client.generate_appraisal_notes(
            appraisal_item,
            method,
            str(result.get("verdict") or "未见明显作伪"),
            int(result.get("confidence") or 0),
            int(result.get("appraised_value_low") or result.get("appraised_value") or 0),
            int(result.get("appraised_value_high") or result.get("appraised_value") or 0),
        )
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
        self._record_item_encounter(item, "display")
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
        self._record_item_encounter(item, "storage")
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
        cost = max(60, int(item.market_value * (0.08 + item.repair_difficulty * 0.015) * self.economy_index * (1 - 0.05 * (facility_level - 1) - 0.03 * (skill_level - 1))))
        if self.staff["restorer"]:
            cost = int(cost * 0.75)
        cost = max(30, int(cost * method_info["cost_multiplier"]))
        if self.cash < cost:
            return {"error": f"修复资金不足，需要 ${cost}。"}

        self.cash -= cost
        item.status = "repairing"
        item.display_slot = None
        item.repair_days_remaining = max(1, item.repair_difficulty - facility_level // 2 + int(method_info["days_delta"]))
        item.repair_success_bonus = float(method_info["success_bonus"])
        notes = ai_notes or [
            f"修复方案：{method_info['name_cn']}。{method_info['desc']}",
            f"损坏记录：{item.damage_report}",
            f"预计 {item.repair_days_remaining} 天完成，工坊等级 Lv.{facility_level}。",
        ]
        item.appraisal_notes = list(item.appraisal_notes) + notes
        self.daily_summary["upgrades"] += cost
        self.add_skill_xp("restoration", int(method_info["xp"]))
        self._record_item_encounter(item, "repair_started")
        return {"success": True, "message": f"【{item.name}】已按【{method_info['name_cn']}】送入修复工坊，预计 {item.repair_days_remaining} 天完成。", "cost": cost, "method": method, "method_name": method_info["name_cn"], "notes": notes}

    async def async_start_repair(self, ai_client, item_id: str, method: str = "standard") -> Dict[str, Any]:
        item = self.get_item(item_id)
        if not item:
            return {"error": "未找到该物品。"}
        method_info = REPAIR_METHODS.get(method, REPAIR_METHODS["standard"])
        facility_level = self.facilities["restoration_workshop"]
        skill_level = self.skills["restoration"]["level"]
        preview_cost = max(60, int(item.market_value * (0.08 + item.repair_difficulty * 0.015) * self.economy_index * (1 - 0.05 * (facility_level - 1) - 0.03 * (skill_level - 1))))
        if self.staff["restorer"]:
            preview_cost = int(preview_cost * 0.75)
        preview_cost = max(30, int(preview_cost * method_info["cost_multiplier"]))
        preview_days = max(1, item.repair_difficulty - facility_level // 2 + int(method_info["days_delta"]))
        ai_notes = await ai_client.generate_repair_notes(item.to_dict(), method, preview_days, preview_cost)
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
        self._record_item_encounter(item, "direct_sell")
        self._check_achievements("direct_sell", {"item": item.to_dict(), "price": price})
        message = f"你通过渠道卖出了【{item.name}】，收入 ${price}。"
        if active_buyer_waiting:
            if self._retarget_buyer(self.active_customer, item_id):
                message += f" {active_buyer_name}看中的货已经售出，但他转而想看看【{self.active_customer.item.name}】，谈判仍可继续。"
            else:
                self.select_next_customer()
                message += f" {active_buyer_name}看中的货已经售出，店里暂无其他可售藏品，只好先离开。"
        self._repair_buyer_queue_after_item_removed(item_id)
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
            item.acquired_day = self.day
            item.last_value_update_day = self.day
            item.base_value_at_purchase = item.market_value
            item.holding_cost_paid = 0
            item.value_history = [{"day": self.day, "market_value": item.market_value, "delta": 0, "holding_cost": 0}]
            item.value_trend_note = "今天刚入库，尚未产生持有成本。"
            item.status = "stored"
            self.inventory.append(item)
            self.daily_summary["revenue"] -= price
            self._record_item_encounter(item, "acquired")
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
            self._record_item_encounter(item, "customer_sale")
            message = "交易成功！你卖出了该物品。"
            tx_type = "sell"

        dialogue = "合作愉快，这笔买卖就这么定了！"
        customer.dialogue_history.append({"role": "customer", "content": dialogue})
        self.transaction_log.append({"day": self.day, "type": tx_type, "item": item.name, "amount": -price if tx_type == "buy" else price})
        self.add_skill_xp("negotiation", 25)
        self.successful_trades += 1
        self.positive_reviews += 1 if random.random() < 0.75 else 0
        self.reputation += 1
        self._record_customer_outcome(customer, "deal", price, item)
        if tx_type == "sell":
            self.add_skill_xp("commerce", 20)
            self._repair_buyer_queue_after_item_removed(item.id)
        self.select_next_customer()
        self._check_achievements("deal", {"type": tx_type, "item": item.to_dict(), "price": price})
        return {"success": True, "message": message, "price_transacted": price, "dialogue": dialogue}

    def reject(self) -> Dict[str, Any]:
        if not self.active_customer:
            return {"error": "没有活跃的顾客。"}
        self._record_customer_outcome(self.active_customer, "reject")
        self.select_next_customer()
        self._check_achievements("reject")
        return {"success": True, "message": "已拒绝交易。下一位顾客！"}

    def hire_staff(self, staff_type: str) -> Dict[str, Any]:
        if staff_type not in STAFF_TYPES:
            return {"error": "未知的职员类型。"}
        if self.staff[staff_type]:
            return {"error": "你已经雇佣了该岗位的员工！"}
        cost = int(STAFF_TYPES[staff_type]["hire_cost"] * self.economy_index)
        if self.cash < cost:
            return {"error": f"招聘资金不足，需要花费 ${cost}。"}
        self.cash -= cost
        self.staff[staff_type] = True
        self.daily_summary["upgrades"] += cost
        self._check_achievements("hire", {"staff_type": staff_type})
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
        cost = int(SHOP_UPGRADE_COSTS[next_lvl]["cost"] * self.economy_index)
        if self.cash < cost:
            return {"error": f"店铺升级资金不足，需要 ${cost}。"}
        self.cash -= cost
        self.shop_level = next_lvl
        self.daily_summary["upgrades"] += cost
        self._check_achievements("upgrade_shop")
        return {"success": True, "message": f"店铺升级成功！当前等级：Lv.{self.shop_level} ({SHOP_UPGRADE_COSTS[next_lvl]['desc']})"}

    def facility_upgrade_cost(self, facility: str) -> Optional[int]:
        if facility not in FACILITY_INFO:
            return None
        level = self.facilities[facility]
        if level >= 5:
            return None
        return int(FACILITY_INFO[facility]["base_cost"] * (level ** 1.65) * self.economy_index)

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
        self._check_achievements("upgrade_facility", {"facility": facility})
        return {"success": True, "message": f"【{FACILITY_INFO[facility]['name_cn']}】升级到 Lv.{self.facilities[facility]}。"}

    def borrow_loan(self, amount: int) -> Dict[str, Any]:
        amount = int(amount)
        max_principal = int((20000 + self.shop_level * 8000) * max(0.85, self.economy_index))
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

    def _process_repairs(self) -> List[str]:
        events: List[str] = []
        for item in list(self.inventory):
            if item.status != "repairing":
                continue
            item.repair_days_remaining -= 1 + (1 if self.staff["restorer"] and random.random() < 0.35 else 0)
            if item.repair_days_remaining > 0:
                continue
            success_chance = min(0.97, 0.55 + self.skills["restoration"]["level"] * 0.035 + self.facilities["restoration_workshop"] * 0.06 + (0.12 if self.staff["restorer"] else 0) + float(getattr(item, "repair_success_bonus", 0.0)))
            old_condition = item.condition
            if random.random() < success_chance:
                item.condition = CONDITION_UPGRADE.get(item.condition, item.condition)
                item.actual_value = int(item.actual_value * (1.45 if item.condition == "Good" else 1.7))
                item.market_value = int(item.market_value * (1.35 if item.condition == "Good" else 1.55))
                events.append(f"修复完成：【{item.name}】成色从 {old_condition} 提升到 {item.condition}。")
                self.add_skill_xp("restoration", 40)
                self.achievement_stats["repairs_completed"] = int(self.achievement_stats.get("repairs_completed", 0)) + 1
            else:
                item.actual_value = max(10, int(item.actual_value * 0.92))
                events.append(f"修复意外：【{item.name}】修复失败，价值略有受损。")
                self.achievement_stats["repair_failures"] = int(self.achievement_stats.get("repair_failures", 0)) + 1
            item.status = "stored"
            item.repair_days_remaining = 0
            item.repair_success_bonus = 0.0
            self._record_item_encounter(item, "repair_completed")
        if events:
            self._check_achievements("repair")
        return events

    def _generate_pending_event(self) -> Optional[Dict[str, Any]]:
        quiet_days = int(self.achievement_stats.get("quiet_event_days", 0))
        if quiet_days < EVENT_GUARANTEE_AFTER_QUIET_DAYS and random.random() > EVENT_BASE_CHANCE:
            self.achievement_stats["quiet_event_days"] = quiet_days + 1
            return None

        self.achievement_stats["quiet_event_days"] = 0
        event = deepcopy(random.choice(LOCAL_EVENT_TEMPLATES))
        event["id"] = str(uuid.uuid4())[:8]
        event["local_generated"] = True
        return event

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
                        "economy_index": self.economy_index,
                        "economic_pressure": self.economic_pressure,
                        "money_supply_score": self.money_supply_score,
                    }
                )
            )
            if ai_event:
                self.pending_event = ai_event
                if self.daily_summary["events"] and self.daily_summary["events"][-1].startswith("待处理事件："):
                    self.daily_summary["events"][-1] = f"待处理事件：{ai_event['title']}。"
        return self.daily_summary

    def _roll_event_amount(self, value: Any) -> int:
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            low = int(value[0])
            high = int(value[1])
            return random.randint(min(low, high), max(low, high))
        return int(value or 0)

    def _apply_event_mitigation(self, cash_delta: int, mitigation: Optional[Dict[str, Any]]) -> int:
        if cash_delta >= 0 or not mitigation:
            return cash_delta
        loss = abs(cash_delta)
        facility = mitigation.get("facility")
        if facility in self.facilities:
            loss -= self.facilities[facility] * int(mitigation.get("per_level", 0))
        staff = mitigation.get("staff")
        if staff in self.staff and self.staff[staff]:
            loss -= int(mitigation.get("staff_bonus", 0))
        return -max(int(mitigation.get("min_loss", 0)), loss)

    def _resolve_structured_event_choice(self, event: Dict[str, Any], choice: Dict[str, Any]) -> Dict[str, Any]:
        outcome = choice.get("outcome") if isinstance(choice.get("outcome"), dict) else choice
        cash_delta = self._roll_event_amount(outcome.get("cash_delta", 0))
        cash_delta = self._apply_event_mitigation(cash_delta, outcome.get("mitigate_by") if isinstance(outcome.get("mitigate_by"), dict) else None)
        reputation_delta = int(outcome.get("reputation_delta") or 0)

        self.cash += cash_delta
        self.reputation += reputation_delta
        if cash_delta > 0:
            self.daily_summary["revenue"] = int(self.daily_summary.get("revenue", 0)) + cash_delta

        skill = outcome.get("skill")
        if skill in SKILL_INFO:
            self.add_skill_xp(skill, int(outcome.get("skill_xp") or 0))

        message = f"{choice.get('label')}：{choice.get('effect')}"
        if cash_delta:
            message += f"，现金{'+' if cash_delta > 0 else ''}${cash_delta}"
        if reputation_delta:
            message += f"，声誉{'+' if reputation_delta > 0 else ''}{reputation_delta}"

        market_shift = float(outcome.get("market_shift") or 0)
        if market_shift:
            category = random.choice(list(self.market_trends.keys()))
            self.market_trends[category] = round(max(0.72, min(1.6, self.market_trends[category] + market_shift)), 2)
            message += f"，{category} 市场系数调整至 {self.market_trends[category]:.2f}"

        self.daily_summary["events"].append(f"{event['title']}：{message}")
        self.pending_event = None
        self.daily_summary["ending_cash"] = self.cash
        self.daily_summary["net_profit"] = self.cash - self.daily_summary.get("starting_cash", self.cash)
        self._check_achievements("event", {"title": event["title"], "choice": choice.get("id")})
        return {"success": True, "message": message}

    def resolve_event(self, choice_id: str) -> Dict[str, Any]:
        if not self.pending_event:
            return {"error": "当前没有待处理事件。"}
        event = self.pending_event
        title = event["title"]
        message = ""
        choice = next((item for item in event.get("choices", []) if item.get("id") == choice_id), None)
        if event.get("ai_generated") or event.get("local_generated"):
            if not choice:
                return {"error": "未知的事件选择。"}
            return self._resolve_structured_event_choice(event, choice)
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
        self._check_achievements("event", {"title": title, "choice": choice_id})
        return {"success": True, "message": message}

    def end_day(self) -> Dict[str, Any]:
        if self.day_ended:
            return {"error": "今天已经结算过了！"}
        self.day_ended = True

        economy_entry = self._apply_economy_tick()
        salary_total = int(sum(STAFF_TYPES[s]["daily_salary"] for s, active in self.staff.items() if active) * self.economy_index)
        commerce_discount = min(0.25, (self.skills["commerce"]["level"] - 1) * 0.025)
        operating_cost = int((260 + self.shop_level * 90 + sum(self.facilities.values()) * 18) * self.economy_index * (1 - commerce_discount))
        interest_rate = self.loan["interest_rate"] + max(0, self.inflation_rate) * 0.5
        interest = max(1, round(self.loan["principal"] * interest_rate)) if self.loan["principal"] else 0
        tax_due = 0
        if self.day >= self.tax["next_due_day"]:
            taxable = max(0, self.cash - self.daily_summary["starting_cash"])
            tax_due = int(taxable * (self.tax["rate"] + max(0, self.economy_index - 1.0) * 0.015))
            self.tax["last_paid"] = tax_due
            self.tax["next_due_day"] = self.day + 7

        inventory_tick = self._apply_inventory_value_tick()
        holding_cost = int(inventory_tick["holding_cost"])
        self.cash -= salary_total + operating_cost + interest + tax_due
        self.daily_summary["salaries"] = salary_total
        self.daily_summary["operating_cost"] = operating_cost
        self.daily_summary["loan_interest"] = interest
        self.daily_summary["tax"] = tax_due
        self.daily_summary["holding_cost"] = holding_cost
        self.daily_summary["economy_index"] = self.economy_index
        self.daily_summary["inflation_rate"] = self.inflation_rate
        self.daily_summary["economy_pressure"] = self.economic_pressure
        if economy_entry["pressure"] != "stable":
            label = "通胀" if economy_entry["pressure"] == "inflation" else "通缩"
            self.daily_summary["events"].append(f"宏观环境进入{label}压力，经济指数 {self.economy_index:.3f}。")
        if holding_cost:
            self.daily_summary["events"].append(f"库存持有成本 ${holding_cost}，{inventory_tick['changed_items']} 件藏品完成时间价值结算。")
        if inventory_tick["value_delta"]:
            direction = "增值" if inventory_tick["value_delta"] > 0 else "折价"
            self.daily_summary["events"].append(f"库存估值整体{direction} ${abs(int(inventory_tick['value_delta']))}。")
        if interest:
            self.daily_summary["events"].append(f"银行按动态利率 {interest_rate * 100:.1f}% 收取贷款利息 ${interest}。")

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
        self._check_achievements("end_day")
        return self.daily_summary

    def to_dict(self) -> Dict[str, Any]:
        self.ensure_active_customer_target()
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
            "economy_index": self.economy_index,
            "inflation_rate": self.inflation_rate,
            "money_supply_score": self.money_supply_score,
            "economic_pressure": self.economic_pressure,
            "economy_history": self.economy_history[-30:],
            "pending_event": self.pending_event,
            "shop_name": self.shop_name,
            "reputation": self.reputation,
            "total_profit": self.total_profit,
            "successful_trades": self.successful_trades,
            "positive_reviews": self.positive_reviews,
            "customer_registry": self.customer_registry,
            "customer_codex": self.customer_codex,
            "item_codex": self.item_codex,
            "achievements": self.achievement_list(),
            "achievement_unlocks": self.achievement_unlocks[-12:],
            "achievement_stats": self.achievement_stats,
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
        inventory_data = list(data.get("inventory", []))
        state.inventory = [Item.from_dict(item) for item in inventory_data]
        for item_data, item in zip(inventory_data, state.inventory):
            if "acquired_day" not in item_data:
                item.acquired_day = state.day
                item.last_value_update_day = state.day
                item.base_value_at_purchase = item.market_value
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
        state.economy_index = float(data.get("economy_index", 1.0))
        state.inflation_rate = float(data.get("inflation_rate", 0.0))
        state.money_supply_score = int(data.get("money_supply_score", state.cash))
        state.economic_pressure = data.get("economic_pressure", "stable")
        state.economy_history = list(data.get("economy_history", []))[-30:]
        state.pending_event = data.get("pending_event")
        state.shop_name = data.get("shop_name", "无名当铺")
        state.reputation = int(data.get("reputation", 100))
        state.total_profit = int(data.get("total_profit", 0))
        state.successful_trades = int(data.get("successful_trades", 0))
        state.positive_reviews = int(data.get("positive_reviews", 0))
        state.customer_registry = {
            str(key): dict(value)
            for key, value in (data.get("customer_registry") or {}).items()
            if isinstance(value, dict)
        }
        state.customer_codex = {
            str(key): dict(value)
            for key, value in (data.get("customer_codex") or {}).items()
            if isinstance(value, dict)
        }
        state.item_codex = {
            str(key): dict(value)
            for key, value in (data.get("item_codex") or {}).items()
            if isinstance(value, dict)
        }
        if not state.customer_codex:
            for key, record in state.customer_registry.items():
                state.customer_codex[key] = {
                    **record,
                    "trait_cn": CUSTOMER_TRAITS.get(record.get("trait", "hesitant"), CUSTOMER_TRAITS["hesitant"])["name_cn"],
                    "trait_desc": CUSTOMER_TRAITS.get(record.get("trait", "hesitant"), CUSTOMER_TRAITS["hesitant"])["desc"],
                    "first_seen_day": int(record.get("last_visit_day", state.day)),
                    "last_seen_day": int(record.get("last_visit_day", state.day)),
                    "times_seen": int(record.get("visit_count", 1)),
                    "sources": ["legacy_relationship"],
                }
        if not state.item_codex:
            for item in state.inventory + state.sold_items:
                state._record_item_encounter(item, "legacy_inventory")
        state.achievements = {
            str(item.get("id") or key): dict(item)
            for key, item in (data.get("achievements") or {}).items()
            if isinstance(item, dict)
        } if isinstance(data.get("achievements"), dict) else {
            str(item.get("id")): {"id": str(item.get("id")), "progress": int(item.get("progress", 0)), "target": int(item.get("target", 1)), "unlocked": bool(item.get("unlocked")), "unlocked_day": item.get("unlocked_day")}
            for item in (data.get("achievements") or [])
            if isinstance(item, dict) and item.get("id")
        }
        state.achievement_unlocks = list(data.get("achievement_unlocks", []))[-12:]
        state.achievement_stats = {
            **state.achievement_stats,
            **{key: int(value) for key, value in (data.get("achievement_stats") or {}).items() if isinstance(value, (int, float))},
        }
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
            "holding_cost": 0,
            "economy_index": state.economy_index,
            "inflation_rate": state.inflation_rate,
            "events": [],
            "starting_cash": state.cash,
            "ending_cash": state.cash,
            "net_profit": 0,
        }
        return state
