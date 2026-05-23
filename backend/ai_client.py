import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from env_loader import load_env_file

load_env_file()

logger = logging.getLogger(__name__)

API_URL = os.getenv("DOUBAO_API_URL", "https://ark.cn-beijing.volces.com/api/v3/chat/completions")
MODEL_ENDPOINT = os.getenv("DOUBAO_MODEL_ENDPOINT", "ep-20260215154235-cjxx7")


class AIClient:
    def __init__(self):
        self.api_key = os.getenv("DOUBAO_API_KEY", "")
        self.model = MODEL_ENDPOINT
        self.api_url = API_URL

    def available(self) -> bool:
        return bool(self.api_key)

    async def _chat_json(self, system_prompt: str, user_message: str, timeout: float = 10.0) -> Dict[str, Any]:
        if not self.available():
            raise RuntimeError("DOUBAO_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.api_url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.7,
                    "reasoning_effort": "low",
                    "response_format": {"type": "json_object"},
                },
            )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    async def generate_random_content(self, prompt_type: str, context: Optional[Dict[str, Any]] = None) -> str:
        context = context or {}
        if not self.available():
            return ""
        if prompt_type == "customer_name":
            system_prompt = "你是一个起名专家。请随机生成一个中文姓名，或带有市井气息的当铺顾客称呼。只输出名字。"
        elif prompt_type == "item_details":
            category = context.get("category", "未知")
            system_prompt = f"生成一件属于【{category}】的当铺交易物品。严格输出 JSON：{{\"name\":\"物品名称\",\"desc\":\"30字以内背景描述\"}}。"
        else:
            return ""
        try:
            timeout = 6.0 if prompt_type == "customer_name" else 15.0
            payload = {
                "model": self.model,
                "messages": [{"role": "system", "content": system_prompt}],
                "temperature": 0.9,
                "reasoning_effort": "low",
            }
            if prompt_type == "item_details":
                payload["response_format"] = {"type": "json_object"}

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            logger.warning("AI content generation failed: %s %s", response.status_code, response.text)
        except Exception as exc:
            logger.warning("Failed to generate random content (%s): %s", type(exc).__name__, exc)
        return ""

    async def generate_item_details(self, category: str) -> Dict[str, str]:
        raw = await self.generate_random_content("item_details", {"category": category})
        if not raw:
            return {}
        try:
            if raw.startswith("```json"):
                raw = raw[7:-3].strip()
            elif raw.startswith("```"):
                raw = raw[3:-3].strip()
            parsed = json.loads(raw)
            return {
                "name": parsed.get("name", ""),
                "desc": parsed.get("desc", ""),
                "story": parsed.get("story", ""),
                "era": parsed.get("era", ""),
                "damage_report": parsed.get("damage_report", ""),
                "hidden_attrs": parsed.get("hidden_attrs", []),
                "special_effects": parsed.get("special_effects", []),
                "authentication_tips": parsed.get("authentication_tips", []),
            }
        except Exception as exc:
            logger.warning("Failed to parse AI item JSON: %s - %s", exc, raw)
            return {}

    async def generate_deep_item(self, category: str, rarity: str, condition: str, value_hint: int) -> Dict[str, Any]:
        if not self.available():
            return {}
        system_prompt = f"""你是《当铺代理人》的物品生成器。生成一件当铺交易物品，分类 {category}，稀有度 {rarity}，成色 {condition}，价值约 {value_hint}。
严格输出 JSON：{{"name":"物品名","desc":"30字内描述","story":"80字内历史故事","era":"年代/时期","damage_report":"损坏情况","hidden_attrs":["隐藏属性"],"special_effects":["经营影响或收藏亮点"],"authentication_tips":["真伪鉴别要点"]}}。"""
        try:
            result = await self._chat_json(system_prompt, "生成物品。", timeout=15.0)
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            logger.warning("AI deep item generation failed: %s", exc)
            return {}

    async def generate_customer_profile(self, role: str, trait: str, item_name: str, category: str) -> Dict[str, Any]:
        if not self.available():
            return {}
        system_prompt = f"""你是《当铺代理人》的顾客生成器。顾客角色：{role}，性格：{trait}，围绕物品【{item_name}】分类 {category}。
严格输出 JSON：{{"name":"中文姓名或市井称呼","age":整数,"appearance":"外貌衣着","backstory":"来当铺原因，60字内","transaction_prefs":["交易偏好"],"persuasion_points":["容易被说服的点"],"fraud_intent":布尔}}。"""
        try:
            result = await self._chat_json(system_prompt, "生成顾客。", timeout=12.0)
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            logger.warning("AI customer profile generation failed: %s", exc)
            return {}

    async def generate_random_event(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available():
            return {}
        system_prompt = f"""你是《当铺代理人》的随机事件导演。根据状态生成一个当铺经营随机事件。
状态：当铺等级 {context.get("shop_level")}，现金 {context.get("cash")}，天数 {context.get("day")}，声誉 {context.get("reputation")}。
事件类型可包含抢劫、诈骗、名人来访、稀有物品出现、市场波动、法律纠纷、员工问题。
严格输出 JSON：{{"title":"事件标题","description":"80字内描述","type":"theft|scam|celebrity|rare_item|market|legal|staff","choices":[{{"id":"a","label":"选择文案","effect":"预期效果","cash_delta":整数,"reputation_delta":整数,"skill":"negotiation|appraisal|restoration|charm|commerce|null","skill_xp":整数}}]}}。必须给 2 个 choices。"""
        try:
            result = await self._chat_json(system_prompt, "生成事件。", timeout=14.0)
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            logger.warning("AI event generation failed: %s", exc)
            return {}

    async def generate_appraisal_notes(self, item: Dict[str, Any], method: str, is_fake_result: bool, appraised_value: int) -> List[str]:
        if not self.available():
            return []
        system_prompt = """你是当铺鉴定师。根据物品资料和玩家选择的鉴定方法，输出 JSON：{"notes":["鉴定步骤或发现"]}，3到5条，文字短而有画面感。"""
        try:
            result = await self._chat_json(
                system_prompt,
                json.dumps({"item": item, "method": method, "is_fake_result": is_fake_result, "appraised_value": appraised_value}, ensure_ascii=False),
                timeout=10.0,
            )
            notes = result.get("notes", [])
            return [str(note) for note in notes[:5]] if isinstance(notes, list) else []
        except Exception as exc:
            logger.warning("AI appraisal notes failed: %s", exc)
            return []

    async def generate_repair_notes(self, item: Dict[str, Any], method: str, days: int, cost: int) -> List[str]:
        if not self.available():
            return []
        system_prompt = """你是当铺修复师。根据物品资料和玩家选择的修复方案，输出 JSON：{"notes":["修复步骤或风险"]}，3到5条。"""
        try:
            result = await self._chat_json(
                system_prompt,
                json.dumps({"item": item, "method": method, "days": days, "cost": cost}, ensure_ascii=False),
                timeout=10.0,
            )
            notes = result.get("notes", [])
            return [str(note) for note in notes[:5]] if isinstance(notes, list) else []
        except Exception as exc:
            logger.warning("AI repair notes failed: %s", exc)
            return []

    async def parse_player_negotiation(self, message: str, explicit_offer: Optional[int] = None) -> Dict[str, Any]:
        if explicit_offer and explicit_offer > 0:
            return {"offer": explicit_offer, "intent": "offer", "confidence": 1.0}
        if self.available():
            system_prompt = """你负责解析玩家在当铺谈判里的自然语言。严格输出 JSON：
{"offer": 整数或null, "intent": "offer|accept|reject|question|persuade", "confidence": 0到1}
只提取玩家明确表达的价格，不能编造。"""
            try:
                result = await self._chat_json(system_prompt, message, timeout=6.0)
                offer = result.get("offer")
                return {
                    "offer": int(offer) if offer else None,
                    "intent": result.get("intent", "persuade"),
                    "confidence": float(result.get("confidence", 0.5)),
                }
            except Exception as exc:
                logger.warning("AI negotiation parse failed, using fallback: %s", exc)
        return self._parse_offer_fallback(message)

    def _parse_offer_fallback(self, message: str) -> Dict[str, Any]:
        lowered = message.lower()
        if any(token in lowered for token in ["成交", "就这样", "同意", "可以", "accept"]):
            intent = "accept"
        elif any(token in lowered for token in ["不卖", "不买", "算了", "拒绝", "走吧"]):
            intent = "reject"
        elif any(token in lowered for token in ["为什么", "来历", "真假", "鉴定", "吗", "?"]):
            intent = "question"
        else:
            intent = "persuade"

        arabic = re.findall(r"\d+(?:,\d{3})*", message)
        if arabic:
            return {"offer": int(arabic[-1].replace(",", "")), "intent": "offer", "confidence": 0.9}

        chinese_offer = self._parse_chinese_amount(message)
        if chinese_offer:
            return {"offer": chinese_offer, "intent": "offer", "confidence": 0.75}
        return {"offer": None, "intent": intent, "confidence": 0.45}

    def _parse_chinese_amount(self, message: str) -> Optional[int]:
        digits = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        match = re.search(r"([一二两三四五六七八九十百千万零]+)\s*(?:块|元|刀)?", message)
        if not match:
            return None
        text = match.group(1)
        total = 0
        section = 0
        number = 0
        units = {"十": 10, "百": 100, "千": 1000}
        for char in text:
            if char in digits:
                number = digits[char]
            elif char in units:
                section += (number or 1) * units[char]
                number = 0
            elif char == "万":
                total += (section + number) * 10000
                section = 0
                number = 0
        total += section + number
        return total or None

    async def generate_negotiation(
        self,
        customer_name: str,
        trait: str,
        trait_desc: str,
        role: str,
        item_name: str,
        item_category: str,
        item_condition: str,
        is_fake: bool,
        actual_value: int,
        limit_price: int,
        current_offer: int,
        player_message: str,
        player_offer: Optional[int],
        intent: str,
        patience: int,
        negotiation_level: int,
        charm_level: int,
        dialogue_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        if player_offer is None and intent == "accept":
            player_offer = current_offer
        if player_offer is None:
            player_offer = current_offer

        history = ""
        for turn in dialogue_history[-8:]:
            speaker = "玩家" if turn["role"] == "player" else "顾客"
            history += f"{speaker}: {turn['content']}\n"

        if self.available():
            system_prompt = f"""你是文字经营游戏《当铺代理人》中的 AI 顾客。
姓名：{customer_name}
性格：{trait_desc} ({trait})
角色：{"买家，要从玩家店里买东西" if role == "buyer" else "卖家，要把东西卖给玩家"}
物品：{item_name}，分类 {item_category}，成色 {item_condition}
赝品状态：{is_fake}
你的心理底线/上限价：{limit_price}
当前报价：{current_offer}
玩家解析意图：{intent}
玩家报价：{player_offer}
玩家谈判技能：{negotiation_level}，魅力：{charm_level}
耐心值：{patience}/8

输出严格 JSON：{{"dialogue":"顾客第一人称回复","new_offer":整数,"patience_change":整数,"accepted":布尔,"walk_out":布尔}}
必须遵守交易利益：卖家只在玩家出价接近或高于底线时成交；买家只在玩家售价接近或低于上限时成交。技能可让你多一点耐心或小幅让步。"""
            try:
                result = await self._chat_json(system_prompt, f"历史：\n{history}\n玩家最新发言：{player_message}", timeout=14.0)
                return self._normalize_negotiation_result(result, current_offer, player_offer)
            except Exception as exc:
                logger.warning("AI negotiation failed, using fallback: %s", exc)

        return self._calculate_algorithmic_fallback(
            role=role,
            trait=trait,
            limit_price=limit_price,
            current_offer=current_offer,
            player_offer=player_offer,
            patience=patience,
            intent=intent,
            negotiation_level=negotiation_level,
            charm_level=charm_level,
        )

    def _as_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ["true", "1", "yes", "是", "成交"]
        return bool(value)

    def _normalize_negotiation_result(self, result: Dict[str, Any], current_offer: int, player_offer: int) -> Dict[str, Any]:
        return {
            "dialogue": str(result.get("dialogue", "嗯，我再想想这个价。")),
            "new_offer": max(1, int(result.get("new_offer", current_offer))),
            "patience_change": int(result.get("patience_change", 0)),
            "accepted": self._as_bool(result.get("accepted", False)),
            "walk_out": self._as_bool(result.get("walk_out", False)),
            "parsed_offer": player_offer,
        }

    def _calculate_algorithmic_fallback(
        self,
        role: str,
        trait: str,
        limit_price: int,
        current_offer: int,
        player_offer: int,
        patience: int,
        intent: str,
        negotiation_level: int,
        charm_level: int,
    ) -> Dict[str, Any]:
        if intent == "reject":
            return {"dialogue": "既然掌柜的没兴趣，那我就不打扰了。", "new_offer": current_offer, "patience_change": -1, "accepted": False, "walk_out": True, "parsed_offer": player_offer}

        skill_relief = 0.015 * negotiation_level + 0.01 * charm_level
        patience_change = 0
        accepted = False
        walk_out = False

        if role == "seller":
            acceptable = player_offer >= int(limit_price * (1 - skill_relief))
            if acceptable or intent == "accept":
                accepted = player_offer >= int(limit_price * 0.9)
                new_offer = player_offer if accepted else max(limit_price, int(current_offer * 0.96))
                dialogue = f"你这话说得还算有诚意。{player_offer} 元" + ("成交！" if accepted else f"还差点意思，最低 {new_offer}。")
            else:
                ratio = player_offer / max(1, current_offer)
                patience_change = -2 if ratio < 0.35 and trait in ["hardball", "fraud"] else -1
                if patience + patience_change <= 0:
                    walk_out = True
                    new_offer = current_offer
                    dialogue = "这价太离谱了，我不卖了。"
                else:
                    step = 0.18 + skill_relief
                    new_offer = max(limit_price, int(current_offer - (current_offer - limit_price) * step))
                    dialogue = f"你说得有点道理，但 {player_offer} 不够。这样，{new_offer} 元，别再压了。"
        else:
            acceptable = player_offer <= int(limit_price * (1 + skill_relief))
            if acceptable or intent == "accept":
                accepted = player_offer <= int(limit_price * 1.1)
                new_offer = player_offer if accepted else min(limit_price, int(current_offer * 1.05))
                dialogue = f"这个价我能考虑。" + ("成交，帮我包起来。" if accepted else f"不过最多 {new_offer}。")
            else:
                ratio = player_offer / max(1, current_offer)
                patience_change = -2 if ratio > 2.6 and trait in ["hardball", "expert"] else -1
                if patience + patience_change <= 0:
                    walk_out = True
                    new_offer = current_offer
                    dialogue = "你这价格太黑了，我还是去别家看看。"
                else:
                    step = 0.18 + skill_relief
                    new_offer = min(limit_price, int(current_offer + (limit_price - current_offer) * step))
                    dialogue = f"{player_offer} 太高。看在你会说话的份上，我能出到 {new_offer}。"

        if intent in ["question", "persuade"] and not accepted and not walk_out:
            patience_change = min(0, patience_change + (1 if charm_level >= 4 else 0))
        return {
            "dialogue": dialogue,
            "new_offer": max(1, new_offer),
            "patience_change": patience_change,
            "accepted": accepted,
            "walk_out": walk_out,
            "parsed_offer": player_offer,
        }
