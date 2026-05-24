export interface PlayerCosmetics {
  is_sponsor?: boolean;
  sponsor_title?: string | null;
  monthly_expires_at?: number | null;
  shop_emblem?: string | null;
  shop_emblem_label?: string | null;
  has_plaque?: boolean;
  showcase_tagline?: string | null;
}

export interface CosmeticNameSource {
  shop_name: string;
  is_sponsor?: boolean;
  shop_emblem?: string | null;
  shop_emblem_label?: string | null;
}

const EMBLEM_LABEL: Record<string, string> = { plaque: '匾', seal: '印', lantern: '灯' };

export function emblemLabel(emblem: string | null | undefined): string | null {
  if (!emblem) return null;
  return EMBLEM_LABEL[emblem] || emblem;
}

export function formatMonthlyExpiry(ts: number | null | undefined): string {
  if (!ts) return '未开通';
  const d = new Date(ts * 1000);
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

export function ShopNameLine({ name, cosmetics, className = '' }: { name: string; cosmetics?: CosmeticNameSource | null; className?: string }) {
  const emblem = cosmetics?.shop_emblem_label || emblemLabel(cosmetics?.shop_emblem);
  const sponsorClass = cosmetics?.is_sponsor ? 'shop-sign--sponsor' : 'text-[#E0E0E0]';
  return (
    <span className={`inline-flex items-center gap-1.5 min-w-0 ${className}`}>
      {emblem ? <span className="shop-emblem shrink-0" title="当铺匾额">{emblem}</span> : null}
      <span className={`truncate font-bold ${sponsorClass}`}>{name}</span>
      {cosmetics?.is_sponsor ? <span className="sponsor-plate shrink-0">赞助</span> : null}
    </span>
  );
}

export function SponsorSubtitle({ rankingBadge, sponsorTitle }: { rankingBadge?: string | null; sponsorTitle?: string | null }) {
  const parts = [rankingBadge, sponsorTitle].filter(Boolean);
  if (parts.length === 0) return <span>全服经营中</span>;
  return <span>{parts.join(' · ')}</span>;
}

export function ShowcaseCover({ tagline }: { tagline?: string | null }) {
  if (!tagline?.trim()) return null;
  return (
    <div className="showcase-cover py-4 border-b border-[#2A2D34] mb-2">
      <p className="text-[16px] leading-relaxed text-[#E0E0E0] font-serif m-0">{tagline}</p>
    </div>
  );
}
