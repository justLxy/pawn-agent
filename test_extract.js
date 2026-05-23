function extractOffer(text) {
  const regex = /(?:出|给|卖|要|报价|成交|拿走|一口价|就|最多|最少)\s*(\d+(?:,\d{3})*)/g;
  let match;
  let lastMatch = null;
  while ((match = regex.exec(text)) !== null) {
    lastMatch = match[1];
  }
  if (lastMatch) {
    return parseInt(lastMatch.replaceAll(',', ''), 10);
  }

  // Fallback to the first number that is NOT preceded by 便宜, 市场价, 亏, 赚, 加, 减, 贵, 高, 低
  const allMatches = [...text.matchAll(/(?<!便宜|市场价|亏|赚|加|减|贵|高|低)\s*(\d+(?:,\d{3})*)/g)];
  if (allMatches.length > 0) {
     // return the first one? or largest?
     return parseInt(allMatches[0][1].replaceAll(',', ''), 10);
  }

  const matches = text.match(/\d+(?:,\d{3})*/g);
  if (!matches?.length) return null;
  return parseInt(matches[matches.length - 1].replaceAll(',', ''), 10);
}

console.log(extractOffer("20000卖，比市场价便宜2000")); // 20000
console.log(extractOffer("便宜2000，我出20000")); // 20000
console.log(extractOffer("市场价20000，我出15000")); // 15000
console.log(extractOffer("我出15000，市场价20000")); // 15000
console.log(extractOffer("20000")); // 20000
console.log(extractOffer("给你 5000 块")); // 5000
console.log(extractOffer("太贵了，便宜 200 吧，800 成交")); // 800
