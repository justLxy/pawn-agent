import React, { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
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
type ActiveTab = 'lobby' | 'inventory' | 'management' | 'staff' | 'upgrades' | 'leaderboard' | 'market' | 'showcase' | 'history';
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
  is_appraised_fake: boolean | null;
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
  patience: number;
  current_offer: number;
  dialogue_history: Array<{ role: 'player' | 'customer'; content: string }>;
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
  appraisal_methods: Record<string, { name_cn: string; desc: string; cost_multiplier: number; accuracy_bonus: number; xp: number }>;
  repair_methods: Record<string, { name_cn: string; desc: string; cost_multiplier: number; days_delta: number; success_bonus: number; xp: number }>;
  skills: Record<string, { level: number; xp: number }>;
  skill_info: Record<string, { name_cn: string; desc: string }>;
  facilities: Record<string, number>;
  facility_info: Record<string, { name_cn: string; desc: string; level: number; upgrade_cost: number | null }>;
  loan: { principal: number; interest_rate: number };
  tax: { next_due_day: number; rate: number; last_paid: number };
  market_trends: Record<string, number>;
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

function categoryLabel(category: string): string {
  return CATEGORY_MAP[category] || category;
}

function extractOffer(text: string): number | null {
  const matches = text.match(/\d+(?:,\d{3})*/g);
  if (!matches?.length) return null;
  return parseInt(matches[matches.length - 1].replaceAll(',', ''), 10);
}

function tokenHeader(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { headers: tokenHeader() });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || '服务器响应异常。');
  return response.json();
}

async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...tokenHeader() },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || '操作失败。');
  return response.json();
}

async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'DELETE',
    headers: tokenHeader()
  });
  if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || '删除失败。');
  return response.json();
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
  const [resetting, setResetting] = useState(false);
  const [appraising, setAppraising] = useState(false);
  const [negotiatingMsg, setNegotiatingMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [mobileInfoOpen, setMobileInfoOpen] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const musicContextRef = useRef<AudioContext | null>(null);
  const musicNodesRef = useRef<{ oscillators: OscillatorNode[]; intervals: number[]; gain: GainNode } | null>(null);

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
    }
  };

  const appraiseActiveItem = async () => {
    setAppraising(true);
    try {
      const data = await apiPost<{ appraise_result: { cost: number; method_name?: string; is_fake: boolean; appraised_value: number; notes?: string[] }; state: GameState }>('/api/appraise', { method: appraisalMethod });
      setState(data.state);
      playSound('appraise');
      const result = data.appraise_result;
      setSuccessMsg(`${result.method_name || '鉴定'}完成：${result.is_fake ? '赝品' : '正品'}，估值 $${result.appraised_value.toLocaleString()}，花费 $${result.cost.toLocaleString()}。`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '鉴定失败。');
    } finally {
      setAppraising(false);
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
      const streamResult: { finalPayload?: NegotiationStreamPayload } = {};
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
      if (!streamResult.finalPayload) throw new Error('谈判流式响应未完成。');

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
    const price = listingPrice[item.id] || item.market_value;
    await runStateAction('/api/market/list', { item_id: item.id, price }, 'market_result', '已挂售。', 'cash');
    await loadMarket().catch(() => {});
  };

  const buyMarketItem = async (listingId: string) => {
    await runStateAction('/api/market/buy', { listing_id: listingId }, 'market_result', '购买成功。', 'cash');
    await loadMarket().catch(() => {});
    await loadLeaderboard().catch(() => {});
  };

  const setShowcaseItemPrice = async (item: Item) => {
    const price = showcasePrice[item.id] ?? item.showcase_price ?? item.market_value;
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
        <div className="hidden lg:flex items-center gap-8 font-sans text-sm text-[#9E9E9E]">
          <span>第 {state.day} 天</span>
          <span>现金 ${state.cash.toLocaleString()}</span>
          <span>声誉 {state.reputation}</span>
          <span>客流 {Math.min(state.customers_served_today + (activeCustomer ? 1 : 0), state.total_customers_today)}/{state.total_customers_today}</span>
          <span>展示 {displayedCount}/{state.display_capacity}</span>
        </div>
        <div className="flex items-center gap-1 md:gap-2">
          <button onClick={() => setMobileInfoOpen(true)} className="btn-icon !w-9 !h-9 lg:hidden" title="信息栏"><Info className="w-4 h-4" /></button>
          <button onClick={toggleSound} className="btn-icon !w-9 !h-9" title={soundEnabled ? '关闭音乐' : '开启音乐'}>{soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}</button>
          <button onClick={restart} disabled={resetting} className="btn-icon !w-9 !h-9" title="重置"><RefreshCw className={`w-4 h-4 ${resetting ? 'animate-spin' : ''}`} /></button>
          <button onClick={deleteAccount} disabled={loading} className="btn-icon !w-9 !h-9 hover:!text-[#F44336]" title="注销账号"><Trash2 className="w-4 h-4" /></button>
          <button onClick={logout} className="btn-icon !w-9 !h-9" title="退出"><LogOut className="w-4 h-4" /></button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside className="hidden md:flex w-[230px] shrink-0 bg-[#14171C] border-r border-[#2A2D34] flex-col py-6 overflow-y-auto custom-scrollbar z-30">
          <NavButton tab="lobby" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Store className="w-5 h-5" />} label="大堂柜台" />
          <NavButton tab="inventory" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Briefcase className="w-5 h-5" />} label="仓库藏品" />
          <NavButton tab="market" activeTab={activeTab} setActiveTab={setActiveTab} icon={<Landmark className="w-5 h-5" />} label="玩家市场" />
          <NavButton tab="leaderboard" activeTab={activeTab} setActiveTab={setActiveTab} icon={<ListOrdered className="w-5 h-5" />} label="全服排行" />
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
              setListingPrice={setListingPrice}
              setRepairMethod={setRepairMethod}
              setShowcasePrice={setShowcasePrice}
              onAction={runStateAction}
              onList={listToMarket}
              onSetShowcasePrice={setShowcaseItemPrice}
              onClearShowcasePrice={clearShowcaseItemPrice}
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

        <aside className="w-[300px] shrink-0 bg-[#14171C] border-l border-[#2A2D34] hidden lg:flex flex-col py-8 px-6 overflow-y-auto custom-scrollbar z-30">
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
  return <button onClick={() => setActiveTab(tab)} className={`nav-item ${activeTab === tab ? 'active' : ''}`}>{icon}<span>{label}</span></button>;
}

function MobileNav({ activeTab, setActiveTab }: { activeTab: ActiveTab; setActiveTab: (tab: ActiveTab) => void }) {
  const items: Array<{ tab: ActiveTab; label: string; icon: React.ReactNode }> = [
    { tab: 'lobby', label: '大堂', icon: <Store className="w-5 h-5" /> },
    { tab: 'inventory', label: '仓库', icon: <Briefcase className="w-5 h-5" /> },
    { tab: 'market', label: '市场', icon: <Landmark className="w-5 h-5" /> },
    { tab: 'leaderboard', label: '排行', icon: <ListOrdered className="w-5 h-5" /> },
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
    <div className="lg:hidden fixed inset-0 z-[60]">
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

function LobbyTab({ appraisalMethod, appraising, chatEndRef, loading, message, negotiatingMsg, onAction, onAppraise, onNegotiate, setAppraisalMethod, setMessage, state }: { state: GameState; loading: boolean; appraising: boolean; appraisalMethod: string; message: string; negotiatingMsg: string | null; setMessage: (value: string) => void; setAppraisalMethod: (value: string) => void; onNegotiate: (event: React.FormEvent) => void; onAppraise: () => Promise<void>; chatEndRef: React.RefObject<HTMLDivElement | null>; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  const customer = state.active_customer;
  if (state.day_ended) {
    return (
      <div className="max-w-3xl mx-auto w-full flex-1 flex flex-col justify-center">
        <h1 className="text-[32px] font-bold text-[#C8A97E] mb-8">第 {state.day} 天 营业结算</h1>
        <SummaryLine label="期初资金" value={state.daily_summary.starting_cash} />
        <SummaryLine label="交易盈亏" value={state.daily_summary.revenue} delta />
        <SummaryLine label="员工薪水" value={-state.daily_summary.salaries} delta />
        <SummaryLine label="运营成本" value={-state.daily_summary.operating_cost} delta />
        <SummaryLine label="贷款利息" value={-state.daily_summary.loan_interest} delta />
        <SummaryLine label="营业税" value={-state.daily_summary.tax} delta />
        <SummaryLine label="净变化" value={state.daily_summary.net_profit} delta />
        <div className="my-8 space-y-3">{state.daily_summary.events.map((event, idx) => <p key={idx} className="border-l border-[#2A2D34] pl-4 text-[#9E9E9E]">{event}</p>)}</div>
        {state.pending_event && (
          <div className="border-y border-[#2A2D34] py-5 mb-6">
            <h2 className="text-[#C8A97E] text-xl font-bold mb-2">{state.pending_event.title}</h2>
            <p className="text-[#E0E0E0] mb-4">{state.pending_event.description}</p>
            <div className="space-y-2">{state.pending_event.choices.map((choice) => <button key={choice.id} onClick={() => onAction('/api/event/choice', { choice_id: choice.id }, 'event_result', '事件已处理。')} className="w-full text-left py-3 border-b border-[#2A2D34] hover:text-[#C8A97E]">{choice.label}<span className="block text-xs text-[#616161]">{choice.effect}</span></button>)}</div>
          </div>
        )}
        <button onClick={() => onAction('/api/next_day', undefined, 'result', '新的一天开始了。', 'cash')} disabled={loading || !!state.pending_event} className="btn-primary w-full md:w-auto">开启第 {state.day + 1} 天 <ArrowRight className="w-5 h-5 ml-2" /></button>
      </div>
    );
  }
  if (!customer) {
    return <div className="flex-1 flex flex-col items-center justify-center text-center"><Clock className="w-12 h-12 text-[#616161] mb-6" /><h1 className="text-[32px] font-bold mb-4">今日打烊</h1><button onClick={() => onAction('/api/end_day', undefined, 'summary', '结算完成。', 'deal')} disabled={loading} className="btn-primary">营业结算</button></div>;
  }
  const quickOffer = (ratio: number) => {
    const price = Math.max(1, Math.round(customer.current_offer * ratio));
    setMessage(customer.role === 'seller' ? `我出 ${price} 元，现金马上给你。` : `这件货 ${price} 元给你，附带来源说明。`);
  };
  const selectedAppraisal = state.appraisal_methods[appraisalMethod] || state.appraisal_methods.standard;
  const appraisalBaseCost = Math.max(120, Math.round(customer.item.market_value * 0.06));
  const appraisalDiscount = 0.08 * (state.facilities.appraisal_room - 1) + (state.staff.appraiser ? 0.35 : 0);
  const appraisalCost = Math.max(80, Math.round(appraisalBaseCost * selectedAppraisal.cost_multiplier * (1 - Math.min(0.65, appraisalDiscount))));
  const accuracyText = appraisalMethod === 'visual' ? '准确率较低' : appraisalMethod === 'forensic' ? '准确率最高' : '准确率均衡';
  const tradeMode = customer.role === 'seller'
    ? { label: '收购', tone: '你正在向顾客收购物品，报价越低利润空间越大。', priceLabel: '对方要价' }
    : { label: '出售', tone: '顾客想从你的库存买走这件物品，报价越高利润越大。', priceLabel: '对方出价' };
  return (
    <div className="max-w-3xl mx-auto w-full flex-1 flex flex-col">
      <div className="mb-6 border-y border-[#2A2D34] py-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 font-sans">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="text-[#C8A97E] text-sm tracking-[0.25em]">{tradeMode.label}</span>
              <span className="text-[#616161] text-xs">{customer.trait_cn} / 耐心 {customer.patience}</span>
            </div>
            <p className="text-[#9E9E9E] text-xs leading-relaxed">{customer.name} 走进店里，{customer.backstory}</p>
            <p className="text-[#616161] text-xs mt-1">{tradeMode.tone}</p>
          </div>
          <div className="text-left sm:text-right">
            <div className="text-xs text-[#616161]">{tradeMode.priceLabel}</div>
            <div className="text-[#C8A97E] text-[28px] font-bold leading-tight">${customer.current_offer.toLocaleString()}</div>
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto custom-scrollbar pr-3 space-y-5 pb-6">
        <Chat speaker={customer.name} avatarUrl={customer.avatar_url}>掌柜的，我今天带来【{customer.item.name}】。{customer.role === 'seller' ? '你给个价。' : '你打算卖多少钱？'}</Chat>
        {customer.dialogue_history.map((turn, idx) => (
          <Chat key={idx} speaker={turn.role === 'player' ? '你' : customer.name} right={turn.role === 'player'} avatarUrl={turn.role === 'customer' ? customer.avatar_url : undefined}>
            {turn.content}
          </Chat>
        ))}
        {negotiatingMsg && <div className="flex gap-2 text-[#616161]"><RefreshCw className="w-4 h-4 animate-spin" />{negotiatingMsg}</div>}
        <div ref={chatEndRef} />
      </div>
      <div className="border-t border-[#2A2D34] pt-4">
        <div className="flex gap-2 mb-3"><button onClick={() => quickOffer(0.85)} className="btn-secondary !h-8 !px-3 !text-xs">试探价</button><button onClick={() => quickOffer(1)} className="btn-secondary !h-8 !px-3 !text-xs">当前价</button><button onClick={() => quickOffer(1.12)} className="btn-secondary !h-8 !px-3 !text-xs">强势报价</button></div>
        <form onSubmit={onNegotiate} className="flex gap-3"><input value={message} onChange={(event) => setMessage(event.target.value)} className="input-field flex-1" style={{ paddingLeft: 16 }} placeholder="用自然语言谈判..." /><button disabled={loading} className="btn-primary">谈判</button></form>
        <div className="flex flex-col sm:flex-row gap-2 mt-3">
          <select value={appraisalMethod} onChange={(event) => setAppraisalMethod(event.target.value)} className="input-field !h-10 !px-3 sm:w-[150px]">
            {Object.entries(state.appraisal_methods).map(([key, info]) => <option key={key} value={key}>{info.name_cn}</option>)}
          </select>
          <button onClick={onAppraise} disabled={loading || appraising || customer.item.is_appraised_fake !== null} className="btn-secondary flex-1 !h-10">{appraising ? '鉴定中...' : customer.item.is_appraised_fake !== null ? '已鉴定' : '鉴定'}</button>
          <button onClick={() => onAction('/api/deal', undefined, 'deal_result', '成交。', 'deal')} className="btn-secondary flex-1 !h-10">成交</button>
          <button onClick={() => onAction('/api/reject', undefined, 'result', '已拒绝。', 'reject')} className="btn-secondary flex-1 !h-10">拒绝</button>
        </div>
        <p className="mt-2 text-xs text-[#616161] font-sans">
          {selectedAppraisal.name_cn}：预计 ${appraisalCost.toLocaleString()}，{accuracyText}。{selectedAppraisal.desc}
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

function InventoryTab({ state, listingPrice, repairMethod, showcasePrice, onAction, onClearShowcasePrice, onList, onSetShowcasePrice, setListingPrice, setRepairMethod, setShowcasePrice }: { state: GameState; listingPrice: Record<string, number>; repairMethod: Record<string, string>; showcasePrice: Record<string, number>; setListingPrice: (value: Record<string, number>) => void; setRepairMethod: (value: Record<string, string>) => void; setShowcasePrice: (value: Record<string, number>) => void; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void>; onList: (item: Item) => Promise<void>; onSetShowcasePrice: (item: Item) => Promise<void>; onClearShowcasePrice: (item: Item) => Promise<void> }) {
  const activeItems = state.inventory.filter((item) => item.status !== 'sold');
  const repairPreview = (item: Item) => {
    const method = state.repair_methods[repairMethod[item.id] || 'standard'] || state.repair_methods.standard;
    const nextCondition = item.condition === 'Poor' ? 'Good' : item.condition === 'Good' ? 'Mint' : item.condition;
    const multiplier = item.condition === 'Poor' ? 1.35 : item.condition === 'Good' ? 1.55 : 1;
    const nextValue = Math.round(item.market_value * multiplier);
    const baseCost = Math.max(60, Math.round(item.market_value * (0.08 + item.repair_difficulty * 0.015) * (1 - 0.05 * (state.facilities.restoration_workshop - 1) - 0.03 * (state.skills.restoration.level - 1))));
    const staffCost = state.staff.restorer ? Math.round(baseCost * 0.75) : baseCost;
    const cost = Math.max(30, Math.round(staffCost * method.cost_multiplier));
    const days = Math.max(1, item.repair_difficulty - Math.floor(state.facilities.restoration_workshop / 2) + method.days_delta);
    return { cost, days, method, nextCondition, nextValue };
  };
  return (
    <ListPage title="仓库藏品" subtitle={`当前库存 ${activeItems.length} 件，可展示、修复、出售或挂入玩家市场。`}>
      {activeItems.map((item) => (
        <div key={item.id} className="py-5 border-b border-[#2A2D34] flex flex-col xl:flex-row xl:items-center gap-4">
          <ItemText item={item} />
          <div className="xl:w-[460px] flex flex-wrap gap-2 justify-end">
            <input type="number" className="input-field !h-9 w-[130px]" style={{ paddingLeft: 12 }} value={listingPrice[item.id] ?? item.market_value} onChange={(event) => setListingPrice({ ...listingPrice, [item.id]: parseInt(event.target.value) || item.market_value })} />
            <button onClick={() => onList(item)} disabled={!['stored', 'displayed'].includes(item.status)} className="btn-secondary !h-9 !px-4">挂售</button>
            {item.status === 'displayed' ? <button onClick={() => onAction('/api/undisplay', { item_id: item.id }, 'display_result', '已下架。')} className="btn-secondary !h-9 !px-4">下架</button> : <button onClick={() => onAction('/api/display', { item_id: item.id }, 'display_result', '已展示。')} disabled={item.status !== 'stored'} className="btn-secondary !h-9 !px-4">展示</button>}
            {item.status === 'displayed' && <input type="number" className="input-field !h-9 w-[130px]" style={{ paddingLeft: 12 }} value={showcasePrice[item.id] ?? item.showcase_price ?? item.market_value} onChange={(event) => setShowcasePrice({ ...showcasePrice, [item.id]: parseInt(event.target.value) || item.market_value })} />}
            {item.status === 'displayed' && <button onClick={() => onSetShowcasePrice(item)} className="btn-secondary !h-9 !px-4">橱窗价</button>}
            {item.status === 'displayed' && item.showcase_price && <button onClick={() => onClearShowcasePrice(item)} className="btn-secondary !h-9 !px-4">取消价</button>}
            <select value={repairMethod[item.id] || 'standard'} onChange={(event) => setRepairMethod({ ...repairMethod, [item.id]: event.target.value })} disabled={item.condition === 'Mint' || item.status === 'repairing'} className="input-field !h-9 !px-3 w-[120px]"><option value="conservative">保守修复</option><option value="standard">标准修复</option><option value="premium">高阶修复</option></select>
            <button onClick={() => onAction('/api/repair', { item_id: item.id, method: repairMethod[item.id] || 'standard' }, 'repair_result', '已送修。', 'upgrade')} disabled={item.condition === 'Mint' || item.status === 'repairing'} className="btn-secondary !h-9 !px-4">修复</button>
            <button onClick={() => onAction('/api/sell', { item_id: item.id }, 'sell_result', '已出售。', 'cash')} disabled={item.status === 'repairing'} className="btn-primary !h-9 !px-4">系统出售</button>
            {item.status !== 'repairing' && item.condition !== 'Mint' && <div className="basis-full text-right text-xs text-[#616161]">修复成功：{CONDITION_MAP[item.condition] || item.condition} → {CONDITION_MAP[repairPreview(item).nextCondition] || repairPreview(item).nextCondition}，市场估值约 ${repairPreview(item).nextValue.toLocaleString()}，费用约 ${repairPreview(item).cost.toLocaleString()} / {repairPreview(item).days} 天</div>}
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
          <div className="flex gap-6 border-b border-[#2A2D34] lg:border-b-0">
            {(['browse', 'mine', 'trades'] as const).map((view) => <button key={view} onClick={() => setMarketView(view)} className={`pb-3 ${marketView === view ? 'text-[#C8A97E] border-b border-[#C8A97E]' : 'text-[#616161]'}`}>{view === 'browse' ? '全服市场' : view === 'mine' ? '我的摊位' : '交易记录'}</button>)}
          </div>
          <div className="flex gap-2 flex-1">
            <div className="relative flex-1"><Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#616161]" /><input value={marketSearch} onChange={(event) => setMarketSearch(event.target.value)} className="input-field w-full" placeholder="搜索物品..." /></div>
            <select value={marketSort} onChange={(event) => setMarketSort(event.target.value)} className="input-field !px-3"><option value="newest">最新</option><option value="price_asc">低价</option><option value="price_desc">高价</option><option value="value_gap">价值差</option></select>
            <button onClick={() => refresh()} className="btn-secondary !px-4">刷新</button>
          </div>
        </div>
      </div>
      {marketView === 'trades' ? trades.map((trade) => <div key={trade.id} className="py-4 border-b border-[#2A2D34] flex justify-between gap-4"><span>【{trade.item_name}】</span><span className="text-[#9E9E9E]">{trade.buyer_shop || '买家'} ↔ {trade.seller_shop || '卖家'}</span><span className="text-[#C8A97E]">${trade.price.toLocaleString()} / 税 ${trade.tax}</span></div>) : shown.map((listing) => (
        <div key={listing.id} className="py-5 border-b border-[#2A2D34] flex flex-col xl:flex-row xl:items-center gap-4">
          <ItemText item={listing.item} extra={listing.seller_online ? '卖家在线' : '卖家离线'} />
          <div className="xl:w-[300px] flex items-center justify-end gap-5">
            <button onClick={() => openShowcase(listing.seller_id)} className="text-[#9E9E9E] hover:text-[#C8A97E] text-sm text-right">{listing.seller_shop}<span className="block text-xs text-[#616161]">进店看橱窗</span></button>
            <div className="text-right"><div className="text-[#C8A97E] text-lg font-bold">${listing.price.toLocaleString()}</div><div className="text-xs text-[#616161]">参考 ${listing.reference_price.toLocaleString()}</div></div>
            {marketView === 'browse' ? <button onClick={() => buy(listing.id)} className="btn-primary !h-9 !px-4">购买</button> : <button onClick={() => onMarketAction('/api/market/unlist', { listing_id: listing.id }, 'market_result', '已下架。').then(refresh)} className="btn-secondary !h-9 !px-4">下架</button>}
          </div>
        </div>
      ))}
    </ListPage>
  );
}

function LeaderboardTab({ boardType, data, openShowcase, refresh, setBoardType }: { boardType: BoardType; setBoardType: (value: BoardType) => void; data: { entries: LeaderboardEntry[]; my_rank: LeaderboardEntry | null } | null; refresh: () => Promise<void>; openShowcase: (ownerId: number) => Promise<void> }) {
  return (
    <ListPage title="全服排行榜" subtitle="10 秒自动刷新，前 100 名获得每日声誉与稀有刷新奖励。">
      <div className="sticky top-0 bg-[#0D0F12]/95 backdrop-blur z-10 border-b border-[#2A2D34] mb-2 flex justify-between gap-4">
        <div className="flex gap-8 overflow-x-auto">
          {(Object.keys(BOARD_LABEL) as BoardType[]).map((type) => <button key={type} onClick={() => setBoardType(type)} className={`pb-3 whitespace-nowrap ${boardType === type ? 'text-[#C8A97E] border-b border-[#C8A97E]' : 'text-[#616161]'}`}>{BOARD_LABEL[type]}</button>)}
        </div>
        <button onClick={() => refresh()} className="text-[#9E9E9E] hover:text-[#C8A97E]"><RefreshCw className="w-4 h-4" /></button>
      </div>
      {(data?.entries || []).map((entry) => (
        <div key={entry.player_id} className={`py-4 border-b border-[#2A2D34] grid grid-cols-[60px_1fr_120px_100px_80px] gap-4 items-center ${entry.rank <= 3 ? 'text-[#C8A97E]' : ''}`}>
          <span className="text-xl font-bold">#{entry.rank}</span>
          <button onClick={() => openShowcase(entry.player_id)} className="truncate text-left hover:text-[#C8A97E]">{entry.badge ? `${entry.badge} · ` : ''}{entry.shop_name}</button>
          <span>${entry.assets.toLocaleString()}</span>
          <span>声誉 {entry.reputation}</span>
          <span className={entry.online ? 'text-[#4CAF50]' : 'text-[#616161]'}>{entry.online ? '在线' : '离线'}</span>
        </div>
      ))}
      {data?.my_rank && <div className="sticky bottom-0 mt-8 py-4 bg-[#0D0F12]/95 backdrop-blur border-t border-[#C8A97E] flex justify-between text-[#C8A97E]"><span>我的排名 #{data.my_rank.rank}</span><span>{data.my_rank.shop_name}</span><span>分数 {data.my_rank.score.toLocaleString()}</span></div>}
    </ListPage>
  );
}

function HistoryTab({ entries }: { entries: TransactionEntry[] }) {
  const shown = [...entries].reverse();
  const typeLabel: Record<string, string> = {
    buy: '收购物品',
    sell: '顾客购买',
    direct_sell: '系统出售',
    market_buy: '市场购入',
    market_sell: '市场售出',
    showcase_buy: '橱窗购入',
    showcase_sell: '橱窗售出'
  };
  const totalIn = entries.filter((entry) => entry.amount > 0).reduce((sum, entry) => sum + entry.amount, 0);
  const totalOut = entries.filter((entry) => entry.amount < 0).reduce((sum, entry) => sum + Math.abs(entry.amount), 0);
  return (
    <ListPage title="过往交易记录" subtitle={`保留最近 ${entries.length} 条经营流水，方便复盘收购、出售、市场和橱窗交易。`}>
      <div className="grid grid-cols-3 gap-4 border-b border-[#2A2D34] pb-5 mb-2 text-sm">
        <Stat label="交易数" value={entries.length} />
        <Stat label="总流入" value={`$${totalIn.toLocaleString()}`} />
        <Stat label="总流出" value={`$${totalOut.toLocaleString()}`} />
      </div>
      {shown.length === 0 ? (
        <div className="py-16 text-center text-[#616161]">还没有交易记录。完成收购或出售后，这里会留下流水。</div>
      ) : (
        shown.map((entry, index) => (
          <div key={`${entry.day}-${entry.type}-${entry.item}-${index}`} className="py-4 border-b border-[#2A2D34] grid grid-cols-[72px_1fr_110px] gap-4 items-center">
            <span className="text-[#616161] text-sm">第 {entry.day} 天</span>
            <div className="min-w-0">
              <div className="font-bold truncate">【{entry.item}】</div>
              <div className="text-xs text-[#9E9E9E]">{typeLabel[entry.type] || entry.type}</div>
            </div>
            <span className={`text-right font-sans font-bold ${entry.amount >= 0 ? 'text-[#4CAF50]' : 'text-[#F44336]'}`}>
              {entry.amount >= 0 ? '+' : '-'}${Math.abs(entry.amount).toLocaleString()}
            </span>
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
            <div className="xl:w-[260px] flex items-center justify-end gap-5">
              <div className="text-right">
                <div className="text-[#C8A97E] text-lg font-bold">{item.showcase_price ? `$${item.showcase_price.toLocaleString()}` : '非卖品'}</div>
                <div className="text-xs text-[#616161]">市场 ${item.market_value.toLocaleString()}</div>
              </div>
              {!showcase.owner.is_self && item.showcase_price && <button onClick={() => buy(showcase.owner.id, item.id)} className="btn-primary !h-9 !px-4">购买</button>}
            </div>
          </div>
        ))
      )}
    </ListPage>
  );
}

function ManagementTab({ loanAmount, onAction, setLoanAmount, state }: { state: GameState; loanAmount: number; setLoanAmount: (value: number) => void; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  return (
    <ListPage title="经营财务" subtitle="技能、贷款、税务和市场趋势共同影响长期竞争。">
      {Object.entries(state.skills).map(([key, skill]) => <div key={key} className="py-4 border-b border-[#2A2D34]"><div className="flex justify-between"><span>{state.skill_info[key]?.name_cn || key}</span><span className="text-[#C8A97E]">Lv.{skill.level}</span></div><div className="progress-bg mt-2"><div className="progress-fill" style={{ width: `${Math.min(100, (skill.xp / Math.max(100, skill.level * 100)) * 100)}%` }} /></div></div>)}
      <div className="py-6 border-b border-[#2A2D34] flex flex-wrap gap-3 items-center"><span>贷款本金 ${state.loan.principal.toLocaleString()}</span><input type="number" value={loanAmount} onChange={(event) => setLoanAmount(parseInt(event.target.value) || 100)} className="input-field !h-9 w-[150px]" style={{ paddingLeft: 12 }} /><button onClick={() => onAction('/api/loan/borrow', { amount: loanAmount }, 'loan_result', '贷款到账。', 'cash')} className="btn-primary !h-9">借款</button><button onClick={() => onAction('/api/loan/repay', { amount: loanAmount }, 'loan_result', '还款成功。', 'cash')} className="btn-secondary !h-9">还款</button></div>
      {Object.entries(state.market_trends).map(([category, trend]) => <div key={category} className="py-3 border-b border-[#2A2D34] flex justify-between"><span>{categoryLabel(category)}</span><span className="text-[#C8A97E]">{trend.toFixed(2)}x</span></div>)}
    </ListPage>
  );
}

function StaffTab({ onAction, state }: { state: GameState; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  return <ListPage title="员工管理" subtitle="专业人员会影响鉴定、修复、客流和安全。">{Object.entries(state.staff_info).map(([key, info]) => <div key={key} className="py-5 border-b border-[#2A2D34] flex justify-between gap-4"><div><h3 className="text-lg font-bold">{info.name_cn} {state.staff[key] && <span className="text-[#C8A97E] text-sm">在岗</span>}</h3><p className="text-[#9E9E9E] text-sm">{info.desc}</p><p className="text-[#616161] text-xs">签约 ${info.hire_cost} / 日薪 ${info.daily_salary}</p></div>{state.staff[key] ? <button onClick={() => onAction('/api/fire', { staff_type: key }, 'fire_result', '已解雇。', 'reject')} className="btn-secondary !h-9">解雇</button> : <button onClick={() => onAction('/api/hire', { staff_type: key }, 'hire_result', '雇佣成功。', 'upgrade')} className="btn-primary !h-9">雇佣</button>}</div>)}</ListPage>;
}

function UpgradesTab({ onAction, state }: { state: GameState; onAction: (path: string, body: unknown, resultKey: string, fallback: string, sound?: 'deal' | 'cash' | 'reject' | 'appraise' | 'click' | 'upgrade') => Promise<void> }) {
  return <ListPage title="当铺升级" subtitle="声望和设施等级共同决定经营上限。"><div className="py-5 border-b border-[#2A2D34] flex justify-between"><div><h3 className="text-xl font-bold">声望 Lv.{state.shop_level}</h3><p className="text-[#9E9E9E]">{state.shop_upgrade_desc || '已达到最高声望。'}</p></div>{state.shop_upgrade_cost && <button onClick={() => onAction('/api/upgrade', undefined, 'upgrade_result', '升级成功。', 'upgrade')} className="btn-primary !h-9">${state.shop_upgrade_cost.toLocaleString()}</button>}</div>{Object.entries(state.facility_info).map(([key, info]) => <div key={key} className="py-5 border-b border-[#2A2D34] flex justify-between gap-4"><div><h3 className="text-lg font-bold">{info.name_cn} Lv.{state.facilities[key]}</h3><p className="text-[#9E9E9E] text-sm">{info.desc}</p></div><button disabled={info.upgrade_cost === null} onClick={() => onAction('/api/upgrade_facility', { facility: key }, 'upgrade_result', '设施升级成功。', 'upgrade')} className="btn-secondary !h-9">{info.upgrade_cost ? `$${info.upgrade_cost.toLocaleString()}` : '满级'}</button></div>)}</ListPage>;
}

function InfoSidebar({ state }: { state: GameState }) {
  const customer = state.active_customer;
  return (
    <>
      <h3 className="text-[18px] font-bold text-[#C8A97E] mb-4 pb-2 border-b border-[#C8A97E] w-[50px]">资产</h3>
      <div className="space-y-3 text-sm mb-10"><Stat label="现金" value={`$${state.cash.toLocaleString()}`} /><Stat label="声誉" value={state.reputation} /><Stat label="盈利" value={`$${state.total_profit.toLocaleString()}`} /><Stat label="贷款" value={`$${state.loan.principal.toLocaleString()}`} /></div>
      {customer && <>
        <h3 className="text-[18px] font-bold text-[#C8A97E] mb-4 pb-2 border-b border-[#C8A97E] w-[50px]">顾客</h3>
        <div className="flex items-center gap-3 mb-4"><img src={customer.avatar_url} alt={customer.name} className="w-12 h-12 rounded-full bg-[#14171C] border border-[#2A2D34]" referrerPolicy="no-referrer" /><div><div className="font-bold">{customer.name}</div><div className="text-xs text-[#9E9E9E]">{customer.trait_cn} / 耐心 {customer.patience}</div></div></div>
        <div className="space-y-2 text-xs text-[#9E9E9E] mb-8">
          {customer.transaction_prefs?.slice(0, 2).map((pref, index) => <p key={`pref-${index}`}>偏好：{pref}</p>)}
          {customer.persuasion_points?.slice(0, 2).map((point, index) => <p key={`point-${index}`}>突破口：{point}</p>)}
        </div>
        <h3 className="text-[18px] font-bold text-[#C8A97E] mb-4 pb-2 border-b border-[#C8A97E] w-[50px]">物证</h3>
        <div className="space-y-3 text-sm"><div className="font-bold">{customer.item.name}</div><Stat label="年代" value={customer.item.era} /><Stat label="稀有度" value={customer.item.rarity_cn} /><Stat label="成色" value={CONDITION_MAP[customer.item.condition] || customer.item.condition} /><Stat label="市场估值" value={`$${customer.item.market_value.toLocaleString()}`} />{customer.item.appraised_value !== null && <Stat label="鉴定估值" value={`$${customer.item.appraised_value.toLocaleString()}`} />}{customer.item.is_appraised_fake !== null && <Stat label="鉴定结论" value={customer.item.is_appraised_fake ? '赝品' : '正品'} />}<p className="text-[#9E9E9E] text-xs leading-relaxed">{customer.item.story}</p><p className="text-[#9E9E9E] text-xs leading-relaxed">损坏：{customer.item.damage_report}</p>{customer.item.authentication_tips?.length > 0 && <div className="pt-3 border-t border-[#2A2D34] space-y-2">{customer.item.authentication_tips.map((tip, index) => <p key={index} className="text-[#9E9E9E] text-xs leading-relaxed">鉴别：{tip}</p>)}</div>}{customer.item.appraisal_notes.length > 0 && <div className="pt-3 border-t border-[#2A2D34] space-y-2">{customer.item.appraisal_notes.map((note, index) => <p key={index} className="text-[#9E9E9E] text-xs leading-relaxed">• {note}</p>)}</div>}</div>
      </>}
    </>
  );
}

function ItemText({ extra, item }: { item: Item; extra?: string }) {
  return <div className="flex-1 min-w-0"><div className="flex flex-wrap gap-3 items-center mb-1"><h3 className="text-lg font-bold truncate">{item.name}</h3><span className={RARITY_COLOR[item.rarity] || 'text-[#9E9E9E]'}>{item.rarity_cn}</span><span className="text-[#616161] text-sm">{STATUS_MAP[item.status]}</span><span className="text-[#C8A97E] text-sm">{CONDITION_MAP[item.condition] || item.condition}</span>{extra && <span className="text-[#9E9E9E] text-sm">{extra}</span>}{item.showcase_price && <span className="text-[#C8A97E] text-sm">橱窗 ${item.showcase_price.toLocaleString()}</span>}</div><p className="text-[#9E9E9E] text-sm leading-relaxed line-clamp-2">{item.story || item.description}</p><div className="flex flex-wrap gap-5 text-xs text-[#616161] mt-2"><span>{categoryLabel(item.category)}</span><span>{item.era}</span><span>市场 ${item.market_value.toLocaleString()}</span><span>鉴定 {item.is_appraised_fake === null ? '未知' : item.is_appraised_fake ? '赝品' : '正品'}</span></div>{(item.special_effects?.length > 0 || item.authentication_tips?.length > 0) && <div className="flex flex-wrap gap-3 text-xs text-[#9E9E9E] mt-2">{item.special_effects?.slice(0, 2).map((effect, index) => <span key={`effect-${index}`}>亮点：{effect}</span>)}{item.authentication_tips?.slice(0, 2).map((tip, index) => <span key={`tip-${index}`}>鉴别：{tip}</span>)}</div>}</div>;
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
