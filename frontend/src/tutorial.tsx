import React, { useEffect, useState } from 'react';
import {
  Award,
  BookOpen,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  Crown,
  GraduationCap,
  HandCoins,
  Landmark,
  Scale,
  Sparkles,
  Store,
  TrendingUp,
  Users,
  X
} from 'lucide-react';

const STORAGE_PREFIX = 'pawnshop-tutorial-seen-v1:';

export function isTutorialSeen(username: string): boolean {
  try {
    return localStorage.getItem(`${STORAGE_PREFIX}${username}`) === '1';
  } catch {
    return false;
  }
}

export function markTutorialSeen(username: string): void {
  try {
    localStorage.setItem(`${STORAGE_PREFIX}${username}`, '1');
  } catch {
    /* ignore */
  }
}

function Term({ children, title }: { title: string; children: React.ReactNode }) {
  return (
    <div className="py-4 border-b border-[#2A2D34] last:border-b-0">
      <h4 className="text-[#C8A97E] font-semibold text-sm font-sans mb-2">{title}</h4>
      <div className="text-[15px] leading-relaxed text-[#E0E0E0] font-serif space-y-2">{children}</div>
    </div>
  );
}

function Tip({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-sm text-[#9E9E9E] font-sans pl-3 border-l-2 border-[#C8A97E]/50 leading-relaxed mt-3">{children}</p>
  );
}

function Flow({ steps }: { steps: string[] }) {
  return (
    <ol className="space-y-2 mt-3 font-sans text-sm text-[#E0E0E0]">
      {steps.map((step, index) => (
        <li key={step} className="flex gap-3">
          <span className="text-[#C8A97E] font-semibold shrink-0 w-5">{index + 1}.</span>
          <span className="leading-relaxed">{step}</span>
        </li>
      ))}
    </ol>
  );
}

interface TutorialSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  tagline: string;
  body: React.ReactNode;
}

const SECTIONS: TutorialSection[] = [
  {
    id: 'welcome',
    title: '开局须知',
    icon: <Sparkles className="w-4 h-4" />,
    tagline: '你在经营什么、怎样算赢',
    body: (
      <>
        <p className="text-[17px] leading-relaxed mb-4">
          你是当铺掌柜。顾客带着货上门，或盯着你库里的藏品询价——你要在<strong className="text-[#C8A97E] font-sans">信息尽量充分</strong>
          的前提下低买高卖，扛住每日开销，把小店做成全服闻名的老字号。
        </p>
        <p className="text-[15px] leading-relaxed text-[#9E9E9E] font-sans">
          本作没有强制 Game Over，可以一直经营；进度用资产、声誉、累计盈利、成就与排行榜衡量。
        </p>
        <Tip>核心口诀：先看清货，再谈价；收购压价、出售抬价；贵货别盲收，赝品会吞利润。</Tip>
      </>
    )
  },
  {
    id: 'resources',
    title: '资金与声誉',
    icon: <HandCoins className="w-4 h-4" />,
    tagline: '顶栏与右侧栏最常看的数字',
    body: (
      <>
        <Term title="现金">
          你手头可支配的钱，成交、鉴定、修复、升级、发工资都从这里扣。顶栏「现金」即当前余额；开局约 <strong className="font-sans">$10,000</strong>。
        </Term>
        <Term title="声誉（声誉值）">
          当铺口碑，范围大致 0～200+。好评成交、识破骗局、完成成就等会提升；拒绝顾客、谈崩离场、收假货等会下降（常见 -1～-2）。
          声誉越高，越容易吸引优质客流与高端回头客，部分升级与排行榜也看这项。
        </Term>
        <Term title="盈利（累计盈利）">
          经营财务与排行榜里的「累计盈利」= 历史卖出收入减去收购等成本后的<strong className="font-sans">总账利润</strong>，不是当日现金增减。
          单笔利润 ≈ 卖出价 − 收购价 − 鉴定费 − 修复费 − 持有成本。
        </Term>
        <Term title="总资产">
          现金 + 库存市值（含展示中、修复中的货）。全服资产榜按此排名。
        </Term>
        <Term title="贷款本金">
          在「经营财务」借款后产生的未还本金；每日营业结算扣利息（约本金 × 2% 起，随经济指数浮动）。
          可随时部分或全额还款，还款额不超过本金。别把「本金」和「现金」混为一谈——本金是欠银行的钱。
        </Term>
        <Term title="经济 / 经济指数">
          宏观系数，约 0.72～1.85，每日微变。影响鉴定费、运营成本、贷款额度、估值与持有成本等。
          顶栏「经济 1.02x」即当前指数；压力标签（通胀 / 通缩 / 平稳）会写在经营财务页，并牵动市场叙事。
        </Term>
      </>
    )
  },
  {
    id: 'daily',
    title: '一天怎么过',
    icon: <Store className="w-4 h-4" />,
    tagline: '从开门到「开启下一天」',
    body: (
      <>
        <p className="text-[15px] leading-relaxed mb-2">
          每日客流 ≈ <span className="font-sans text-[#E0E0E0]">max(2, 2 + 当铺等级 + 店面等级÷2)</span>
          ，雇宣传员再 +1～2 人。顶栏「客流 2/5」表示已接待 2 人、今日共 5 人。
        </p>
        <Flow
          steps={[
            '大堂接待顾客 → 谈判 / 鉴定 → 成交或拒绝',
            '点「送离」叫下一位，直到今日队列清空',
            '点「营业结算」：工资、运营成本、持有费、贷款利息等入账',
            '若有随机事件，读完两个选项的效果再选',
            '点「开启第 N 天」进入明日（结算后不可再谈价）'
          ]}
        />
        <Tip>修复中的货在日终推进天数；完工信息出现在结算日志里。整理库存、挂市场宜在叫下一位顾客的空档完成。</Tip>
      </>
    )
  },
  {
    id: 'trade-modes',
    title: '收购与出售',
    icon: <Scale className="w-4 h-4" />,
    tagline: '同一套对话，目标相反',
    body: (
      <>
        <div className="overflow-x-auto font-sans text-sm mb-4">
          <table className="w-full text-left border-collapse min-w-[520px]">
            <thead>
              <tr className="text-[#616161] border-b border-[#2A2D34]">
                <th className="py-2 pr-4 font-medium"> </th>
                <th className="py-2 pr-4 font-medium text-[#C8A97E]">收购（对方卖货）</th>
                <th className="py-2 font-medium text-[#2196F3]">出售（对方买你的货）</th>
              </tr>
            </thead>
            <tbody className="text-[#E0E0E0]">
              <tr className="border-b border-[#2A2D34]/60">
                <td className="py-2 pr-4 text-[#9E9E9E]">你的钱</td>
                <td className="py-2 pr-4">流出（你付款）</td>
                <td className="py-2">流入（对方付款）</td>
              </tr>
              <tr className="border-b border-[#2A2D34]/60">
                <td className="py-2 pr-4 text-[#9E9E9E]">顶栏标签</td>
                <td className="py-2 pr-4">收购 · 对方要价</td>
                <td className="py-2">出售 · 对方出价</td>
              </tr>
              <tr className="border-b border-[#2A2D34]/60">
                <td className="py-2 pr-4 text-[#9E9E9E]">你的目标</td>
                <td className="py-2 pr-4">成交价越低越好</td>
                <td className="py-2">成交价越高越好</td>
              </tr>
              <tr>
                <td className="py-2 pr-4 text-[#9E9E9E]">成交后</td>
                <td className="py-2 pr-4">货进仓库</td>
                <td className="py-2">货出库，进已售记录</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="text-[15px] leading-relaxed">
          约六成顾客是<strong className="font-sans">卖家上门</strong>；其余为买家，前提是你仓库或展示柜里有可售货。买家优先盯展示柜里的货。
        </p>
        <Tip>顶栏大字价格 = 当前有效报价；点「成交」即按此价结算，与对话里最后一句不一定相同。</Tip>
      </>
    )
  },
  {
    id: 'negotiation',
    title: '谈判',
    icon: <Users className="w-4 h-4" />,
    tagline: '说话、报价与耐心',
    body: (
      <>
        <Term title="你可以说什么">
          支持自由输入：报价（「我出 5000」）、说服、追问来历、接受成交、拒绝。阿拉伯数字与「三千五」等中文数字均可识别。
          能否成交、新报价、耐心变化，全凭顾客心性与你的谈价火候；谈判、魅力技能会暗中助你一臂。
        </Term>
        <Term title="耐心">
          每位顾客有耐心条（约 5～7 起）。报价太离谱会扣耐心；聊得好可能回升。耐心 ≤ 0 时顾客直接离场（walk_out），本单失败，有时声誉 -1。
        </Term>
        <Term title="性格">
          强硬（难让步）、急切（易成交）、犹豫（需安抚）、欺诈（常带赝品）、专家（懂行、少忽悠）。右侧可见性格中文与描述。
        </Term>
        <Term title="快捷按钮">
          「试探价 / 当前价 / 强势报价」只拟好面谈措辞，须再点发送；收购侧偏压价，出售侧偏抬价。
        </Term>
        <Term title="大堂按钮">
          鉴定（本单货，付鉴定费）、成交（按顶栏价）、拒绝（顾客离开）、送离（本单已结束后叫下一位）。
        </Term>
      </>
    )
  },
  {
    id: 'appraisal',
    title: '鉴定',
    icon: <Briefcase className="w-4 h-4" />,
    tagline: '看清真伪与真实价值区间',
    body: (
      <>
        <p className="text-[15px] leading-relaxed mb-3">
          谈判中在大堂鉴定针对<strong className="font-sans">当前顾客带来的货</strong>；入库后在仓库鉴定，每件货<strong className="font-sans">只能鉴定一次</strong>。
        </p>
        <div className="font-sans text-sm space-y-2 mb-4 text-[#9E9E9E]">
          <p>
            <span className="text-[#E0E0E0]">目测初鉴</span> — 便宜、误差大；<span className="text-[#E0E0E0]">标准鉴定</span> — 日常；{' '}
            <span className="text-[#E0E0E0]">深度鉴定</span> — 贵、识破赝品率高。
          </p>
          <p>费用约 max(120, 市值×8%×经济指数×方法系数)，鉴定室与鉴定师可折扣。</p>
        </div>
        <Term title="鉴定结果怎么读">
          给出估值区间（围绕<strong className="font-sans">真实价值</strong>，不是围绕顾客叫价）、真伪结论与鉴定笔记。
          赝品被识破后，顾客情绪会变，收购时可趁机压价。
        </Term>
        <Term title="市值 vs 真实价值">
          <strong className="font-sans text-[#E0E0E0]">真实价值 actual_value</strong>：鉴定前不显示，决定货到底值多少钱。
          <strong className="font-sans text-[#E0E0E0]">市值 market_value</strong>：会随日子波动，用于持有成本与系统出售；赝品、行情会让市值与真值偏离。
        </Term>
        <Tip>不鉴定就收购 = 博彩；欺诈型顾客尤其要先鉴定。</Tip>
      </>
    )
  },
  {
    id: 'items',
    title: '物品术语',
    icon: <Crown className="w-4 h-4" />,
    tagline: '稀有度、成色与分类',
    body: (
      <>
        <Term title="稀有度">
          普通 / 稀有 / 史诗 / 传奇 — 影响价值倍率、持有成本、系统出售加成（稀有 +6%、史诗 +12%、传奇 +20%）及收藏榜权重。
          颜色在物品名旁区分：灰、蓝、紫、橙。
        </Term>
        <Term title="成色">
          <strong className="font-sans">较差（Poor）</strong>：价低，修复潜力大；<strong className="font-sans">良好（Good）</strong>：中间档；{' '}
          <strong className="font-sans">完好（Mint）</strong>：最高档，<strong className="font-sans">不可再修复</strong>。
          修复成功会升一级（Poor→Good→Mint），真值与市值跳涨。
        </Term>
        <Term title="分类与市场趋势">
          流行文化、艺术、珠宝钟表、古董、历史遗物 — 各类有独立「市场趋势」系数，每日刷新，影响新货估值与库存日终涨跌。
        </Term>
        <Term title="物品状态">
          在库、展示中、修复中、已售、玩家市场挂单 — 修复中不能卖不能展示；挂单后货在全服市场，不在本地仓库列表。
        </Term>
        <Term title="持有成本">
          每件在库/展示/修复中的货，日终按市值与稀有度扣现金；展示中略高。长期囤贵货要算：涨价期望 vs 每日持有费。
        </Term>
      </>
    )
  },
  {
    id: 'inventory',
    title: '仓库·修复·展示',
    icon: <TrendingUp className="w-4 h-4" />,
    tagline: '收到货之后怎么办',
    body: (
      <>
        <Term title="修复">
          非 Mint 且未在修的可选方案（保守 / 标准 / 高阶），付修理费后进入修复中，日终推进天数；成功升成色，失败真值约 -8%。
          修复工坊、修复师、修复技能影响费用与成功率。
        </Term>
        <Term title="展示柜">
          容量 = 2 + 展示柜等级×2。展示中的货：市值额外正向漂移；系统出售有加成；更容易被上门买家选中。可设「橱窗售价」供他人参观购买。
        </Term>
        <Term title="出货渠道">
          ① 系统出售（即时，价≈市值×系数+技能+展示+稀有加成）② 等上门买家谈判 ③ 赌持有涨跌 ④ 玩家市场挂单（成交扣 5% 税）。
        </Term>
        <Tip>现金流紧时用系统出售清仓；想博高价可展示等买家，但占展示位且要会抬价。</Tip>
      </>
    )
  },
  {
    id: 'customers',
    title: '顾客与回头客',
    icon: <Users className="w-4 h-4" />,
    tagline: '关系、熟客与引荐',
    body: (
      <>
        <Term title="回头客">
          满意的老客有概率再次进店，带着「熟客 · 第 N 次」与上次成交摘要，通常更好说话。顶栏与对话区会标明是否回头客。
        </Term>
        <Term title="关系等级">
          由满意度与来访次数决定：新客 → 熟客 → 忠实 → 贵宾（耐心与让步更好）；满意度过低会变成「关系紧张」。
          成交约 +12～14 满意，拒绝约 -8，谈崩约 -14。
        </Term>
        <Term title="引荐">
          忠实 / 贵宾可能引荐新面孔，带推荐关系，利于声誉与成就。
        </Term>
        <Term title="图鉴">
          「经营图鉴」记录见过的顾客与物品，纯收集向，与成就统计联动。
        </Term>
        <Term title="镜影（彩蛋）">
          据说偶尔会有来客报的名字与<strong className="font-sans">你的账号一字不差</strong>，谈价口吻还像许多年前的自己。
          多在积累一定谈判话术之后、隔若干日才可能遇见；对话区会标「镜影」。与镜中人完成一次交涉可解锁隐藏成就。
        </Term>
      </>
    )
  },
  {
    id: 'upgrades',
    title: '技能·设施·员工',
    icon: <Crown className="w-4 h-4" />,
    tagline: '宣传员、店面与其它投资',
    body: (
      <>
        <div className="grid gap-0 font-sans text-sm">
          <Term title="五项技能（1～10 级）">
            谈判（价区间与成交）、鉴定（识破与误差）、修复（费用与成功率）、魅力（耐心与回头客概率）、商业（运营成本与系统出售价）。
            通过日常经营攒经验升级。
          </Term>
          <Term title="店面（设施）">
            提高每日客流与高稀有度物品出现率；与当铺等级一起决定顶栏「客流」上限。在「当铺升级」页与其它设施一并升级。
          </Term>
          <Term title="宣传员（员工）">
            雇佣费 $600、日薪 $80：每日额外 +1～2 位顾客，提高稀有货权重与老顾客引荐概率。在「员工管理」雇佣，可解雇。
          </Term>
          <Term title="其它设施">
            展示柜（容量与售价）、安全系统（降事件损失）、鉴定室（降鉴定费）、修复工坊（降修理费）。升级费随等级递增，高等级需达到最低经营天数。
          </Term>
          <Term title="其它员工">
            鉴定师、修复师、保安 — 分别强化鉴定、修复与日终安全类事件。
          </Term>
        </div>
      </>
    )
  },
  {
    id: 'economy',
    title: '经济与成本',
    icon: <TrendingUp className="w-4 h-4" />,
    tagline: '营业结算里每一项是什么',
    body: (
      <>
        <Term title="日终账单">
          员工工资（日薪×经济指数）、运营成本（租金水电等，商业技能可减）、贷款利息、每 7 天一次的营业税（按当日现金增值部分计）、库存持有成本。
        </Term>
        <Term title="随机事件">
          约六成营业结算后出现；连续两天无事件则第三天必出。读清两个选项的「效果摘要」再选（现金、声誉、技能、收进仓库等）。
        </Term>
        <Term title="当铺等级">
          Lv.1～8，升级解锁更好客流与货色；费用与最低经营天数见「当铺升级」页，费用受经济指数影响。
        </Term>
        <Tip>前期勿盲目贷款囤满货；先稳几笔交易，优先鉴定室或商业技能。</Tip>
      </>
    )
  },
  {
    id: 'online',
    title: '成就·市场·排行',
    icon: <Landmark className="w-4 h-4" />,
    tagline: '全服玩法与长期目标',
    body: (
      <>
        <Term title="成就">
          「经营成就」追踪现金里程碑、利润、交易次数、声誉、经营天数、传奇收藏、识破骗局、设施等级、回头客交易等；达成常奖现金、声誉或技能经验。
        </Term>
        <Term title="玩家市场">
          仓库挂售，标价须在参考价 30%～300%；他人购买你收成交价扣 5% 税。从市场买来的货 24 小时内不能再挂（防刷）。
        </Term>
        <Term title="全服排行">
          资产榜（现金+库存市值）、声誉榜、利润榜、收藏榜（稀有度加权）。前 100 名有每日声誉等奖励；可参观他人展示柜购买已标价展品。
        </Term>
      </>
    )
  },
  {
    id: 'first-day',
    title: '第一天建议',
    icon: <BookOpen className="w-4 h-4" />,
    tagline: '开铺头几单的实操顺序',
    body: (
      <>
        <Flow
          steps={[
            '进「大堂柜台」：看收购/出售标签与顶栏报价',
            '卖家上门：先鉴定或问来历，再试探压价，满意后成交',
            '买家上门：尽量抬价，成交后货出库、现金增加',
            '送离顾客直到今日队列空 → 营业结算 → 处理事件 → 下一天',
            '到「仓库藏品」看新货：贵的可鉴定/展示；Poor/Good 可考虑修复',
            '有闲钱再去「当铺升级」「员工管理」投资店面或宣传员'
          ]}
        />
        <p className="mt-6 text-[15px] leading-relaxed text-[#9E9E9E] font-sans">
          随时点顶栏「学士帽」图标重新打开本教程。祝掌柜生意兴隆。
        </p>
      </>
    )
  }
];

export function TutorialPanel({
  open,
  onClose,
  username,
  markSeenOnClose = true
}: {
  open: boolean;
  onClose: () => void;
  username: string;
  markSeenOnClose?: boolean;
}) {
  const [activeId, setActiveId] = useState(SECTIONS[0].id);

  useEffect(() => {
    if (open) setActiveId(SECTIONS[0].id);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') handleClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const handleClose = () => {
    if (markSeenOnClose) markTutorialSeen(username);
    onClose();
  };

  const activeIndex = SECTIONS.findIndex((section) => section.id === activeId);
  const active = SECTIONS[activeIndex >= 0 ? activeIndex : 0];

  const goPrev = () => {
    if (activeIndex > 0) setActiveId(SECTIONS[activeIndex - 1].id);
  };
  const goNext = () => {
    if (activeIndex < SECTIONS.length - 1) setActiveId(SECTIONS[activeIndex + 1].id);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[90] flex items-end md:items-center justify-center bg-[rgba(0,0,0,0.78)] backdrop-blur-sm p-0 md:p-6"
      role="dialog"
      aria-modal
      aria-labelledby="tutorial-title"
      onClick={handleClose}
    >
      <div
        className="tutorial-panel w-full md:max-w-5xl h-[94vh] md:h-[min(88vh,820px)] flex flex-col bg-[#0D0F12] border-t md:border border-[#2A2D34] md:rounded-sm shadow-2xl animate-slide-up overflow-hidden"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="shrink-0 flex items-center justify-between gap-4 px-4 md:px-6 py-4 border-b border-[#2A2D34] bg-[#14171C]/60">
          <div className="flex items-center gap-3 min-w-0">
            <GraduationCap className="w-6 h-6 text-[#C8A97E] shrink-0" />
            <div className="min-w-0">
              <h2 id="tutorial-title" className="text-lg md:text-xl font-bold text-[#C8A97E] font-sans truncate">
                掌柜入门手册
              </h2>
              <p className="text-xs text-[#616161] font-sans truncate">机制与专有术语说明 · 可随时查阅</p>
            </div>
          </div>
          <button type="button" onClick={handleClose} className="btn-icon shrink-0" aria-label="关闭教程">
            <X className="w-5 h-5" />
          </button>
        </header>

        <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
          <nav
            className="shrink-0 md:w-[220px] lg:w-[240px] border-b md:border-b-0 md:border-r border-[#2A2D34] bg-[#14171C] overflow-x-auto md:overflow-y-auto custom-scrollbar flex md:flex-col"
            aria-label="教程目录"
          >
            {SECTIONS.map((section) => (
              <button
                key={section.id}
                type="button"
                onClick={() => setActiveId(section.id)}
                className={`tutorial-nav-item shrink-0 md:shrink md:w-full text-left px-4 py-3 md:py-3.5 font-sans transition-colors border-l-[3px] ${
                  activeId === section.id
                    ? 'border-[#C8A97E] text-[#C8A97E] bg-[rgba(200,169,126,0.1)]'
                    : 'border-transparent text-[#9E9E9E] hover:text-[#C8A97E] hover:bg-[rgba(200,169,126,0.05)]'
                }`}
              >
                <span className="flex items-center gap-2 text-sm font-medium whitespace-nowrap md:whitespace-normal">
                  {section.icon}
                  {section.title}
                </span>
                <span className="hidden md:block text-[11px] text-[#616161] mt-0.5 leading-snug">{section.tagline}</span>
              </button>
            ))}
          </nav>

          <article className="flex-1 flex flex-col min-h-0 min-w-0">
            <div className="shrink-0 px-5 md:px-8 pt-5 pb-3 border-b border-[#2A2D34]/80">
              <div className="flex items-center gap-2 text-[#C8A97E] font-sans text-xs mb-1">
                {active.icon}
                <span>
                  {activeIndex + 1} / {SECTIONS.length}
                </span>
              </div>
              <h3 className="text-2xl font-bold text-[#E0E0E0] font-sans">{active.title}</h3>
              <p className="text-sm text-[#9E9E9E] font-sans mt-1">{active.tagline}</p>
              <div className="w-[50px] h-px bg-[#C8A97E] mt-3" />
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar px-5 md:px-8 py-5 md:py-6">{active.body}</div>

            <footer className="shrink-0 flex items-center justify-between gap-3 px-4 md:px-6 py-4 border-t border-[#2A2D34] bg-[#14171C]/40 font-sans">
              <button
                type="button"
                onClick={goPrev}
                disabled={activeIndex <= 0}
                className="btn-secondary !h-10 !px-4 !text-sm disabled:opacity-40"
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                上一章
              </button>
              <span className="text-xs text-[#616161] hidden sm:inline">{active.title}</span>
              {activeIndex < SECTIONS.length - 1 ? (
                <button type="button" onClick={goNext} className="btn-primary !h-10 !px-4 !text-sm">
                  下一章
                  <ChevronRight className="w-4 h-4 ml-1" />
                </button>
              ) : (
                <button type="button" onClick={handleClose} className="btn-primary !h-10 !px-5 !text-sm">
                  <Award className="w-4 h-4 mr-1.5" />
                  开始营业
                </button>
              )}
            </footer>
          </article>
        </div>
      </div>
    </div>
  );
}

export function TutorialHelpButton({ onClick, className = '' }: { onClick: () => void; className?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`btn-icon !w-9 !h-9 ${className}`}
      title="掌柜入门手册"
      aria-label="打开新手教程"
    >
      <GraduationCap className="w-4 h-4" />
    </button>
  );
}
