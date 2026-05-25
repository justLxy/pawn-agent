import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Award,
  BookOpen,
  Briefcase,
  CheckCircle,
  Clock,
  Crown,
  Copy,
  Gem,
  GraduationCap,
  Download,
  Heart,
  ImageDown,
  Info,
  Landmark,
  ListOrdered,
  LogOut,
  RefreshCw,
  Search,
  Share2,
  Store,
  Trash2,
  TrendingUp,
  Users,
  Volume2,
  VolumeX,
  X
} from 'lucide-react';
import {
  buildScreenshotFilename,
  copyChatScreenshotToClipboard,
  downloadChatScreenshot,
  renderChatScreenshot,
  shareChatScreenshot,
} from './chatScreenshot';
import { ShopNameLine, ShowcaseCover, SponsorSubtitle, type PlayerCosmetics } from './cosmetics';
import { ShopTab } from './shopTab';
import { TutorialHelpButton, TutorialPanel, isTutorialSeen } from './tutorial';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_KEY = 'pawnshop-agent-token-v1';
type ActiveTab = 'lobby' | 'inventory' | 'management' | 'staff' | 'upgrades' | 'leaderboard' | 'market' | 'showcase' | 'history' | 'achievements' | 'codex' | 'shop';
type ItemStatus = 'stored' | 'repairing' | 'displayed' | 'sold' | 'listed';
type BoardType = 'assets' | 'reputation' | 'profit' | 'collection';
type MarketView = 'browse' | 'mine' | 'offers' | 'hot' | 'trades';

interface Player extends PlayerCosmetics {
  id: number;
  username: string;
  shop_name: string;
  online: boolean;
  reputation: number;
  ranking_badge: string | null;
  reward_bonus: number;
  is_shop_admin?: boolean;
}

interface Item {
  id: string;
  name: string;
  category: string;
  condition: string;
  is_fake: boolean;
  actual_value: number;
  market_value: number;
  appraised_value: number | null;
  appraised_value_low: number | null;
  appraised_value_high: number | null;
  is_appraised_fake: boolean | null;
  appraisal_confidence: number | null;
  appraisal_verdict: string | null;
  appraisal_notes: string[];
  purchase_price: number | null;
  selling_price: number | null;
  status: ItemStatus;
  description: string;
  rarity: string;
  rarity_cn: string;
  story: string;
  hidden_attrs: string[];
  era: string;
  damage_report: string;
  special_effects: string[];
  authentication_tips: string[];
  repair_difficulty: number;
  repair_days_remaining: number;
  repair_success_bonus: number;
  display_slot: number | null;
  acquired_at: number;
  acquired_day: number;
  last_value_update_day: number;
  base_value_at_purchase: number;
  value_history: Array<{ day: number; market_value: number; delta: number; holding_cost: number }>;
  holding_cost_paid: number;
  value_trend_note: string;
  showcase_price: number | null;
}

interface CaseClue {
  id: string;
  type: string;
  title: string;
  detail: string;
  reliability: number;
}

interface CaseState {
  phase: string;
  points_max: number;
  points_remaining: number;
  clues: CaseClue[];
  flags: {
    knows_fake_risk: boolean;
    knows_hidden_bonus: boolean;
    customer_angered: boolean;
    graceful_reject: boolean;
  };
  investigations_used: string[];
}

interface Customer {
  name: string;
  trait_cn: string;
  trait_desc: string;
  role: 'buyer' | 'seller';
  item: Item;
  case_state?: CaseState;
  age: number;
  appearance: string;
  backstory: string;
  avatar_url: string;
  transaction_prefs: string[];
  persuasion_points: string[];
  customer_id: string;
  is_returning: boolean;
  visit_count: number;
  relationship_level: string;
  relationship_cn: string;
  last_deal_summary: string | null;
  satisfaction: number;
  referred_by: string | null;
  patience: number;
  current_offer: number;
  initial_offer: number;
  dialogue_history: Array<{ role: 'player' | 'customer' | 'narrator'; content: string }>;
  session_closed?: 'deal' | 'walk_out' | null;
  deal_summary?: string | null;
  is_past_self?: boolean;
}

interface Achievement {
  id: string;
  category: string;
  name: string;
  desc: string;
  target: number;
  progress: number;
  reward: Record<string, unknown>;
  hidden: boolean;
  unlocked: boolean;
  unlocked_day: number | null;
}

interface AchievementUnlock {
  id: string;
  name: string;
  category: string;
  day: number;
  reward: Record<string, unknown>;
}

interface CustomerCodexEntry {
  customer_id: string;
  name: string;
  trait: string;
  trait_cn: string;
  trait_desc: string;
  role: 'buyer' | 'seller';
  age: number;
  appearance: string;
  backstory: string;
  avatar_url: string;
  transaction_prefs: string[];
  persuasion_points: string[];
  is_returning: boolean;
  visit_count: number;
  relationship_level: string;
  relationship_cn: string;
  satisfaction: number;
  last_deal_summary?: string | null;
  first_seen_day: number;
  last_seen_day: number;
  times_seen: number;
  sources: string[];
  last_item_name?: string;
}

interface ItemCodexEntry {
  id: string;
  name: string;
  category: string;
  condition: string;
  rarity: string;
  rarity_cn: string;
  era: string;
  description: string;
  story: string;
  market_value: number;
  appraised_value: number | null;
  appraisal_verdict: string | null;
  appraisal_confidence: number | null;
  is_appraised_fake: boolean | null;
  status: ItemStatus;
  first_seen_day: number;
  last_seen_day: number;
  times_seen: number;
  sources: string[];
  owned: boolean;
  sold: boolean;
  purchase_price: number | null;
  selling_price: number | null;
  value_trend_note?: string;
  special_effects: string[];
  authentication_tips: string[];
}

interface GameState {
  cash: number;
  day: number;
  shop_level: number;
  shop_name: string;
  reputation: number;
  total_profit: number;
  ranking_badge: string | null;
  ranking_reward_bonus: number;
  inventory: Item[];
  sold_items: Item[];
  transaction_log: TransactionEntry[];
  staff: Record<string, boolean>;
  staff_info: Record<string, { name_cn: string; hire_cost: number; daily_salary: number; desc: string }>;
  appraisal_methods: Record<string, { name_cn: string; desc: string; cost_multiplier: number; accuracy_bonus: number; value_margin: number; xp: number }>;
  case_investigation_actions?: Record<string, { name_cn: string; cost_points: number; patience_cost?: number; requires_staff?: string }>;
  repair_methods: Record<string, { name_cn: string; desc: string; cost_multiplier: number; days_delta: number; success_bonus: number; xp: number }>;
  skills: Record<string, { level: number; xp: number }>;
  skill_info: Record<string, { name_cn: string; desc: string }>;
  facilities: Record<string, number>;
  facility_info: Record<string, { name_cn: string; desc: string; level: number; upgrade_cost: number | null; upgrade_blocked?: 'max_level' | 'shop_level' | 'min_day' | null; upgrade_min_day?: number | null; upgrade_min_shop_level?: number | null }>;
  loan: { principal: number; interest_rate: number };
  tax: { next_due_day: number; rate: number; last_paid: number };
  market_trends: Record<string, number>;
  economy_index: number;
  inflation_rate: number;
  money_supply_score: number;
  economic_pressure: string;
  economy_history: Array<{ day: number; economy_index: number; inflation_rate: number; pressure: string; money_supply_score: number }>;
  achievements: Achievement[];
  achievement_unlocks: AchievementUnlock[];
  achievement_stats: Record<string, number>;
  customer_registry: Record<string, { name: string; visit_count: number; satisfaction: number; relationship_level: string; last_deal_summary?: string }>;
  customer_codex: Record<string, CustomerCodexEntry>;
  item_codex: Record<string, ItemCodexEntry>;
  successful_trades: number;
  positive_reviews: number;
  daily_customer_queue: Customer[];
  pending_event: null | { id: string; title: string; description: string; choices: Array<{ id: string; label: string; effect: string }> };
  active_customer: Customer | null;
  customers_served_today: number;
  customers_seen_today?: number;
  daily_traffic_complete?: boolean;
  total_customers_today: number;
  day_ended: boolean;
  daily_summary: {
    revenue: number;
    salaries: number;
    upgrades: number;
    operating_cost: number;
    loan_interest: number;
    tax: number;
    holding_cost: number;
    economy_index: number;
    inflation_rate: number;
    economy_pressure?: string;
    events: string[];
    starting_cash: number;
    ending_cash: number;
    net_profit: number;
  };
  display_capacity: number;
  shop_upgrade_cost: number | null;
  shop_upgrade_desc: string | null;
  shop_upgrade_min_day?: number | null;
  skill_xp_to_next?: Record<string, number>;
}

interface TransactionEntry {
  day: number;
  type: string;
  item: string;
  amount: number;
}

interface Listing {
  id: string;
  seller_id: number;
  seller_shop: string;
  seller_online: boolean;
  item: Item;
  item_name: string;
  rarity: string;
  category: string;
  condition: string;
  price: number;
  reference_price: number;
  status: string;
  created_at: number;
}

interface LeaderboardEntry extends PlayerCosmetics {
  player_id: number;
  username: string;
  shop_name: string;
  online: boolean;
  badge: string | null;
  score: number;
  assets: number;
  reputation: number;
  profit: number;
  collection: number;
  rank: number;
}

interface TradeLog {
  id: number;
  buyer_id: number;
  seller_id: number;
  buyer_shop: string | null;
  seller_shop: string | null;
  item_name: string;
  price: number;
  tax: number;
  trade_type: string;
  created_at: number;
}

interface NegotiationStreamPayload {
  negotiation: { patience_change: number; stale?: boolean };
  deal_completed: boolean;
  walk_out_completed: boolean;
  stale?: boolean;
  deal_result?: { message?: string };
  state: GameState;
}

interface ShowcaseData {
  owner: PlayerCosmetics & {
    id: number;
    shop_name: string;
    online: boolean;
    reputation: number;
    ranking_badge: string | null;
    is_self: boolean;
  };
  items: Item[];
  display_capacity: number;
  like_count: number;
  recent_like_count: number;
  liked_by_me: boolean;
  guestbook: GuestbookEntry[];
  hot_rank: number | null;
}

interface GuestbookEntry {
  id: number;
  owner_id: number;
  author_id: number;
  author_shop: string;
  content: string;
  created_at: number;
}

interface MarketOffer {
  id: string;
  listing_id: string;
  buyer_id: number;
  seller_id: number;
  buyer_shop: string;
  seller_shop: string;
  buyer_offer: number;
  seller_counter: number | null;
  status: string;
  round: number;
  final_price: number | null;
  listing_price: number;
  reference_price: number;
  item_name: string;
  item: Item;
  created_at: number;
  updated_at: number;
  expires_at: number;
}

interface HotShowcaseEntry extends PlayerCosmetics {
  player_id: number;
  shop_name: string;
  online: boolean;
  ranking_badge: string | null;
  recent_likes: number;
  total_likes: number;
  displayed_count: number;
  display_capacity: number;
  rank: number;
}

interface OfferBundle {
  sent: MarketOffer[];
  received: MarketOffer[];
}

const CONDITION_MAP: Record<string, string> = { Mint: '极佳', Good: '良好', Poor: '较差' };
const STATUS_MAP: Record<ItemStatus, string> = { stored: '仓库', repairing: '修复中', displayed: '展示中', sold: '已售出', listed: '挂售中' };
const RARITY_COLOR: Record<string, string> = { common: 'text-[#9E9E9E]', rare: 'text-[#64B5F6]', epic: 'text-[#C8A97E]', legendary: 'text-[#FFB74D]' };
const BOARD_LABEL: Record<BoardType, string> = { assets: '总资产', reputation: '当铺声誉', profit: '累计盈利', collection: '稀有收藏' };
const CATEGORY_MAP: Record<string, string> = {
  'Pop Culture': '流行文化',
  Art: '艺术品',
  Jewelry: '珠宝首饰',
  Antiquities: '古董文物',
  Historical: '历史藏品'
};

/** 与 backend/game_state.py appraise_active_item 保持一致 */
function computeAppraisalPreview(
  marketValue: number,
  method: { cost_multiplier: number; accuracy_bonus: number; value_margin?: number },
  appraisalSkillLevel: number,
  appraisalRoomLevel: number,
  hasAppraiser: boolean,
  economyIndex = 1
) {
  const baseCost = Math.max(160, Math.floor(marketValue * 0.08 * economyIndex));
  const discount = 0.08 * (appraisalRoomLevel - 1) + (hasAppraiser ? 0.35 : 0);
  const cost = Math.max(120, Math.floor(baseCost * method.cost_multiplier * (1 - Math.min(0.58, discount))));
  const fakeDetectionRate = Math.min(
    0.92,
    Math.max(0.25, 0.45 + appraisalSkillLevel * 0.035 + appraisalRoomLevel * 0.04 + (hasAppraiser ? 0.12 : 0) + method.accuracy_bonus)
  );
  const valueErrorMargin = Math.max(0.06, (method.value_margin ?? 0.30) - (appraisalSkillLevel - 1) * 0.015 - (appraisalRoomLevel - 1) * 0.02 - (hasAppraiser ? 0.04 : 0));
  return { cost, fakeDetectionRate, valueErrorMargin };
}

function formatAppraisalPercent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

function formatSignedPercent(rate: number): string {
  const percent = rate * 100;
  return `${percent > 0 ? '+' : ''}${percent.toFixed(2)}%`;
}

function categoryLabel(category: string): string {
  return CATEGORY_MAP[category] || category;
}

function appraisalVerdict(item: Item): string {
  if (item.is_appraised_fake === null) return '未知';
  return item.appraisal_verdict || (item.is_appraised_fake ? '发现明显作伪' : '未见明显作伪');
}

function appraisalRange(item: Item): string | null {
  if (item.appraised_value_low !== null && item.appraised_value_high !== null) {
    return `$${item.appraised_value_low.toLocaleString()} - $${item.appraised_value_high.toLocaleString()}`;
  }
  if (item.appraised_value !== null) return `$${item.appraised_value.toLocaleString()}`;
  return null;
}

function extractOffer(text: string): number | null {
  const actionRegex = /(?:出|给|卖|要|报价|成交|拿走|一口价|就|最多|最少)\s*(\d+(?:,\d{3})*)/g;
  let match;
  let lastMatch = null;
  while ((match = actionRegex.exec(text)) !== null) {
    lastMatch = match[1];
  }
  if (lastMatch) {
    return parseInt(lastMatch.replaceAll(',', ''), 10);
  }

  const allMatches = [...text.matchAll(/\d+(?:,\d{3})*/g)];
  if (!allMatches.length) return null;

  for (const m of allMatches) {
    const start = m.index;
    if (start !== undefined) {
      const context = text.slice(Math.max(0, start - 5), start);
      if (!/(便宜|市场|亏|赚|加|减|贵|高|低|多|少)/.test(context)) {
        return parseInt(m[0].replaceAll(',', ''), 10);
      }
    }
  }

  return parseInt(allMatches[0][0].replaceAll(',', ''), 10);
}

/** 流式谈判晚到的结算不应覆盖玩家已拒绝/成交后的 session_closed。 */
function preserveClosedCustomerState(incoming: GameState, current: GameState | null): GameState {
  const cur = current?.active_customer;
  const next = incoming.active_customer;
  if (!cur?.session_closed || !next || cur.customer_id !== next.customer_id || next.session_closed) {
    return incoming;
  }
  return {
    ...incoming,
    active_customer: {
      ...next,
      session_closed: cur.session_closed,
      deal_summary: cur.deal_summary ?? next.deal_summary,
    },
  };
}

function tokenHeader(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const AUTH_EXPIRED_EVENT = 'pawnshop-auth-expired';

class AuthExpiredError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AuthExpiredError';
  }
}

async function readApiError(response: Response, fallback: string): Promise<string> {
  const payload = await response.json().catch(() => null);
  if (payload && typeof payload.detail === 'string') return payload.detail;
  return fallback;
}

async function apiRequest<T>(path: string, options: RequestInit, fallback: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options);
  } catch {
    throw new Error('网络请求失败，请检查后端服务或跨域配置。');
  }
  if (!response.ok) {
    const message = await readApiError(response, fallback);
    if (response.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      if (path !== '/api/auth/logout') {
        window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
      }
      throw new AuthExpiredError(message);
    }
    throw new Error(message);
  }
  return response.json();
}

async function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { headers: tokenHeader() }, '服务器响应异常。');
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...tokenHeader() },
    body: body ? JSON.stringify(body) : undefined
  }, '操作失败。');
}

async function apiDelete<T>(path: string): Promise<T> {
  return apiRequest<T>(path, {
    method: 'DELETE',
    headers: tokenHeader()
  }, '删除失败。');
}

async function apiPatch<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...tokenHeader() },
    body: body ? JSON.stringify(body) : undefined
  }, '保存失败。');
}

export default function App() {
  const [player, setPlayer] = useState<Player | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('lobby');
  const [message, setMessage] = useState('');
  const [loanAmount, setLoanAmount] = useState(3000);
  const [listingPrice, setListingPrice] = useState<Record<string, number>>({});
  const [showcasePrice, setShowcasePrice] = useState<Record<string, number>>({});
  const [appraisalMethod, setAppraisalMethod] = useState('standard');
  const [inventoryAppraiseMethod, setInventoryAppraiseMethod] = useState<Record<string, string>>({});
  const [repairMethod, setRepairMethod] = useState<Record<string, string>>({});
  const [boardType, setBoardType] = useState<BoardType>('assets');
  const [leaderboard, setLeaderboard] = useState<{ entries: LeaderboardEntry[]; my_rank: LeaderboardEntry | null } | null>(null);
  const [showcase, setShowcase] = useState<ShowcaseData | null>(null);
  const [marketView, setMarketView] = useState<MarketView>('browse');
  const [marketSearch, setMarketSearch] = useState('');
  const [marketSort, setMarketSort] = useState('newest');
  const [listings, setListings] = useState<Listing[]>([]);
  const [myListings, setMyListings] = useState<Listing[]>([]);
  const [trades, setTrades] = useState<TradeLog[]>([]);
  const [offers, setOffers] = useState<OfferBundle>({ sent: [], received: [] });
  const [hotShowcases, setHotShowcases] = useState<HotShowcaseEntry[]>([]);
  const [offerPrices, setOfferPrices] = useState<Record<string, number>>({});
  const [counterPrices, setCounterPrices] = useState<Record<string, number>>({});
  const [authMode, setAuthMode] = useState<'login' | 'register' | 'recover'>('login');
  const [recoveredUsernames, setRecoveredUsernames] = useState<string[]>([]);
  const [authForm, setAuthForm] = useState({ username: '', password: '', shop_name: '' });
  const [loading, setLoading] = useState(false);
  const [authBusy, setAuthBusy] = useState<'register' | 'login' | null>(null);
  const [sessionBooting, setSessionBooting] = useState(() => Boolean(localStorage.getItem(TOKEN_KEY)));
  const [dayTransition, setDayTransition] = useState<'end_day' | 'next_day' | null>(null);
  const [resetting, setResetting] = useState(false);
  const [investigating, setInvestigating] = useState(false);
  const [inventoryAppraisingId, setInventoryAppraisingId] = useState<string | null>(null);
  const [customerThinking, setCustomerThinking] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [mobileInfoOpen, setMobileInfoOpen] = useState(false);
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const tutorialAutoOpenedRef = useRef(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const negotiateAbortRef = useRef<AbortController | null>(null);
  const negotiateGenerationRef = useRef(0);
  const lastAchievementRef = useRef<string | null>(null);
  const musicContextRef = useRef<AudioContext | null>(null);
  const musicNodesRef = useRef<{ oscillators: OscillatorNode[]; intervals: number[]; gain: GainNode } | null>(null);

  useEffect(() => {
    const handleAuthExpired = () => {
      setPlayer(null);
      setState(null);
      setLeaderboard(null);
      setShowcase(null);
      setListings([]);
      setMyListings([]);
      setTrades([]);
      setSuccessMsg(null);
      setErrorMsg('登录已失效，请重新登录。');
    };
    window.addEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleAuthExpired);
  }, []);

  const playSound = (type: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade' | 'patience_down') => {
    if (!soundEnabled) return;
    const urls: Record<string, string> = {
      deal: 'https://assets.mixkit.co/active_storage/sfx/2019/2019-84.wav',
      cash: 'https://assets.mixkit.co/active_storage/sfx/2017/2017-84.wav',
      reject: 'https://assets.mixkit.co/active_storage/sfx/2568/2568-84.wav',
      appraise: 'https://assets.mixkit.co/active_storage/sfx/1487/1487-84.wav',
      click: 'https://assets.mixkit.co/active_storage/sfx/2568/2568-84.wav',
      upgrade: 'https://assets.mixkit.co/active_storage/sfx/2019/2019-84.wav',
      patience_down: 'https://assets.mixkit.co/active_storage/sfx/2539/2539-84.wav'
    };
    const audio = new Audio(urls[type]);
    audio.volume = 0.25;
    audio.play().catch(() => {});
  };

  const startMusic = () => {
    if (musicContextRef.current) {
      musicContextRef.current.resume().catch(() => {});
      return;
    }
    const AudioContextClass = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AudioContextClass) {
      setErrorMsg('当前浏览器不支持背景音乐。');
      return;
    }
    const context = new AudioContextClass();
    const master = context.createGain();
    master.gain.value = 0.16;
    master.connect(context.destination);

    const delay = context.createDelay(1.5);
    delay.delayTime.value = 0.42;
    const feedback = context.createGain();
    feedback.gain.value = 0.26;
    const wet = context.createGain();
    wet.gain.value = 0.22;
    delay.connect(feedback);
    feedback.connect(delay);
    delay.connect(wet);
    wet.connect(master);

    const padFilter = context.createBiquadFilter();
    padFilter.type = 'lowpass';
    padFilter.frequency.value = 580;
    const padGain = context.createGain();
    padGain.gain.value = 0.025;
    padFilter.connect(padGain);
    padGain.connect(master);

    const padOscillators = [55, 82.41, 110].map((frequency, index) => {
      const oscillator = context.createOscillator();
      oscillator.type = index === 1 ? 'triangle' : 'sine';
      oscillator.frequency.value = frequency;
      oscillator.detune.value = index === 2 ? -7 : 0;
      oscillator.connect(padFilter);
      oscillator.start();
      return oscillator;
    });

    const playNote = (frequency: number, when: number, duration: number, volume: number, type: OscillatorType = 'triangle') => {
      const oscillator = context.createOscillator();
      const noteGain = context.createGain();
      const noteFilter = context.createBiquadFilter();
      oscillator.type = type;
      oscillator.frequency.value = frequency;
      noteFilter.type = 'lowpass';
      noteFilter.frequency.value = type === 'sine' ? 360 : 1200;
      noteGain.gain.setValueAtTime(0.0001, when);
      noteGain.gain.exponentialRampToValueAtTime(volume, when + 0.035);
      noteGain.gain.exponentialRampToValueAtTime(0.0001, when + duration);
      oscillator.connect(noteGain);
      noteGain.connect(noteFilter);
      noteFilter.connect(master);
      noteFilter.connect(delay);
      oscillator.start(when);
      oscillator.stop(when + duration + 0.08);
    };

    const progression = [
      [73.42, 146.83, 174.61, 220.0, 293.66],
      [65.41, 130.81, 174.61, 196.0, 261.63],
      [55.0, 110.0, 146.83, 220.0, 246.94],
      [61.74, 123.47, 164.81, 207.65, 277.18]
    ];
    let bar = 0;
    const scheduleBar = () => {
      const chord = progression[bar % progression.length];
      const start = context.currentTime + 0.08;
      playNote(chord[0], start, 1.8, 0.09, 'sine');
      chord.slice(1).forEach((frequency, index) => {
        playNote(frequency * 2, start + index * 0.36, 0.58, 0.045, index % 2 ? 'triangle' : 'sine');
      });
      if (bar % 2 === 1) {
        playNote(chord[2] * 2, start + 1.58, 0.9, 0.035, 'triangle');
      }
      bar += 1;
    };
    scheduleBar();
    const interval = window.setInterval(scheduleBar, 2000);

    musicContextRef.current = context;
    musicNodesRef.current = { oscillators: padOscillators, intervals: [interval], gain: master };
  };

  const stopMusic = () => {
    musicNodesRef.current?.intervals.forEach((interval) => window.clearInterval(interval));
    musicNodesRef.current?.oscillators.forEach((oscillator) => {
      try {
        oscillator.stop();
      } catch {
        // Oscillators can only be stopped once.
      }
    });
    musicNodesRef.current?.gain.disconnect();
    musicContextRef.current?.close().catch(() => {});
    musicNodesRef.current = null;
    musicContextRef.current = null;
  };

  const toggleSound = () => {
    if (soundEnabled) {
      stopMusic();
      setSoundEnabled(false);
    } else {
      startMusic();
      setSoundEnabled(true);
    }
  };

  const loadCloudState = async () => {
    const cloud = await apiGet<GameState>('/api/cloud/state');
    setState(cloud);
  };

  const boot = async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setSessionBooting(false);
      return;
    }
    try {
      const me = await apiGet<{ player: Player }>('/api/auth/me');
      setPlayer(me.player);
      await loadCloudState();
    } catch {
      localStorage.removeItem(TOKEN_KEY);
    } finally {
      setSessionBooting(false);
    }
  };

  useEffect(() => {
    boot();
    return () => stopMusic();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state?.active_customer?.dialogue_history, customerThinking]);

  useEffect(() => {
    if (!successMsg && !errorMsg) return;
    const timer = setTimeout(() => {
      setSuccessMsg(null);
      setErrorMsg(null);
    }, 4200);
    return () => clearTimeout(timer);
  }, [successMsg, errorMsg]);

  useEffect(() => {
    const latest = state?.achievement_unlocks?.[state.achievement_unlocks.length - 1];
    if (!latest) return;
    const key = `${latest.id}-${latest.day}`;
    if (lastAchievementRef.current === null) {
      lastAchievementRef.current = key;
      return;
    }
    if (lastAchievementRef.current !== key) {
      lastAchievementRef.current = key;
      setSuccessMsg(`成就解锁：${latest.name}`);
      playSound('upgrade');
    }
  }, [state?.achievement_unlocks]);

  const loadLeaderboard = async () => {
    const data = await apiGet<{ entries: LeaderboardEntry[]; my_rank: LeaderboardEntry | null }>(`/api/leaderboard?type=${boardType}`);
    setLeaderboard(data);
  };

  const loadMarket = async () => {
    const params = new URLSearchParams({ search: marketSearch, sort: marketSort });
    const [listingsData, mineData, tradesData, offersData, hotData] = await Promise.all([
      apiGet<{ listings: Listing[] }>(`/api/market/listings?${params.toString()}`),
      apiGet<{ listings: Listing[] }>('/api/market/mine'),
      apiGet<{ trades: TradeLog[] }>('/api/market/trades'),
      apiGet<OfferBundle>('/api/market/offers'),
      apiGet<{ entries: HotShowcaseEntry[] }>('/api/showcase/hot'),
    ]);
    setListings(listingsData.listings);
    setMyListings(mineData.listings);
    setTrades(tradesData.trades);
    setOffers(offersData);
    setHotShowcases(hotData.entries);
  };

  const openMarketHot = () => {
    setMarketView('hot');
    setActiveTab('market');
  };

  const pendingReceivedOffers = offers.received.filter((offer) => offer.status === 'pending_seller' || offer.status === 'countered').length;

  const marketOfferAction = async (path: string, body: unknown, fallback: string, sound: 'deal' | 'cash' | 'click' | 'reject' = 'click') => {
    setLoading(true);
    try {
      const data = await apiPost<{ market_result: { message?: string }; state?: GameState; offers: OfferBundle }>(path, body);
      if (data.state) setState(data.state);
      setOffers(data.offers);
      setSuccessMsg(data.market_result.message || fallback);
      playSound(sound);
      await loadMarket().catch(() => {});
      await loadLeaderboard().catch(() => {});
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '议价操作失败。');
      playSound('reject');
    } finally {
      setLoading(false);
    }
  };

  const submitMarketOffer = async (listing: Listing) => {
    const price = offerPrices[listing.id] ?? Math.max(1, Math.floor(listing.price * 0.85));
    await marketOfferAction('/api/market/offer', { listing_id: listing.id, price }, '出价已发送。');
  };

  const openShowcase = async (ownerId: number) => {
    try {
      const data = await apiGet<ShowcaseData>(`/api/showcase/${ownerId}`);
      setShowcase(data);
      setActiveTab('showcase');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '无法打开玩家橱窗。');
    }
  };

  useEffect(() => {
    if (!player || activeTab !== 'leaderboard') return;
    loadLeaderboard().catch((err) => setErrorMsg(err.message));
    const timer = setInterval(() => loadLeaderboard().catch(() => {}), 10000);
    return () => clearInterval(timer);
  }, [player, activeTab, boardType]);

  useEffect(() => {
    if (!player || activeTab !== 'market') return;
    loadMarket().catch((err) => setErrorMsg(err.message));
  }, [player, activeTab, marketSort]);

  useEffect(() => {
    if (!player || !state || tutorialAutoOpenedRef.current) return;
    if (state.day === 1 && !isTutorialSeen(player.username)) {
      tutorialAutoOpenedRef.current = true;
      setTutorialOpen(true);
    }
  }, [player, state]);

  const handleAuth = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setRecoveredUsernames([]);
    const busyMode = authMode === 'register' ? 'register' : authMode === 'login' ? 'login' : null;
    if (busyMode) setAuthBusy(busyMode);
    try {
      if (authMode === 'recover') {
        const data = await apiPost<{ usernames: string[]; count: number; message: string }>('/api/auth/recover_username', {
          password: authForm.password
        });
        setRecoveredUsernames(data.usernames);
        if (data.count > 0) {
          setSuccessMsg(data.message);
          setErrorMsg(null);
        } else {
          setSuccessMsg(null);
          setErrorMsg(data.message);
        }
        return;
      }
      const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const isRegister = authMode === 'register';
      const data = await apiPost<{ token: string; player: Player }>(endpoint, authForm);
      localStorage.setItem(TOKEN_KEY, data.token);
      setPlayer(data.player);
      tutorialAutoOpenedRef.current = false;
      if (isRegister) {
        setSuccessMsg('账号已创建，正在载入当铺…');
      }
      await loadCloudState();
      if (isRegister && !isTutorialSeen(data.player.username)) {
        tutorialAutoOpenedRef.current = true;
        setTutorialOpen(true);
      }
      setSuccessMsg(authMode === 'login' ? '欢迎回来。' : '当铺创建成功，可以开始营业了。');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '操作失败。');
    } finally {
      setLoading(false);
      setAuthBusy(null);
    }
  };

  const changeAuthMode = (mode: 'login' | 'register' | 'recover') => {
    setAuthMode(mode);
    if (mode !== 'recover') setRecoveredUsernames([]);
  };

  const useRecoveredUsername = (username: string) => {
    setAuthForm({ ...authForm, username });
    setRecoveredUsernames([]);
    setAuthMode('login');
    setSuccessMsg(`已填入用户名「${username}」，请输入密码登录。`);
    setErrorMsg(null);
  };

  const logout = async () => {
    await apiPost('/api/auth/logout').catch(() => {});
    localStorage.removeItem(TOKEN_KEY);
    setPlayer(null);
    setState(null);
  };

  const deleteAccount = async () => {
    if (!window.confirm('确定要永久注销账号吗？账号、云端存档、市场挂售和排行榜记录都会删除，且不可恢复。')) return;
    setLoading(true);
    try {
      await apiDelete('/api/auth/account');
      localStorage.removeItem(TOKEN_KEY);
      setPlayer(null);
      setState(null);
      setLeaderboard(null);
      setShowcase(null);
      setListings([]);
      setMyListings([]);
      setTrades([]);
      setSuccessMsg('账号已注销。');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '注销账号失败。');
    } finally {
      setLoading(false);
    }
  };

  const restart = async () => {
    if (!window.confirm('确定要重开当前云端存档吗？')) return;
    setResetting(true);
    setSuccessMsg('正在重置当铺...');
    try {
      await apiPost<GameState>('/api/restart');
      const freshState = await apiGet<GameState>('/api/cloud/state');
      setState(freshState);
      setMessage('');
      setCustomerThinking(false);
      setListingPrice({});
      setShowcasePrice({});
      setRepairMethod({});
      setShowcase(null);
      setLeaderboard(null);
      setListings([]);
      setMyListings([]);
      setTrades([]);
      setActiveTab('lobby');
      setSuccessMsg('当铺已重置，新的一天重新开始。');
      playSound('cash');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '重置失败。');
    } finally {
      setResetting(false);
    }
  };

  const abortInFlightNegotiation = () => {
    negotiateGenerationRef.current += 1;
    negotiateAbortRef.current?.abort();
    negotiateAbortRef.current = null;
    setCustomerThinking(false);
  };

  const runStateAction = async (path: string, body: unknown, resultKey: string, fallback: string, sound: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade' = 'click') => {
    if (path === '/api/reject' || path === '/api/deal') {
      abortInFlightNegotiation();
    }
    const transitionMode = path === '/api/end_day' ? 'end_day' : path === '/api/next_day' ? 'next_day' : null;
    if (transitionMode) setDayTransition(transitionMode);
    setLoading(true);
    try {
      const data = await apiPost<Record<string, any>>(path, body);
      const nextState = data.state || (typeof data.cash === 'number' && typeof data.day === 'number' ? data : null);
      if (nextState) setState(nextState as GameState);
      playSound(sound);
      setErrorMsg(null);
      setSuccessMsg(data[resultKey]?.message || fallback);
    } catch (err) {
      setSuccessMsg(null);
      setErrorMsg(err instanceof Error ? err.message : '操作失败。');
    } finally {
      setLoading(false);
      if (transitionMode) setDayTransition(null);
    }
  };

  const investigateCase = async (action: string) => {
    setInvestigating(true);
    setErrorMsg(null);
    try {
      const data = await apiPost<{
        investigation_result: {
          action_name?: string;
          narration?: string;
          clue?: CaseClue | null;
          walk_out?: boolean;
          cost_cash?: number;
          points_remaining?: number;
          appraise_result?: { cost: number; method_name?: string; verdict?: string; confidence?: number; appraised_value: number; appraised_value_low?: number; appraised_value_high?: number };
        };
        state: GameState;
      }>('/api/case/investigate', { action, method: appraisalMethod });
      setState(data.state);
      playSound(action === 'appraise' ? 'appraise' : 'click');
      const result = data.investigation_result;
      let msg = result.narration || `${result.action_name || '调查'}完成。`;
      if (result.appraise_result) {
        const appraise = result.appraise_result;
        const low = appraise.appraised_value_low ?? appraise.appraised_value;
        const high = appraise.appraised_value_high ?? appraise.appraised_value;
        msg = `${appraise.method_name || '鉴定'}：${appraise.verdict || '未见明显作伪'}，估值 $${low.toLocaleString()} - $${high.toLocaleString()}（约 ${appraise.confidence ?? 0}%），花费 $${appraise.cost.toLocaleString()}。`;
      }
      if (typeof result.points_remaining === 'number') {
        msg += ` 剩余调查点 ${result.points_remaining}。`;
      }
      if (result.walk_out) {
        playSound('reject');
      }
      setSuccessMsg(msg);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '调查失败。');
    } finally {
      setInvestigating(false);
    }
  };

  const appraiseInventoryItem = async (itemId: string, method: string) => {
    if (inventoryAppraisingId) return;
    setInventoryAppraisingId(itemId);
    setErrorMsg(null);
    try {
      const data = await apiPost<{ appraise_result: { cost: number; method_name?: string; verdict?: string; confidence?: number; appraised_value: number; appraised_value_low?: number; appraised_value_high?: number; notes?: string[] }; state: GameState }>('/api/appraise_inventory', { item_id: itemId, method });
      setState(data.state);
      playSound('appraise');
      const result = data.appraise_result;
      const low = result.appraised_value_low ?? result.appraised_value;
      const high = result.appraised_value_high ?? result.appraised_value;
      setSuccessMsg(`${result.method_name || '鉴定'}完成：${result.verdict || '未见明显作伪'}，估值区间 $${low.toLocaleString()} - $${high.toLocaleString()}，可信度约 ${result.confidence ?? 0}%，花费 $${result.cost.toLocaleString()}。`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '鉴定失败。');
    } finally {
      setInventoryAppraisingId(null);
    }
  };

  const negotiate = async (event: React.FormEvent) => {
    event.preventDefault();
    const playerMessage = message.trim();
    if (!playerMessage) return setErrorMsg('请输入谈判内容。');
    if (!state?.active_customer) return;
    const offeredPrice = extractOffer(playerMessage);
    if (state.active_customer.role === 'seller' && offeredPrice !== null && offeredPrice > state.cash) {
      setErrorMsg(`现金不足，你当前最多只能出 $${state.cash.toLocaleString()}。`);
      return;
    }

    const previousState = state;
    const optimisticState: GameState = {
      ...state,
      active_customer: {
        ...state.active_customer,
        dialogue_history: [
          ...state.active_customer.dialogue_history,
          { role: 'player', content: playerMessage }
        ]
      }
    };
    setState(optimisticState);
    setMessage('');
    const negotiationGeneration = negotiateGenerationRef.current + 1;
    negotiateGenerationRef.current = negotiationGeneration;
    negotiateAbortRef.current?.abort();
    const abortController = new AbortController();
    negotiateAbortRef.current = abortController;
    setLoading(true);
    setCustomerThinking(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/negotiate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenHeader() },
        body: JSON.stringify({ message: playerMessage }),
        signal: abortController.signal
      });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || '谈判失败。');
      if (!response.body) throw new Error('当前浏览器不支持流式谈判。');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const streamResult: { finalPayload?: NegotiationStreamPayload; error?: string } = {};
      let streamedDialogue = '';
      const updateStreamedDialogue = (content: string) => {
        if (negotiationGeneration !== negotiateGenerationRef.current) return;
        streamedDialogue += content;
        setCustomerThinking(false);
        setState((current) => {
          if (!current?.active_customer) return current;
          const history = [...current.active_customer.dialogue_history];
          const last = history[history.length - 1];
          if (last?.role === 'customer') {
            history[history.length - 1] = { role: 'customer', content: streamedDialogue };
          } else {
            history.push({ role: 'customer', content: streamedDialogue });
          }
          return { ...current, active_customer: { ...current.active_customer, dialogue_history: history } };
        });
      };
      const handleLine = (line: string) => {
        if (!line.trim()) return;
        const eventData = JSON.parse(line);
        if (eventData.type === 'chunk') updateStreamedDialogue(String(eventData.content || ''));
        if (eventData.type === 'error') streamResult.error = String(eventData.detail || '谈判结算失败。');
        if (eventData.type === 'final') streamResult.finalPayload = eventData.payload as NegotiationStreamPayload;
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        lines.forEach(handleLine);
      }
      buffer += decoder.decode();
      if (buffer.trim()) handleLine(buffer);
      if (streamResult.error) throw new Error(streamResult.error);
      if (!streamResult.finalPayload) throw new Error('谈判响应中断，尚未完成结算，请重试。');

      if (negotiationGeneration !== negotiateGenerationRef.current) return;

      const data = streamResult.finalPayload;
      if (data.stale || data.negotiation.stale) {
        setState((current) => preserveClosedCustomerState(data.state, current));
        setCustomerThinking(false);
        return;
      }
      setState((current) => preserveClosedCustomerState(data.state, current));
      setCustomerThinking(false);
      if (data.negotiation.patience_change < 0) playSound('patience_down');
      if (data.deal_completed) {
        playSound('deal');
        setSuccessMsg(data.deal_result?.message || '交易达成。');
      }
      if (data.walk_out_completed) setErrorMsg('顾客离场，交易中止，声誉 -2。');
    } catch (err) {
      if (negotiationGeneration !== negotiateGenerationRef.current) return;
      if (err instanceof DOMException && err.name === 'AbortError') {
        setCustomerThinking(false);
        return;
      }
      setState(previousState);
      setMessage(playerMessage);
      setCustomerThinking(false);
      setErrorMsg(err instanceof Error ? err.message : '谈判失败。');
    } finally {
      if (negotiateAbortRef.current === abortController) {
        negotiateAbortRef.current = null;
      }
      if (negotiationGeneration === negotiateGenerationRef.current) {
        setLoading(false);
      }
    }
  };

  const listToMarket = async (item: Item) => {
    const price = listingPrice[item.id] || item.appraised_value_low || item.purchase_price || 0;
    await runStateAction('/api/market/list', { item_id: item.id, price }, 'market_result', '已挂售。', 'cash');
    await loadMarket().catch(() => {});
  };

  const buyMarketItem = async (listingId: string) => {
    await runStateAction('/api/market/buy', { listing_id: listingId }, 'market_result', '购买成功。', 'cash');
    await loadMarket().catch(() => {});
    await loadLeaderboard().catch(() => {});
  };

  const setShowcaseItemPrice = async (item: Item) => {
    const price = showcasePrice[item.id] ?? item.showcase_price ?? item.appraised_value_low ?? item.purchase_price ?? 0;
    await runStateAction('/api/showcase/price', { item_id: item.id, price }, 'showcase_result', '橱窗售价已更新。', 'cash');
  };

  const clearShowcaseItemPrice = async (item: Item) => {
    await runStateAction('/api/showcase/price', { item_id: item.id, price: null }, 'showcase_result', '橱窗售价已取消。', 'click');
  };

  const buyShowcaseItem = async (ownerId: number, itemId: string) => {
    setLoading(true);
    try {
      const data = await apiPost<{ showcase_result: { message?: string }; state: GameState; showcase: ShowcaseData }>('/api/showcase/buy', { owner_id: ownerId, item_id: itemId });
      setState(data.state);
      setShowcase(data.showcase);
      setSuccessMsg(data.showcase_result.message || '橱窗购买成功。');
      playSound('cash');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '橱窗购买失败。');
    } finally {
      setLoading(false);
    }
  };

  const toggleShowcaseLike = async (ownerId: number) => {
    setLoading(true);
    try {
      const data = await apiPost<{ showcase_result: { message?: string }; showcase: ShowcaseData }>('/api/showcase/like', { owner_id: ownerId });
      setShowcase(data.showcase);
      setSuccessMsg(data.showcase_result.message || '已更新点赞。');
      playSound('click');
      await loadMarket().catch(() => {});
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '点赞失败。');
    } finally {
      setLoading(false);
    }
  };

  const postShowcaseGuestbook = async (ownerId: number, content: string) => {
    setLoading(true);
    try {
      const data = await apiPost<{ showcase_result: { message?: string }; showcase: ShowcaseData }>('/api/showcase/guestbook', { owner_id: ownerId, content });
      setShowcase(data.showcase);
      setSuccessMsg(data.showcase_result.message || '留言已发布。');
      playSound('click');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '留言失败。');
    } finally {
      setLoading(false);
    }
  };

  const deleteShowcaseGuestbook = async (messageId: number) => {
    setLoading(true);
    try {
      const data = await apiDelete<{ showcase_result: { message?: string }; showcase: ShowcaseData }>(`/api/showcase/guestbook/${messageId}`);
      setShowcase(data.showcase);
      setSuccessMsg(data.showcase_result.message || '留言已删除。');
      playSound('click');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '删除留言失败。');
    } finally {
      setLoading(false);
    }
  };

  if (!player || !state) {
    const bootMode = authBusy || (sessionBooting ? 'login' : null);
    return (
      <div className="h-screen w-screen bg-[#0D0F12] text-[#E0E0E0] flex items-center justify-center px-6 relative overflow-hidden">
        {bootMode ? (
          <PawnshopBootLoader mode={bootMode} shopName={authForm.shop_name.trim() || undefined} />
        ) : (
          <AuthScreen
            authForm={authForm}
            authMode={authMode}
            loading={loading}
            recoveredUsernames={recoveredUsernames}
            setAuthForm={setAuthForm}
            setAuthMode={changeAuthMode}
            onSubmit={handleAuth}
            onUseRecoveredUsername={useRecoveredUsername}
            onOpenTutorial={() => setTutorialOpen(true)}
          />
        )}
        <TutorialPanel
          open={tutorialOpen}
          onClose={() => setTutorialOpen(false)}
          username={authForm.username || '__guest__'}
          markSeenOnClose={false}
        />
        <Notifications errorMsg={errorMsg} successMsg={successMsg} setErrorMsg={setErrorMsg} setSuccessMsg={setSuccessMsg} />
      </div>
    );
  }

  const activeCustomer = state.active_customer;
  const displayedCount = state.inventory.filter((item) => item.status === 'displayed').length;

  return (
    <div className="h-screen w-screen flex flex-col bg-[#0D0F12] text-[#E0E0E0] overflow-hidden">
      <Notifications errorMsg={errorMsg} successMsg={successMsg} setErrorMsg={setErrorMsg} setSuccessMsg={setSuccessMsg} />

      <header className="h-[64px] shrink-0 bg-[#0D0F12]/80 backdrop-blur-[20px] border-b border-[#2A2D34] flex items-center justify-between px-4 md:px-6 z-40">
        <div className="flex items-center gap-3 min-w-0">
          <Store className="w-6 h-6 text-[#C8A97E] shrink-0" />
          <div className="min-w-0">
            <h1 className="text-[16px] md:text-[20px] font-bold tracking-widest truncate font-sans text-[#E0E0E0]">
              <ShopNameLine name={state.shop_name || player.shop_name} cosmetics={player} />
            </h1>
            <div className="hidden md:block text-[11px] text-[#616161] font-sans">
              <SponsorSubtitle rankingBadge={player.ranking_badge || state.ranking_badge} sponsorTitle={player.sponsor_title} />
            </div>
          </div>
        </div>
        <div className="hidden md:flex items-center gap-4 lg:gap-8 font-sans text-xs lg:text-sm text-[#9E9E9E]">
          <span>第 {state.day} 天</span>
          <span>现金 ${state.cash.toLocaleString()}</span>
          <span>声誉 {state.reputation}</span>
          <span>经济 {(state.economy_index || 1).toFixed(2)}x</span>
          <span>客流 {state.customers_seen_today ?? state.customers_served_today + (activeCustomer ? 1 : 0)}/{state.total_customers_today}</span>
          <span>展示 {displayedCount}/{state.display_capacity}</span>
        </div>
        <div className="flex items-center gap-1 md:gap-2">
          <div className="md:hidden">
            <button
              type="button"
              onClick={() => setMobileInfoOpen(true)}
              className="flex items-center gap-1.5 h-9 px-2.5 border border-[#C8A97E]/45 bg-[rgba(200,169,126,0.14)] text-[#C8A97E] text-xs font-semibold rounded-sm shrink-0 touch-manipulation"
              title="查看经营与物证详情"
            >
              <Info className="w-4 h-4 shrink-0" />
              <span>详情</span>
            </button>
          </div>
          <TutorialHelpButton onClick={() => setTutorialOpen(true)} />
          <button onClick={toggleSound} className="btn-icon !w-9 !h-9" title={soundEnabled ? '关闭音乐' : '开启音乐'}>{soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}</button>
          <button onClick={restart} disabled={resetting} className="btn-icon !w-9 !h-9" title="重置"><RefreshCw className={`w-4 h-4 ${resetting ? 'animate-spin' : ''}`} /></button>
          <button onClick={deleteAccount} disabled={loading} className="btn-icon !w-9 !h-9 hover:!text-[#F44336]" title="注销账号"><Trash2 className="w-4 h-4" /></button>
          <button onClick={logout} className="btn-icon !w-9 !h-9" title="退出"><LogOut className="w-4 h-4" /></button>
        </div>
      </header>

      <MobileStatusBar state={state} displayedCount={displayedCount} hasActiveCustomer={Boolean(activeCustomer)} />

      <div className="flex-1 flex overflow-hidden">
        <aside className="hidden md:flex w-[64px] xl:w-[240px] shrink-0 bg-[#14171C] border-r border-[#2A2D34] flex-col py-6 overflow-y-auto custom-scrollbar z-30 transition-all duration-300">
          <NavButton tab="lobby" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Store className="w-5 h-5" />} label="大堂柜台" />
          <NavButton tab="inventory" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Briefcase className="w-5 h-5" />} label="仓库藏品" />
          <NavButton tab="market" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Landmark className="w-5 h-5" />} label="玩家市场" badge={pendingReceivedOffers} />
          <NavButton tab="leaderboard" activeTab={activeTab} setActiveTab={setActiveTab} icon={<ListOrdered className="w-5 h-5" />} label="全服排行" />
          <NavButton tab="achievements" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Award className="w-5 h-5" />} label="经营成就" />
          <NavButton tab="codex" activeTab={activeTab} setActiveTab={setActiveTab} icon={<BookOpen className="w-5 h-5" />} label="经营图鉴" />
          <NavButton tab="history" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Clock className="w-5 h-5" />} label="交易记录" />
          <NavButton tab="management" activeTab={activeTab} setActiveTab={setActiveTab} icon={<TrendingUp className="w-5 h-5" />} label="经营财务" />
          <NavButton tab="staff" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Users className="w-5 h-5" />} label="员工管理" />
          <NavButton tab="upgrades" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Crown className="w-5 h-5" />} label="当铺升级" />
          <NavButton tab="shop" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Gem className="w-5 h-5" />} label="赞助支持" />
        </aside>

        <main className="flex-1 bg-[#0D0F12] p-4 pb-28 md:p-8 overflow-y-auto custom-scrollbar relative flex flex-col">
          {activeTab === 'lobby' && (
            <LobbyTab
              state={state}
              loading={loading}
              dayTransition={dayTransition}
              message={message}
              customerThinking={customerThinking}
              investigating={investigating}
              appraisalMethod={appraisalMethod}
              setMessage={setMessage}
              setAppraisalMethod={setAppraisalMethod}
              onNegotiate={negotiate}
              onInvestigate={investigateCase}
              chatEndRef={chatEndRef}
              onAction={runStateAction}
              onDismissCustomer={() => runStateAction('/api/dismiss_customer', undefined, 'result', '下一位顾客已上前。', 'click')}
              onScreenshotError={setErrorMsg}
              onScreenshotSuccess={setSuccessMsg}
            />
          )}
          {activeTab === 'inventory' && (
            <InventoryTab
              state={state}
              listingPrice={listingPrice}
              showcasePrice={showcasePrice}
              repairMethod={repairMethod}
              inventoryAppraiseMethod={inventoryAppraiseMethod}
              inventoryAppraisingId={inventoryAppraisingId}
              setListingPrice={setListingPrice}
              setRepairMethod={setRepairMethod}
              setShowcasePrice={setShowcasePrice}
              setInventoryAppraiseMethod={setInventoryAppraiseMethod}
              onAction={runStateAction}
              onList={listToMarket}
              onSetShowcasePrice={setShowcaseItemPrice}
              onClearShowcasePrice={clearShowcaseItemPrice}
              onAppraise={appraiseInventoryItem}
            />
          )}
          {activeTab === 'market' && (
            <MarketTab
              listings={listings}
              myListings={myListings}
              trades={trades}
              offers={offers}
              hotShowcases={hotShowcases}
              offerPrices={offerPrices}
              counterPrices={counterPrices}
              setOfferPrices={setOfferPrices}
              setCounterPrices={setCounterPrices}
              marketSearch={marketSearch}
              marketSort={marketSort}
              marketView={marketView}
              setMarketSearch={setMarketSearch}
              setMarketSort={setMarketSort}
              setMarketView={setMarketView}
              refresh={loadMarket}
              buy={buyMarketItem}
              openShowcase={openShowcase}
              submitOffer={submitMarketOffer}
              marketOfferAction={marketOfferAction}
              onMarketAction={runStateAction}
            />
          )}
          {activeTab === 'leaderboard' && (
            <LeaderboardTab boardType={boardType} setBoardType={setBoardType} data={leaderboard} refresh={loadLeaderboard} openShowcase={openShowcase} openMarketHot={openMarketHot} />
          )}
          {activeTab === 'history' && (
            <HistoryTab entries={state.transaction_log || []} />
          )}
          {activeTab === 'achievements' && (
            <AchievementsTab achievements={state.achievements || []} unlocks={state.achievement_unlocks || []} />
          )}
          {activeTab === 'codex' && (
            <CodexTab customers={state.customer_codex || {}} items={state.item_codex || {}} />
          )}
          {activeTab === 'shop' && player && (
            <ShopTab
              player={player}
              apiGet={apiGet}
              apiPost={apiPost}
              apiPatch={apiPatch}
              onPlayerUpdate={(p) => setPlayer((prev) => (prev ? { ...prev, ...p } : prev))}
              onSuccess={setSuccessMsg}
              onError={setErrorMsg}
            />
          )}
          {activeTab === 'showcase' && showcase && (
            <ShowcaseTab
              showcase={showcase}
              buy={buyShowcaseItem}
              back={() => setActiveTab('market')}
              onLike={toggleShowcaseLike}
              onPostGuestbook={postShowcaseGuestbook}
              onDeleteGuestbook={deleteShowcaseGuestbook}
            />
          )}
          {activeTab === 'management' && (
            <ManagementTab state={state} loanAmount={loanAmount} setLoanAmount={setLoanAmount} onAction={runStateAction} />
          )}
          {activeTab === 'staff' && (
            <StaffTab state={state} onAction={runStateAction} />
          )}
          {activeTab === 'upgrades' && (
            <UpgradesTab state={state} onAction={runStateAction} />
          )}
        </main>

        <aside className="w-[280px] shrink-0 bg-[#14171C] border-l border-[#2A2D34] hidden md:flex flex-col py-8 px-6 overflow-y-auto custom-scrollbar z-30">
          <InfoSidebar state={state} />
        </aside>
      </div>
      {mobileInfoOpen && <MobileInfoDrawer state={state} onClose={() => setMobileInfoOpen(false)} />}
      <MobileNav activeTab={activeTab} setActiveTab={setActiveTab} />

      {player && (
        <TutorialPanel
          open={tutorialOpen}
          onClose={() => setTutorialOpen(false)}
          username={player.username}
        />
      )}
    </div>
  );
}

function AuthScreen(props: {
  authForm: { username: string; password: string; shop_name: string };
  authMode: 'login' | 'register' | 'recover';
  loading: boolean;
  recoveredUsernames: string[];
  setAuthForm: (form: { username: string; password: string; shop_name: string }) => void;
  setAuthMode: (mode: 'login' | 'register' | 'recover') => void;
  onSubmit: (event: React.FormEvent) => void;
  onUseRecoveredUsername: (username: string) => void;
  onOpenTutorial: () => void;
}) {
  const { authForm, authMode, loading, onSubmit, recoveredUsernames, setAuthForm, setAuthMode, onUseRecoveredUsername, onOpenTutorial } = props;
  const [onlineCount, setOnlineCount] = useState<number | null>(null);

  const switchMode = (mode: 'login' | 'register' | 'recover') => {
    setAuthMode(mode);
  };

  useEffect(() => {
    let cancelled = false;
    const loadOnlineCount = () => {
      apiGet<{ online: number }>('/api/online/count')
        .then((data) => {
          if (!cancelled) setOnlineCount(data.online);
        })
        .catch(() => {
          if (!cancelled) setOnlineCount(null);
        });
    };
    loadOnlineCount();
    const timer = window.setInterval(loadOnlineCount, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className="w-full max-w-[520px]">
      <div className="flex items-center gap-3 mb-8">
        <Store className="w-9 h-9 text-[#C8A97E] shrink-0" />
        <div className="min-w-0">
          <h1 className="text-[28px] font-bold text-[#C8A97E] tracking-widest">当铺代理人</h1>
          <p className="text-[#616161] text-sm font-sans leading-relaxed">
            {onlineCount !== null ? (
              <>
                <span className="text-[#4CAF50] font-medium">当前 {onlineCount} 人在线</span>
                <span className="mx-2 text-[#2A2D34]">·</span>
              </>
            ) : null}
            联机市场与全服排行已开启
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-2 border-b border-[#2A2D34] mb-8">
        <div className="flex gap-6 md:gap-8 overflow-x-auto custom-scrollbar min-w-0">
          {([
            ['login', '登录账号'],
            ['register', '注册当铺'],
            ['recover', '找回账号']
          ] as const).map(([mode, label]) => (
            <button
              key={mode}
              type="button"
              onClick={() => switchMode(mode)}
              className={`pb-3 font-sans shrink-0 whitespace-nowrap ${authMode === mode ? 'text-[#C8A97E] border-b border-[#C8A97E]' : 'text-[#616161]'}`}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={onOpenTutorial}
          className="pb-3 shrink-0 text-sm font-sans text-[#C8A97E] hover:text-[#D4B88A] transition-colors inline-flex items-center gap-1.5 whitespace-nowrap"
        >
          <GraduationCap className="w-4 h-4 shrink-0" />
          新手教程
        </button>
      </div>
      {authMode === 'recover' ? (
        <form onSubmit={onSubmit} className="space-y-4">
          <p className="text-sm text-[#9E9E9E] font-sans leading-relaxed border-l-2 border-[#C8A97E] pl-4">
            忘记用户名了？输入你注册时设置的密码，系统会列出所有使用该密码的账号。若多人碰巧密码相同，会一并显示。
          </p>
          <input
            className="input-field w-full"
            style={{ paddingLeft: 16 }}
            placeholder="注册时使用的密码"
            type="password"
            value={authForm.password}
            onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })}
          />
          <button disabled={loading} className="btn-primary w-full">
            {loading ? '查找中…' : '查找用户名'}
          </button>
          {recoveredUsernames.length > 0 && (
            <div className="border-t border-[#2A2D34] pt-4 space-y-2">
              <p className="text-xs text-[#616161] font-sans">点击用户名可填入登录页：</p>
              {recoveredUsernames.map((username) => (
                <button
                  key={username}
                  type="button"
                  onClick={() => onUseRecoveredUsername(username)}
                  className="w-full text-left px-4 py-3 border-l-2 border-[#C8A97E] bg-[rgba(200,169,126,0.08)] hover:bg-[rgba(200,169,126,0.14)] transition-colors font-sans text-[#E0E0E0]"
                >
                  {username}
                </button>
              ))}
            </div>
          )}
        </form>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <input className="input-field w-full" style={{ paddingLeft: 16 }} placeholder="用户名（支持中文）" value={authForm.username} onChange={(event) => setAuthForm({ ...authForm, username: event.target.value })} />
          <input className="input-field w-full" style={{ paddingLeft: 16 }} placeholder="密码" type="password" value={authForm.password} onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })} />
          {authMode === 'register' && <input className="input-field w-full" style={{ paddingLeft: 16 }} placeholder="当铺名称" value={authForm.shop_name} onChange={(event) => setAuthForm({ ...authForm, shop_name: event.target.value })} />}
          <button disabled={loading} className="btn-primary w-full">
            {loading
              ? authMode === 'register'
                ? '正在创建当铺…'
                : authMode === 'login'
                  ? '正在进入…'
                  : '查询中…'
              : authMode === 'login'
                ? '进入当铺'
                : '挂牌开业'}
          </button>
          {authMode === 'login' && (
            <button type="button" onClick={() => switchMode('recover')} className="w-full text-center text-sm text-[#9E9E9E] font-sans hover:text-[#C8A97E] transition-colors">
              忘记用户名？用密码找回
            </button>
          )}
        </form>
      )}
    </div>
  );
}

function Notifications({ errorMsg, successMsg, setErrorMsg, setSuccessMsg }: { errorMsg: string | null; successMsg: string | null; setErrorMsg: (value: string | null) => void; setSuccessMsg: (value: string | null) => void }) {
  return (
    <div className="fixed top-[7.25rem] md:top-20 right-4 md:right-6 z-50 flex flex-col gap-2 pointer-events-none w-[90%] md:w-auto max-w-[420px]">
      {errorMsg && <Toast type="error" message={errorMsg} onClose={() => setErrorMsg(null)} />}
      {successMsg && <Toast type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}
    </div>
  );
}

function Toast({ type, message, onClose }: { type: 'error' | 'success'; message: string; onClose: () => void }) {
  const isError = type === 'error';
  return (
    <div className={`bg-[#14171C] border-l-4 ${isError ? 'border-[#F44336]' : 'border-[#4CAF50]'} p-4 shadow-lg flex items-center gap-3 pointer-events-auto animate-slide-right w-full`}>
      {isError ? <AlertTriangle className="w-5 h-5 text-[#F44336] shrink-0" /> : <CheckCircle className="w-5 h-5 text-[#4CAF50] shrink-0" />}
      <span className="font-sans text-sm text-[#E0E0E0] flex-1">{message}</span>
      <button onClick={onClose} className="text-[#616161] hover:text-[#E0E0E0] shrink-0"><X className="w-4 h-4" /></button>
    </div>
  );
}

function NavButton({ activeTab, badge, icon, label, setActiveTab, tab }: { activeTab: ActiveTab; badge?: number; icon: React.ReactNode; label: string; setActiveTab: (tab: ActiveTab) => void; tab: ActiveTab }) {
  return (
    <button title={label} onClick={() => setActiveTab(tab)} className={`nav-item relative ${activeTab === tab ? 'active' : ''} !px-0 justify-center xl:!px-5 xl:justify-start`}>
      <div className="shrink-0">{icon}</div>
      <span className="hidden xl:inline">{label}</span>
      {badge ? <span className="absolute top-2 left-8 xl:left-auto xl:right-3 w-2 h-2 rounded-full bg-[#C8A97E]" /> : null}
    </button>
  );
}

function MobileNav({ activeTab, setActiveTab }: { activeTab: ActiveTab; setActiveTab: (tab: ActiveTab) => void }) {
  const items: Array<{ tab: ActiveTab; label: string; icon: React.ReactNode }> = [
    { tab: 'lobby', label: '大堂', icon: <Store className="w-5 h-5" /> },
    { tab: 'inventory', label: '仓库', icon: <Briefcase className="w-5 h-5" /> },
    { tab: 'market', label: '市场', icon: <Landmark className="w-5 h-5" /> },
    { tab: 'leaderboard', label: '排行', icon: <ListOrdered className="w-5 h-5" /> },
    { tab: 'achievements', label: '成就', icon: <Award className="w-5 h-5" /> },
    { tab: 'codex', label: '图鉴', icon: <BookOpen className="w-5 h-5" /> },
    { tab: 'history', label: '流水', icon: <Clock className="w-5 h-5" /> },
    { tab: 'management', label: '财务', icon: <TrendingUp className="w-5 h-5" /> },
    { tab: 'staff', label: '员工', icon: <Users className="w-5 h-5" /> },
    { tab: 'upgrades', label: '升级', icon: <Crown className="w-5 h-5" /> },
    { tab: 'shop', label: '赞助', icon: <Gem className="w-5 h-5" /> }
  ];
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#14171C]/95 backdrop-blur border-t border-[#2A2D34] px-2 pt-2 pb-[calc(8px+env(safe-area-inset-bottom))]">
      <div className="flex gap-2 overflow-x-auto custom-scrollbar">
        {items.map((item) => (
          <button
            key={item.tab}
            onClick={() => setActiveTab(item.tab)}
            className={`min-w-[72px] h-[58px] flex flex-col items-center justify-center gap-1 border-b font-sans text-xs transition-colors ${activeTab === item.tab ? 'text-[#C8A97E] border-[#C8A97E] bg-[rgba(200,169,126,0.08)]' : 'text-[#9E9E9E] border-transparent'}`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}

function getTradeMode(customer: Customer) {
  return customer.role === 'seller'
    ? { label: '向顾客收购', tone: '你正在向顾客收购物品，报价越低利润空间越大。', priceLabel: '对方要价', itemSource: '顾客带货上门' }
    : { label: '向顾客出售', tone: '顾客想从你的库存买走这件物品，报价越高利润越大。', priceLabel: '对方出价', itemSource: '店内库存出货' };
}

function MobileStatusBar({ state, displayedCount, hasActiveCustomer }: { state: GameState; displayedCount: number; hasActiveCustomer: boolean }) {
  const served = state.customers_seen_today ?? state.customers_served_today + (hasActiveCustomer ? 1 : 0);
  const pills = [
    { label: '天数', value: `第 ${state.day} 天`, accent: false },
    { label: '现金', value: `$${state.cash.toLocaleString()}`, accent: true },
    { label: '声誉', value: String(state.reputation), accent: false },
    { label: '经济', value: `${(state.economy_index || 1).toFixed(2)}x`, accent: false },
    { label: '客流', value: `${served}/${state.total_customers_today}`, accent: false },
    { label: '展示', value: `${displayedCount}/${state.display_capacity}`, accent: false },
  ];
  return (
    <div className="md:hidden shrink-0 border-b border-[#2A2D34] bg-[#14171C]/95 backdrop-blur-[12px] z-30">
      <div className="px-3 py-2 overflow-x-auto custom-scrollbar">
        <div className="flex gap-2 min-w-max font-sans">
          {pills.map((pill) => (
            <div
              key={pill.label}
              className={`px-3 py-1.5 border rounded-sm shrink-0 ${pill.accent ? 'border-[#C8A97E]/50 bg-[rgba(200,169,126,0.12)]' : 'border-[#2A2D34] bg-[rgba(255,255,255,0.03)]'}`}
            >
              <div className="text-[10px] tracking-[0.12em] text-[#616161]">{pill.label}</div>
              <div className={`text-xs font-semibold mt-0.5 ${pill.accent ? 'text-[#C8A97E]' : 'text-[#E0E0E0]'}`}>{pill.value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MobileBriefCell({
  label,
  value,
  valueClassName = 'text-[#E0E0E0]',
  span = 1,
}: {
  label: string;
  value: string;
  valueClassName?: string;
  span?: 1 | 2;
}) {
  return (
    <div className={`min-w-0 leading-tight ${span === 2 ? 'col-span-2' : ''}`}>
      <span className="text-[#616161]">{label}</span>
      <span className={`ml-1 ${valueClassName}`}>{value}</span>
    </div>
  );
}

function MobileNegotiationBrief({ customer }: { customer: Customer }) {
  const tradeMode = getTradeMode(customer);
  const item = customer.item;
  const condition = CONDITION_MAP[item.condition] || item.condition;
  const appraisal = item.is_appraised_fake !== null ? appraisalVerdict(item) : null;
  const range = appraisalRange(item);
  const customerLine = `${customer.name}·${customer.trait_cn}·耐${customer.patience}${customer.is_past_self ? '·镜影' : customer.is_returning ? `·${customer.relationship_cn}` : ''}`;
  const appraisalLine = appraisal
    ? `${appraisal}${item.appraisal_confidence !== null ? `/${item.appraisal_confidence}%` : ''}`
    : null;
  return (
    <div className="md:hidden sticky top-0 z-20 -mx-4 mb-3 border-y border-[#2A2D34] bg-[#0D0F12]/97 backdrop-blur-[16px] shadow-[0_8px_20px_rgba(0,0,0,0.32)]">
      <div className="px-3 py-2 border-b border-[#2A2D34]/70 flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[#C8A97E] text-[10px] font-bold tracking-[0.12em] shrink-0">{tradeMode.label}</span>
            <span className="text-[9px] text-[#616161] shrink-0">{tradeMode.itemSource}</span>
          </div>
          <h3 className="text-[13px] font-bold text-[#E0E0E0] leading-snug">{item.name}</h3>
        </div>
        <div className="text-right shrink-0 pl-1">
          <div className="text-[9px] text-[#616161]">{tradeMode.priceLabel}</div>
          <div className="text-[#C8A97E] text-[17px] font-bold leading-tight">${customer.current_offer.toLocaleString()}</div>
        </div>
      </div>
      <div className="px-3 py-1.5 grid grid-cols-2 gap-x-2.5 gap-y-1 text-[10px] font-sans">
        <MobileBriefCell label="顾客" value={customerLine} />
        <MobileBriefCell label="稀有" value={item.rarity_cn} valueClassName={RARITY_COLOR[item.rarity] || 'text-[#9E9E9E]'} />
        <MobileBriefCell label="成色" value={condition} valueClassName="text-[#C8A97E]" />
        <MobileBriefCell label="年代" value={item.era} />
        <MobileBriefCell label="市价" value={`$${item.market_value.toLocaleString()}`} />
        {range ? <MobileBriefCell label="鉴定" value={range} /> : <div />}
        {appraisalLine ? (
          <MobileBriefCell label="结论" value={appraisalLine} valueClassName="text-[#E0E0E0]" span={range ? 1 : 2} />
        ) : (
          <div />
        )}
        {customer.transaction_prefs?.[0] && (
          <MobileBriefCell label="偏好" value={customer.transaction_prefs[0]} span={2} />
        )}
        {customer.persuasion_points?.[0] && (
          <MobileBriefCell label="突破" value={customer.persuasion_points[0]} valueClassName="text-[#C8A97E]/90" span={2} />
        )}
        {item.authentication_tips?.[0] && <MobileBriefCell label="鉴别" value={item.authentication_tips[0]} span={2} />}
        {customer.last_deal_summary && (
          <MobileBriefCell label="往来" value={customer.last_deal_summary} valueClassName="text-[#616161]" span={2} />
        )}
      </div>
    </div>
  );
}

function MobileInfoDrawer({ onClose, state }: { state: GameState; onClose: () => void }) {
  return (
    <div className="md:hidden fixed inset-0 z-[60]">
      <button aria-label="关闭信息栏" onClick={onClose} className="absolute inset-0 bg-black/55 backdrop-blur-sm" />
      <aside className="absolute inset-x-0 bottom-0 max-h-[88vh] bg-[#14171C] border-t border-[#2A2D34] rounded-t-md py-5 px-5 overflow-y-auto custom-scrollbar shadow-2xl animate-slide-up pb-[calc(16px+env(safe-area-inset-bottom))]">
        <div className="w-10 h-1 rounded-full bg-[#2A2D34] mx-auto mb-4" aria-hidden />
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[#C8A97E] font-bold text-lg">经营与物证详情</h2>
          <button onClick={onClose} className="btn-icon !w-9 !h-9" title="关闭"><X className="w-4 h-4" /></button>
        </div>
        <InfoSidebar state={state} />
      </aside>
    </div>
  );
}

function ImmersiveWaitScreen({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex-1 w-full min-h-[min(72vh,640px)] flex flex-col items-center justify-center px-4 md:px-8 py-10 md:py-14">
      {children}
    </div>
  );
}

function ImmersiveWaitLoader({
  centerIcon,
  footerHint,
  phases,
  subtitle,
  tips,
  title
}: {
  centerIcon: React.ReactNode;
  footerHint?: string;
  phases: string[];
  subtitle: string;
  tips: string[];
  title: string;
}) {
  const [tipIndex, setTipIndex] = useState(0);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const phaseCount = phases.length;
  const lineFillPercent = phaseCount > 1 ? (phaseIndex / (phaseCount - 1)) * 100 : 0;
  useEffect(() => {
    const tipTimer = window.setInterval(() => setTipIndex((index) => (index + 1) % tips.length), 2600);
    return () => window.clearInterval(tipTimer);
  }, [tips.length]);
  useEffect(() => {
    const phaseTimer = window.setInterval(
      () => setPhaseIndex((index) => (index < phases.length - 1 ? index + 1 : index)),
      4200
    );
    return () => window.clearInterval(phaseTimer);
  }, [phases.length]);
  return (
    <div className="w-full max-w-xl flex flex-col items-center justify-center text-center animate-slide-up">
      <div className="relative mb-8 md:mb-10 flex items-center justify-center">
        <div className="day-loader-ring" />
        <div className="absolute day-loader-icon text-[#C8A97E]">{centerIcon}</div>
      </div>
      <h1 className="text-[24px] md:text-[32px] font-bold text-[#C8A97E] mb-3 font-sans tracking-wide">{title}</h1>
      <p className="text-[#9E9E9E] text-sm md:text-[15px] mb-8 md:mb-10 max-w-md leading-relaxed font-serif px-2">{subtitle}</p>

      <div className="immersive-stepper mb-6 font-sans" aria-hidden>
        <div className="immersive-stepper__dots">
          <div className="immersive-stepper__connector" aria-hidden>
            <div className="immersive-stepper__line-bg" />
            <div className="immersive-stepper__line-fill" style={{ width: `${lineFillPercent}%` }} />
          </div>
          <div className="grid grid-cols-4 relative z-10 h-full">
            {phases.map((phase, index) => {
              const active = index <= phaseIndex;
              const current = index === phaseIndex;
              return (
                <div key={`dot-${phase}`} className="flex justify-center items-center">
                  <span
                    className={`immersive-stepper__dot ${active ? 'immersive-stepper__dot--active' : ''} ${
                      current ? 'immersive-stepper__dot--current' : ''
                    }`}
                  />
                </div>
              );
            })}
          </div>
        </div>
        <div className="grid grid-cols-4">
          {phases.map((phase, index) => {
            const active = index <= phaseIndex;
            const current = index === phaseIndex;
            return (
              <p
                key={`label-${phase}`}
                className={`immersive-stepper__label ${
                  current ? 'text-[#C8A97E] font-semibold' : active ? 'text-[#9E9E9E]' : 'text-[#616161]'
                }`}
              >
                {phase}
              </p>
            );
          })}
        </div>
      </div>

      <p key={tipIndex} className="text-[#9E9E9E] text-xs md:text-sm font-sans day-loader-tip min-h-[22px] max-w-sm mt-5 px-2">
        {tips[tipIndex]}
      </p>
      {footerHint ? <p className="text-[#616161] text-[11px] font-sans mt-6 max-w-sm leading-relaxed px-2">{footerHint}</p> : null}
    </div>
  );
}

function PawnshopBootLoader({ mode, shopName }: { mode: 'register' | 'login'; shopName?: string }) {
  const shopLabel = shopName || '你的当铺';
  const config =
    mode === 'register'
      ? {
          title: '正在创办当铺',
          subtitle: `「${shopLabel}」即将挂牌开业，街角已有路人驻足张望`,
          phases: ['揭牌立项', '整顿门面', '备齐本金', '恭迎首日'],
          tips: [
            `擦拭「${shopLabel}」金字匾额…`,
            '核实开业本金 $10,000 与空白账本…',
            '摆放柜台、秤杆与验光镜…',
            '打通鉴定室与修复工坊的隔间…',
            '撰写掌柜名讳，登记行当名册…',
            '联络行会，安排首日迎客次序…',
            '听闻已有稀客在街口徘徊…',
            '街角风铃轻响，卷帘即将拉起…'
          ]
        }
      : {
          title: '正在推开当铺门',
          subtitle: '核对密令，翻开昨夜封存的账本，今日柜台仍等着你',
          phases: ['验明身份', '翻阅账本', '整理柜台', '开门迎客'],
          tips: [
            '核对掌柜名讳与通行密令…',
            '拂去柜台浮尘，翻看经营日志…',
            '清点库存市值与昨日结余…',
            '整理展示柜与待接见的来客…',
            '嗅一嗅街市风向，掂量今日客流…',
            '擦拭柜台，等待第一声叩门…'
          ]
        };
  return (
    <ImmersiveWaitScreen>
      <ImmersiveWaitLoader
        centerIcon={mode === 'register' ? <Store className="w-7 h-7" /> : <Clock className="w-7 h-7" />}
        title={config.title}
        subtitle={config.subtitle}
        phases={config.phases}
        tips={config.tips}
        footerHint={mode === 'register' ? '开张筹备颇费时辰，请勿中途离柜' : '账本厚重，请稍候片刻'}
      />
    </ImmersiveWaitScreen>
  );
}

function DayTransitionLoader({ mode }: { mode: 'end_day' | 'next_day' }) {
  const config = mode === 'end_day'
    ? {
        title: '正在结算今日经营',
        subtitle: '账本合上，街灯渐暗，当铺进入打烊时分',
        phases: ['核对流水', '结算开销', '清点库存', '打烊收工'],
        tips: ['核对今日交易流水…', '结算员工薪水与运营成本…', '清点库存持有与市场行情…', '整理今日坊间轶事与往来账目…', '留意是否还有未了之事…']
      }
    : {
        title: '正在开启新的一天',
        subtitle: '卷帘拉起，街声渐近，当铺准备开门迎客',
        phases: ['翻开日志', '刷新行情', '整理库房', '等待叩门'],
        tips: [
          '翻开新一页经营日志…',
          '打听街坊行情与行市涨跌…',
          '整理仓库与展示柜…',
          '巷口已有人影向当铺张望…',
          '擦拭柜台，等待第一声叩门…'
        ]
      };
  return (
    <ImmersiveWaitScreen>
      <ImmersiveWaitLoader
        centerIcon={<Clock className="w-7 h-7" />}
        title={config.title}
        subtitle={config.subtitle}
        phases={config.phases}
        tips={config.tips}
        footerHint={mode === 'next_day' ? '客官尚在途中，街市繁忙时须多候片刻' : undefined}
      />
    </ImmersiveWaitScreen>
  );
}

/** 鉴定走底部方法选择 +「鉴定」按钮，不占案件簿按钮位 */
const CASE_ACTION_ORDER = ['chat', 'visual', 'provenance', 'records', 'expert'] as const;

function caseClueTypeLabel(type: string) {
  const labels: Record<string, string> = {
    authenticity: '真伪',
    value: '价值',
    provenance: '来历',
    risk: '风险',
    condition: '品相'
  };
  return labels[type] || type;
}

function LobbyTab({ appraisalMethod, investigating, chatEndRef, customerThinking, dayTransition, loading, message, onAction, onInvestigate, onDismissCustomer, onNegotiate, onScreenshotError, onScreenshotSuccess, setAppraisalMethod, setMessage, state }: { state: GameState; loading: boolean; customerThinking: boolean; dayTransition: 'end_day' | 'next_day' | null; investigating: boolean; appraisalMethod: string; message: string; setMessage: (value: string) => void; setAppraisalMethod: (value: string) => void; onNegotiate: (event: React.FormEvent) => void; onInvestigate: (action: string) => Promise<void>; onDismissCustomer: () => Promise<void>; onScreenshotSuccess: (message: string) => void; onScreenshotError: (message: string) => void; chatEndRef: React.RefObject<HTMLDivElement | null>; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  const customer = state.active_customer;
  useEffect(() => {
    if (customer?.session_closed) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [customer?.session_closed, customer?.dialogue_history.length, chatEndRef]);
  if (dayTransition === 'next_day' && (state.day_ended || loading)) {
    return (
      <div className="flex-1 flex flex-col w-full min-h-0">
        <DayTransitionLoader mode="next_day" />
      </div>
    );
  }
  if (state.day_ended) {
    return (
      <div className="max-w-3xl mx-auto w-full flex-1 flex flex-col justify-center">
        <h1 className="text-[32px] font-bold text-[#C8A97E] mb-8">第 {state.day} 天 营业结算</h1>
        <SummaryLine label="期初资金" value={state.daily_summary.starting_cash} />
        <SummaryLine label="交易盈亏" value={state.daily_summary.revenue} delta />
        <SummaryLine label="员工薪水" value={-state.daily_summary.salaries} delta />
        <SummaryLine label="运营成本" value={-state.daily_summary.operating_cost} delta />
        <SummaryLine label="库存持有" value={-state.daily_summary.holding_cost} delta />
        <SummaryLine label="贷款利息" value={-state.daily_summary.loan_interest} delta />
        <SummaryLine label="营业税" value={-state.daily_summary.tax} delta />
        <SummaryLine label="净变化" value={state.daily_summary.net_profit} delta />
        <p className="mt-4 text-xs text-[#616161] font-sans">
          经济指数 {(state.daily_summary.economy_index || state.economy_index || 1).toFixed(3)}，
          日变化 {formatSignedPercent(state.daily_summary.inflation_rate || state.inflation_rate || 0)}。
        </p>
        <div className="my-8 space-y-3">{state.daily_summary.events.map((event, idx) => <p key={idx} className="border-l border-[#2A2D34] pl-4 text-[#9E9E9E]">{event}</p>)}</div>
        {state.pending_event && (
          <div className="border-y border-[#2A2D34] py-5 mb-6">
            <h2 className="text-[#C8A97E] text-xl font-bold mb-2">{state.pending_event.title}</h2>
            <p className="text-[#E0E0E0] mb-4">{state.pending_event.description}</p>
            <p className="text-xs text-[#9E9E9E] font-sans mb-3 tracking-wide">请做出选择（点击选项生效）</p>
            <div className="space-y-3">
              {state.pending_event.choices.map((choice) => (
                <button
                  key={choice.id}
                  type="button"
                  disabled={loading}
                  onClick={() => onAction('/api/event/choice', { choice_id: choice.id }, 'event_result', '事件已处理。', 'click')}
                  className="event-choice touch-manipulation"
                >
                  <span className="event-choice__body">
                    <span className="event-choice__label">{choice.label}</span>
                    <span className="event-choice__effect">{choice.effect}</span>
                  </span>
                  <ArrowRight className="event-choice__icon" aria-hidden />
                </button>
              ))}
            </div>
          </div>
        )}
        <button onClick={() => onAction('/api/next_day', undefined, 'result', '新的一天开始了。', 'cash')} disabled={loading || !!state.pending_event} className="btn-primary w-full md:w-auto">
          {loading ? <><RefreshCw className="w-5 h-5 mr-2 animate-spin" />切换中…</> : <>开启第 {state.day + 1} 天 <ArrowRight className="w-5 h-5 ml-2" /></>}
        </button>
      </div>
    );
  }
  if (!customer) {
    if (dayTransition === 'end_day') {
      return (
        <div className="flex-1 flex flex-col w-full min-h-0">
          <DayTransitionLoader mode="end_day" />
        </div>
      );
    }
    const seenToday = state.customers_seen_today ?? state.customers_served_today;
    const trafficComplete = state.daily_traffic_complete ?? seenToday >= state.total_customers_today;
    if (!trafficComplete) {
      const remaining = Math.max(0, state.total_customers_today - seenToday);
      return (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
          <Users className="w-12 h-12 text-[#C8A97E] mb-6" />
          <h1 className="text-[28px] font-bold mb-3">还有顾客在路上</h1>
          <p className="text-[#9E9E9E] mb-6 max-w-md">
            今日客流 {seenToday}/{state.total_customers_today}，预计还有 {remaining} 位预约顾客即将上门。
          </p>
          <button
            onClick={() => onAction('/api/dismiss_customer', undefined, 'result', '下一位顾客已上前。', 'click')}
            disabled={loading}
            className="btn-primary"
          >
            {loading ? <><RefreshCw className="w-5 h-5 mr-2 animate-spin" />请稍候…</> : '迎接下一位顾客'}
          </button>
        </div>
      );
    }
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center">
        <Clock className="w-12 h-12 text-[#616161] mb-6" />
        <h1 className="text-[32px] font-bold mb-4">今日打烊</h1>
        <p className="text-[#9E9E9E] mb-6">今日 {state.total_customers_today} 位顾客已全部接待完毕。</p>
        <button onClick={() => onAction('/api/end_day', undefined, 'summary', '结算完成。', 'deal')} disabled={loading} className="btn-primary">
          {loading ? <><RefreshCw className="w-5 h-5 mr-2 animate-spin" />结算中…</> : '营业结算'}
        </button>
      </div>
    );
  }
  const quickOffer = (ratio: number) => {
    const initial = customer.initial_offer ?? customer.current_offer;
    const current = customer.current_offer;
    let price: number;
    if (ratio === 0.5) {
      if (customer.role === 'seller') {
        // 收购：对方降价让步时，试探价随之中幅上移，而非跟着往下滑
        const concession = Math.max(0, initial - current);
        price = Math.round(initial * 0.5 + concession * 0.3);
        price = Math.min(price, Math.max(1, current - 1));
      } else {
        // 出售：对方抬价时，要价随之上探
        const raised = Math.max(0, current - initial);
        price = Math.round(initial * 1.15 + raised * 0.35);
        price = Math.max(price, current + 1);
      }
    } else {
      price = Math.max(1, Math.round(current * ratio));
    }
    price = Math.max(1, price);
    const formattedPrice = price.toLocaleString();
    // persuasion_points 是「突破口」策略提示，不能原样拼进玩家台词
    const sellerHooks = [
      '咱们实在点谈',
      '现金立结，你也省心',
      '这价我已经把风险算进去了',
      '市场行情就这样，我也不想压太狠',
    ];
    const buyerHooks = [
      '品相和来历我都摆明了',
      '这价算下来你也不亏',
      '店里的把关成本我也算进去了',
      '诚心要的话，就这个数',
    ];
    const hooks = customer.role === 'seller' ? sellerHooks : buyerHooks;
    const hook = hooks[Math.floor(Math.random() * hooks.length)];
    const sellerLines = [
      `${hook}，我出 $${formattedPrice}，现金马上给你。`,
      `$${formattedPrice}，我现在就能付款，这价不算亏待你。`,
      `按我看这件货的风险，最多先报 $${formattedPrice}。`,
    ];
    const buyerLines = [
      `${hook}，这件货 $${formattedPrice} 给你。`,
      `$${formattedPrice}，你今天带走，来源说明我也一并给你。`,
      `我开 $${formattedPrice}，品相和来历都值这个价。`,
    ];
    const lines = customer.role === 'seller' ? sellerLines : buyerLines;
    setMessage(lines[Math.floor(Math.random() * lines.length)]);
  };
  const selectedAppraisal = state.appraisal_methods[appraisalMethod] || state.appraisal_methods.standard;
  const appraisalSkillLevel = state.skills.appraisal?.level ?? 1;
  const appraisalRoomLevel = state.facilities.appraisal_room ?? 1;
  const appraisalContext = {
    marketValue: customer.item.market_value,
    skillLevel: appraisalSkillLevel,
    roomLevel: appraisalRoomLevel,
    hasAppraiser: Boolean(state.staff.appraiser)
  };
  const appraisalPreview = computeAppraisalPreview(
    appraisalContext.marketValue,
    selectedAppraisal,
    appraisalContext.skillLevel,
    appraisalContext.roomLevel,
    appraisalContext.hasAppraiser,
    state.economy_index || 1
  );
  const tradeMode = getTradeMode(customer);
  const sessionClosed = customer.session_closed;
  const caseState = customer.case_state;
  const casePointsLeft = caseState?.points_remaining ?? 0;
  const caseUsed = caseState?.investigations_used ?? [];
  const caseActions = state.case_investigation_actions || {};
  const canCaseInvestigate = (action: string) => {
    if (sessionClosed || loading || investigating) return false;
    if (caseUsed.includes(action)) return false;
    if (casePointsLeft < 1) return false;
    const meta = caseActions[action];
    if (meta?.requires_staff === 'appraiser' && !state.staff.appraiser) return false;
    return true;
  };
  return (
    <div className="max-w-3xl mx-auto w-full flex-1 flex flex-col">
      <MobileNegotiationBrief customer={customer} />
      <div className="mb-10 border-b border-[#2A2D34] pb-4 pt-2 md:-mt-8 sticky top-0 bg-[#0D0F12]/95 backdrop-blur z-10 hidden md:block">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 font-sans">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="text-[#C8A97E] text-sm tracking-[0.25em]">{tradeMode.label}</span>
              <span className="text-[#616161] text-xs">{customer.trait_cn} / 耐心 {customer.patience}</span>
              {customer.is_past_self && <span className="text-[#C8A97E] text-xs border-l border-[#2A2D34] pl-3 tracking-wide">镜影</span>}
              {customer.is_returning && !customer.is_past_self && <span className="text-[#C8A97E] text-xs border-l border-[#2A2D34] pl-3">{customer.relationship_cn} · 第 {customer.visit_count} 次</span>}
            </div>
            <p className="text-[#9E9E9E] text-xs leading-relaxed">{customer.age} 岁 · {customer.appearance}</p>
            <p className="text-[#616161] text-xs leading-relaxed mt-1">{customer.backstory}</p>
            {customer.last_deal_summary && <p className="text-[#616161] text-xs mt-1">上次往来：{customer.last_deal_summary}</p>}
            <p className="text-[#616161] text-xs mt-1">{tradeMode.tone}</p>
          </div>
          <div className="text-left sm:text-right">
            <div className="text-xs text-[#616161]">{tradeMode.priceLabel}</div>
            <div className="text-[#C8A97E] text-[28px] font-bold leading-tight">${customer.current_offer.toLocaleString()}</div>
          </div>
        </div>
      </div>
      {!sessionClosed && caseState && (
        <div className="mb-5 border-l-2 border-[#C8A97E] pl-4 pr-1 animate-slide-up">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3 font-sans">
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-[#C8A97E]" />
              <span className="text-[#C8A97E] text-sm tracking-[0.2em]">案件簿</span>
            </div>
            <span className="text-xs text-[#616161]">
              调查点 {casePointsLeft}/{caseState.points_max}
              {caseState.flags.knows_fake_risk && <span className="text-[#FF9800] ml-2">已掌握真伪疑点</span>}
              {caseState.flags.graceful_reject && <span className="text-[#4CAF50] ml-2">可无损拒收</span>}
            </span>
          </div>
          {caseState.clues.length > 0 ? (
            <ul className="space-y-0 mb-3">
              {caseState.clues.map((clue) => (
                <li key={clue.id} className="py-2.5 border-b border-[#2A2D34] last:border-b-0">
                  <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                    <span className="text-[#C8A97E] text-sm font-semibold">{clue.title}</span>
                    <span className="text-[#616161] text-xs">{caseClueTypeLabel(clue.type)} · 可信度 {Math.round(clue.reliability * 100)}%</span>
                  </div>
                  <p className="text-[#9E9E9E] text-xs leading-relaxed mt-1">{clue.detail}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[#616161] text-xs mb-3">尚未取得线索。可先套话、查档；专业鉴定用下方方法选择后点「鉴定」（同样消耗 1 调查点）。</p>
          )}
          <div className="flex flex-wrap gap-1.5">
            {CASE_ACTION_ORDER.map((action) => {
              const meta = caseActions[action];
              if (!meta) return null;
              const disabled = !canCaseInvestigate(action);
              const used = caseUsed.includes(action);
              return (
                <button
                  key={action}
                  type="button"
                  disabled={disabled}
                  onClick={() => onInvestigate(action)}
                  className={`btn-secondary !h-8 !px-2.5 !text-xs touch-manipulation ${used ? 'opacity-40' : ''}`}
                  title={meta.requires_staff === 'appraiser' && !state.staff.appraiser ? '需雇佣鉴定师' : undefined}
                >
                  {investigating ? '…' : used ? `已${meta.name_cn}` : meta.name_cn}
                </button>
              );
            })}
          </div>
        </div>
      )}
      <div className="flex items-center justify-between gap-3 mb-3 shrink-0 font-sans">
        <span className="text-xs text-[#616161] tracking-wide">柜台对话 · 可生成分享图</span>
        <ChatScreenshotButton
          state={state}
          customer={customer}
          onSuccess={onScreenshotSuccess}
          onError={onScreenshotError}
        />
      </div>
      <div className="flex-1 overflow-y-auto custom-scrollbar pr-3 space-y-5 pb-6">
        {customer.dialogue_history.map((turn, idx) => (
          turn.role === 'narrator' ? (
            <Chat key={idx} narrator>{turn.content}</Chat>
          ) : (
            <Chat key={idx} speaker={turn.role === 'player' ? '你' : customer.name} right={turn.role === 'player'} avatarUrl={turn.role === 'customer' ? customer.avatar_url : undefined}>
              {turn.content}
            </Chat>
          )
        ))}
        {customerThinking && <CustomerThinkingBubble customer={customer} />}
        <div ref={chatEndRef} />
      </div>
      <div className="border-t border-[#2A2D34] pt-3 shrink-0">
        {sessionClosed ? (
          <div className="animate-slide-up">
            <div className={`mb-4 px-4 py-4 border-l-2 ${sessionClosed === 'deal' ? 'border-[#4CAF50] bg-[rgba(76,175,80,0.08)]' : 'border-[#FF9800] bg-[rgba(255,152,0,0.08)]'}`}>
              <div className={`font-bold mb-1 ${sessionClosed === 'deal' ? 'text-[#4CAF50]' : 'text-[#FF9800]'}`}>
                {sessionClosed === 'deal' ? '交易已落定' : '顾客告辞离去'}
              </div>
              <p className="text-sm text-[#9E9E9E] leading-relaxed">{customer.deal_summary || (sessionClosed === 'deal' ? '这笔买卖已经办妥。' : '对方没有继续谈下去。')}</p>
              <p className="text-xs text-[#616161] mt-2">请读完上面的对话，再送离顾客。觉得好笑？可先保存对话截图再送客。</p>
            </div>
            <div className="mb-3 flex justify-end">
              <ChatScreenshotButton
                state={state}
                customer={customer}
                onSuccess={onScreenshotSuccess}
                onError={onScreenshotError}
                prominent
              />
            </div>
            <button onClick={onDismissCustomer} disabled={loading} className="btn-primary w-full">
              {loading ? <><RefreshCw className="w-5 h-5 mr-2 animate-spin" />请稍候…</> : '送离顾客，迎接下一位'}
            </button>
          </div>
        ) : (
          <>
        <div className="md:hidden space-y-2">
          <div className="grid grid-cols-3 gap-1.5">
            <button type="button" onClick={() => quickOffer(0.5)} className="btn-secondary !h-9 !px-1 !text-xs touch-manipulation">试探价</button>
            <button type="button" onClick={() => quickOffer(1)} className="btn-secondary !h-9 !px-1 !text-xs touch-manipulation">当前价</button>
            <button type="button" onClick={() => quickOffer(2)} className="btn-secondary !h-9 !px-1 !text-xs touch-manipulation">强势报价</button>
          </div>
          <form onSubmit={onNegotiate} className="flex gap-1.5">
            <input
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              className="input-field flex-1 min-w-0 !h-10 !py-2"
              style={{ paddingLeft: 12 }}
              placeholder="用自然语言谈判..."
            />
            <button type="submit" disabled={loading} className="btn-primary !h-10 !px-4 shrink-0 touch-manipulation">谈判</button>
          </form>
          <div className="flex gap-1.5 items-stretch">
            <select
              value={appraisalMethod}
              onChange={(event) => setAppraisalMethod(event.target.value)}
              className="input-field !h-10 !px-2 !text-xs w-[5.5rem] shrink-0 touch-manipulation"
            >
              {Object.entries(state.appraisal_methods).map(([key, info]) => {
                const preview = computeAppraisalPreview(appraisalContext.marketValue, info, appraisalContext.skillLevel, appraisalContext.roomLevel, appraisalContext.hasAppraiser, state.economy_index || 1);
                return (
                  <option key={key} value={key}>
                    {info.name_cn.replace(/鉴定$/, '')} {formatAppraisalPercent(preview.fakeDetectionRate)}
                  </option>
                );
              })}
            </select>
            <button
              type="button"
              onClick={() => onInvestigate('appraise')}
              disabled={!canCaseInvestigate('appraise')}
              title={casePointsLeft < 1 ? '调查点已用尽' : '消耗 1 调查点并完成鉴定'}
              className="btn-secondary !h-10 !px-3 !text-sm shrink-0 touch-manipulation"
            >
              {investigating ? '…' : caseUsed.includes('appraise') ? '已鉴' : '鉴定'}
            </button>
            <button type="button" onClick={() => onAction('/api/deal', undefined, 'deal_result', '成交。', 'deal')} className="btn-secondary !h-10 flex-1 min-w-0 !text-sm touch-manipulation">成交</button>
            <button type="button" onClick={() => onAction('/api/reject', undefined, 'result', '已拒绝。', 'reject')} className="btn-secondary !h-10 flex-1 min-w-0 !text-sm touch-manipulation">拒绝</button>
          </div>
        </div>
        <div className="hidden md:block">
          <div className="flex gap-2 mb-3">
            <button type="button" onClick={() => quickOffer(0.5)} className="btn-secondary !h-8 !px-3 !text-xs">试探价</button>
            <button type="button" onClick={() => quickOffer(1)} className="btn-secondary !h-8 !px-3 !text-xs">当前价</button>
            <button type="button" onClick={() => quickOffer(2)} className="btn-secondary !h-8 !px-3 !text-xs">强势报价</button>
          </div>
          <form onSubmit={onNegotiate} className="flex gap-3">
            <input value={message} onChange={(event) => setMessage(event.target.value)} className="input-field flex-1" style={{ paddingLeft: 16 }} placeholder="用自然语言谈判..." />
            <button type="submit" disabled={loading} className="btn-primary">谈判</button>
          </form>
          <div className="flex flex-row gap-2 mt-3">
            <select value={appraisalMethod} onChange={(event) => setAppraisalMethod(event.target.value)} className="input-field !h-10 !px-3 w-[180px]">
              {Object.entries(state.appraisal_methods).map(([key, info]) => {
                const preview = computeAppraisalPreview(appraisalContext.marketValue, info, appraisalContext.skillLevel, appraisalContext.roomLevel, appraisalContext.hasAppraiser, state.economy_index || 1);
                return (
                  <option key={key} value={key}>
                    {info.name_cn}（识破 {formatAppraisalPercent(preview.fakeDetectionRate)}）
                  </option>
                );
              })}
            </select>
            <button
              type="button"
              onClick={() => onInvestigate('appraise')}
              disabled={!canCaseInvestigate('appraise')}
              title={casePointsLeft < 1 ? '调查点已用尽' : '消耗 1 调查点并完成鉴定'}
              className="btn-secondary flex-1 !h-10"
            >
              {investigating ? '调查中...' : caseUsed.includes('appraise') ? '已鉴定' : '鉴定'}
            </button>
            <button type="button" onClick={() => onAction('/api/deal', undefined, 'deal_result', '成交。', 'deal')} className="btn-secondary flex-1 !h-10">成交</button>
            <button type="button" onClick={() => onAction('/api/reject', undefined, 'result', '已拒绝。', 'reject')} className="btn-secondary flex-1 !h-10">拒绝</button>
          </div>
        </div>
        <p className="mt-2 text-[10px] md:text-xs text-[#616161] font-sans leading-snug line-clamp-2 md:line-clamp-none md:leading-relaxed">
          {selectedAppraisal.name_cn}：预计 ${appraisalPreview.cost.toLocaleString()}；
          赝品识破率 {formatAppraisalPercent(appraisalPreview.fakeDetectionRate)}（若为赝品时判定为假）；
          估值误差 ±{formatAppraisalPercent(appraisalPreview.valueErrorMargin)}。
          {selectedAppraisal.desc}
        </p>
          </>
        )}
      </div>
    </div>
  );
}

function ChatScreenshotButton({
  customer,
  onError,
  onSuccess,
  prominent,
  state,
}: {
  state: GameState;
  customer: Customer;
  onSuccess: (message: string) => void;
  onError: (message: string) => void;
  prominent?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const filename = buildScreenshotFilename(customer.name, state.day);
  const speechCount = customer.dialogue_history.filter((turn) => turn.role !== 'narrator').length;
  const disabled = busy || speechCount < 1;
  const canShare = typeof navigator !== 'undefined' && Boolean(navigator.share);
  const canCopy = typeof navigator !== 'undefined' && Boolean(navigator.clipboard?.write) && typeof ClipboardItem !== 'undefined';

  const closePreview = () => {
    setPreviewUrl(null);
    canvasRef.current = null;
  };

  const generate = async () => {
    if (speechCount < 1) {
      onError('还没有可保存的对话，先和顾客聊几句吧。');
      return;
    }
    setBusy(true);
    try {
      const tradeMode = getTradeMode(customer);
      const canvas = await renderChatScreenshot({
        shopName: state.shop_name,
        gameDay: state.day,
        customerName: customer.name,
        customerTrait: customer.trait_cn,
        tradeLabel: tradeMode.label,
        itemName: customer.item.name,
        itemRarityCn: customer.item.rarity_cn,
        avatarUrl: customer.avatar_url,
        dialogue: customer.dialogue_history,
        dealSummary: customer.deal_summary,
        sessionClosed: customer.session_closed,
        playUrl: window.location.origin,
      });
      canvasRef.current = canvas;
      setPreviewUrl(canvas.toDataURL('image/png'));
    } catch {
      onError('生成截图失败，请稍后再试。');
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = () => {
    if (!canvasRef.current) return;
    downloadChatScreenshot(canvasRef.current, filename);
    onSuccess('对话截图已保存，可发到群聊或社交平台。');
    closePreview();
  };

  const handleCopy = async () => {
    if (!canvasRef.current) return;
    const ok = await copyChatScreenshotToClipboard(canvasRef.current);
    if (ok) {
      onSuccess('截图已复制到剪贴板，可直接粘贴发送。');
      closePreview();
    } else {
      onError('当前浏览器不支持复制图片，请使用「保存图片」。');
    }
  };

  const handleShare = async () => {
    if (!canvasRef.current) return;
    const result = await shareChatScreenshot(
      canvasRef.current,
      `当铺代理人 · ${customer.name} 的搞笑对话`,
      `${state.shop_name} 第 ${state.day} 天 · ${customer.item.name}`
    );
    if (result === 'shared') {
      onSuccess('已通过系统分享面板发出。');
      closePreview();
    } else if (result === 'unsupported') {
      handleDownload();
    }
  };

  return (
    <>
      <button
        type="button"
        disabled={disabled}
        onClick={() => void generate()}
        className={
          prominent
            ? 'btn-primary !h-10 !px-4 !text-sm touch-manipulation'
            : 'btn-secondary !h-8 !px-3 !text-xs touch-manipulation inline-flex items-center gap-1.5'
        }
        title={speechCount < 1 ? '先进行对话' : '生成可分享的对话长图'}
      >
        {busy ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ImageDown className="w-4 h-4" />}
        {busy ? '生成中…' : prominent ? '保存搞笑对话图' : '保存对话图'}
      </button>
      {previewUrl && (
        <div
          className="fixed inset-0 z-[100] flex items-end md:items-center justify-center bg-[rgba(0,0,0,0.72)] backdrop-blur-sm p-0 md:p-6"
          role="dialog"
          aria-modal
          aria-label="对话截图预览"
          onClick={closePreview}
        >
          <div
            className="w-full md:max-w-lg max-h-[92vh] flex flex-col bg-[#14171C] border-t md:border border-[#2A2D34] md:rounded-sm shadow-2xl animate-slide-up"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#2A2D34] font-sans shrink-0">
              <h3 className="text-[#C8A97E] font-semibold text-sm">对话截图预览</h3>
              <button type="button" onClick={closePreview} className="btn-icon !w-8 !h-8" aria-label="关闭">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="overflow-y-auto custom-scrollbar p-4 flex-1 min-h-0">
              <img src={previewUrl} alt="当铺对话截图" className="w-full h-auto border border-[#2A2D34]" />
              <p className="text-xs text-[#616161] mt-3 font-sans leading-relaxed">
                长图含当铺名、顾客与完整对话，底部带有游戏标识，方便传播。手机可长按图片保存，或使用下方按钮。
              </p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 p-4 border-t border-[#2A2D34] font-sans shrink-0">
              <button type="button" onClick={handleDownload} className="btn-primary !h-10 col-span-2 md:col-span-1">
                <Download className="w-4 h-4 mr-1.5" />
                保存图片
              </button>
              {canCopy && (
                <button type="button" onClick={() => void handleCopy()} className="btn-secondary !h-10">
                  <Copy className="w-4 h-4 mr-1.5" />
                  复制
                </button>
              )}
              {canShare && (
                <button type="button" onClick={() => void handleShare()} className="btn-secondary !h-10">
                  <Share2 className="w-4 h-4 mr-1.5" />
                  分享
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/** 顾客内心独白碎片：口水话、无实质信息，串起来像真在想 */
const CUSTOMER_THINKING_CHAINS: Record<string, { seller: string[][]; buyer: string[][] }> = {
  强硬: {
    seller: [
      [
        '你这价……听着也不是完全瞎报……', '但我凭什么就这么让了……', '再想想……我要是松口了岂不是很亏……',
        '不行，还得绷住……', '他要是再抬价我就更被动了……', '先晾他一会儿也无妨……', '反正我不急……', '嗯……再听听他怎么说……',
      ],
      [
        '嗯……你话说得挺圆……', '可我心里这关还是过不去……', '卖便宜了回头找谁哭去……', '再拖一拖也无妨……',
        '这价……还能不能再往上谈谈……', '不能让他觉得我好说话……', '稳住……别露怯……', '下一句怎么接来着……',
      ],
    ],
    buyer: [
      [
        '行吧……你讲得也算有道理……', '可我就这预算……再多真掏不出……', '要不再磨磨……', '总不能上赶着送钱吧……',
        '这老板……看着不好惹……', '再砍砍试试……', '砍不动就算了……', '反正我不急……',
      ],
      [
        '听着是挺像那么回事……', '但我也不想当冤大头啊……', '这价……还能不能再往下聊聊……', '急什么，我又不是非买不可……',
        '兜里就这么多……', '多一分都没有……', '要不再看看别的……', '嗯……再想想……',
      ],
    ],
  },
  急切: {
    seller: [
      [
        '你这话……好像也有点道理……', '但我现在就想赶紧出手……', '拖下去夜长梦多……', '要不再让一点点？就一点点……',
        '再磨下去我怕黄了……', '差不多得了吧……', '能成交就行……', '唉……快点定了吧……',
      ],
      [
        '嗯……是这么个理……', '可我还等着用钱呢……', '再磨下去我怕黄了……', '算了算了……差不多就行了吧……',
        '再拖就耽误事了……', '要不……就这个价？……', '再想想……', '不行……还是得快点……',
      ],
    ],
    buyer: [
      [
        '好像……也不是不能考虑……', '但我兜里就这么多……', '再砍砍行不行……', '再拖我可就走了啊……',
        '这店看着还行……', '价要是合适就买……', '不合适拉倒……', '嗯……快点吧……',
      ],
      [
        '你讲得我也有点动心……', '就是手头紧……', '能不能痛快点……', '再犹豫下去店都要关门了……',
        '再砍一刀……', '砍不下来……', '算了……', '要不再看看……',
      ],
    ],
  },
  犹豫: {
    seller: [
      [
        '你刚才说的……好像也有点道理……', '可我要是真答应你……', '回家会不会越想越后悔……', '要不再想想……真的要这样吗……',
        '要不先不急着点头……', '再看看他什么反应……', '卖了会不会亏啊……', '唉……好难拿主意……',
      ],
      [
        '嗯……听着是挺像那么回事……', '但我心里还是没底……', '卖了会不会亏啊……', '要不……再等等看？',
        '对方说得……好像也有点道理……', '可我又怕后悔……', '要不再琢磨琢磨……', '这价……到底行不行啊……',
      ],
    ],
    buyer: [
      [
        '你说的……似乎有点道理……', '但我想想……真的要买吗……', '不买吧又怕错过……', '买了吧又怕买贵了……',
        '要不再逛逛……', '逛完回来还在不在……', '这价……心里还是没底……', '唉……好纠结……',
      ],
      [
        '这个价……好像还行……', '又好像不太行……', '要不再看看别家……', '唉……好难决定啊……',
        '老板人看着还行……', '货嘛……也还行……', '就是钱包在抗议……', '要不再想想……',
      ],
    ],
  },
  欺诈: {
    seller: [
      [
        '他这表情……应该没看出来吧……', '反正先稳住……', '能蒙过去就蒙过去……', '对对对……就这么圆……',
        '别慌……别慌……', '咬死这个价……', '他要是再追问……', '我就再编一句……',
      ],
      [
        '嗯……不能露怯……', '咬死这个价……', '他要是再追问……', '我就再编个理由……',
        '先拖一拖……', '装傻充愣一下……', '反正不能先露馅……', '嗯……下一句怎么说……',
      ],
    ],
    buyer: [
      [
        '这老板……看着挺好忽悠……', '再压压价……', '他要是答应了就赚了……', '不行就换一家呗……',
        '先装不想要……', '让他急一急……', '说不定还能便宜……', '反正我不急……',
      ],
      [
        '嗯……先装犹豫一下……', '让他觉得我不想买……', '说不定还能再便宜点……', '反正我不急……',
        '这表情……得绷住……', '再挑挑刺……', '能砍一点是一点……', '嗯……继续磨……',
      ],
    ],
  },
  专家: {
    seller: [
      [
        '这成色……他心里应该有数……', '我报高了怕露馅……', '报低了又亏……', '再掂量掂量怎么开口……',
        '他说的那个点……不算外行……', '我得把话圆回来……', '不能露怯……', '嗯……下一句怎么说……',
      ],
      [
        '他说的那个点……不算外行……', '我得把话圆回来……', '不能让他觉得我好糊弄……', '嗯……下一句怎么说……',
        '这价……是不是还得再抬一点……', '抬多了怕露馅……', '不抬又亏……', '再想想……',
      ],
    ],
    buyer: [
      [
        '这东西……值不值这个价……', '他有没有在唬我……', '再挑挑毛病试试……', '能砍一点是一点……',
        '细节……得再对一对……', '对上了也不代表没坑……', '要不再压压……', '嗯……继续看……',
      ],
      [
        '嗯……细节对得上……', '但总觉得还能再聊聊……', '老板表情有点虚？……', '要不再试探试探……',
        '这价……心里还是没数……', '再砍砍看……', '砍不动……', '要不再想想……',
      ],
    ],
  },
};

const CUSTOMER_THINKING_OVERFLOW: Record<string, { seller: string[]; buyer: string[] }> = {
  强硬: {
    seller: ['哼……', '不能急……', '再晾他一下……', '这价……还能不能再磨磨……', '反正我不松口……', '嗯……'],
    buyer: ['不急……', '再砍砍……', '砍不动拉倒……', '反正还有别家……', '嗯……再听听……', '不能上当……'],
  },
  急切: {
    seller: ['快点吧……', '再拖怕黄了……', '差不多得了……', '能出就行……', '唉……', '要不再让一点点……'],
    buyer: ['快点定吧……', '价合适就买……', '不合适就走……', '兜里就这些……', '嗯……', '再砍一刀试试……'],
  },
  犹豫: {
    seller: ['要不再想想……', '真的好难决定……', '怕后悔……', '要不先缓缓……', '嗯……', '对方说得……好像也有点道理……'],
    buyer: ['买吧……不买吧……', '好纠结……', '要不再逛逛……', '怕买贵了……', '怕错过……', '嗯……再想想……'],
  },
  欺诈: {
    seller: ['稳住……', '别露馅……', '嗯……', '就这么说……', '他好像没起疑……', '再编一句……'],
    buyer: ['装犹豫……', '再压压……', '嗯……', '不急……', '看他急不急……', '能省一点是一点……'],
  },
  专家: {
    seller: ['再掂量掂量……', '不能露怯……', '嗯……', '这价……', '下一句怎么说……', '得圆回来……'],
    buyer: ['再对对细节……', '有没有坑……', '嗯……', '再砍砍……', '值不值这个价……', '要不再试探……'],
  },
};

const CUSTOMER_THINKING_OVERFLOW_COMMON = {
  seller: ['嗯……', '再想想……', '好像也有点道理……', '但又说不好……', '要不再等等……', '这价……', '唉……', '怎么说呢……'],
  buyer: ['嗯……', '再想想……', '好像还行……', '又好像不太行……', '要不再看看……', '兜里就这些……', '唉……', '买还是不买……'],
};

const PAST_SELF_THINKING: string[] = [
  '这说法怎么耳熟……', '好像……我也说过类似的……', '要是按当年的口气……', '这价……',
  '嗯……', '有点意思……', '再想想……', '像在哪听过……',
];

const CUSTOMER_THINKING_FALLBACK: { seller: string[]; buyer: string[] } = {
  seller: [
    '你刚才那话……', '好像也不是完全没道理……', '但我还得再琢磨琢磨……', '真的要就这样吗……',
    '要不再想想……', '卖了会不会后悔……', '唉……', '嗯……',
  ],
  buyer: [
    '听着是挺诱人的……', '可我钱包不允许啊……', '要不再想想……', '不买又有点不甘心……',
    '这价……', '好像还行……', '又好像不太行……', '唉……',
  ],
};

const THINKING_MAX_FRAGMENTS = 16;

function thinkingChainSeed(customerId: string): number {
  let hash = 0;
  for (let i = 0; i < customerId.length; i += 1) {
    hash = (hash * 31 + customerId.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function buildCustomerThinkingSequence(customer: Customer): string[] {
  if (customer.is_past_self) {
    return PAST_SELF_THINKING;
  }
  const roleKey = customer.role === 'buyer' ? 'buyer' : 'seller';
  const traitChains = CUSTOMER_THINKING_CHAINS[customer.trait_cn]?.[roleKey];
  if (traitChains?.length) {
    const index = thinkingChainSeed(customer.customer_id) % traitChains.length;
    return traitChains[index];
  }
  return CUSTOMER_THINKING_FALLBACK[roleKey];
}

function pickThinkingOverflowFragment(customer: Customer, fragmentIndex: number): string {
  const roleKey = customer.role === 'buyer' ? 'buyer' : 'seller';
  const pool =
    CUSTOMER_THINKING_OVERFLOW[customer.trait_cn]?.[roleKey] ?? CUSTOMER_THINKING_OVERFLOW_COMMON[roleKey];
  const seed = thinkingChainSeed(customer.customer_id);
  return pool[(fragmentIndex + seed) % pool.length];
}

const THINKING_CHAR_MS = 52;
const THINKING_LINE_PAUSE_MS = 380;

function CustomerThinkingBubble({ customer }: { customer: Customer }) {
  const baseLines = useMemo(
    () => buildCustomerThinkingSequence(customer),
    [customer.trait_cn, customer.role, customer.customer_id]
  );
  const [fragments, setFragments] = useState(baseLines);
  const [sentenceIndex, setSentenceIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const currentFragment = fragments[sentenceIndex] ?? '';
  const canAppendMore = fragments.length < THINKING_MAX_FRAGMENTS;

  useEffect(() => {
    setFragments(baseLines);
    setSentenceIndex(0);
    setCharIndex(0);
  }, [customer.customer_id, baseLines]);

  useEffect(() => {
    if (!currentFragment) return undefined;

    if (charIndex < currentFragment.length) {
      const timer = window.setTimeout(() => setCharIndex((index) => index + 1), THINKING_CHAR_MS);
      return () => window.clearTimeout(timer);
    }

    const advance = () => {
      setSentenceIndex((index) => index + 1);
      setCharIndex(0);
    };

    if (sentenceIndex < fragments.length - 1) {
      const timer = window.setTimeout(advance, THINKING_LINE_PAUSE_MS);
      return () => window.clearTimeout(timer);
    }

    if (!canAppendMore) return undefined;

    const timer = window.setTimeout(() => {
      setFragments((prev) => [...prev, pickThinkingOverflowFragment(customer, prev.length)]);
      advance();
    }, THINKING_LINE_PAUSE_MS * 1.4);
    return () => window.clearTimeout(timer);
  }, [sentenceIndex, charIndex, fragments, currentFragment, canAppendMore, customer]);

  const completedText = fragments.slice(0, sentenceIndex).join('');
  const visibleText = completedText + currentFragment.slice(0, charIndex);

  return (
    <div className="flex gap-3 max-w-[86%] animate-slide-up">
      <img
        src={customer.avatar_url}
        alt={customer.name}
        className="w-10 h-10 rounded-full bg-[#14171C] border border-[#2A2D34] object-cover shrink-0 mt-5"
        referrerPolicy="no-referrer"
      />
      <div className="flex flex-col min-w-0 items-start">
        <span className="text-xs text-[#616161] mb-1 font-sans">{customer.name}</span>
        <div className="px-4 py-3 leading-relaxed rounded-sm border-l border-[#2A2D34] bg-[rgba(255,255,255,0.03)]">
          <p className="customer-thinking-text text-sm text-[#616161] italic m-0 min-h-[22px]">
            {visibleText}
            <span className="customer-thinking-cursor" aria-hidden />
          </p>
        </div>
      </div>
    </div>
  );
}

function Chat({ avatarUrl, children, right, speaker, narrator }: { avatarUrl?: string; children: React.ReactNode; right?: boolean; speaker?: string; narrator?: boolean }) {
  if (narrator) {
    return (
      <div className="max-w-[92%] mx-auto text-center animate-slide-up">
        <p className="text-sm text-[#616161] italic leading-relaxed px-4 py-2 border-y border-[#2A2D34]/60 whitespace-pre-wrap">{children}</p>
      </div>
    );
  }
  return (
    <div className={`flex gap-3 max-w-[86%] animate-slide-up ${right ? 'ml-auto flex-row-reverse' : ''}`}>
      {!right && (
        <img
          src={avatarUrl}
          alt={speaker}
          className="w-10 h-10 rounded-full bg-[#14171C] border border-[#2A2D34] object-cover shrink-0 mt-5"
          referrerPolicy="no-referrer"
        />
      )}
      <div className={`flex flex-col min-w-0 ${right ? 'items-end' : 'items-start'}`}>
        <span className="text-xs text-[#616161] mb-1">{speaker}</span>
        <div className={`px-4 py-3 leading-relaxed rounded-sm whitespace-pre-wrap ${right ? 'border-r border-[#C8A97E] text-right bg-[rgba(200,169,126,0.06)] text-[#D4B88A]' : 'border-l border-[#2A2D34] bg-[rgba(255,255,255,0.03)] text-[#E0E0E0]'}`}>{children}</div>
      </div>
    </div>
  );
}

function InventoryTab({ state, listingPrice, repairMethod, inventoryAppraiseMethod, inventoryAppraisingId, showcasePrice, onAction, onClearShowcasePrice, onList, onSetShowcasePrice, setListingPrice, setRepairMethod, setInventoryAppraiseMethod, setShowcasePrice, onAppraise }: { state: GameState; listingPrice: Record<string, number>; repairMethod: Record<string, string>; inventoryAppraiseMethod: Record<string, string>; inventoryAppraisingId: string | null; showcasePrice: Record<string, number>; setListingPrice: (value: Record<string, number>) => void; setRepairMethod: (value: Record<string, string>) => void; setInventoryAppraiseMethod: (value: Record<string, string>) => void; setShowcasePrice: (value: Record<string, number>) => void; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void>; onList: (item: Item) => Promise<void>; onSetShowcasePrice: (item: Item) => Promise<void>; onClearShowcasePrice: (item: Item) => Promise<void>; onAppraise: (itemId: string, method: string) => Promise<void> }) {
  const activeItems = state.inventory.filter((item) => item.status !== 'sold');
  const repairPreview = (item: Item) => {
    const method = state.repair_methods[repairMethod[item.id] || 'standard'] || state.repair_methods.standard;
    const nextCondition = item.condition === 'Poor' ? 'Good' : item.condition === 'Good' ? 'Mint' : item.condition;
    const multiplier = item.condition === 'Poor' ? 1.35 : item.condition === 'Good' ? 1.55 : 1;
    const baseCost = Math.max(60, Math.round(item.market_value * (0.08 + item.repair_difficulty * 0.015) * (state.economy_index || 1) * (1 - 0.05 * (state.facilities.restoration_workshop - 1) - 0.03 * (state.skills.restoration.level - 1))));
    const staffCost = state.staff.restorer ? Math.round(baseCost * 0.75) : baseCost;
    const cost = Math.max(30, Math.round(staffCost * method.cost_multiplier));
    const days = Math.max(1, item.repair_difficulty - Math.floor(state.facilities.restoration_workshop / 2) + method.days_delta);
    return { cost, days, method, nextCondition, multiplier };
  };
  const systemSellPreview = (item: Item) => {
    const commerce = state.skills.commerce?.level ?? 1;
    const showcaseBonus = item.status === 'displayed' ? 0.04 * state.facilities.showcase : 0;
    const rarityBonus = { common: 0, rare: 0.06, epic: 0.12, legendary: 0.2 }[item.rarity as 'common' | 'rare' | 'epic' | 'legendary'] ?? 0;
    const fixedBonus = commerce * 0.025 + showcaseBonus + rarityBonus;
    const minPercent = 0.72 + fixedBonus;
    const maxPercent = 0.92 + fixedBonus;
    
    let minVal = null;
    let maxVal = null;
    if (item.appraised_value_low !== null && item.appraised_value_high !== null) {
      minVal = Math.max(10, Math.floor(item.appraised_value_low * minPercent));
      maxVal = Math.max(10, Math.floor(item.appraised_value_high * maxPercent));
    } else if (item.appraised_value !== null) {
      minVal = Math.max(10, Math.floor(item.appraised_value * minPercent));
      maxVal = Math.max(10, Math.floor(item.appraised_value * maxPercent));
    }

    return {
      minPercent: Math.round(minPercent * 100),
      maxPercent: Math.round(maxPercent * 100),
      minVal,
      maxVal,
      commerce,
      showcaseBonus,
      rarityBonus,
    };
  };
  return (
    <ListPage title="仓库藏品" subtitle={`当前库存 ${activeItems.length} 件，可展示、修复、出售或挂入玩家市场。`}>
      {activeItems.map((item) => {
        const isAppraising = inventoryAppraisingId === item.id;
        return (
        <div key={item.id} className={`py-5 border-b border-[#2A2D34] flex flex-col xl:flex-row xl:items-center gap-4 transition-opacity ${isAppraising ? 'opacity-80' : ''}`}>
          <ItemText item={item} />
          <div className="w-full xl:w-[500px] flex flex-wrap gap-x-6 gap-y-4 justify-start xl:justify-end mt-4 xl:mt-0 items-end">
            {item.is_appraised_fake === null && (
              <div className="flex items-center gap-2 border-b border-[#2A2D34] pb-1">
                <select value={inventoryAppraiseMethod[item.id] || 'standard'} onChange={(event) => setInventoryAppraiseMethod({ ...inventoryAppraiseMethod, [item.id]: event.target.value })} disabled={isAppraising || inventoryAppraisingId !== null} className="bg-transparent text-[#E0E0E0] outline-none text-sm w-[90px] disabled:opacity-50">
                  {Object.entries(state.appraisal_methods).map(([key, info]) => (
                    <option key={key} value={key}>{info.name_cn}</option>
                  ))}
                </select>
                <button
                  onClick={() => onAppraise(item.id, inventoryAppraiseMethod[item.id] || 'standard')}
                  disabled={isAppraising || inventoryAppraisingId !== null}
                  className="text-[#D4B88A] hover:text-[#C8A97E] text-sm whitespace-nowrap transition-colors disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5 min-w-[4.5rem]"
                >
                  {isAppraising ? <><RefreshCw className="w-3.5 h-3.5 animate-spin" />鉴定中</> : '鉴定'}
                </button>
              </div>
            )}
            <div className="flex items-center gap-2 border-b border-[#2A2D34] pb-1">
              <select value={repairMethod[item.id] || 'standard'} onChange={(event) => setRepairMethod({ ...repairMethod, [item.id]: event.target.value })} disabled={item.condition === 'Mint' || item.status === 'repairing'} className="bg-transparent text-[#E0E0E0] outline-none text-sm w-[90px] disabled:opacity-50">
                {Object.entries(state.repair_methods).map(([key, info]) => (
                  <option key={key} value={key}>{info.name_cn}</option>
                ))}
              </select>
              <button onClick={() => onAction('/api/repair', { item_id: item.id, method: repairMethod[item.id] || 'standard' }, 'repair_result', '已送修。', 'upgrade')} disabled={item.condition === 'Mint' || item.status === 'repairing'} className="text-[#D4B88A] hover:text-[#C8A97E] text-sm whitespace-nowrap disabled:opacity-50 transition-colors">修复</button>
            </div>
            <div className="flex items-center gap-3 border-b border-[#2A2D34] pb-1">
              <div className="flex items-center gap-2">
                <input type="number" className="bg-transparent text-[#E0E0E0] outline-none text-sm w-[70px] placeholder:text-[#616161]" placeholder="橱窗价" value={showcasePrice[item.id] ?? item.showcase_price ?? item.appraised_value_low ?? item.purchase_price ?? ''} onChange={(event) => setShowcasePrice({ ...showcasePrice, [item.id]: parseInt(event.target.value) || 0 })} />
                {item.status === 'displayed' ? (
                  <>
                    <button onClick={() => onSetShowcasePrice(item)} className="text-[#D4B88A] hover:text-[#C8A97E] text-sm whitespace-nowrap transition-colors">改价</button>
                    {item.showcase_price && <button onClick={() => onClearShowcasePrice(item)} className="text-[#D4B88A] hover:text-[#C8A97E] text-sm whitespace-nowrap transition-colors">撤价</button>}
                    <button onClick={() => onAction('/api/undisplay', { item_id: item.id }, 'display_result', '已下架。')} className="text-[#9E9E9E] hover:text-[#E0E0E0] text-sm whitespace-nowrap transition-colors">下架</button>
                  </>
                ) : (
                  <button onClick={() => onAction('/api/display', { item_id: item.id }, 'display_result', '已展示。')} disabled={item.status !== 'stored'} className="text-[#D4B88A] hover:text-[#C8A97E] text-sm whitespace-nowrap disabled:opacity-50 transition-colors">展示</button>
                )}
              </div>
              <div className="w-[1px] h-4 bg-[#2A2D34]"></div>
              <div className="flex items-center gap-2">
                <input type="number" className="bg-transparent text-[#E0E0E0] outline-none text-sm w-[70px] placeholder:text-[#616161]" placeholder="挂售价" value={listingPrice[item.id] ?? item.appraised_value_low ?? item.purchase_price ?? ''} onChange={(event) => setListingPrice({ ...listingPrice, [item.id]: parseInt(event.target.value) || 0 })} />
                <button onClick={() => onList(item)} disabled={!['stored', 'displayed'].includes(item.status)} className="text-[#D4B88A] hover:text-[#C8A97E] text-sm whitespace-nowrap disabled:opacity-50 transition-colors">挂售</button>
              </div>
            </div>
            <button onClick={() => onAction('/api/sell', { item_id: item.id }, 'sell_result', '已出售。', 'cash')} disabled={item.status === 'repairing'} className="btn-primary !h-8 !px-4 ml-auto xl:ml-0 disabled:opacity-50 text-sm">系统出售</button>
            {item.status !== 'repairing' && (() => {
              const preview = systemSellPreview(item);
              const rangeText = preview.minVal !== null ? `$${preview.minVal.toLocaleString()} - $${preview.maxVal?.toLocaleString()}` : '未知（需鉴定）';
              return (
                <div className="basis-full text-right text-xs text-[#C8A97E]">
                  系统出售预计：{rangeText}（真实价值的 {preview.minPercent}%-{preview.maxPercent}%，商业 Lv.{preview.commerce}{preview.showcaseBonus > 0 ? '，展示加成' : ''}{preview.rarityBonus > 0 ? '，稀有度加成' : ''}）
                </div>
              );
            })()}
            {item.status !== 'repairing' && item.condition !== 'Mint' && <div className="basis-full text-right text-xs text-[#616161]">修复成功：{CONDITION_MAP[item.condition] || item.condition} → {CONDITION_MAP[repairPreview(item).nextCondition] || repairPreview(item).nextCondition}，真实价值提升约 {Math.round((repairPreview(item).multiplier - 1) * 100)}%，费用约 ${repairPreview(item).cost.toLocaleString()} / {repairPreview(item).days} 天</div>}
            <div className="basis-full text-right text-xs text-[#616161]">
              持有 {Math.max(0, state.day - (item.acquired_day || state.day))} 天；
              成本 ${Number(item.purchase_price || item.base_value_at_purchase || 0).toLocaleString()}；
              累计持有成本 ${Number(item.holding_cost_paid || 0).toLocaleString()}
            </div>
            {isAppraising && <div className="basis-full text-right text-xs text-[#C8A97E] animate-slide-up">正在鉴定，请稍候…</div>}
            {item.status === 'repairing' && <div className="basis-full text-right text-xs text-[#C8A97E]">修复中：还需 {item.repair_days_remaining} 天，营业结算后推进进度。</div>}
          </div>
        </div>
        );
      })}
    </ListPage>
  );
}

function offerStatusLabel(offer: MarketOffer, viewerIsBuyer: boolean): string {
  if (offer.status === 'pending_seller') return viewerIsBuyer ? '等待卖家回应' : '待你回应';
  if (offer.status === 'countered') return viewerIsBuyer ? '待你回应' : '等待买家回应';
  if (offer.status === 'accepted') return '已成交';
  if (offer.status === 'rejected') return '已拒绝';
  if (offer.status === 'expired') return '已过期';
  if (offer.status === 'cancelled') return '已撤回';
  return offer.status;
}

function isActiveOffer(status: string): boolean {
  return status === 'pending_seller' || status === 'countered';
}

function formatOfferTime(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function tradeTypeLabel(tradeType: string): string {
  if (tradeType === 'negotiated_sale') return '议价成交';
  if (tradeType === 'sale') return '市场成交';
  if (tradeType === 'showcase_sale') return '橱窗成交';
  return tradeType;
}

function MarketTab(props: {
  listings: Listing[];
  myListings: Listing[];
  trades: TradeLog[];
  offers: OfferBundle;
  hotShowcases: HotShowcaseEntry[];
  offerPrices: Record<string, number>;
  counterPrices: Record<string, number>;
  setOfferPrices: (value: Record<string, number>) => void;
  setCounterPrices: (value: Record<string, number>) => void;
  marketSearch: string;
  marketSort: string;
  marketView: MarketView;
  setMarketSearch: (value: string) => void;
  setMarketSort: (value: string) => void;
  setMarketView: (value: MarketView) => void;
  refresh: () => Promise<void>;
  buy: (id: string) => Promise<void>;
  openShowcase: (ownerId: number) => Promise<void>;
  submitOffer: (listing: Listing) => Promise<void>;
  marketOfferAction: (path: string, body: unknown, fallback: string, sound?: 'deal' | 'cash' | 'click' | 'reject') => Promise<void>;
  onMarketAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void>;
}) {
  const {
    buy,
    counterPrices,
    hotShowcases,
    listings,
    marketOfferAction,
    marketSearch,
    marketSort,
    marketView,
    myListings,
    offerPrices,
    offers,
    onMarketAction,
    openShowcase,
    refresh,
    setCounterPrices,
    setMarketSearch,
    setMarketSort,
    setMarketView,
    setOfferPrices,
    submitOffer,
    trades,
  } = props;

  const activeSentByListing = new Map(
    offers.sent.filter((offer) => isActiveOffer(offer.status)).map((offer) => [offer.listing_id, offer]),
  );
  const receivedByListing = offers.received.reduce<Record<string, MarketOffer[]>>((acc, offer) => {
    if (!isActiveOffer(offer.status)) return acc;
    acc[offer.listing_id] = [...(acc[offer.listing_id] || []), offer];
    return acc;
  }, {});

  const marketViews: Array<{ key: MarketView; label: string }> = [
    { key: 'browse', label: '全服市场' },
    { key: 'mine', label: '我的摊位' },
    { key: 'offers', label: '我的议价' },
    { key: 'hot', label: '热门橱窗' },
    { key: 'trades', label: '交易记录' },
  ];

  const renderOfferActions = (offer: MarketOffer, role: 'buyer' | 'seller') => {
    if (!isActiveOffer(offer.status)) {
      return <span className="text-xs text-[#616161]">{offerStatusLabel(offer, role === 'buyer')}</span>;
    }
    if (role === 'seller' && offer.status === 'pending_seller') {
      return (
        <div className="flex flex-wrap gap-2 justify-end">
          <button onClick={() => marketOfferAction('/api/market/offer/respond', { offer_id: offer.id, action: 'accept' }, '已接受出价。', 'cash')} className="btn-primary !h-8 !px-3 !text-xs">接受</button>
          <input type="number" value={counterPrices[offer.id] ?? offer.buyer_offer} onChange={(event) => setCounterPrices({ ...counterPrices, [offer.id]: parseInt(event.target.value) || 0 })} className="input-field !h-8 !w-24 !px-2" />
          <button onClick={() => marketOfferAction('/api/market/offer/respond', { offer_id: offer.id, action: 'counter', counter_price: counterPrices[offer.id] ?? offer.buyer_offer }, '已发送反价。')} className="btn-secondary !h-8 !px-3 !text-xs">反价</button>
          <button onClick={() => marketOfferAction('/api/market/offer/respond', { offer_id: offer.id, action: 'reject' }, '已拒绝。', 'reject')} className="btn-secondary !h-8 !px-3 !text-xs">拒绝</button>
        </div>
      );
    }
    if (role === 'buyer' && offer.status === 'countered' && offer.seller_counter) {
      return (
        <div className="flex flex-wrap gap-2 justify-end">
          <button onClick={() => marketOfferAction('/api/market/offer/buyer_respond', { offer_id: offer.id, action: 'accept' }, '议价成交。', 'cash')} className="btn-primary !h-8 !px-3 !text-xs">接受 ${offer.seller_counter.toLocaleString()}</button>
          <input type="number" value={offerPrices[offer.id] ?? offer.seller_counter} onChange={(event) => setOfferPrices({ ...offerPrices, [offer.id]: parseInt(event.target.value) || 0 })} className="input-field !h-8 !w-24 !px-2" />
          <button onClick={() => marketOfferAction('/api/market/offer/buyer_respond', { offer_id: offer.id, action: 'counter', price: offerPrices[offer.id] ?? offer.seller_counter }, '已更新出价。')} className="btn-secondary !h-8 !px-3 !text-xs">再出价</button>
          <button onClick={() => marketOfferAction('/api/market/offer/buyer_respond', { offer_id: offer.id, action: 'cancel' }, '已撤回。', 'reject')} className="btn-secondary !h-8 !px-3 !text-xs">撤回</button>
        </div>
      );
    }
    if (role === 'buyer' && offer.status === 'pending_seller') {
      return (
        <button onClick={() => marketOfferAction('/api/market/offer/buyer_respond', { offer_id: offer.id, action: 'cancel' }, '已撤回。', 'reject')} className="btn-secondary !h-8 !px-3 !text-xs">撤回</button>
      );
    }
    return <span className="text-xs text-[#616161]">{offerStatusLabel(offer, role === 'buyer')}</span>;
  };

  return (
    <ListPage title="玩家交易市场" subtitle="全服玩家互买互卖；支持一口价购买与结构化议价，热门橱窗按近 7 天点赞排序。">
      <div className="sticky top-0 bg-[#0D0F12]/95 backdrop-blur z-10 pb-4 border-b border-[#2A2D34] mb-2">
        <div className="flex flex-col lg:flex-row gap-3 lg:items-center">
          <div className="flex gap-4 sm:gap-6 border-b border-[#2A2D34] lg:border-b-0 overflow-x-auto custom-scrollbar pb-1">
            {marketViews.map((view) => (
              <button key={view.key} onClick={() => setMarketView(view.key)} className={`pb-2 whitespace-nowrap ${marketView === view.key ? 'text-[#C8A97E] border-b border-[#C8A97E]' : 'text-[#616161]'}`}>
                {view.label}
                {view.key === 'offers' && offers.received.filter((offer) => offer.status === 'pending_seller').length > 0 ? (
                  <span className="ml-2 text-[10px] text-[#C8A97E]">待处理 {offers.received.filter((offer) => offer.status === 'pending_seller').length}</span>
                ) : null}
              </button>
            ))}
          </div>
          {marketView === 'browse' || marketView === 'mine' ? (
            <div className="flex flex-wrap sm:flex-nowrap gap-2 flex-1 mt-1 lg:mt-0">
              <div className="relative w-full sm:flex-1"><Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#616161]" /><input value={marketSearch} onChange={(event) => setMarketSearch(event.target.value)} className="input-field w-full" placeholder="搜索物品..." /></div>
              <div className="flex gap-2 w-full sm:w-auto">
                <select value={marketSort} onChange={(event) => setMarketSort(event.target.value)} className="input-field flex-1 sm:flex-none !px-3"><option value="newest">最新</option><option value="price_asc">低价</option><option value="price_desc">高价</option></select>
                <button onClick={() => refresh()} className="btn-secondary !px-4 flex-1 sm:flex-none">刷新</button>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex justify-end mt-1 lg:mt-0">
              <button onClick={() => refresh()} className="btn-secondary !px-4">刷新</button>
            </div>
          )}
        </div>
      </div>

      {marketView === 'trades' && trades.map((trade) => (
        <div key={trade.id} className="py-4 border-b border-[#2A2D34] flex flex-col sm:flex-row sm:justify-between gap-2">
          <span>【{trade.item_name}】<span className="ml-2 text-xs text-[#616161]">{tradeTypeLabel(trade.trade_type)}</span></span>
          <span className="text-[#9E9E9E]">{trade.buyer_shop || '买家'} ↔ {trade.seller_shop || '卖家'}</span>
          <span className="text-[#C8A97E]">${trade.price.toLocaleString()} / 税 ${trade.tax}</span>
        </div>
      ))}

      {marketView === 'hot' && (
        hotShowcases.length === 0 ? (
          <div className="py-16 text-center text-[#616161]">暂无热门橱窗。参观他人橱窗并点赞，即可登上热门榜。</div>
        ) : hotShowcases.map((entry) => (
          <div key={entry.player_id} className="py-5 border-b border-[#2A2D34] flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex items-center gap-4 min-w-[120px]">
              <span className="text-2xl font-bold text-[#C8A97E]">#{entry.rank}</span>
              <div>
                <div className="font-bold">
                  {entry.ranking_badge ? <span className="text-[#9E9E9E] font-normal text-xs">{entry.ranking_badge} · </span> : null}
                  <ShopNameLine name={entry.shop_name} cosmetics={entry} />
                </div>
                <div className="text-xs text-[#616161] mt-1">近7天 {entry.recent_likes} 赞 · 累计 {entry.total_likes} 赞 · 展示 {entry.displayed_count}/{entry.display_capacity}</div>
              </div>
            </div>
            <div className="flex-1 text-sm text-[#9E9E9E]">{entry.online ? '在线' : '离线'}</div>
            <button onClick={() => openShowcase(entry.player_id)} className="btn-secondary !h-9 !px-4 shrink-0">参观橱窗</button>
          </div>
        ))
      )}

      {marketView === 'offers' && (
        <>
          <div className="py-4 border-b border-[#2A2D34]">
            <h3 className="text-[#C8A97E] font-bold mb-3">我发起的议价</h3>
            {offers.sent.length === 0 ? <div className="text-sm text-[#616161]">还没有发起过议价。</div> : offers.sent.map((offer) => (
              <div key={offer.id} className="py-4 border-t border-[#2A2D34] flex flex-col xl:flex-row xl:items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="font-bold">【{offer.item_name}】</div>
                  <div className="text-xs text-[#9E9E9E] mt-1">卖家 {offer.seller_shop} · 标价 ${offer.listing_price.toLocaleString()} · 出价 ${offer.buyer_offer.toLocaleString()}{offer.seller_counter ? ` · 反价 $${offer.seller_counter.toLocaleString()}` : ''}</div>
                  <div className="text-xs text-[#616161] mt-1">第 {offer.round} 轮 · {offerStatusLabel(offer, true)} · 截止 {formatOfferTime(offer.expires_at)}</div>
                </div>
                {renderOfferActions(offer, 'buyer')}
              </div>
            ))}
          </div>
          <div className="py-4">
            <h3 className="text-[#C8A97E] font-bold mb-3">收到的议价</h3>
            {offers.received.length === 0 ? <div className="text-sm text-[#616161]">还没有收到议价。</div> : offers.received.map((offer) => (
              <div key={offer.id} className="py-4 border-t border-[#2A2D34] flex flex-col xl:flex-row xl:items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="font-bold">【{offer.item_name}】</div>
                  <div className="text-xs text-[#9E9E9E] mt-1">买家 {offer.buyer_shop} · 出价 ${offer.buyer_offer.toLocaleString()}{offer.seller_counter ? ` · 反价 $${offer.seller_counter.toLocaleString()}` : ''}</div>
                  <div className="text-xs text-[#616161] mt-1">第 {offer.round} 轮 · {offerStatusLabel(offer, false)} · 截止 {formatOfferTime(offer.expires_at)}</div>
                </div>
                {renderOfferActions(offer, 'seller')}
              </div>
            ))}
          </div>
        </>
      )}

      {(marketView === 'browse' || marketView === 'mine') && (marketView === 'browse' ? listings : myListings).map((listing) => {
        const myOffer = activeSentByListing.get(listing.id);
        const incoming = receivedByListing[listing.id] || [];
        return (
          <div key={listing.id} className="py-5 border-b border-[#2A2D34]">
            <div className="flex flex-col xl:flex-row xl:items-center gap-4">
              <ItemText item={listing.item} extra={listing.seller_online ? '卖家在线' : '卖家离线'} />
              <div className="w-full xl:w-[360px] flex flex-col gap-3 mt-2 xl:mt-0">
                <div className="flex items-center justify-between gap-4">
                  <button onClick={() => openShowcase(listing.seller_id)} className="text-[#9E9E9E] hover:text-[#C8A97E] text-sm text-left">{listing.seller_shop}<span className="block text-xs text-[#616161]">进店看橱窗</span></button>
                  <div className="text-right">
                    <div className="text-[#C8A97E] text-lg font-bold">${listing.price.toLocaleString()}</div>
                    {appraisalRange(listing.item) ? <div className="text-xs text-[#616161]">鉴定区间 {appraisalRange(listing.item)}</div> : <div className="text-xs text-[#616161]">未知（需鉴定）</div>}
                  </div>
                </div>
                {marketView === 'browse' ? (
                  <div className="flex flex-wrap items-center gap-2 justify-end">
                    <input type="number" value={offerPrices[listing.id] ?? Math.max(1, Math.floor(listing.price * 0.85))} onChange={(event) => setOfferPrices({ ...offerPrices, [listing.id]: parseInt(event.target.value) || 0 })} className="input-field !h-9 !w-28 !px-2" placeholder="出价" />
                    <button onClick={() => submitOffer(listing)} className="btn-secondary !h-9 !px-3">议价</button>
                    <button onClick={() => buy(listing.id)} className="btn-primary !h-9 !px-4">购买</button>
                    {myOffer ? <span className="text-xs text-[#C8A97E]">{offerStatusLabel(myOffer, true)}</span> : null}
                  </div>
                ) : (
                  <div className="flex justify-end">
                    <button onClick={() => onMarketAction('/api/market/unlist', { listing_id: listing.id }, 'market_result', '已下架。').then(refresh)} className="btn-secondary !h-9 !px-4">下架</button>
                  </div>
                )}
              </div>
            </div>
            {marketView === 'mine' && incoming.length > 0 && (
              <div className="mt-4 pl-3 border-l border-[#C8A97E]/40 space-y-3">
                {incoming.map((offer) => (
                  <div key={offer.id} className="flex flex-col lg:flex-row lg:items-center gap-3">
                    <div className="flex-1 text-sm text-[#9E9E9E]">
                      买家 {offer.buyer_shop} 出价 ${offer.buyer_offer.toLocaleString()}
                      {offer.seller_counter ? ` · 你的反价 $${offer.seller_counter.toLocaleString()}` : ''}
                      <span className="block text-xs text-[#616161] mt-1">第 {offer.round} 轮 · 截止 {formatOfferTime(offer.expires_at)}</span>
                    </div>
                    {renderOfferActions(offer, 'seller')}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </ListPage>
  );
}

function leaderboardScore(entry: LeaderboardEntry, boardType: BoardType): number {
  if (boardType === 'reputation') return entry.reputation;
  if (boardType === 'profit') return entry.profit;
  if (boardType === 'collection') return entry.collection;
  return entry.assets;
}

function LeaderboardTab({ boardType, data, openMarketHot, openShowcase, refresh, setBoardType }: { boardType: BoardType; setBoardType: (value: BoardType) => void; data: { entries: LeaderboardEntry[]; my_rank: LeaderboardEntry | null } | null; refresh: () => Promise<void>; openShowcase: (ownerId: number) => Promise<void>; openMarketHot: () => void }) {
  const scoreLabel = BOARD_LABEL[boardType];
  return (
    <ListPage title="全服排行榜" subtitle="10 秒自动刷新；点击当铺名或「参观橱窗」可浏览他人展示柜与在售藏品。前 100 名获每日声誉与稀有刷新奖励。">
      <div className="py-3 border-b border-[#2A2D34] mb-2 flex justify-between items-center gap-3">
        <button type="button" onClick={openMarketHot} className="text-sm text-[#9E9E9E] hover:text-[#C8A97E] inline-flex items-center gap-2">
          查看热门橱窗榜
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
      <div className="sticky top-0 bg-[#0D0F12]/95 backdrop-blur z-10 border-b border-[#2A2D34] mb-2 flex justify-between gap-4">
        <div className="flex gap-4 sm:gap-8 overflow-x-auto custom-scrollbar pb-1">
          {(Object.keys(BOARD_LABEL) as BoardType[]).map((type) => <button key={type} onClick={() => setBoardType(type)} className={`pb-2 whitespace-nowrap ${boardType === type ? 'text-[#C8A97E] border-b border-[#C8A97E]' : 'text-[#616161]'}`}>{BOARD_LABEL[type]}</button>)}
        </div>
        <button onClick={() => refresh()} className="text-[#9E9E9E] hover:text-[#C8A97E] shrink-0" aria-label="刷新排行榜"><RefreshCw className="w-4 h-4" /></button>
      </div>
      <div className="overflow-x-auto custom-scrollbar pb-4">
        <div className="min-w-[600px]">
          <div className="grid grid-cols-[52px_minmax(0,1fr)_108px_80px_64px_104px] gap-3 sm:gap-4 items-center pb-2 text-xs text-[#616161] font-sans border-b border-[#2A2D34]">
            <span>排名</span>
            <span>当铺</span>
            <span>{scoreLabel}</span>
            <span>声誉</span>
            <span>状态</span>
            <span className="text-right">操作</span>
          </div>
          {(data?.entries || []).map((entry) => (
            <div
              key={entry.player_id}
              className={`py-4 border-b border-[#2A2D34] grid grid-cols-[52px_minmax(0,1fr)_108px_80px_64px_104px] gap-3 sm:gap-4 items-center transition-colors hover:bg-[rgba(255,255,255,0.02)] ${entry.rank <= 3 ? 'text-[#C8A97E]' : ''}`}
            >
              <span className="text-xl font-bold">#{entry.rank}</span>
              <div className="min-w-0 pr-2">
                <button
                  type="button"
                  onClick={() => openShowcase(entry.player_id)}
                  className="truncate w-full text-left text-[#E0E0E0] hover:text-[#C8A97E] underline decoration-[#2A2D34] underline-offset-4 hover:decoration-[#C8A97E]"
                >
                  {entry.badge ? <span className="text-[#9E9E9E]">{entry.badge} · </span> : null}
                  <ShopNameLine name={entry.shop_name} cosmetics={entry} />
                </button>
                <span className="mt-1 block text-[11px] text-[#616161] truncate">{entry.username}</span>
              </div>
              <span className="font-sans tabular-nums">${leaderboardScore(entry, boardType).toLocaleString()}</span>
              <span className="text-sm text-[#9E9E9E]">声誉 {entry.reputation}</span>
              <span className={`text-sm ${entry.online ? 'text-[#4CAF50]' : 'text-[#616161]'}`}>{entry.online ? '在线' : '离线'}</span>
              <button
                type="button"
                onClick={() => openShowcase(entry.player_id)}
                className="btn-secondary !h-8 !px-3 !text-xs inline-flex items-center justify-center gap-1.5 justify-self-end whitespace-nowrap"
              >
                <Store className="w-3.5 h-3.5 shrink-0" />
                参观橱窗
              </button>
            </div>
          ))}
        </div>
      </div>
      {data?.my_rank && (
        <div className="sticky bottom-0 mt-8 py-4 bg-[#0D0F12]/95 backdrop-blur border-t border-[#C8A97E] flex flex-wrap justify-between gap-3 text-[#C8A97E] font-sans">
          <span>我的排名 #{data.my_rank.rank}</span>
          <span>{data.my_rank.shop_name}<span className="block text-xs text-[#9E9E9E] font-normal">{data.my_rank.username}</span></span>
          <span>{scoreLabel} {leaderboardScore(data.my_rank, boardType).toLocaleString()}</span>
        </div>
      )}
    </ListPage>
  );
}

function HistoryTab({ entries }: { entries: TransactionEntry[] }) {
  const normalizeAmount = (entry: TransactionEntry) => {
    const expenseTypes = new Set(['buy', 'market_buy', 'showcase_buy', 'appraisal_fee', 'event_buy']);
    if (expenseTypes.has(entry.type)) return -Math.abs(entry.amount);
    return entry.amount;
  };
  const shown = [...entries].reverse();
  const typeLabel: Record<string, string> = {
    buy: '收购物品',
    sell: '顾客购买',
    direct_sell: '系统出售',
    appraisal_fee: '鉴定费用',
    event_buy: '事件收购',
    market_buy: '市场购入',
    market_sell: '市场售出',
    showcase_buy: '橱窗购入',
    showcase_sell: '橱窗售出'
  };
  const normalizedEntries = entries.map((entry) => ({ ...entry, amount: normalizeAmount(entry) }));
  const totalIn = normalizedEntries.filter((entry) => entry.amount > 0).reduce((sum, entry) => sum + entry.amount, 0);
  const totalOut = normalizedEntries.filter((entry) => entry.amount < 0).reduce((sum, entry) => sum + Math.abs(entry.amount), 0);
  return (
    <ListPage title="过往交易记录" subtitle={`保留最近 ${entries.length} 条经营流水，方便复盘收购、出售、市场和橱窗交易。`}>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-4 border-b border-[#2A2D34] pb-5 mb-2 text-sm">
        <Stat label="交易数" value={entries.length} />
        <Stat label="总流入" value={`$${totalIn.toLocaleString()}`} />
        <Stat label="总流出" value={`$${totalOut.toLocaleString()}`} />
      </div>
      {shown.length === 0 ? (
        <div className="py-16 text-center text-[#616161]">还没有交易记录。完成收购或出售后，这里会留下流水。</div>
      ) : (
        shown.map((entry, index) => {
          const amount = normalizeAmount(entry);
          return <div key={`${entry.day}-${entry.type}-${entry.item}-${index}`} className="py-4 border-b border-[#2A2D34] grid grid-cols-[60px_1fr_80px] sm:grid-cols-[72px_1fr_110px] gap-2 sm:gap-4 items-center">
            <span className="text-[#616161] text-xs sm:text-sm">第 {entry.day} 天</span>
            <div className="min-w-0">
              <div className="font-bold text-sm sm:text-base truncate">【{entry.item}】</div>
              <div className="text-xs text-[#9E9E9E]">{typeLabel[entry.type] || entry.type}</div>
            </div>
            <span className={`text-right font-sans font-bold text-sm sm:text-base ${amount >= 0 ? 'text-[#4CAF50]' : 'text-[#F44336]'}`}>
              {amount >= 0 ? '+' : '-'}${Math.abs(amount).toLocaleString()}
            </span>
          </div>;
        })
      )}
    </ListPage>
  );
}

function AchievementsTab({ achievements, unlocks }: { achievements: Achievement[]; unlocks: AchievementUnlock[] }) {
  const unlockedCount = achievements.filter((achievement) => achievement.unlocked).length;
  const categories = Array.from(new Set(achievements.map((achievement) => achievement.category)));
  const rewardText = (reward: Record<string, unknown>) => {
    const parts: string[] = [];
    if (typeof reward.cash === 'number') parts.push(`现金 $${reward.cash.toLocaleString()}`);
    if (typeof reward.reputation === 'number') parts.push(`声誉 +${reward.reputation}`);
    if (reward.skill_xp && typeof reward.skill_xp === 'object') parts.push('技能经验');
    return parts.join(' / ') || '纪念解锁';
  };
  return (
    <ListPage title="经营成就" subtitle={`已解锁 ${unlockedCount}/${achievements.length} 项。`}>
      {unlocks.length > 0 && (
        <div className="border-b border-[#2A2D34] pb-5 mb-2">
          <div className="text-[#C8A97E] font-bold mb-3">最近解锁</div>
          <div className="space-y-2 text-sm text-[#9E9E9E]">
            {unlocks.slice(-5).reverse().map((unlock) => <p key={`${unlock.id}-${unlock.day}`}>第 {unlock.day} 天 · {unlock.category} · {unlock.name}</p>)}
          </div>
        </div>
      )}
      {categories.map((category) => (
        <div key={category} className="py-5 border-b border-[#2A2D34]">
          <h2 className="text-[#C8A97E] font-bold mb-3">{category}</h2>
          {achievements.filter((achievement) => achievement.category === category).map((achievement) => {
            const percent = Math.min(100, Math.round((achievement.progress / Math.max(1, achievement.target)) * 100));
            const isSecretEgg = Boolean(achievement.hidden) && !achievement.unlocked;
            return (
              <div key={achievement.id} className={`py-3 border-t border-[#2A2D34] ${achievement.unlocked ? 'text-[#E0E0E0]' : 'text-[#9E9E9E]'}`}>
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <div className="font-bold">
                      {achievement.name}
                      {achievement.hidden && achievement.unlocked && (
                        <span className="text-[#C8A97E] text-xs ml-2 tracking-wide">彩蛋</span>
                      )}
                      {achievement.unlocked && <span className="text-[#C8A97E] text-xs ml-2">已解锁</span>}
                      {isSecretEgg && <span className="text-[#616161] text-xs ml-2">未揭示</span>}
                    </div>
                    <p className={`text-xs mt-1 ${isSecretEgg ? 'text-[#616161] italic' : 'text-[#9E9E9E]'}`}>{achievement.desc}</p>
                  </div>
                  <div className="text-xs text-[#616161] sm:text-right shrink-0">
                    <div>{achievement.progress.toLocaleString()} / {achievement.target.toLocaleString()}</div>
                    <div>{rewardText(achievement.reward)}</div>
                  </div>
                </div>
                <div className="progress-bg mt-3"><div className="progress-fill" style={{ width: `${percent}%` }} /></div>
              </div>
            );
          })}
        </div>
      ))}
    </ListPage>
  );
}

function CodexTab({ customers, items }: { customers: Record<string, CustomerCodexEntry>; items: Record<string, ItemCodexEntry> }) {
  const [view, setView] = useState<'customers' | 'items'>('customers');
  const customerList = Object.values(customers).sort((a, b) => b.last_seen_day - a.last_seen_day || b.times_seen - a.times_seen);
  const itemList = Object.values(items).sort((a, b) => b.last_seen_day - a.last_seen_day || (b.purchase_price || 0) - (a.purchase_price || 0));
  const sourceText = (sources: string[] = []) => sources.slice(-3).map((source) => {
    if (source.startsWith('customer:')) return `顾客携带：${source.replace('customer:', '')}`;
    return {
      daily_queue: '当日到访',
      served: '柜台接待',
      retarget: '转看藏品',
      appraisal: '鉴定记录',
      acquired: '收购入库',
      customer_sale: '顾客购走',
      direct_sell: '渠道出售',
      display: '展示柜',
      storage: '仓库存放',
      repair_started: '送修',
      repair_completed: '修复完成',
      value_tick: '价值结算',
      market_buy: '市场购入',
      market_sell: '市场售出',
      market_list: '市场挂售',
      market_unlist: '市场下架',
      showcase_buy: '橱窗购入',
      showcase_sell: '橱窗售出',
    }[source] || source;
  }).join(' / ');
  return (
    <ListPage title="经营图鉴" subtitle={`记录所有遇到过的顾客和物品：顾客 ${customerList.length} 位，物品 ${itemList.length} 件。`}>
      <div className="sticky top-0 bg-[#0D0F12]/95 backdrop-blur z-10 border-b border-[#2A2D34] mb-2 flex gap-8 pb-2">
        <button onClick={() => setView('customers')} className={`pb-2 ${view === 'customers' ? 'text-[#C8A97E] border-b border-[#C8A97E]' : 'text-[#616161]'}`}>顾客图鉴</button>
        <button onClick={() => setView('items')} className={`pb-2 ${view === 'items' ? 'text-[#C8A97E] border-b border-[#C8A97E]' : 'text-[#616161]'}`}>物品图鉴</button>
      </div>
      {view === 'customers' ? (
        customerList.length === 0 ? (
          <div className="py-16 text-center text-[#616161]">还没有顾客记录。开门接待后，图鉴会自动补全。</div>
        ) : customerList.map((customer) => (
          <div key={customer.customer_id} className="py-5 border-b border-[#2A2D34] flex gap-4">
            <img src={customer.avatar_url} alt={customer.name} className="w-12 h-12 rounded-full bg-[#14171C] border border-[#2A2D34] object-cover shrink-0" referrerPolicy="no-referrer" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h3 className="text-lg font-bold text-[#E0E0E0]">{customer.name}</h3>
                <span className="text-sm text-[#C8A97E]">{customer.relationship_cn || '新客'}</span>
                <span className="text-xs text-[#616161]">第 {customer.first_seen_day} 天初遇 / 最近第 {customer.last_seen_day} 天</span>
              </div>
              <p className="text-sm text-[#9E9E9E] mt-1">{customer.trait_cn} · {customer.role === 'seller' ? '卖家' : '买家'} · {customer.appearance}</p>
              <p className="text-sm text-[#9E9E9E] mt-2 line-clamp-2">{customer.backstory}</p>
              <div className="ui-text flex flex-wrap gap-x-5 gap-y-1 text-xs text-[#616161] mt-2">
                <span>到访：{customer.visit_count} 次</span>
                <span>记录：{customer.times_seen} 次</span>
                <span>满意度：{customer.satisfaction}</span>
                {customer.last_item_name && <span>最近物品：{customer.last_item_name}</span>}
                {customer.last_deal_summary && <span>上次往来：{customer.last_deal_summary}</span>}
                {sourceText(customer.sources) && <span>来源：{sourceText(customer.sources)}</span>}
              </div>
            </div>
          </div>
        ))
      ) : (
        itemList.length === 0 ? (
          <div className="py-16 text-center text-[#616161]">还没有物品记录。顾客带来的物品、库存和交易品都会进入这里。</div>
        ) : itemList.map((item) => (
          <div key={item.id} className="py-5 border-b border-[#2A2D34]">
            <div className="flex flex-col xl:flex-row xl:items-start gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <h3 className="text-lg font-bold text-[#E0E0E0]">{item.name}</h3>
                  <span className={RARITY_COLOR[item.rarity] || 'text-[#9E9E9E]'}>{item.rarity_cn}</span>
                  <span className="text-xs text-[#616161]">第 {item.first_seen_day} 天初见 / 最近第 {item.last_seen_day} 天</span>
                </div>
                <p className="text-sm text-[#9E9E9E] mt-2 line-clamp-2">{item.story || item.description}</p>
                <div className="ui-text flex flex-wrap gap-x-5 gap-y-1 text-xs text-[#616161] mt-2">
                  <span>类别：{categoryLabel(item.category)}</span>
                  <span>年代：{item.era}</span>
                  <span>成色：{CONDITION_MAP[item.condition] || item.condition}</span>
                  <span>状态：{STATUS_MAP[item.status] || item.status}</span>
                  <span>记录：{item.times_seen} 次</span>
                  {item.owned && <span className="text-[#C8A97E]">当前持有</span>}
                  {item.sold && <span>已售出</span>}
                  {item.appraisal_verdict && <span>鉴定：{item.appraisal_verdict}{item.appraisal_confidence ? ` / ${item.appraisal_confidence}%` : ''}</span>}
                  {sourceText(item.sources) && <span>来源：{sourceText(item.sources)}</span>}
                </div>
              </div>
              <div className="xl:w-[220px] text-xs text-[#9E9E9E] space-y-1">
                {item.purchase_price !== null && <div>买入：${item.purchase_price.toLocaleString()}</div>}
                {item.selling_price !== null && <div>卖出：${item.selling_price.toLocaleString()}</div>}
                {item.value_trend_note && <div>{item.value_trend_note}</div>}
                {item.special_effects?.slice(0, 2).map((effect, index) => <div key={`effect-${item.id}-${index}`}>亮点：{effect}</div>)}
                {item.authentication_tips?.slice(0, 2).map((tip, index) => <div key={`tip-${item.id}-${index}`}>鉴别：{tip}</div>)}
              </div>
            </div>
          </div>
        ))
      )}
    </ListPage>
  );
}

function ShowcaseTab({ back, buy, onDeleteGuestbook, onLike, onPostGuestbook, showcase }: {
  showcase: ShowcaseData;
  buy: (ownerId: number, itemId: string) => Promise<void>;
  back: () => void;
  onLike: (ownerId: number) => Promise<void>;
  onPostGuestbook: (ownerId: number, content: string) => Promise<void>;
  onDeleteGuestbook: (messageId: number) => Promise<void>;
}) {
  const [guestbookDraft, setGuestbookDraft] = useState('');

  const submitGuestbook = async () => {
    const content = guestbookDraft.trim();
    if (!content) return;
    await onPostGuestbook(showcase.owner.id, content);
    setGuestbookDraft('');
  };

  return (
    <ListPage title={`${showcase.owner.shop_name} 的当铺橱窗`} subtitle={`展示 ${showcase.items.length}/${showcase.display_capacity} 件藏品。可点赞、留言，高赞橱窗会登上热门榜。`}>
      <div className="mb-4 text-xl font-bold font-sans">
        <ShopNameLine name={showcase.owner.shop_name} cosmetics={showcase.owner} />
      </div>
      <ShowcaseCover tagline={showcase.owner.showcase_tagline} />
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[#2A2D34] pb-4 mb-2">
        <div className="text-sm text-[#9E9E9E]">
          <span className={showcase.owner.online ? 'text-[#4CAF50]' : 'text-[#616161]'}>{showcase.owner.online ? '在线' : '离线'}</span>
          <span className="mx-3">声誉 {showcase.owner.reputation}</span>
          {showcase.owner.ranking_badge && <span className="text-[#C8A97E]">{showcase.owner.ranking_badge}</span>}
          {showcase.owner.sponsor_title && <span className="ml-3 text-[#C8A97E]">{showcase.owner.sponsor_title}</span>}
          {showcase.hot_rank ? <span className="ml-3 text-[#C8A97E]">热门榜 #{showcase.hot_rank}</span> : null}
        </div>
        <div className="flex items-center gap-3">
          {!showcase.owner.is_self ? (
            <button onClick={() => onLike(showcase.owner.id)} className={`inline-flex items-center gap-2 text-sm ${showcase.liked_by_me ? 'text-[#C8A97E]' : 'text-[#9E9E9E] hover:text-[#C8A97E]'}`}>
              <Heart className={`w-4 h-4 ${showcase.liked_by_me ? 'fill-[#C8A97E]' : ''}`} />
              {showcase.like_count} 赞
              <span className="text-xs text-[#616161]">近7天 {showcase.recent_like_count}</span>
            </button>
          ) : (
            <span className="text-sm text-[#9E9E9E] inline-flex items-center gap-2"><Heart className="w-4 h-4 text-[#C8A97E]" />{showcase.like_count} 赞 · 近7天 {showcase.recent_like_count}</span>
          )}
          <button onClick={back} className="btn-secondary !h-9 !px-4">返回市场</button>
        </div>
      </div>

      <div className="py-5 border-b border-[#2A2D34] mb-2">
        <h3 className="text-[#C8A97E] font-bold mb-3">访客留言</h3>
        {showcase.guestbook.length === 0 ? (
          <div className="text-sm text-[#616161] mb-4">还没有留言，做第一个参观者吧。</div>
        ) : (
          <div className="space-y-3 mb-4 max-h-[240px] overflow-y-auto custom-scrollbar">
            {showcase.guestbook.map((entry) => (
              <div key={entry.id} className="py-3 border-t border-[#2A2D34] flex gap-3">
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-[#E0E0E0]">{entry.content}</div>
                  <div className="text-xs text-[#616161] mt-1">{entry.author_shop} · {formatOfferTime(entry.created_at)}</div>
                </div>
                {showcase.owner.is_self && (
                  <button onClick={() => onDeleteGuestbook(entry.id)} className="text-xs text-[#616161] hover:text-[#F44336] shrink-0">删除</button>
                )}
              </div>
            ))}
          </div>
        )}
        {!showcase.owner.is_self && (
          <div className="flex flex-col sm:flex-row gap-2">
            <input value={guestbookDraft} onChange={(event) => setGuestbookDraft(event.target.value)} maxLength={200} className="input-field flex-1" placeholder="写下参观感受（最多 200 字）..." />
            <button onClick={() => submitGuestbook()} className="btn-primary !h-10 !px-4 shrink-0">发送留言</button>
          </div>
        )}
      </div>

      {showcase.items.length === 0 ? (
        <div className="py-16 text-center text-[#616161]">这家当铺暂时没有公开展示的藏品。</div>
      ) : (
        showcase.items.map((item) => (
          <div key={item.id} className="py-5 border-b border-[#2A2D34] flex flex-col xl:flex-row xl:items-center gap-4">
            <ItemText item={item} extra={item.showcase_price ? '可购买' : '仅展示'} />
            <div className="w-full xl:w-[260px] flex items-center justify-between xl:justify-end gap-5 mt-2 xl:mt-0">
              <div className="text-left xl:text-right">
                <div className="text-[#C8A97E] text-lg font-bold">{item.showcase_price ? `$${item.showcase_price.toLocaleString()}` : '非卖品'}</div>
                {appraisalRange(item) && <div className="text-xs text-[#616161]">鉴定区间 {appraisalRange(item)}</div>}
              </div>
              {!showcase.owner.is_self && item.showcase_price && <button onClick={() => buy(showcase.owner.id, item.id)} className="btn-primary !h-9 !px-4 shrink-0">购买</button>}
            </div>
          </div>
        ))
      )}
    </ListPage>
  );
}

function ManagementTab({ loanAmount, onAction, setLoanAmount, state }: { state: GameState; loanAmount: number; setLoanAmount: (value: number) => void; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  const dynamicInterestRate = state.loan.interest_rate + Math.max(0, state.inflation_rate || 0) * 0.5;
  const dailyInterest = state.loan.principal > 0 ? Math.max(1, Math.round(state.loan.principal * dynamicInterestRate)) : 0;
  const pressureLabel = state.economic_pressure === 'inflation' ? '通胀压力' : state.economic_pressure === 'deflation' ? '通缩压力' : '平稳';
  const salaryEstimate = Object.entries(state.staff).reduce((sum, [key, active]) => sum + (active ? Math.round((state.staff_info[key]?.daily_salary || 0) * (state.economy_index || 1)) : 0), 0);
  const operatingEstimate = Math.round((260 + state.shop_level * 90 + Object.values(state.facilities).reduce((sum, value) => sum + value, 0) * 18) * (state.economy_index || 1));
  return (
    <ListPage title="经营财务" subtitle="技能、贷款、税务和市场趋势共同影响长期竞争。">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 border-b border-[#2A2D34] pb-5 mb-2 text-sm">
        <Stat label="经济指数" value={`${(state.economy_index || 1).toFixed(3)} · ${pressureLabel}`} />
        <Stat label="日变化" value={formatSignedPercent(state.inflation_rate || 0)} />
        <Stat label="明日基础成本" value={`$${(salaryEstimate + operatingEstimate).toLocaleString()}`} />
      </div>
      {Object.entries(state.skills).map(([key, skill]) => {
        const xpNeeded = state.skill_xp_to_next?.[key] ?? Math.max(100, skill.level * 100);
        const xpProgress = xpNeeded > 0 ? Math.min(100, (skill.xp / xpNeeded) * 100) : 100;
        return (
          <div key={key} className="py-4 border-b border-[#2A2D34]">
            <div className="flex justify-between"><span>{state.skill_info[key]?.name_cn || key}</span><span className="text-[#C8A97E]">Lv.{skill.level}</span></div>
            <div className="progress-bg mt-2"><div className="progress-fill" style={{ width: `${xpProgress}%` }} /></div>
          </div>
        );
      })}
      <div className="py-6 border-b border-[#2A2D34] flex flex-col sm:flex-row flex-wrap gap-3 sm:items-center">
        <span>贷款本金 ${state.loan.principal.toLocaleString()}</span>
        <span className="text-xs text-[#9E9E9E]">动态日息 {(dynamicInterestRate * 100).toFixed(1)}%，结算扣 ${dailyInterest.toLocaleString()}</span>
        <div className="flex flex-wrap gap-2 w-full sm:w-auto mt-2 sm:mt-0">
          <input type="number" value={loanAmount} onChange={(event) => setLoanAmount(parseInt(event.target.value) || 100)} className="input-field !h-9 flex-1 sm:flex-none sm:w-[150px] min-w-[100px]" style={{ paddingLeft: 12 }} />
          <button onClick={() => onAction('/api/loan/borrow', { amount: loanAmount }, 'loan_result', '贷款到账。', 'cash')} className="btn-primary !h-9 px-3 sm:px-4">借款</button>
          <button onClick={() => onAction('/api/loan/repay', { amount: loanAmount }, 'loan_result', '还款成功。', 'cash')} className="btn-secondary !h-9 px-3 sm:px-4">还款</button>
        </div>
      </div>
      {Object.entries(state.market_trends).map(([category, trend]) => <div key={category} className="py-3 border-b border-[#2A2D34] flex justify-between"><span>{categoryLabel(category)}</span><span className={trend >= 1 ? 'text-[#C8A97E]' : 'text-[#9E9E9E]'}>{trend.toFixed(2)}x</span></div>)}
    </ListPage>
  );
}

function StaffTab({ onAction, state }: { state: GameState; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  return (
    <ListPage title="员工管理" subtitle="专业人员会影响鉴定、修复、客流和安全。">
      {Object.entries(state.staff_info).map(([key, info]) => (
        <div key={key} className="py-5 border-b border-[#2A2D34] flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
          <div>
            <h3 className="text-lg font-bold">{info.name_cn} {state.staff[key] && <span className="text-[#C8A97E] text-sm">在岗</span>}</h3>
            <p className="text-[#9E9E9E] text-sm my-1">{info.desc}</p>
            <p className="text-[#616161] text-xs">签约 ${info.hire_cost} / 日薪 ${info.daily_salary}</p>
          </div>
          {state.staff[key] ? (
            <button onClick={() => onAction('/api/fire', { staff_type: key }, 'fire_result', '已解雇。', 'reject')} className="btn-secondary !h-9 w-full sm:w-auto shrink-0">解雇</button>
          ) : (
            <button onClick={() => onAction('/api/hire', { staff_type: key }, 'hire_result', '雇佣成功。', 'upgrade')} className="btn-primary !h-9 w-full sm:w-auto shrink-0">雇佣</button>
          )}
        </div>
      ))}
    </ListPage>
  );
}

function UpgradesTab({ onAction, state }: { state: GameState; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  return (
    <ListPage title="当铺升级" subtitle="声望和设施等级共同决定经营上限。">
      <div className="py-5 border-b border-[#2A2D34] flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
        <div>
          <h3 className="text-xl font-bold">声望 Lv.{state.shop_level}</h3>
          <p className="text-[#9E9E9E] mt-1 text-sm">{state.shop_upgrade_desc || '已达到最高声望。'}</p>
          {state.shop_upgrade_min_day && state.day < state.shop_upgrade_min_day && (
            <p className="text-[#FF9800] mt-1 text-xs">需经营至第 {state.shop_upgrade_min_day} 天（当前第 {state.day} 天）</p>
          )}
        </div>
        {state.shop_upgrade_cost && (
          <button
            disabled={!!state.shop_upgrade_min_day && state.day < state.shop_upgrade_min_day}
            onClick={() => onAction('/api/upgrade', undefined, 'upgrade_result', '升级成功。', 'upgrade')}
            className="btn-primary !h-9 w-full sm:w-auto shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ${state.shop_upgrade_cost.toLocaleString()}
          </button>
        )}
      </div>
      {Object.entries(state.facility_info).map(([key, info]) => (
        <div key={key} className="py-5 border-b border-[#2A2D34] flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
          <div>
            <h3 className="text-lg font-bold">{info.name_cn} Lv.{state.facilities[key]}</h3>
            <p className="text-[#9E9E9E] text-sm mt-1">{info.desc}</p>
            {info.upgrade_min_shop_level && state.shop_level < info.upgrade_min_shop_level && (
              <p className="text-[#FF9800] mt-1 text-xs">需声望 Lv.{info.upgrade_min_shop_level}（当前 Lv.{state.shop_level}）</p>
            )}
            {info.upgrade_min_day && state.day < info.upgrade_min_day && (
              <p className="text-[#FF9800] mt-1 text-xs">需经营至第 {info.upgrade_min_day} 天（当前第 {state.day} 天）</p>
            )}
          </div>
          {info.upgrade_blocked === 'max_level' ? (
            <button disabled className="btn-secondary !h-9 w-full sm:w-auto shrink-0 opacity-50 cursor-not-allowed">满级</button>
          ) : info.upgrade_cost ? (
            <button onClick={() => onAction('/api/upgrade_facility', { facility: key }, 'upgrade_result', '设施升级成功。', 'upgrade')} className="btn-secondary !h-9 w-full sm:w-auto shrink-0">${info.upgrade_cost.toLocaleString()}</button>
          ) : (
            <button disabled className="btn-secondary !h-9 w-full sm:w-auto shrink-0 opacity-50 cursor-not-allowed">未解锁</button>
          )}
        </div>
      ))}
    </ListPage>
  );
}

function InfoSidebar({ state }: { state: GameState }) {
  const customer = state.active_customer;
  return (
    <>
      <h3 className="text-[18px] font-bold text-[#C8A97E] mb-4 pb-2 border-b border-[#C8A97E] w-[50px]">资产</h3>
      <div className="space-y-3 text-sm mb-10"><Stat label="现金" value={`$${state.cash.toLocaleString()}`} /><Stat label="声誉" value={state.reputation} /><Stat label="盈利" value={`$${state.total_profit.toLocaleString()}`} /><Stat label="贷款" value={`$${state.loan.principal.toLocaleString()}`} /></div>
      <h3 className="text-[18px] font-bold text-[#C8A97E] mb-4 pb-2 border-b border-[#C8A97E] w-[50px]">经济</h3>
      <div className="space-y-3 text-sm mb-10">
        <Stat label="指数" value={`${(state.economy_index || 1).toFixed(3)}`} />
        <Stat label="日变化" value={formatSignedPercent(state.inflation_rate || 0)} />
        <Stat label="成就" value={`${(state.achievements || []).filter((item) => item.unlocked).length}/${(state.achievements || []).length}`} />
        <Stat label="图鉴" value={`${Object.keys(state.customer_codex || {}).length} 客 / ${Object.keys(state.item_codex || {}).length} 物`} />
      </div>
      {(state.achievement_unlocks || []).length > 0 && (
        <>
          <h3 className="text-[18px] font-bold text-[#C8A97E] mb-4 pb-2 border-b border-[#C8A97E] w-[50px]">里程</h3>
          <div className="space-y-2 text-xs text-[#9E9E9E] mb-10">
            {state.achievement_unlocks.slice(-3).reverse().map((unlock) => <p key={`${unlock.id}-${unlock.day}`}>第 {unlock.day} 天：{unlock.name}</p>)}
          </div>
        </>
      )}
      {customer && <>
        <h3 className="text-[18px] font-bold text-[#C8A97E] mb-4 pb-2 border-b border-[#C8A97E] w-[50px]">顾客</h3>
        <div className="flex items-center gap-3 mb-4"><img src={customer.avatar_url} alt={customer.name} className="w-12 h-12 rounded-full bg-[#14171C] border border-[#2A2D34]" referrerPolicy="no-referrer" /><div><div className="font-bold">{customer.name}</div><div className="text-xs text-[#9E9E9E]">{customer.trait_cn} / 耐心 {customer.patience}</div>{customer.is_returning && <div className="text-xs text-[#C8A97E]">{customer.relationship_cn} · 第 {customer.visit_count} 次</div>}</div></div>
        <div className="space-y-2 text-xs text-[#9E9E9E] mb-8">
          {customer.last_deal_summary && <p>上次往来：{customer.last_deal_summary}</p>}
          {customer.referred_by && <p>来源：忠实顾客推荐</p>}
          {customer.transaction_prefs?.slice(0, 2).map((pref, index) => <p key={`pref-${index}`}>偏好：{pref}</p>)}
          {customer.persuasion_points?.slice(0, 2).map((point, index) => <p key={`point-${index}`}>突破口：{point}</p>)}
        </div>
        <h3 className="text-[18px] font-bold text-[#C8A97E] mb-4 pb-2 border-b border-[#C8A97E] w-[50px]">物证</h3>
        <div className="space-y-3 text-sm"><div className="font-bold">{customer.item.name}</div><Stat label="年代" value={customer.item.era} /><Stat label="稀有度" value={customer.item.rarity_cn} /><Stat label="成色" value={CONDITION_MAP[customer.item.condition] || customer.item.condition} />{appraisalRange(customer.item) && <Stat label="鉴定区间" value={appraisalRange(customer.item) || ''} />}{customer.item.is_appraised_fake !== null && <Stat label="鉴定结论" value={`${appraisalVerdict(customer.item)}${customer.item.appraisal_confidence !== null ? ` / ${customer.item.appraisal_confidence}%` : ''}`} />}<p className="text-[#9E9E9E] text-xs leading-relaxed">{customer.item.story}</p><p className="text-[#9E9E9E] text-xs leading-relaxed">损坏：{customer.item.damage_report}</p>{customer.case_state && customer.case_state.clues.length > 0 && <div className="pt-3 border-t border-[#2A2D34] space-y-2">{customer.case_state.clues.map((clue) => <p key={clue.id} className="text-[#9E9E9E] text-xs leading-relaxed"><span className="text-[#C8A97E]">{clue.title}：</span>{clue.detail}</p>)}</div>}{customer.item.appraisal_notes.length > 0 && <div className="pt-3 border-t border-[#2A2D34] space-y-2">{customer.item.appraisal_notes.map((note, index) => <p key={index} className="text-[#9E9E9E] text-xs leading-relaxed">• {note}</p>)}</div>}</div>
      </>}
    </>
  );
}

function ItemText({ extra, item }: { item: Item; extra?: string }) {
  const condition = CONDITION_MAP[item.condition] || item.condition;
  const status = STATUS_MAP[item.status] || item.status;
  const appraisal = appraisalVerdict(item);

  return (
    <div className="flex-1 min-w-0">
      <div className="mb-2 space-y-2">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h3 className="text-lg font-bold truncate text-[#E0E0E0]">{item.name}</h3>
          {item.showcase_price && <span className="ui-text text-sm text-[#C8A97E]">橱窗 ${item.showcase_price.toLocaleString()}</span>}
          {extra && <span className="ui-text text-sm text-[#9E9E9E]">{extra}</span>}
        </div>
        <div className="ui-text flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
          <ItemMeta label="稀有度" value={item.rarity_cn} valueClassName={RARITY_COLOR[item.rarity] || 'text-[#9E9E9E]'} />
          <ItemMeta label="位置" value={status} valueClassName="text-[#9E9E9E]" />
          <ItemMeta label="成色" value={condition} valueClassName="text-[#C8A97E]" />
        </div>
      </div>
      <p className="text-[#9E9E9E] text-sm leading-relaxed line-clamp-2">{item.story || item.description}</p>
      <div className="ui-text flex flex-wrap gap-x-5 gap-y-1 text-xs text-[#616161] mt-2">
        <span>类别：{categoryLabel(item.category)}</span>
        <span>年代：{item.era}</span>
        {item.value_trend_note && <span>趋势：{item.value_trend_note}</span>}
        <span>鉴定：{appraisal}</span>
        {appraisalRange(item) && <span>鉴定区间：{appraisalRange(item)}</span>}
      </div>
      {item.special_effects?.length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#9E9E9E] mt-2">
          {item.special_effects?.slice(0, 2).map((effect, index) => <span key={`effect-${index}`}>亮点：{effect}</span>)}
        </div>
      )}
    </div>
  );
}

function ItemMeta({ label, value, valueClassName = 'text-[#E0E0E0]' }: { label: string; value: React.ReactNode; valueClassName?: string }) {
  return (
    <span className="inline-flex items-baseline gap-1.5 border-l border-[#2A2D34] pl-3 first:border-l-0 first:pl-0">
      <span className="tracking-[0.18em] text-[#616161]">{label}</span>
      <span className={`font-semibold ${valueClassName}`}>{value}</span>
    </span>
  );
}

function ListPage({ children, subtitle, title }: { children: React.ReactNode; title: React.ReactNode; subtitle: string }) {
  return <div className="max-w-6xl mx-auto w-full animate-slide-up"><h1 className="text-[28px] md:text-[36px] font-bold text-[#C8A97E] mb-2">{title}</h1><p className="text-[#9E9E9E] text-sm mb-6 pb-4 border-b border-[#2A2D34]">{subtitle}</p>{children}</div>;
}

function SummaryLine({ delta, label, value }: { label: string; value: number; delta?: boolean }) {
  return <div className="flex justify-between py-2 border-b border-[#2A2D34]"><span className="text-[#9E9E9E]">{label}</span><span className={delta ? value >= 0 ? 'text-[#4CAF50]' : 'text-[#F44336]' : 'text-[#E0E0E0]'}>{delta && value > 0 ? '+' : ''}${Math.abs(value).toLocaleString()}</span></div>;
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="flex justify-between gap-4"><span className="text-[#9E9E9E]">{label}</span><span className="text-[#E0E0E0] text-right">{value}</span></div>;
}
