import re

def extract_offer(text):
    # Try to find numbers preceded by action keywords
    action_pattern = r"(?:出|给|卖|要|报价|成交|拿走|一口价|就|最多|最少)\s*(\d+(?:,\d{3})*)"
    matches = re.findall(action_pattern, text)
    if matches:
        return int(matches[-1].replace(',', ''))
        
    # Fallback to finding numbers not preceded by relative keywords
    # Python re doesn't support variable-length negative lookbehind, so we can't do (?<!便宜|市场价)
    # Instead, we can find all numbers and their preceding context
    all_numbers = list(re.finditer(r"\d+(?:,\d{3})*", text))
    if not all_numbers:
        return None
        
    for match in all_numbers:
        start = match.start()
        # Look at the 5 characters before the number
        context = text[max(0, start-5):start]
        if not any(k in context for k in ["便宜", "市场", "亏", "赚", "加", "减", "贵", "高", "低", "多", "少"]):
            return int(match.group().replace(',', ''))
            
    # If all numbers have relative keywords, just return the first one
    return int(all_numbers[0].group().replace(',', ''))

print(extract_offer("20000卖，比市场价便宜2000"))
print(extract_offer("便宜2000，我出20000"))
print(extract_offer("市场价20000，我出15000"))
print(extract_offer("我出15000，市场价20000"))
print(extract_offer("20000"))
print(extract_offer("给你 5000 块"))
print(extract_offer("太贵了，便宜 200 吧，800 成交"))
