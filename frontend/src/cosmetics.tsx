export interface PlayerCosmetics {
  is_sponsor?: boolean;
  sponsor_title?: string | null;
  monthly_expires_at?: number | null;
  shop_emblem?: string | null;
  shop_emblem_label?: string | null;
  has_plaque?: boolean;
  showcase_tagline?: string | null;
  plaque_title?: string | null;
  plaque_title_label?: string | null;
  shop_sign_style?: string | null;
  shop_sign_style_label?: string | null;
  showcase_mood?: string | null;
  showcase_mood_label?: string | null;
  showcase_seal_line?: string | null;
  chat_accent?: string | null;
  chat_accent_label?: string | null;
}

export interface CosmeticNameSource {
  shop_name: string;
  is_sponsor?: boolean;
  has_plaque?: boolean;
  shop_emblem?: string | null;
  shop_emblem_label?: string | null;
  shop_sign_style?: string | null;
}

const EMBLEM_LABEL: Record<string, string> = {
  plaque: '匾',
  seal: '印',
  lantern: '灯',
  bell: '钟',
  ding: '鼎',
  jade: '玉',
  scroll: '卷',
  coin: '钱',
};

export const EMBLEM_OPTIONS = [
  { id: 'plaque', label: '匾' },
  { id: 'seal', label: '印' },
  { id: 'lantern', label: '灯' },
  { id: 'bell', label: '钟' },
  { id: 'ding', label: '鼎' },
  { id: 'jade', label: '玉' },
  { id: 'scroll', label: '卷' },
  { id: 'coin', label: '钱' },
] as const;

export const PLAQUE_TITLE_OPTIONS = [
  { id: 'heritage', label: '传世掌柜' },
  { id: 'veteran', label: '名匾老铺' },
  { id: 'gilded', label: '金字招牌' },
] as const;

export const SIGN_STYLE_OPTIONS = [
  { id: 'classic', label: '经典金字' },
  { id: 'carved', label: '刻匾' },
  { id: 'gilded', label: '静光' },
] as const;

export const SHOWCASE_MOOD_OPTIONS = [
  { id: 'plain', label: '素面' },
  { id: 'letter', label: '信笺' },
  { id: 'couplet', label: '对联' },
] as const;

export const CHAT_ACCENT_OPTIONS = [
  { id: 'default', label: '默认' },
  { id: 'bronze', label: '铜色' },
  { id: 'jade', label: '玉色' },
] as const;

export function emblemLabel(emblem: string | null | undefined): string | null {
  if (!emblem) return null;
  return EMBLEM_LABEL[emblem] || emblem;
}

export function formatMonthlyExpiry(ts: number | null | undefined): string {
  if (!ts) return '未开通';
  const d = new Date(ts * 1000);
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function shopNameClass(cosmetics?: CosmeticNameSource | null): string {
  if (cosmetics?.is_sponsor) return 'shop-sign--sponsor';
  if (!cosmetics?.has_plaque && !cosmetics?.shop_emblem) return 'text-[#E0E0E0]';
  const style = cosmetics?.shop_sign_style || 'classic';
  if (style === 'carved') return 'shop-sign--plaque-carved';
  if (style === 'gilded') return 'shop-sign--plaque-gilded';
  return 'shop-sign--plaque-classic';
}

export function ShopNameLine({ name, cosmetics, className = '' }: { name: string; cosmetics?: CosmeticNameSource | null; className?: string }) {
  const emblem = cosmetics?.shop_emblem_label || emblemLabel(cosmetics?.shop_emblem);
  return (
    <span className={`inline-flex items-center gap-1.5 min-w-0 ${className}`}>
      {emblem ? <span className="shop-emblem shrink-0" title="当铺匾额">{emblem}</span> : null}
      <span className={`truncate font-bold ${shopNameClass(cosmetics)}`}>{name}</span>
      {cosmetics?.is_sponsor ? <span className="sponsor-plate shrink-0">赞助</span> : null}
      {!cosmetics?.is_sponsor && (cosmetics?.has_plaque || cosmetics?.shop_emblem) ? (
        <span className="plaque-plate shrink-0">匾额</span>
      ) : null}
    </span>
  );
}

export function SponsorSubtitle({
  rankingBadge,
  sponsorTitle,
  plaqueTitle,
}: {
  rankingBadge?: string | null;
  sponsorTitle?: string | null;
  plaqueTitle?: string | null;
}) {
  const parts = [rankingBadge, sponsorTitle, plaqueTitle].filter(Boolean);
  if (parts.length === 0) return <span>全服经营中</span>;
  return <span>{parts.join(' · ')}</span>;
}

export function ShowcaseCover({
  tagline,
  mood,
  sealLine,
}: {
  tagline?: string | null;
  mood?: string | null;
  sealLine?: string | null;
}) {
  const text = tagline?.trim();
  const seal = sealLine?.trim();
  if (!text && !seal) return null;
  const moodClass = mood === 'letter' ? 'showcase-cover--letter' : mood === 'couplet' ? 'showcase-cover--couplet' : 'showcase-cover--plain';
  return (
    <div className={`showcase-cover ${moodClass} py-4 border-b border-[#2A2D34] mb-2`}>
      {text ? <p className="text-[16px] leading-relaxed text-[#E0E0E0] font-serif m-0">{text}</p> : null}
      {seal ? <p className="text-sm text-[#9E9E9E] font-serif mt-3 mb-0 text-right tracking-widest">{seal}</p> : null}
    </div>
  );
}

const CHAT_ACCENT_CLASS: Record<string, string> = {
  default: 'border-r border-[#C8A97E] text-right bg-[rgba(200,169,126,0.06)] text-[#D4B88A]',
  bronze: 'border-r-2 border-[#A68B5B] text-right bg-[rgba(166,139,91,0.12)] text-[#E8D4B0]',
  jade: 'border-r-2 border-[#5A8F7B] text-right bg-[rgba(90,143,123,0.1)] text-[#B8D4C8]',
};

export function playerChatBubbleClass(accent?: string | null): string {
  return CHAT_ACCENT_CLASS[accent || 'default'] || CHAT_ACCENT_CLASS.default;
}
