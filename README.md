# 当铺代理人（AI 当铺人生）

《当铺代理人》是一款**模拟经营类纯文字网页游戏**。玩家扮演当铺掌柜，通过接待顾客、鉴定物品、讨价还价、修复转卖、升级店铺，在 AI 与规则引擎共同驱动的经济系统中积累财富与声誉。

本作在保留《当铺人生》式核心经济循环的同时，将**物品、顾客、对话、谈判、鉴定/修复叙事、随机事件**尽可能交给大模型实时生成；未配置 AI 或接口超时时，由本地模板与算法兜底，保证可完整游玩。

---

## 目录

- [核心特色](#核心特色)
- [技术栈与项目结构](#技术栈与项目结构)
- [快速开始](#快速开始)
- [游戏流程](#游戏流程)
- [顾客与谈判](#顾客与谈判)
- [物品、鉴定与修复](#物品鉴定与修复)
- [经济与每日结算](#经济与每日结算)
- [技能、设施与员工](#技能设施与员工)
- [随机事件](#随机事件)
- [联机功能](#联机功能)
- [成就与图鉴](#成就与图鉴)
- [AI 配置与兜底策略](#ai-配置与兜底策略)
- [API 一览](#api-一览)
- [界面设计](#界面设计)
- [开发与扩展](#开发与扩展)

---

## 核心特色

| 能力 | 说明 |
|------|------|
| 纯文字经营 | 对话、旁白、物品故事是主体验；UI 负责氛围与操作引导 |
| AI 无限内容 | 顾客人设、物品细节、谈判台词、事件分支、鉴定/修复说明可由模型生成 |
| 双角色顾客 | 既有**卖家上门**（你收购），也有**买家上门**（你出售库存） |
| 自然语言谈判 | 支持自由输入；后端解析意图与报价，AI 生成回应，规则引擎裁决成交 |
| 流式谈判 | 前端默认走 `/api/negotiate/stream`，逐字显示顾客回复 |
| 完整物品链路 | 收购 → 鉴定 → 修复 → 展示 → 系统出售 / 卖给上门买家 / 挂玩家市场 |
| 宏观经济 | 经济指数、通胀压力、分类市场趋势、库存持有成本与时间价值 |
| 顾客关系 | 回头客、满意度、关系等级、引荐与图鉴记录 |
| 云端存档 | 注册登录后 SQLite 持久化；支持导入导出与重开 |
| 玩家市场 | 全服挂单买卖、橱窗参观、交易税与排行榜 |
| 成就系统 | 经营、交易、声誉、收藏、技能等多类成就与奖励 |
| 离线可玩 | 无 API Key 时使用 `ITEM_TEMPLATES`、本地顾客与 12 类兜底事件 |

---

## 技术栈与项目结构

```
当铺代理人/
├── backend/                 # FastAPI 后端
│   ├── app.py               # HTTP 路由、谈判结算、CORS
│   ├── game_state.py        # 核心游戏规则与状态机（约 2700 行）
│   ├── ai_client.py         # 豆包/火山方舟 API 封装
│   ├── online_services.py   # 存档、市场、排行榜、橱窗交易
│   ├── auth.py              # 注册/登录/Token 鉴权
│   ├── database.py          # SQLite 表结构
│   ├── env_loader.py        # 加载 .env
│   └── requirements.txt
├── frontend/                # React 19 + Vite 8 + Tailwind CSS 4
│   └── src/
│       ├── App.tsx          # 单页应用：大厅、仓库、市场、排行等
│       ├── index.css        # 暗黑奢华风全局样式
│       └── main.tsx
├── test_extract.py          # 报价数字提取测试
└── README.md
```

| 层级 | 技术 |
|------|------|
| 前端 | React 19、TypeScript、Vite 8、Tailwind CSS 4、Lucide 图标 |
| 后端 | Python 3、FastAPI、Uvicorn、httpx、Pydantic |
| 数据 | SQLite（`pawnshop_online.db`，可通过环境变量改路径） |
| AI | 火山方舟兼容 Chat Completions（豆包） |

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 1. 配置环境变量

在项目根目录或 `backend/` 下创建 `.env`：

```env
# 必填：启用 AI 生成（不填则全程本地兜底）
DOUBAO_API_KEY=你的_API_Key

# 可选
DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DOUBAO_MODEL_ENDPOINT=你的模型_endpoint

# 可选：数据库路径、CORS
PAWNSHOP_DB_PATH=backend/pawnshop_online.db
CORS_ALLOWED_ORIGINS=http://localhost:5173,https://game.lvxy.cc
```

前端可选（`frontend/.env`）：

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

默认监听 `http://127.0.0.1:8000`，启动时自动 `init_db()`。

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://localhost:5173`，注册账号并创建当铺名称即可开局。

### 4. 生产构建

```bash
cd frontend && npm run build
# 将 dist/ 静态资源部署到 CDN 或 Nginx，并保证 API 指向后端
```

---

## 游戏流程

### 每日节奏

1. **开门**：`async_initialize_day` 生成当日顾客队列（人数随店面等级、宣传员等变化，基础约 3 人起）。
2. **接待**：从队列取出 `active_customer`，在大堂柜台谈判、鉴定、成交或拒绝。
3. **换下一位**：成交、拒绝或送离后 `select_next_customer`。
4. **日终结算**：`POST /api/end_day` → 扣运营成本、工资、贷款利息、税费；库存持有成本与估值波动；修复完工；可能生成随机事件。
5. **处理事件**：若有 `pending_event`，在结算界面选择分支后再进入下一天。
6. **下一天**：`POST /api/next_day` → 天数 +1，重新生成顾客队列。

### 前端主要页面（左侧导航 / 移动端底栏）

| 页面 | 功能 |
|------|------|
| 大堂柜台 | 当前顾客谈判、鉴定、成交、拒绝、快捷报价 |
| 仓库藏品 | 库存鉴定、展示、修复、系统出售、挂玩家市场 |
| 玩家市场 | 浏览全服挂单、我的摊位、交易记录 |
| 全服排行 | 资产/声誉/利润/收藏榜，参观他人橱窗 |
| 经营成就 | 成就进度与解锁奖励 |
| 经营图鉴 | 遇见过顾客与物品的 codex |
| 交易记录 | 最近 120 条单机流水 |
| 经营财务 | 技能、贷款、税务、市场趋势 |
| 员工管理 | 雇佣/解雇四类员工 |
| 当铺升级 | 店铺等级与五项设施升级 |

---

## 顾客与谈判

### 顾客角色（`role`）

| 角色 | 含义 | 你的目标 | 顶栏价格标签 |
|------|------|----------|--------------|
| `seller` | 带货上门出售 | 压低收购价 | 对方要价 |
| `buyer` | 来店购买库存 | 抬高出售价 | 对方出价 |

约 **45%** 概率生成买家（需库存有可售物品）。每日生成后会执行 `_rebalance_buyer_targets`，将买家目标重新分配到不同库存件，避免多人争抢同一件；**换目标后会同步重写开场白**（玩家尚未发言时），保证顶部摘要与对话一致。

### 性格（`trait`）

| ID | 中文 | 行为倾向 |
|----|------|----------|
| `hardball` | 强硬 | 底线高，让步慢 |
| `eager` | 急切 | 易让步，偏快速成交 |
| `hesitant` | 犹豫 | 需说服，耐心消耗敏感 |
| `fraud` | 欺诈 | 可能售赝品或隐瞒缺陷 |
| `expert` | 专家 | 对价值与真伪敏感 |

### 关系系统

- `customer_registry` 记录每位顾客的访问次数、满意度、关系等级（新客 / 熟客 / 忠实 / 贵宾 / 关系紧张）。
- 每日队列中会注入回头客与引荐客（`_inject_relationship_customers`）。
- 关系影响耐心、报价区间与谈判文案上下文。

### 谈判流程

1. 玩家输入自然语言（可选附带 `player_offer` 数字）。
2. `ai_client.parse_player_negotiation` 解析 **意图**（`question` / `persuade` / `offer` / `accept` / `reject`）与报价。
3. **规则引擎**（`sanitize_negotiation_result`）根据角色、技能、底线计算 `new_offer`、`accepted`、`walk_out`。
4. **AI** 生成顾客台词；流式接口先流式输出台词，再 `apply_negotiation_outcome` 写回状态。
5. 旁白提示：
   - 报价变化：按涨跌显示「对方将要价/出价 **降至/抬至** $X」（比较 `previous_offer` 与 `new_offer`）。
   - 耐心变化：单独旁白提示。

快捷按钮（试探价 / 当前价 / 强势报价）在前端生成话术填入输入框，逻辑随收购/出售角色区分。

### 成交与离开

- `POST /api/deal`：按当前 `current_offer` 成交。
- `POST /api/reject`：拒绝交易，AI 可生成告别语，可能影响声誉。
- `POST /api/dismiss_customer`：送离已结束会话的顾客。

---

## 物品、鉴定与修复

### 物品分类（`ITEM_TEMPLATES`）

- `Pop Culture` 流行文化
- `Art` 艺术
- `Jewelry` 珠宝钟表
- `Antiquities` 古董
- `Historical` 历史遗物

### 稀有度

| 等级 | 中文 | 价值系数（约） |
|------|------|----------------|
| `common` | 普通 | ×1.0 |
| `rare` | 稀有 | ×1.6 |
| `epic` | 史诗 | ×2.6 |
| `legendary` | 传奇 | ×4.2 |

### 成色

`Poor` → `Good` → `Mint`，影响估值系数与修复后升级路径。

### 物品状态（`status`）

| 状态 | 说明 |
|------|------|
| `stored` | 在库 |
| `displayed` | 展示柜中（有容量上限） |
| `repairing` | 修复中（按天推进） |
| `sold` | 已售出（进入 `sold_items` 历史） |

每件物品含 `market_value`（可见波动）、`actual_value`（真实价值）、`is_fake`、故事、修复难度、鉴定结果、持有成本历史等字段。

### 鉴定

**上门顾客物品**（谈判中）：`POST /api/appraise`，方法：

| 方法 | 中文 | 特点 |
|------|------|------|
| `visual` | 目测初鉴 | 便宜、误差大 |
| `standard` | 标准鉴定 | 均衡 |
| `forensic` | 深度鉴定 | 贵、识破赝品率高 |

**库存物品**：`POST /api/appraise_inventory`，逻辑类似。鉴定消耗现金，产出估值区间、真伪判断、AI 鉴定笔记；卖家顾客可生成 AI 鉴定反应。

### 修复

`POST /api/repair`，方法：`conservative` / `standard` / `premium`。修复占用天数，日终 `_process_repairs` 结算；成功提升成色与价值，失败可能贬值。AI 可生成修复说明（`generate_repair_notes`）。

### 出售渠道

| 方式 | API | 说明 |
|------|-----|------|
| 系统渠道出售 | `/api/sell` | 按市值、商业技能、展示状态、稀有度随机系数 instant sell |
| 卖给上门买家 | `/api/deal`（buyer） | 谈判价成交 |
| 玩家市场挂单 | `/api/market/list` | 全服可见，成交扣 5% 税 |
| 他人橱窗 | `/api/showcase/buy` | 参观排行玩家展示柜标价购买 |

---

## 经济与每日结算

### 初始与压力

- 初始现金：**$10,000**
- 当铺等级 **1–5**（升级费用与描述见 `SHOP_UPGRADE_COSTS`）
- 经济指数 `economy_index`（约 0.72–1.85）影响成本、贷款额度、估值
- 分类 `market_trends` 每日刷新
- 库存**持有成本**与**时间价值**在日终 `_apply_inventory_value_tick` 结算

### 日终扣费（`end_day`）

- 员工工资（四类，按 `economy_index` 缩放）
- 运营成本（租金/水电等，受商业技能减免）
- 贷款利息（动态利率）
- 营业税（每 7 天，按当日现金增值部分比例）
- 库存持有成本

### 贷款

- `POST /api/loan/borrow`、`/api/loan/repay`
- 可贷额度随店铺等级与经济指数变化

### 税费

- `tax.next_due_day` 控制下次缴税日，税率约 8% 起，随经济指数微调

---

## 技能、设施与员工

### 技能（最高 10 级，升级需经验）

| 技能 | 效果 |
|------|------|
| 谈判 | 改善让步与成交判定 |
| 鉴定 | 提高准确度、降低误差 |
| 修复 | 降本增效 |
| 魅力 | 顾客耐心、关系 |
| 商业 | 运营成本、出售收益 |

### 设施（各 1 级起，可升级）

| 设施 | 效果 |
|------|------|
| 展示柜 | 容量 `2 + level×2`，提高展示售价 |
| 安全系统 | 降低事件损失 |
| 鉴定室 | 降鉴定费、提质量 |
| 修复工坊 | 降修复费、提成功率 |
| 店面 | 客流与稀有度 |

### 员工

| 类型 | 中文 | 作用 |
|------|------|------|
| `appraiser` | 鉴定师 | 鉴定折扣与准确 |
| `restorer` | 修复师 | 推进修复、降失败 |
| `marketer` | 宣传员 | 客流与顾客质量 |
| `guard` | 保安 | 安全事件减损 |

`POST /api/hire`、`/api/fire`

---

## 随机事件

- 日终 **约 62%** 概率触发（`EVENT_BASE_CHANCE`）；连续无事件天数达到阈值则**保底**触发。
- 先写入本地模板事件（12 类：盗窃、诈骗、名人、市场、法律、员工、稀有线索、修复、鉴定、银行、老客、天气等），结构化 `choices` 与 `outcome`。
- 若 AI 可用，`async_end_day` 尝试用 AI 事件**替换**本地事件（保留双选项与数值后果字段）。
- 选择 `POST /api/event/choice` 后应用现金/声誉/技能/市场等后果；部分选项可 `acquire_item` 收进仓库。

---

## 联机功能

基于 SQLite 的轻量联机（非实时对战）：

| 功能 | 说明 |
|------|------|
| 账号 | 用户名 + 密码（PBKDF2），Token 鉴权 |
| 云存档 | `game_saves.state_json` 存完整 `GameStateManager` |
| 玩家市场 | 挂单、改价、下架、购买；税率 **5%** |
| 交易记录 | `trade_logs`，类型含 `sale`、`showcase_sale` |
| 排行榜 | 资产 / 声誉 / 利润 / 收藏；每日快照发奖励 |
| 橱窗 | 展示他人 `displayed` 物品，设置 `showcase_price` 后可被购买 |
| 重开 | `/api/restart` 重置进度（保留账号） |

市场挂单上限：`min(30, 5 + (shop_level-1)×6.25)`。同一物品市场交易后有 **24 小时**冷却（`TRADE_COOLDOWN_SECONDS`），防止频繁刷流转。

---

## 成就与图鉴

- **成就**：`ACHIEVEMENT_DEFS` 定义数十项（现金、利润、交易次数、声誉、天数、传奇收藏、鉴定识破、修复、技能、设施、回头客等），达成发放现金/声誉/技能经验。
- **顾客图鉴** `customer_codex`：记录遇见的顾客与关系。
- **物品图鉴** `item_codex`：记录遇见或交易过的物品。

---

## AI 配置与兜底策略

### 调用场景

| 场景 | 方法 |
|------|------|
| 每日顾客队列 | `generate_random_customer_async` + 并行 gather |
| 顾客人设 | `generate_customer_profile` |
| 开场白 | `generate_customer_greeting` |
| 谈判 | `generate_negotiation` / `stream_negotiation_dialogue` |
| 鉴定/修复/拒绝告别 | 对应 `generate_*` |
| 随机事件 | `generate_random_event` |
| 深度物品 | `generate_deep_item` / `generate_item_details` |

### 超时与兜底

- 每日 AI 预生成最长等待 **30 秒**（`AI_DAY_GENERATION_TIMEOUT`）。
- 超时或无 Key → `initialize_day_fast` 本地顾客。
- 谈判：先算规则结果，AI 仅负责台词；AI 失败则用 `_calculate_algorithmic_fallback` 台词。
- 流式谈判：规则先定稿，再流式生成对话；无流则按字切块回放 fallback 台词。

### 报价解析

`ai_client` 与前端共用类似正则，从「出/给/卖/要/报价…」后提取数字（支持千分位逗号）。

---

## API 一览

除健康检查外，业务接口均在 `/api` 下，需登录的接口在 Header 携带：

```
Authorization: Bearer <token>
```

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册（username, password, shop_name） |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 登出 |
| GET | `/api/auth/me` | 当前玩家 |
| DELETE | `/api/auth/account` | 删除账号 |

### 存档

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/state` | 获取游戏状态 |
| GET/POST | `/api/cloud/state` | 云存档读写 |
| POST | `/api/cloud/import_local` | 导入本地状态 |
| POST | `/api/import_state` | 导入 JSON 状态 |
| POST | `/api/restart` | 重开新局 |

### 经营

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/negotiate` | 谈判（一次性返回） |
| POST | `/api/negotiate/stream` | 谈判（NDJSON 流式） |
| POST | `/api/deal` | 成交 |
| POST | `/api/reject` | 拒绝 |
| POST | `/api/dismiss_customer` | 送离顾客 |
| POST | `/api/appraise` | 鉴定当前顾客物品 |
| POST | `/api/appraise_inventory` | 鉴定库存 |
| POST | `/api/display` / `/api/undisplay` | 上/下架展示 |
| POST | `/api/repair` | 开始修复 |
| POST | `/api/sell` | 系统出售 |
| POST | `/api/hire` / `/api/fire` | 雇/解雇 |
| POST | `/api/upgrade` | 升级店铺 |
| POST | `/api/upgrade_facility` | 升级设施 |
| POST | `/api/loan/borrow` / `/api/loan/repay` | 贷款 |
| POST | `/api/event/choice` | 事件选项 |
| POST | `/api/end_day` | 日终结算 |
| POST | `/api/next_day` | 进入下一天 |

### 联机

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/leaderboard?type=assets\|reputation\|profit\|collection` | 排行榜 |
| GET | `/api/market/listings` | 市场列表（支持搜索/筛选/排序） |
| GET | `/api/market/mine` | 我的挂单 |
| POST | `/api/market/list` | 上架 |
| POST | `/api/market/unlist` | 下架 |
| POST | `/api/market/update_price` | 改价 |
| POST | `/api/market/buy` | 购买 |
| GET | `/api/market/trades` | 交易记录 |
| GET | `/api/showcase/{owner_id}` | 参观橱窗 |
| POST | `/api/showcase/price` | 设置橱窗价 |
| POST | `/api/showcase/buy` | 购买橱窗品 |

---

## 界面设计

前端采用**现代暗黑奢华风 + 复古当铺质感**（详见 `.cursor/rules/background.mdc`）：

- 主色：背景 `#0D0F12` / `#14171C`，强调金 `#C8A97E`
- 三栏沉浸布局：左导航、中内容、右资金/技能/当铺信息
- **避免**卡片网格堆砌；用分割线、层级、毛玻璃与左色条区分区域
- 对话气泡：玩家右对齐金色淡底，NPC 左对齐浅灰底
- 响应式：桌面三栏；平板缩窄侧栏；移动端底栏导航

字体：标题 Inter，正文 Georgia，数字 Inter。

---

## 开发与扩展

### 状态单一数据源

所有玩法应写入 `GameStateManager`，经 `to_dict()` / `from_dict()` 序列化。关键数值（现金、报价、物品字段）须由后端计算，AI 只补充叙事文本。

### 扩展新玩法时建议

1. 在 `game_state.py` 增加方法与状态字段。
2. 在 `app.py` 暴露 API，返回 `{ result, state }` 统一格式。
3. 在 `App.tsx` 增加操作入口与类型定义。
4. 若需 AI，在 `ai_client.py` 增加 prompt，并保留本地 fallback。

### 本地测试

```bash
# 报价提取
python test_extract.py

# 鉴定 API（需后端运行）
python frontend/test_appraise.py
```

### 注意事项

- `.env` 含密钥，勿提交版本库（已在 `.gitignore`）。
- 修改 `game_state.py` 后注意旧存档兼容性；`Customer.from_dict` 会在读档时校正未谈判前的开场白。
- CORS 默认允许 `localhost:5173` 与 `https://game.lvxy.cc`，部署时按需修改。

---

## 许可证

本项目为私人/学习用途仓库；对外部署时请自行配置 AI Key、域名与 HTTPS。
