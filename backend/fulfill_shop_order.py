#!/usr/bin/env python3
"""人工发货：核对微信到账后执行。

用法:
  SHOP_ADMIN_SECRET=你的密钥 python fulfill_shop_order.py PS123ABC
  SHOP_ADMIN_SECRET=你的密钥 python fulfill_shop_order.py --order-id xxxxx
"""

import argparse
import os
import sys

from env_loader import load_env_file

load_env_file()

from shop_service import fulfill_order  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="人工发放掌柜月卡/当铺匾额订单")
    parser.add_argument("order_ref", nargs="?", help="订单号 order_no（如 PS1A1B2C）")
    parser.add_argument("--order-id", dest="order_id", help="订单 id")
    args = parser.parse_args()
    if not args.order_ref and not args.order_id:
        parser.error("请提供 order_no 或 --order-id")
    if not os.getenv("SHOP_ADMIN_SECRET"):
        print("请设置环境变量 SHOP_ADMIN_SECRET（与服务器 .env 一致，仅本地脚本自检用）", file=sys.stderr)
    result = fulfill_order(order_id=args.order_id, order_no=args.order_ref if args.order_ref else None)
    order = result["order"]
    print(result["message"])
    print(f"  商品: {order['product_name']} ({order['price_label']})")
    print(f"  订单号: {order['order_no']}  状态: {order['status']}")
    cosmetics = result.get("cosmetics") or {}
    if cosmetics.get("is_sponsor"):
        print(f"  月卡到期: {cosmetics.get('monthly_expires_at')}")
    if cosmetics.get("has_plaque"):
        print(f"  匾额: {cosmetics.get('shop_emblem_label')} ({cosmetics.get('shop_emblem')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
