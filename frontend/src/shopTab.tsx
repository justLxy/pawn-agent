import { useCallback, useEffect, useState } from 'react';
import { Copy } from 'lucide-react';
import wechatPayQr from './assets/IMG_8915.JPG';
import { formatMonthlyExpiry, type PlayerCosmetics, SponsorSubtitle } from './cosmetics';

type ShopPlayer = PlayerCosmetics & {
  id: number;
  username: string;
  shop_name: string;
  ranking_badge: string | null;
  is_shop_admin?: boolean;
};

export interface ShopProduct {
  id: string;
  name: string;
  price_fen: number;
  price_label: string;
  description: string;
}

export interface ShopOrder {
  order_id: string;
  order_no: string;
  product_id: string;
  product_name: string;
  price_label?: string;
  status: string;
  payer_note?: string | null;
  created_at: number;
  submitted_at?: number | null;
  fulfilled_at?: number | null;
  pay_remark?: string;
  instructions?: string;
  reused?: boolean;
  username?: string;
  shop_name?: string;
}

export interface ShopSponsor {
  player_id: number;
  shop_name: string;
  username: string;
  is_sponsor: boolean;
  has_plaque: boolean;
  shop_emblem_label?: string | null;
  sponsor_title?: string | null;
}

interface ShopTabProps {
  player: ShopPlayer;
  apiGet: <T>(path: string) => Promise<T>;
  apiPost: <T>(path: string, body?: unknown) => Promise<T>;
  apiPatch: <T>(path: string, body?: unknown) => Promise<T>;
  onPlayerUpdate: (player: ShopPlayer) => void;
  onSuccess: (msg: string) => void;
  onError: (msg: string) => void;
}

const ORDER_STATUS: Record<string, string> = {
  pending: '待付款',
  submitted: '待发货',
  fulfilled: '已发放',
  cancelled: '已取消',
};

const FALLBACK_PRODUCTS: ShopProduct[] = [
  {
    id: 'monthly_card',
    name: '掌柜月卡',
    price_fen: 500,
    price_label: '¥5',
    description: '顶栏流光店招动效、排行榜赞助铭牌、称号「赞助掌柜」，30 天。',
  },
  {
    id: 'plaque_permanent',
    name: '当铺匾额（永久）',
    price_fen: 1000,
    price_label: '¥10',
    description: '店名旁匾额装饰；橱窗封面文案（最多 80 字）。',
  },
];

export function ShopTab({ player, apiGet, apiPost, apiPatch, onPlayerUpdate, onSuccess, onError }: ShopTabProps) {
  const [products, setProducts] = useState<ShopProduct[]>(FALLBACK_PRODUCTS);
  const [orders, setOrders] = useState<ShopOrder[]>([]);
  const [adminQueue, setAdminQueue] = useState<ShopOrder[]>([]);
  const [sponsors, setSponsors] = useState<ShopSponsor[]>([]);
  const [activeOrder, setActiveOrder] = useState<ShopOrder | null>(null);
  const [payerNote, setPayerNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [taglineDraft, setTaglineDraft] = useState(player.showcase_tagline || '');
  const [emblemDraft, setEmblemDraft] = useState(player.shop_emblem || 'plaque');
  const isAdmin = Boolean(player.is_shop_admin);

  const refresh = useCallback(async () => {
    const tasks: Promise<void>[] = [
      apiGet<{ products: ShopProduct[] }>('/api/shop/catalog').then((catalog) => {
        if (catalog.products?.length) setProducts(catalog.products);
      }),
      apiGet<{ orders: ShopOrder[] }>('/api/shop/orders').then((orderList) => setOrders(orderList.orders)),
      apiGet<{ sponsors: ShopSponsor[] }>('/api/shop/sponsors').then((data) => setSponsors(data.sponsors || [])),
    ];
    if (isAdmin) {
      tasks.push(
        apiGet<{ orders: ShopOrder[] }>('/api/shop/admin/queue').then((data) => setAdminQueue(data.orders)),
      );
    }
    await Promise.all(tasks);
  }, [apiGet, isAdmin]);

  useEffect(() => {
    refresh().catch((err) => onError(err instanceof Error ? err.message : '加载掌柜铺子失败。'));
  }, [refresh, onError]);

  const openOrderFor = (productId: string) =>
    orders.find((o) => o.product_id === productId && (o.status === 'pending' || o.status === 'submitted'));

  const resumeOrder = (order: ShopOrder) => {
    setActiveOrder(order);
    setPayerNote(order.payer_note || '');
  };

  const startOrder = async (productId: string) => {
    const existing = openOrderFor(productId);
    if (existing) {
      resumeOrder(existing);
      onSuccess('已打开未完成订单，请按原订单号付款，勿重复下单。');
      return;
    }
    if (productId === 'plaque_permanent' && cosmetics.has_plaque) {
      onError('你已拥有当铺匾额。');
      return;
    }
    setLoading(true);
    try {
      const order = await apiPost<ShopOrder>('/api/shop/create_order', { product_id: productId });
      setActiveOrder(order);
      setPayerNote('');
      await refresh();
      onSuccess(order.reused ? '已恢复未完成订单，请勿重复付款。' : '订单已创建，请扫码付款并备注订单号。');
    } catch (err) {
      onError(err instanceof Error ? err.message : '创建订单失败。');
    } finally {
      setLoading(false);
    }
  };

  const submitPaid = async () => {
    if (!activeOrder) return;
    setLoading(true);
    try {
      await apiPost('/api/shop/submit_payment', { order_id: activeOrder.order_id, payer_note: payerNote || undefined });
      await refresh();
      onSuccess('已提交！掌柜看到后会尽快发货，谢谢支持。');
      const updated = await apiGet<{ orders: ShopOrder[] }>('/api/shop/orders');
      const current = updated.orders.find((o) => o.order_id === activeOrder.order_id);
      if (current) setActiveOrder({ ...activeOrder, ...current, status: 'submitted' });
    } catch (err) {
      onError(err instanceof Error ? err.message : '提交失败。');
    } finally {
      setLoading(false);
    }
  };

  const adminFulfill = async (orderId: string) => {
    setLoading(true);
    try {
      await apiPost('/api/shop/admin/fulfill', { order_id: orderId });
      await refresh();
      onSuccess('已发放权益。');
    } catch (err) {
      onError(err instanceof Error ? err.message : '发货失败。');
    } finally {
      setLoading(false);
    }
  };

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      onSuccess('已复制。');
    } catch {
      onError('复制失败，请手动复制。');
    }
  };

  const savePlaqueProfile = async () => {
    setLoading(true);
    try {
      const data = await apiPatch<{ player: ShopPlayer }>('/api/profile/cosmetics', {
        shop_emblem: emblemDraft,
        showcase_tagline: taglineDraft,
      });
      onPlayerUpdate(data.player);
      onSuccess('匾额与橱窗文案已保存。');
    } catch (err) {
      onError(err instanceof Error ? err.message : '保存失败。');
    } finally {
      setLoading(false);
    }
  };

  const cosmetics = player;
  const displayProducts = products.length ? products : FALLBACK_PRODUCTS;

  return (
    <div className="max-w-3xl w-full mx-auto space-y-5 pb-8">
      <header className="border-b border-[#2A2D34] pb-4">
        <h2 className="text-2xl font-bold text-[#C8A97E] font-sans">掌柜铺子</h2>
        <p className="mt-2 text-sm text-[#9E9E9E] font-sans leading-relaxed">
          这里是个人开发与自掏腰包维护的小铺。服务器、域名、以及每一位顾客的 AI 对话与稀货生成，都在持续烧 token。
          若你喜欢这款游戏，一杯奶茶钱（月卡 ¥5 / 匾额 ¥10）能帮我勉强盖住一部分账单，让当铺多撑几天。
          不购买也完全可以继续玩，你永远受欢迎。
        </p>
      </header>

      <div className="shop-appeal-box font-sans text-sm leading-relaxed text-[#9E9E9E]">
        <p className="text-[#C8A97E] font-semibold mb-2">写给愿意支持的朋友</p>
        <p>
          说实话，我一个人在做前后端和 AI 接入。玩家越多，豆包 API 的账单就越难看；云主机到期日也总在提醒我续费。
          有时半夜看消费短信，会比看当铺账本还心慌。你的每一笔 ¥5 / ¥10，不是「氪金变强」，只是<strong className="text-[#E0E0E0] font-normal">赞助展示</strong>：
          流光店招、匾额、橱窗文案——让我在排行榜上还能体面地说一声：「多谢捧场，店还在。」
        </p>
        <p className="mt-2 text-xs text-[#616161]">
          付款后请备注订单号；掌柜核实微信到账后人工发放（通常几小时内）。若久未到账，可在游戏内留言或联系掌柜。
        </p>
      </div>

      <section className="border-b border-[#2A2D34] pb-5">
        <h3 className="text-[#C8A97E] font-bold text-sm font-sans mb-1">赞助榜</h3>
        <p className="text-xs text-[#616161] font-sans mb-3">感谢每一位愿意帮当铺续命的掌柜（按当铺名排列）。</p>
        {sponsors.length === 0 ? (
          <p className="text-sm text-[#616161] font-sans italic">还没有人上榜，你会是第一个吗？</p>
        ) : (
          <ul className="sponsor-wall font-sans text-sm">
            {sponsors.map((sponsor) => (
              <li key={sponsor.player_id} className="sponsor-wall-item">
                {sponsor.shop_emblem_label ? (
                  <span className="shop-emblem !min-w-[1.1rem] !h-[1.1rem] !text-[10px] mr-1" title="匾额">
                    {sponsor.shop_emblem_label}
                  </span>
                ) : null}
                <span className="text-[#E0E0E0] font-semibold">{sponsor.shop_name}</span>
                {sponsor.is_sponsor ? <span className="sponsor-plate ml-1.5">月卡</span> : null}
                {!sponsor.is_sponsor && sponsor.has_plaque ? (
                  <span className="text-[10px] text-[#616161] ml-1.5">匾额</span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </section>

      {isAdmin && (
        <section className="border border-[#C8A97E]/40 bg-[rgba(200,169,126,0.06)] px-4 py-4">
          <h3 className="text-[#C8A97E] font-bold text-sm font-sans mb-3">掌柜发货台 · {player.username}</h3>
          {adminQueue.length === 0 ? (
            <p className="text-sm text-[#616161] font-sans">暂无待发货订单。</p>
          ) : (
            <ul className="space-y-3 font-sans text-sm">
              {adminQueue.map((order) => (
                <li key={order.order_id} className="flex flex-col sm:flex-row sm:items-center gap-2 border-t border-[#2A2D34] pt-3 first:border-0 first:pt-0">
                  <div className="flex-1 min-w-0">
                    <div className="text-[#E0E0E0]">
                      <code className="text-[#C8A97E]">{order.order_no}</code>
                      <span className="mx-2 text-[#616161]">·</span>
                      {order.product_name} {order.price_label}
                    </div>
                    <div className="text-xs text-[#9E9E9E] mt-1">
                      {order.shop_name}（{order.username}）
                      {order.payer_note ? ` · 备注：${order.payer_note}` : ''}
                    </div>
                  </div>
                  <button type="button" disabled={loading} onClick={() => adminFulfill(order.order_id)} className="btn-primary !h-9 !px-4 shrink-0">
                    确认发放
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm font-sans text-[#9E9E9E] border-b border-[#2A2D34] pb-4">
        <span>
          月卡：
          <span className={cosmetics.is_sponsor ? 'text-[#C8A97E] ml-1' : 'text-[#616161] ml-1'}>
            {cosmetics.is_sponsor ? `至 ${formatMonthlyExpiry(cosmetics.monthly_expires_at)}` : '未开通'}
          </span>
        </span>
        <span>
          匾额：
          <span className={cosmetics.has_plaque ? 'text-[#C8A97E] ml-1' : 'text-[#616161] ml-1'}>
            {cosmetics.has_plaque ? cosmetics.shop_emblem_label || cosmetics.shop_emblem : '未购买'}
          </span>
        </span>
        <span className="text-xs text-[#616161] w-full sm:w-auto">
          <SponsorSubtitle rankingBadge={player.ranking_badge} sponsorTitle={cosmetics.sponsor_title} />
        </span>
      </div>

      <section className="space-y-0">
        {displayProducts.map((product) => {
          const open = openOrderFor(product.id);
          const ownedPlaque = product.id === 'plaque_permanent' && cosmetics.has_plaque;
          return (
            <div key={product.id} className="py-4 border-b border-[#2A2D34] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-base font-bold text-[#E0E0E0] font-sans">{product.name}</h3>
                <p className="text-sm text-[#9E9E9E] mt-1 font-sans">{product.description}</p>
                {open ? (
                  <p className="text-xs text-[#C8A97E] mt-2 font-sans">
                    进行中订单 <code>{open.order_no}</code> · {ORDER_STATUS[open.status]}
                  </p>
                ) : null}
              </div>
              <button
                type="button"
                disabled={loading || ownedPlaque}
                onClick={() => startOrder(product.id)}
                className="btn-primary !h-10 shrink-0 disabled:opacity-50"
              >
                {ownedPlaque ? '已拥有' : open ? '继续付款' : `${product.price_label} · 支持一下`}
              </button>
            </div>
          );
        })}
      </section>

      {activeOrder && (
        <section className="border border-[#2A2D34] px-4 py-4 space-y-4">
          <h3 className="text-[#C8A97E] font-bold text-sm font-sans">付款 · {activeOrder.product_name}</h3>
          <div className="flex flex-col sm:flex-row gap-5 items-start">
            <div className="shrink-0 bg-white p-2 rounded-sm">
              <img src={wechatPayQr} alt="微信收款码" className="w-[180px] h-[180px] object-contain" />
            </div>
            <div className="flex-1 space-y-3 text-sm font-sans min-w-0">
              <p className="text-[#E0E0E0]">{activeOrder.instructions || `请支付 ${activeOrder.price_label}，备注订单号。`}</p>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[#9E9E9E]">订单号</span>
                <code className="text-[#C8A97E]">{activeOrder.order_no || activeOrder.pay_remark}</code>
                <button type="button" className="btn-icon !w-8 !h-8" onClick={() => copyText(activeOrder.order_no || activeOrder.pay_remark || '')} title="复制">
                  <Copy className="w-4 h-4" />
                </button>
              </div>
              <p className="text-xs text-[#616161]">{ORDER_STATUS[activeOrder.status] || activeOrder.status}</p>
              <input
                className="w-full bg-[rgba(255,255,255,0.05)] rounded px-3 py-2.5 text-[#E0E0E0] placeholder-[#616161] border-0 focus:bg-[rgba(255,255,255,0.08)] focus:outline-none focus:ring-1 focus:ring-[#C8A97E]/40"
                placeholder="可选：付款后四位、时间，方便核对"
                value={payerNote}
                onChange={(e) => setPayerNote(e.target.value)}
              />
              {(activeOrder.status === 'pending' || activeOrder.status === 'submitted') && (
                <button
                  type="button"
                  disabled={loading || activeOrder.status === 'submitted'}
                  onClick={submitPaid}
                  className="btn-primary !h-10"
                >
                  {activeOrder.status === 'submitted' ? '已提交，等待掌柜发货' : '我已付款'}
                </button>
              )}
              {activeOrder.status === 'fulfilled' && <p className="text-[#4CAF50]">权益已发放，刷新页面即可看到。</p>}
            </div>
          </div>
        </section>
      )}

      {cosmetics.has_plaque && (
        <section className="border-b border-[#2A2D34] pb-5 space-y-3">
          <h3 className="text-[#C8A97E] font-bold text-sm font-sans">匾额设置</h3>
          <div className="flex gap-3 font-sans text-sm">
            {(['plaque', 'seal', 'lantern'] as const).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setEmblemDraft(key)}
                className={`px-3 py-1.5 border ${emblemDraft === key ? 'border-[#C8A97E] text-[#C8A97E] bg-[rgba(200,169,126,0.1)]' : 'border-[#2A2D34] text-[#9E9E9E]'}`}
              >
                {key === 'plaque' ? '匾' : key === 'seal' ? '印' : '灯'}
              </button>
            ))}
          </div>
          <textarea
            className="w-full min-h-[88px] bg-[rgba(255,255,255,0.05)] rounded px-3 py-2.5 text-[#E0E0E0] placeholder-[#616161] border-0 focus:bg-[rgba(255,255,255,0.08)] focus:outline-none focus:ring-1 focus:ring-[#C8A97E]/40 font-serif text-sm"
            maxLength={80}
            placeholder="橱窗封面文案（最多 80 字）"
            value={taglineDraft}
            onChange={(e) => setTaglineDraft(e.target.value)}
          />
          <button type="button" disabled={loading} onClick={savePlaqueProfile} className="btn-secondary !h-9">
            保存
          </button>
        </section>
      )}

      <section>
        <h3 className="text-[#C8A97E] font-bold text-sm font-sans mb-2">我的订单</h3>
        {orders.length === 0 ? (
          <p className="text-sm text-[#616161] font-sans">还没有订单。</p>
        ) : (
          <ul className="font-sans text-sm space-y-2">
            {orders.map((order) => (
              <li key={order.order_id} className="flex flex-wrap justify-between gap-2 py-2 border-t border-[#2A2D34] first:border-0">
                <span className="text-[#E0E0E0]">
                  {order.product_name} · <code className="text-[#C8A97E]">{order.order_no}</code>
                </span>
                <span className={order.status === 'fulfilled' ? 'text-[#4CAF50]' : 'text-[#9E9E9E]'}>
                  {ORDER_STATUS[order.status] || order.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
