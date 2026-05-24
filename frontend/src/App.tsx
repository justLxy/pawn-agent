import React, { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Award,
  BookOpen,
  Briefcase,
  CheckCircle,
  Clock,
  Crown,
  Info,
  Landmark,
  ListOrdered,
  LogOut,
  RefreshCw,
  Search,
  Store,
  Trash2,
  TrendingUp,
  Users,
  Volume2,
  VolumeX,
  X
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const TOKEN_KEY = 'pawnshop-agent-token-v1';
type ActiveTab = 'lobby' | 'inventory' | 'management' | 'staff' | 'upgrades' | 'leaderboard' | 'market' | 'showcase' | 'history' | 'achievements' | 'codex';
type ItemStatus = 'stored' | 'repairing' | 'displayed' | 'sold' | 'listed';
type BoardType = 'assets' | 'reputation' | 'profit' | 'collection';
type MarketView = 'browse' | 'mine' | 'trades';

interface Player {
  id: number;
  username: string;
  shop_name: string;
  online: boolean;
  reputation: number;
  ranking_badge: string | null;
  reward_bonus: number;
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

interface Customer {
  name: string;
  trait_cn: string;
  trait_desc: string;
  role: 'buyer' | 'seller';
  item: Item;
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
  dialogue_history: Array<{ role: 'player' | 'customer'; content: string }>;
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
  repair_methods: Record<string, { name_cn: string; desc: string; cost_multiplier: number; days_delta: number; success_bonus: number; xp: number }>;
  skills: Record<string, { level: number; xp: number }>;
  skill_info: Record<string, { name_cn: string; desc: string }>;
  facilities: Record<string, number>;
  facility_info: Record<string, { name_cn: string; desc: string; level: number; upgrade_cost: number | null }>;
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

interface LeaderboardEntry {
  player_id: number;
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
  negotiation: { patience_change: number };
  deal_completed: boolean;
  walk_out_completed: boolean;
  deal_result?: { message?: string };
  state: GameState;
}

interface ShowcaseData {
  owner: {
    id: number;
    shop_name: string;
    online: boolean;
    reputation: number;
    ranking_badge: string | null;
    is_self: boolean;
  };
  items: Item[];
  display_capacity: number;
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
  const cost = Math.max(120, Math.floor(baseCost * method.cost_multiplier * (1 - Math.min(0.45, discount))));
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
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authForm, setAuthForm] = useState({ username: '', password: '', shop_name: '' });
  const [loading, setLoading] = useState(false);
  const [dayTransition, setDayTransition] = useState<'end_day' | 'next_day' | null>(null);
  const [resetting, setResetting] = useState(false);
  const [appraising, setAppraising] = useState(false);
  const [negotiatingMsg, setNegotiatingMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [mobileInfoOpen, setMobileInfoOpen] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
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
    if (!token) return;
    try {
      const me = await apiGet<{ player: Player }>('/api/auth/me');
      setPlayer(me.player);
      await loadCloudState();
    } catch {
      localStorage.removeItem(TOKEN_KEY);
    }
  };

  useEffect(() => {
    boot();
    return () => stopMusic();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state?.active_customer?.dialogue_history, negotiatingMsg]);

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
    const data = await apiGet<{ listings: Listing[] }>(`/api/market/listings?${params.toString()}`);
    setListings(data.listings);
    setMyListings((await apiGet<{ listings: Listing[] }>('/api/market/mine')).listings);
    setTrades((await apiGet<{ trades: TradeLog[] }>('/api/market/trades')).trades);
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

  const handleAuth = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const data = await apiPost<{ token: string; player: Player }>(endpoint, authForm);
      localStorage.setItem(TOKEN_KEY, data.token);
      setPlayer(data.player);
      await loadCloudState();
      setSuccessMsg(authMode === 'login' ? '欢迎回来。' : '账号创建成功。');
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '登录失败。');
    } finally {
      setLoading(false);
    }
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
      setNegotiatingMsg(null);
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

  const runStateAction = async (path: string, body: unknown, resultKey: string, fallback: string, sound: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade' = 'click') => {
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

  const appraiseActiveItem = async () => {
    setAppraising(true);
    try {
      const data = await apiPost<{ appraise_result: { cost: number; method_name?: string; verdict?: string; confidence?: number; appraised_value: number; appraised_value_low?: number; appraised_value_high?: number; notes?: string[] }; state: GameState }>('/api/appraise', { method: appraisalMethod });
      setState(data.state);
      playSound('appraise');
      const result = data.appraise_result;
      const low = result.appraised_value_low ?? result.appraised_value;
      const high = result.appraised_value_high ?? result.appraised_value;
      setSuccessMsg(`${result.method_name || '鉴定'}完成：${result.verdict || '未见明显作伪'}，估值区间 $${low.toLocaleString()} - $${high.toLocaleString()}，可信度约 ${result.confidence ?? 0}%，花费 $${result.cost.toLocaleString()}。`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '鉴定失败。');
    } finally {
      setAppraising(false);
    }
  };

  const appraiseInventoryItem = async (itemId: string, method: string) => {
    setLoading(true);
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
      setLoading(false);
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
    setLoading(true);
    setNegotiatingMsg('对方正在思索...');
    try {
      const response = await fetch(`${API_BASE_URL}/api/negotiate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...tokenHeader() },
        body: JSON.stringify({ message: playerMessage })
      });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || '谈判失败。');
      if (!response.body) throw new Error('当前浏览器不支持流式谈判。');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      const streamResult: { finalPayload?: NegotiationStreamPayload; error?: string } = {};
      let streamedDialogue = '';
      const updateStreamedDialogue = (content: string) => {
        streamedDialogue += content;
        setNegotiatingMsg(null);
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

      const data = streamResult.finalPayload;
      setState(data.state);
      setNegotiatingMsg(null);
      if (data.negotiation.patience_change < 0) playSound('patience_down');
      if (data.deal_completed) setSuccessMsg(data.deal_result?.message || '交易达成。');
      if (data.walk_out_completed) setErrorMsg('顾客离场，交易中止。');
    } catch (err) {
      setState(previousState);
      setMessage(playerMessage);
      setNegotiatingMsg(null);
      setErrorMsg(err instanceof Error ? err.message : '谈判失败。');
    } finally {
      setLoading(false);
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

  if (!player || !state) {
    return (
      <div className="h-screen w-screen bg-[#0D0F12] text-[#E0E0E0] flex items-center justify-center px-6">
        <AuthScreen
          authForm={authForm}
          authMode={authMode}
          loading={loading}
          setAuthForm={setAuthForm}
          setAuthMode={setAuthMode}
          onSubmit={handleAuth}
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
            <h1 className="text-[16px] md:text-[20px] font-bold text-[#C8A97E] tracking-widest truncate">{state.shop_name || player.shop_name}</h1>
            <div className="hidden md:block text-[11px] text-[#616161] font-sans">{player.ranking_badge || state.ranking_badge || '全服经营中'}</div>
          </div>
        </div>
        <div className="hidden md:flex items-center gap-4 lg:gap-8 font-sans text-xs lg:text-sm text-[#9E9E9E]">
          <span>第 {state.day} 天</span>
          <span>现金 ${state.cash.toLocaleString()}</span>
          <span>声誉 {state.reputation}</span>
          <span>经济 {(state.economy_index || 1).toFixed(2)}x</span>
          <span>客流 {Math.min(state.customers_served_today + (activeCustomer ? 1 : 0), state.total_customers_today)}/{state.total_customers_today}</span>
          <span>展示 {displayedCount}/{state.display_capacity}</span>
        </div>
        <div className="flex items-center gap-1 md:gap-2">
          <button onClick={() => setMobileInfoOpen(true)} className="btn-icon !w-9 !h-9 md:hidden" title="信息栏"><Info className="w-4 h-4" /></button>
          <button onClick={toggleSound} className="btn-icon !w-9 !h-9" title={soundEnabled ? '关闭音乐' : '开启音乐'}>{soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}</button>
          <button onClick={restart} disabled={resetting} className="btn-icon !w-9 !h-9" title="重置"><RefreshCw className={`w-4 h-4 ${resetting ? 'animate-spin' : ''}`} /></button>
          <button onClick={deleteAccount} disabled={loading} className="btn-icon !w-9 !h-9 hover:!text-[#F44336]" title="注销账号"><Trash2 className="w-4 h-4" /></button>
          <button onClick={logout} className="btn-icon !w-9 !h-9" title="退出"><LogOut className="w-4 h-4" /></button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside className="hidden md:flex w-[64px] xl:w-[240px] shrink-0 bg-[#14171C] border-r border-[#2A2D34] flex-col py-6 overflow-y-auto custom-scrollbar z-30 transition-all duration-300">
          <NavButton tab="lobby" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Store className="w-5 h-5" />} label="大堂柜台" />
          <NavButton tab="inventory" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Briefcase className="w-5 h-5" />} label="仓库藏品" />
          <NavButton tab="market" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Landmark className="w-5 h-5" />} label="玩家市场" />
          <NavButton tab="leaderboard" activeTab={activeTab} setActiveTab={setActiveTab} icon={<ListOrdered className="w-5 h-5" />} label="全服排行" />
          <NavButton tab="achievements" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Award className="w-5 h-5" />} label="经营成就" />
          <NavButton tab="codex" activeTab={activeTab} setActiveTab={setActiveTab} icon={<BookOpen className="w-5 h-5" />} label="经营图鉴" />
          <NavButton tab="history" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Clock className="w-5 h-5" />} label="交易记录" />
          <NavButton tab="management" activeTab={activeTab} setActiveTab={setActiveTab} icon={<TrendingUp className="w-5 h-5" />} label="经营财务" />
          <NavButton tab="staff" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Users className="w-5 h-5" />} label="员工管理" />
          <NavButton tab="upgrades" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Crown className="w-5 h-5" />} label="当铺升级" />
        </aside>

        <main className="flex-1 bg-[#0D0F12] p-4 pb-28 md:p-8 overflow-y-auto custom-scrollbar relative flex flex-col">
          {activeTab === 'lobby' && (
            <LobbyTab
              state={state}
              loading={loading}
              dayTransition={dayTransition}
              message={message}
              negotiatingMsg={negotiatingMsg}
              appraising={appraising}
              appraisalMethod={appraisalMethod}
              setMessage={setMessage}
              setAppraisalMethod={setAppraisalMethod}
              onNegotiate={negotiate}
              onAppraise={appraiseActiveItem}
              chatEndRef={chatEndRef}
              onAction={runStateAction}
            />
          )}
          {activeTab === 'inventory' && (
            <InventoryTab
              state={state}
              listingPrice={listingPrice}
              showcasePrice={showcasePrice}
              repairMethod={repairMethod}
              inventoryAppraiseMethod={inventoryAppraiseMethod}
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
              marketSearch={marketSearch}
              marketSort={marketSort}
              marketView={marketView}
              setMarketSearch={setMarketSearch}
              setMarketSort={setMarketSort}
              setMarketView={setMarketView}
              refresh={loadMarket}
              buy={buyMarketItem}
              openShowcase={openShowcase}
              onMarketAction={runStateAction}
            />
          )}
          {activeTab === 'leaderboard' && (
            <LeaderboardTab boardType={boardType} setBoardType={setBoardType} data={leaderboard} refresh={loadLeaderboard} openShowcase={openShowcase} />
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
          {activeTab === 'showcase' && showcase && (
            <ShowcaseTab showcase={showcase} buy={buyShowcaseItem} back={() => setActiveTab('market')} />
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
    </div>
  );
}

function AuthScreen(props: {
  authForm: { username: string; password: string; shop_name: string };
  authMode: 'login' | 'register';
  loading: boolean;
  setAuthForm: (form: { username: string; password: string; shop_name: string }) => void;
  setAuthMode: (mode: 'login' | 'register') => void;
  onSubmit: (event: React.FormEvent) => void;
}) {
  const { authForm, authMode, loading, onSubmit, setAuthForm, setAuthMode } = props;
  return (
    <div className="w-full max-w-[520px]">
      <div className="flex items-center gap-3 mb-10">
        <Store className="w-9 h-9 text-[#C8A97E]" />
        <div>
          <h1 className="text-[28px] font-bold text-[#C8A97E] tracking-widest">当铺代理人</h1>
          <p className="text-[#616161] text-sm font-sans">联机市场与全服排行已开启</p>
        </div>
      </div>
      <div className="flex gap-8 border-b border-[#2A2D34] mb-8">
        {(['login', 'register'] as const).map((mode) => (
          <button key={mode} onClick={() => setAuthMode(mode)} className={`pb-3 font-sans ${authMode === mode ? 'text-[#C8A97E] border-b border-[#C8A97E]' : 'text-[#616161]'}`}>
            {mode === 'login' ? '登录账号' : '注册当铺'}
          </button>
        ))}
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <input className="input-field w-full" style={{ paddingLeft: 16 }} placeholder="用户名" value={authForm.username} onChange={(event) => setAuthForm({ ...authForm, username: event.target.value })} />
        <input className="input-field w-full" style={{ paddingLeft: 16 }} placeholder="密码" type="password" value={authForm.password} onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })} />
        {authMode === 'register' && <input className="input-field w-full" style={{ paddingLeft: 16 }} placeholder="当铺名称" value={authForm.shop_name} onChange={(event) => setAuthForm({ ...authForm, shop_name: event.target.value })} />}
        <button disabled={loading} className="btn-primary w-full">{authMode === 'login' ? '进入当铺' : '创建云端当铺'}</button>
      </form>
    </div>
  );
}

function Notifications({ errorMsg, successMsg, setErrorMsg, setSuccessMsg }: { errorMsg: string | null; successMsg: string | null; setErrorMsg: (value: string | null) => void; setSuccessMsg: (value: string | null) => void }) {
  return (
    <div className="fixed top-20 right-4 md:right-6 z-50 flex flex-col gap-2 pointer-events-none w-[90%] md:w-auto max-w-[420px]">
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

function NavButton({ activeTab, icon, label, setActiveTab, tab }: { activeTab: ActiveTab; icon: React.ReactNode; label: string; setActiveTab: (tab: ActiveTab) => void; tab: ActiveTab }) {
  return (
    <button title={label} onClick={() => setActiveTab(tab)} className={`nav-item ${activeTab === tab ? 'active' : ''} !px-0 justify-center xl:!px-5 xl:justify-start`}>
      <div className="shrink-0">{icon}</div>
      <span className="hidden xl:inline">{label}</span>
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
    { tab: 'upgrades', label: '升级', icon: <Crown className="w-5 h-5" /> }
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

function MobileInfoDrawer({ onClose, state }: { state: GameState; onClose: () => void }) {
  return (
    <div className="md:hidden fixed inset-0 z-[60]">
      <button aria-label="关闭信息栏" onClick={onClose} className="absolute inset-0 bg-black/55 backdrop-blur-sm" />
      <aside className="absolute right-0 top-0 h-full w-[86vw] max-w-[360px] bg-[#14171C] border-l border-[#2A2D34] py-6 px-5 overflow-y-auto custom-scrollbar shadow-2xl animate-slide-right">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-[#C8A97E] font-bold text-lg">当铺信息</h2>
          <button onClick={onClose} className="btn-icon !w-9 !h-9" title="关闭"><X className="w-4 h-4" /></button>
        </div>
        <InfoSidebar state={state} />
      </aside>
    </div>
  );
}

function DayTransitionLoader({ mode }: { mode: 'end_day' | 'next_day' }) {
  const config = mode === 'end_day'
    ? {
        title: '正在结算今日经营',
        subtitle: '账本合上，街灯渐暗，当铺进入打烊时分',
        tips: ['核对今日交易流水…', '结算员工薪水与运营成本…', '清点库存持有与市场行情…', '整理今日坊间轶事与往来账目…', '留意是否还有未了之事…']
      }
    : {
        title: '正在开启新的一天',
        subtitle: '卷帘拉起，街声渐近，当铺准备开门迎客',
        tips: ['翻开新一页经营日志…', '刷新经济指数与客流预期…', '整理仓库与展示柜…', '留意今日可能上门的顾客…', '擦拭柜台，等待第一声叩门…']
      };
  const [tipIndex, setTipIndex] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setTipIndex((index) => (index + 1) % config.tips.length), 2800);
    return () => window.clearInterval(timer);
  }, [config.tips.length]);
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-6 animate-slide-up">
      <div className="relative mb-8 flex items-center justify-center">
        <div className="day-loader-ring" />
        <Clock className="w-7 h-7 text-[#C8A97E] absolute day-loader-icon" />
      </div>
      <h1 className="text-[28px] md:text-[32px] font-bold text-[#C8A97E] mb-3">{config.title}</h1>
      <p className="text-[#9E9E9E] text-sm mb-8 max-w-md">{config.subtitle}</p>
      <div className="day-loader-track mb-6" />
      <p key={tipIndex} className="text-[#616161] text-xs font-sans day-loader-tip min-h-[20px]">{config.tips[tipIndex]}</p>
    </div>
  );
}

function LobbyTab({ appraisalMethod, appraising, chatEndRef, dayTransition, loading, message, negotiatingMsg, onAction, onAppraise, onNegotiate, setAppraisalMethod, setMessage, state }: { state: GameState; loading: boolean; dayTransition: 'end_day' | 'next_day' | null; appraising: boolean; appraisalMethod: string; message: string; negotiatingMsg: string | null; setMessage: (value: string) => void; setAppraisalMethod: (value: string) => void; onNegotiate: (event: React.FormEvent) => void; onAppraise: () => Promise<void>; chatEndRef: React.RefObject<HTMLDivElement | null>; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  const customer = state.active_customer;
  if (dayTransition === 'next_day' && state.day_ended) {
    return <DayTransitionLoader mode="next_day" />;
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
            <div className="space-y-2">{state.pending_event.choices.map((choice) => <button key={choice.id} onClick={() => onAction('/api/event/choice', { choice_id: choice.id }, 'event_result', '事件已处理。')} className="w-full text-left py-3 border-b border-[#2A2D34] hover:text-[#C8A97E]">{choice.label}<span className="block text-xs text-[#616161]">{choice.effect}</span></button>)}</div>
          </div>
        )}
        <button onClick={() => onAction('/api/next_day', undefined, 'result', '新的一天开始了。', 'cash')} disabled={loading || !!state.pending_event} className="btn-primary w-full md:w-auto">
          {loading ? <><RefreshCw className="w-5 h-5 mr-2 animate-spin" />正在准备…</> : <>开启第 {state.day + 1} 天 <ArrowRight className="w-5 h-5 ml-2" /></>}
        </button>
      </div>
    );
  }
  if (!customer) {
    if (dayTransition === 'end_day') {
      return <DayTransitionLoader mode="end_day" />;
    }
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center">
        <Clock className="w-12 h-12 text-[#616161] mb-6" />
        <h1 className="text-[32px] font-bold mb-4">今日打烊</h1>
        <button onClick={() => onAction('/api/end_day', undefined, 'summary', '结算完成。', 'deal')} disabled={loading} className="btn-primary">
          {loading ? <><RefreshCw className="w-5 h-5 mr-2 animate-spin" />结算中…</> : '营业结算'}
        </button>
      </div>
    );
  }
  const quickOffer = (ratio: number) => {
    const price = Math.max(1, Math.round(customer.current_offer * ratio));
    const formattedPrice = price.toLocaleString();
    const sellerLines = [
      `我出 ${formattedPrice} 元，现金马上给你。`,
      `${formattedPrice} 元，我现在就能付款，省去你继续跑价的麻烦。`,
      `按我看这件货的风险，我最多先报 ${formattedPrice} 元。`,
      `${formattedPrice} 元成交的话，我这边立刻收下。`,
    ];
    const buyerLines = [
      `这件货 ${formattedPrice} 元给你，附带来源说明。`,
      `${formattedPrice} 元，你今天带走，我把保养要点也交代清楚。`,
      `这件藏品我开 ${formattedPrice} 元，价格里包含店里的把关成本。`,
      `${formattedPrice} 元可以谈，但这件货的品相和来历都值这个价。`,
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
  const tradeMode = customer.role === 'seller'
    ? { label: '收购', tone: '你正在向顾客收购物品，报价越低利润空间越大。', priceLabel: '对方要价' }
    : { label: '出售', tone: '顾客想从你的库存买走这件物品，报价越高利润越大。', priceLabel: '对方出价' };
  return (
    <div className="max-w-3xl mx-auto w-full flex-1 flex flex-col">
      <div className="mb-6 border-b border-[#2A2D34] pb-4 pt-4 md:pt-8 -mt-4 md:-mt-8 sticky top-0 bg-[#0D0F12]/95 backdrop-blur z-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-sans">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="text-[#C8A97E] text-sm tracking-[0.25em]">{tradeMode.label}</span>
              <span className="text-[#616161] text-xs">{customer.trait_cn} / 耐心 {customer.patience}</span>
              {customer.is_returning && <span className="text-[#C8A97E] text-xs border-l border-[#2A2D34] pl-3">{customer.relationship_cn} · 第 {customer.visit_count} 次</span>}
            </div>
            <p className="text-[#9E9E9E] text-xs leading-relaxed">{customer.name} 走进店里，{customer.backstory}</p>
            {customer.last_deal_summary && <p className="text-[#616161] text-xs mt-1">旧账：{customer.last_deal_summary}</p>}
            <p className="text-[#616161] text-xs mt-1">{tradeMode.tone}</p>
          </div>
          <div className="text-left sm:text-right">
            <div className="text-xs text-[#616161]">{tradeMode.priceLabel}</div>
            <div className="text-[#C8A97E] text-[28px] font-bold leading-tight">${customer.current_offer.toLocaleString()}</div>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto custom-scrollbar pr-3 space-y-5 pb-6">
        <Chat speaker={customer.name} avatarUrl={customer.avatar_url}>
          {customer.role === 'seller'
            ? `掌柜的，我今天带来【${customer.item.name}】。你给个价。`
            : `掌柜的，我听说你这儿有件【${customer.item.name}】。你打算卖多少钱？`}
        </Chat>
        {customer.dialogue_history.map((turn, idx) => (
          <Chat key={idx} speaker={turn.role === 'player' ? '你' : customer.name} right={turn.role === 'player'} avatarUrl={turn.role === 'customer' ? customer.avatar_url : undefined}>
            {turn.content}
          </Chat>
        ))}
        {negotiatingMsg && <div className="flex gap-2 text-[#616161]"><RefreshCw className="w-4 h-4 animate-spin" />{negotiatingMsg}</div>}
        <div ref={chatEndRef} />
      </div>
      <div className="border-t border-[#2A2D34] pt-4">
        <div className="flex gap-2 mb-3"><button onClick={() => quickOffer(0.5)} className="btn-secondary !h-8 !px-3 !text-xs">试探价</button><button onClick={() => quickOffer(1)} className="btn-secondary !h-8 !px-3 !text-xs">当前价</button><button onClick={() => quickOffer(2)} className="btn-secondary !h-8 !px-3 !text-xs">强势报价</button></div>
        <form onSubmit={onNegotiate} className="flex gap-3"><input value={message} onChange={(event) => setMessage(event.target.value)} className="input-field flex-1" style={{ paddingLeft: 16 }} placeholder="用自然语言谈判..." /><button disabled={loading} className="btn-primary">谈判</button></form>
        <div className="flex flex-col sm:flex-row gap-2 mt-3">
          <select value={appraisalMethod} onChange={(event) => setAppraisalMethod(event.target.value)} className="input-field !h-10 !px-3 sm:w-[180px]">
            {Object.entries(state.appraisal_methods).map(([key, info]) => {
              const preview = computeAppraisalPreview(appraisalContext.marketValue, info, appraisalContext.skillLevel, appraisalContext.roomLevel, appraisalContext.hasAppraiser, state.economy_index || 1);
              return (
                <option key={key} value={key}>
                  {info.name_cn}（识破 {formatAppraisalPercent(preview.fakeDetectionRate)}）
                </option>
              );
            })}
          </select>
          <button onClick={onAppraise} disabled={loading || appraising || customer.item.is_appraised_fake !== null} className="btn-secondary flex-1 !h-10">{appraising ? '鉴定中...' : customer.item.is_appraised_fake !== null ? '已鉴定' : '鉴定'}</button>
          <button onClick={() => onAction('/api/deal', undefined, 'deal_result', '成交。', 'deal')} className="btn-secondary flex-1 !h-10">成交</button>
          <button onClick={() => onAction('/api/reject', undefined, 'result', '已拒绝。', 'reject')} className="btn-secondary flex-1 !h-10">拒绝</button>
        </div>
        <p className="mt-2 text-xs text-[#616161] font-sans leading-relaxed">
          {selectedAppraisal.name_cn}：预计 ${appraisalPreview.cost.toLocaleString()}；
          赝品识破率 {formatAppraisalPercent(appraisalPreview.fakeDetectionRate)}（若为赝品时判定为假）；
          估值误差 ±{formatAppraisalPercent(appraisalPreview.valueErrorMargin)}。
          {selectedAppraisal.desc}
        </p>
      </div>
    </div>
  );
}

function Chat({ avatarUrl, children, right, speaker }: { avatarUrl?: string; children: React.ReactNode; right?: boolean; speaker: string }) {
  return (
    <div className={`flex gap-3 max-w-[86%] ${right ? 'ml-auto flex-row-reverse' : ''}`}>
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
        <div className={`px-4 py-3 leading-relaxed ${right ? 'border-r border-[#C8A97E] text-right bg-[rgba(200,169,126,0.06)]' : 'border-l border-[#2A2D34] bg-[rgba(255,255,255,0.03)]'}`}>{children}</div>
      </div>
    </div>
  );
}

function InventoryTab({ state, listingPrice, repairMethod, inventoryAppraiseMethod, showcasePrice, onAction, onClearShowcasePrice, onList, onSetShowcasePrice, setListingPrice, setRepairMethod, setInventoryAppraiseMethod, setShowcasePrice, onAppraise }: { state: GameState; listingPrice: Record<string, number>; repairMethod: Record<string, string>; inventoryAppraiseMethod: Record<string, string>; showcasePrice: Record<string, number>; setListingPrice: (value: Record<string, number>) => void; setRepairMethod: (value: Record<string, string>) => void; setInventoryAppraiseMethod: (value: Record<string, string>) => void; setShowcasePrice: (value: Record<string, number>) => void; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void>; onList: (item: Item) => Promise<void>; onSetShowcasePrice: (item: Item) => Promise<void>; onClearShowcasePrice: (item: Item) => Promise<void>; onAppraise: (itemId: string, method: string) => Promise<void> }) {
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
      {activeItems.map((item) => (
        <div key={item.id} className="py-5 border-b border-[#2A2D34] flex flex-col xl:flex-row xl:items-center gap-4">
          <ItemText item={item} />
          <div className="w-full xl:w-[500px] flex flex-wrap gap-x-6 gap-y-4 justify-start xl:justify-end mt-4 xl:mt-0 items-end">
            {item.is_appraised_fake === null && (
              <div className="flex items-center gap-2 border-b border-[#2A2D34] pb-1">
                <select value={inventoryAppraiseMethod[item.id] || 'standard'} onChange={(event) => setInventoryAppraiseMethod({ ...inventoryAppraiseMethod, [item.id]: event.target.value })} className="bg-transparent text-[#E0E0E0] outline-none text-sm w-[90px]">
                  {Object.entries(state.appraisal_methods).map(([key, info]) => (
                    <option key={key} value={key}>{info.name_cn}</option>
                  ))}
                </select>
                <button onClick={() => onAppraise(item.id, inventoryAppraiseMethod[item.id] || 'standard')} className="text-[#D4B88A] hover:text-[#C8A97E] text-sm whitespace-nowrap transition-colors">鉴定</button>
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
            {item.status === 'repairing' && <div className="basis-full text-right text-xs text-[#C8A97E]">修复中：还需 {item.repair_days_remaining} 天，营业结算后推进进度。</div>}
          </div>
        </div>
      ))}
    </ListPage>
  );
}

function MarketTab(props: { listings: Listing[]; myListings: Listing[]; trades: TradeLog[]; marketSearch: string; marketSort: string; marketView: MarketView; setMarketSearch: (value: string) => void; setMarketSort: (value: string) => void; setMarketView: (value: MarketView) => void; refresh: () => Promise<void>; buy: (id: string) => Promise<void>; openShowcase: (ownerId: number) => Promise<void>; onMarketAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  const { buy, listings, marketSearch, marketSort, marketView, myListings, onMarketAction, openShowcase, refresh, setMarketSearch, setMarketSort, setMarketView, trades } = props;
  const shown = marketView === 'browse' ? listings : myListings;
  return (
    <ListPage title="玩家交易市场" subtitle="全服玩家互买互卖，寻找低价捡漏和高价倒卖机会。">
      <div className="sticky top-0 bg-[#0D0F12]/95 backdrop-blur z-10 pb-4 border-b border-[#2A2D34] mb-2">
        <div className="flex flex-col lg:flex-row gap-3 lg:items-center">
          <div className="flex gap-6 border-b border-[#2A2D34] lg:border-b-0 overflow-x-auto custom-scrollbar pb-1">
            {(['browse', 'mine', 'trades'] as const).map((view) => <button key={view} onClick={() => setMarketView(view)} className={`pb-2 whitespace-nowrap ${marketView === view ? 'text-[#C8A97E] border-b border-[#C8A97E]' : 'text-[#616161]'}`}>{view === 'browse' ? '全服市场' : view === 'mine' ? '我的摊位' : '交易记录'}</button>)}
          </div>
          <div className="flex flex-wrap sm:flex-nowrap gap-2 flex-1 mt-1 lg:mt-0">
            <div className="relative w-full sm:flex-1"><Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#616161]" /><input value={marketSearch} onChange={(event) => setMarketSearch(event.target.value)} className="input-field w-full" placeholder="搜索物品..." /></div>
            <div className="flex gap-2 w-full sm:w-auto">
              <select value={marketSort} onChange={(event) => setMarketSort(event.target.value)} className="input-field flex-1 sm:flex-none !px-3"><option value="newest">最新</option><option value="price_asc">低价</option><option value="price_desc">高价</option></select>
              <button onClick={() => refresh()} className="btn-secondary !px-4 flex-1 sm:flex-none">刷新</button>
            </div>
          </div>
        </div>
      </div>
      {marketView === 'trades' ? trades.map((trade) => <div key={trade.id} className="py-4 border-b border-[#2A2D34] flex justify-between gap-4"><span>【{trade.item_name}】</span><span className="text-[#9E9E9E]">{trade.buyer_shop || '买家'} ↔ {trade.seller_shop || '卖家'}</span><span className="text-[#C8A97E]">${trade.price.toLocaleString()} / 税 ${trade.tax}</span></div>) : shown.map((listing) => (
        <div key={listing.id} className="py-5 border-b border-[#2A2D34] flex flex-col xl:flex-row xl:items-center gap-4">
          <ItemText item={listing.item} extra={listing.seller_online ? '卖家在线' : '卖家离线'} />
          <div className="w-full xl:w-[300px] flex items-center justify-between xl:justify-end gap-5 mt-2 xl:mt-0">
            <button onClick={() => openShowcase(listing.seller_id)} className="text-[#9E9E9E] hover:text-[#C8A97E] text-sm text-left xl:text-right">{listing.seller_shop}<span className="block text-xs text-[#616161]">进店看橱窗</span></button>
            <div className="flex-1 text-right"><div className="text-[#C8A97E] text-lg font-bold">${listing.price.toLocaleString()}</div>{appraisalRange(listing.item) ? <div className="text-xs text-[#616161]">鉴定区间 {appraisalRange(listing.item)}</div> : <div className="text-xs text-[#616161]">未知（需鉴定）</div>}</div>
            {marketView === 'browse' ? <button onClick={() => buy(listing.id)} className="btn-primary !h-9 !px-4 shrink-0">购买</button> : <button onClick={() => onMarketAction('/api/market/unlist', { listing_id: listing.id }, 'market_result', '已下架。').then(refresh)} className="btn-secondary !h-9 !px-4 shrink-0">下架</button>}
          </div>
        </div>
      ))}
    </ListPage>
  );
}

function leaderboardScore(entry: LeaderboardEntry, boardType: BoardType): number {
  if (boardType === 'reputation') return entry.reputation;
  if (boardType === 'profit') return entry.profit;
  if (boardType === 'collection') return entry.collection;
  return entry.assets;
}

function LeaderboardTab({ boardType, data, openShowcase, refresh, setBoardType }: { boardType: BoardType; setBoardType: (value: BoardType) => void; data: { entries: LeaderboardEntry[]; my_rank: LeaderboardEntry | null } | null; refresh: () => Promise<void>; openShowcase: (ownerId: number) => Promise<void> }) {
  const scoreLabel = BOARD_LABEL[boardType];
  return (
    <ListPage title="全服排行榜" subtitle="10 秒自动刷新；点击当铺名或「参观橱窗」可浏览他人展示柜与在售藏品。前 100 名获每日声誉与稀有刷新奖励。">
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
                  {entry.badge ? `${entry.badge} · ` : ''}{entry.shop_name}
                </button>
                <span className="mt-1 block text-[11px] text-[#616161] truncate">点击浏览橱窗展览</span>
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
          <span>{data.my_rank.shop_name}</span>
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
            return (
              <div key={achievement.id} className={`py-3 border-t border-[#2A2D34] ${achievement.unlocked ? 'text-[#E0E0E0]' : 'text-[#9E9E9E]'}`}>
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <div className="font-bold">{achievement.name} {achievement.unlocked && <span className="text-[#C8A97E] text-xs">已解锁</span>}</div>
                    <p className="text-xs text-[#9E9E9E] mt-1">{achievement.desc}</p>
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
                {customer.last_deal_summary && <span>旧账：{customer.last_deal_summary}</span>}
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

function ShowcaseTab({ back, buy, showcase }: { showcase: ShowcaseData; buy: (ownerId: number, itemId: string) => Promise<void>; back: () => void }) {
  return (
    <ListPage title={`${showcase.owner.shop_name} 的当铺橱窗`} subtitle={`展示 ${showcase.items.length}/${showcase.display_capacity} 件藏品。只能购买标有橱窗售价的展示品。`}>
      <div className="flex items-center justify-between border-b border-[#2A2D34] pb-4 mb-2">
        <div className="text-sm text-[#9E9E9E]">
          <span className={showcase.owner.online ? 'text-[#4CAF50]' : 'text-[#616161]'}>{showcase.owner.online ? '在线' : '离线'}</span>
          <span className="mx-3">声誉 {showcase.owner.reputation}</span>
          {showcase.owner.ranking_badge && <span className="text-[#C8A97E]">{showcase.owner.ranking_badge}</span>}
        </div>
        <button onClick={back} className="btn-secondary !h-9 !px-4">返回市场</button>
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
      {Object.entries(state.skills).map(([key, skill]) => <div key={key} className="py-4 border-b border-[#2A2D34]"><div className="flex justify-between"><span>{state.skill_info[key]?.name_cn || key}</span><span className="text-[#C8A97E]">Lv.{skill.level}</span></div><div className="progress-bg mt-2"><div className="progress-fill" style={{ width: `${Math.min(100, (skill.xp / Math.max(100, skill.level * 100)) * 100)}%` }} /></div></div>)}
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
        </div>
        {state.shop_upgrade_cost && <button onClick={() => onAction('/api/upgrade', undefined, 'upgrade_result', '升级成功。', 'upgrade')} className="btn-primary !h-9 w-full sm:w-auto shrink-0">${state.shop_upgrade_cost.toLocaleString()}</button>}
      </div>
      {Object.entries(state.facility_info).map(([key, info]) => (
        <div key={key} className="py-5 border-b border-[#2A2D34] flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
          <div>
            <h3 className="text-lg font-bold">{info.name_cn} Lv.{state.facilities[key]}</h3>
            <p className="text-[#9E9E9E] text-sm mt-1">{info.desc}</p>
          </div>
          <button disabled={info.upgrade_cost === null} onClick={() => onAction('/api/upgrade_facility', { facility: key }, 'upgrade_result', '设施升级成功。', 'upgrade')} className="btn-secondary !h-9 w-full sm:w-auto shrink-0">{info.upgrade_cost ? `$${info.upgrade_cost.toLocaleString()}` : '满级'}</button>
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
          {customer.last_deal_summary && <p>旧账：{customer.last_deal_summary}</p>}
          {customer.referred_by && <p>来源：忠实顾客推荐</p>}
          {customer.transaction_prefs?.slice(0, 2).map((pref, index) => <p key={`pref-${index}`}>偏好：{pref}</p>)}
          {customer.persuasion_points?.slice(0, 2).map((point, index) => <p key={`point-${index}`}>突破口：{point}</p>)}
        </div>
        <h3 className="text-[18px] font-bold text-[#C8A97E] mb-4 pb-2 border-b border-[#C8A97E] w-[50px]">物证</h3>
        <div className="space-y-3 text-sm"><div className="font-bold">{customer.item.name}</div><Stat label="年代" value={customer.item.era} /><Stat label="稀有度" value={customer.item.rarity_cn} /><Stat label="成色" value={CONDITION_MAP[customer.item.condition] || customer.item.condition} />{appraisalRange(customer.item) && <Stat label="鉴定区间" value={appraisalRange(customer.item) || ''} />}{customer.item.is_appraised_fake !== null && <Stat label="鉴定结论" value={`${appraisalVerdict(customer.item)}${customer.item.appraisal_confidence !== null ? ` / ${customer.item.appraisal_confidence}%` : ''}`} />}<p className="text-[#9E9E9E] text-xs leading-relaxed">{customer.item.story}</p><p className="text-[#9E9E9E] text-xs leading-relaxed">损坏：{customer.item.damage_report}</p>{customer.item.authentication_tips?.length > 0 && <div className="pt-3 border-t border-[#2A2D34] space-y-2">{customer.item.authentication_tips.map((tip, index) => <p key={index} className="text-[#9E9E9E] text-xs leading-relaxed">鉴别：{tip}</p>)}</div>}{customer.item.appraisal_notes.length > 0 && <div className="pt-3 border-t border-[#2A2D34] space-y-2">{customer.item.appraisal_notes.map((note, index) => <p key={index} className="text-[#9E9E9E] text-xs leading-relaxed">• {note}</p>)}</div>}</div>
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
      {(item.special_effects?.length > 0 || item.authentication_tips?.length > 0) && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#9E9E9E] mt-2">
          {item.special_effects?.slice(0, 2).map((effect, index) => <span key={`effect-${index}`}>亮点：{effect}</span>)}
          {item.authentication_tips?.slice(0, 2).map((tip, index) => <span key={`tip-${index}`}>鉴别：{tip}</span>)}
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

function ListPage({ children, subtitle, title }: { children: React.ReactNode; title: string; subtitle: string }) {
  return <div className="max-w-6xl mx-auto w-full animate-slide-up"><h1 className="text-[28px] md:text-[36px] font-bold text-[#C8A97E] mb-2">{title}</h1><p className="text-[#9E9E9E] text-sm mb-6 pb-4 border-b border-[#2A2D34]">{subtitle}</p>{children}</div>;
}

function SummaryLine({ delta, label, value }: { label: string; value: number; delta?: boolean }) {
  return <div className="flex justify-between py-2 border-b border-[#2A2D34]"><span className="text-[#9E9E9E]">{label}</span><span className={delta ? value >= 0 ? 'text-[#4CAF50]' : 'text-[#F44336]' : 'text-[#E0E0E0]'}>{delta && value > 0 ? '+' : ''}${Math.abs(value).toLocaleString()}</span></div>;
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="flex justify-between gap-4"><span className="text-[#9E9E9E]">{label}</span><span className="text-[#E0E0E0] text-right">{value}</span></div>;
}
