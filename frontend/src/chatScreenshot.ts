export interface DialogueTurn {
  role: 'player' | 'customer' | 'narrator';
  content: string;
}

export interface ChatScreenshotInput {
  shopName: string;
  gameDay: number;
  customerName: string;
  customerTrait: string;
  tradeLabel: string;
  itemName: string;
  itemRarityCn: string;
  avatarUrl?: string;
  dialogue: DialogueTurn[];
  dealSummary?: string | null;
  sessionClosed?: 'deal' | 'walk_out' | null;
  playUrl?: string;
}

const WIDTH = 720;
const PAD = 36;
const BUBBLE_MAX = WIDTH - PAD * 2 - 56;
const MAX_TURNS = 40;
const GAME_TITLE = '当铺代理人';

const COLORS = {
  bgTop: '#0D0F12',
  bgBottom: '#14171C',
  accent: '#C8A97E',
  accentDim: '#A68B5B',
  text: '#E0E0E0',
  textSec: '#9E9E9E',
  textWeak: '#616161',
  divider: '#2A2D34',
  playerBg: 'rgba(200, 169, 126, 0.12)',
  customerBg: 'rgba(255, 255, 255, 0.04)',
  playerText: '#D4B88A',
  deal: '#4CAF50',
  walkOut: '#FF9800',
};

const FONT_SANS = '"Inter", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif';
const FONT_SERIF = 'Georgia, "Songti SC", "SimSun", serif';

function loadImage(url: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.referrerPolicy = 'no-referrer';
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = url;
  });
}

function wrapLines(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  let line = '';
  for (const char of text.replace(/\r\n/g, '\n')) {
    if (char === '\n') {
      if (line) lines.push(line);
      line = '';
      continue;
    }
    const next = line + char;
    if (ctx.measureText(next).width > maxWidth && line) {
      lines.push(line);
      line = char;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines.length ? lines : [''];
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
) {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + w - radius, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
  ctx.lineTo(x + w, y + h - radius);
  ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
  ctx.lineTo(x + radius, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

function drawAvatar(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  img: HTMLImageElement | null,
  label: string
) {
  ctx.save();
  ctx.beginPath();
  ctx.arc(x + size / 2, y + size / 2, size / 2, 0, Math.PI * 2);
  ctx.clip();
  if (img) {
    ctx.drawImage(img, x, y, size, size);
  } else {
    const g = ctx.createLinearGradient(x, y, x + size, y + size);
    g.addColorStop(0, '#1a1d24');
    g.addColorStop(1, '#2a2d34');
    ctx.fillStyle = g;
    ctx.fillRect(x, y, size, size);
    ctx.fillStyle = COLORS.accent;
    ctx.font = `600 ${Math.round(size * 0.42)}px ${FONT_SANS}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(label.slice(0, 1), x + size / 2, y + size / 2 + 1);
  }
  ctx.restore();
  ctx.strokeStyle = COLORS.divider;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(x + size / 2, y + size / 2, size / 2, 0, Math.PI * 2);
  ctx.stroke();
}

interface LayoutBlock {
  kind: 'narrator' | 'player' | 'customer' | 'footer' | 'omit';
  lines?: string[];
  speaker?: string;
  height: number;
}

function prepareDialogue(dialogue: DialogueTurn[]): { turns: DialogueTurn[]; omitted: number } {
  const speech = dialogue.filter((t) => t.role !== 'narrator' || t.content.trim());
  if (speech.length <= MAX_TURNS) {
    return { turns: speech, omitted: 0 };
  }
  const head = speech.slice(0, 2);
  const tail = speech.slice(-(MAX_TURNS - 3));
  return { turns: [...head, { role: 'narrator', content: `··· 已省略中间 ${speech.length - head.length - tail.length} 条 ···` }, ...tail], omitted: speech.length - head.length - tail.length };
}

function measureLayout(
  ctx: CanvasRenderingContext2D,
  input: ChatScreenshotInput
): { blocks: LayoutBlock[]; totalHeight: number } {
  const { turns } = prepareDialogue(input.dialogue);
  const blocks: LayoutBlock[] = [];
  let y = 0;

  const headerH = 168;
  y += headerH;

  for (const turn of turns) {
    if (turn.role === 'narrator') {
      ctx.font = `italic 14px ${FONT_SERIF}`;
      const lines = wrapLines(ctx, turn.content, WIDTH - PAD * 2 - 40);
      const h = lines.length * 22 + 28;
      blocks.push({ kind: 'narrator', lines, height: h });
      y += h;
      continue;
    }
    const isPlayer = turn.role === 'player';
    ctx.font = `16px ${FONT_SERIF}`;
    const lines = wrapLines(ctx, turn.content, BUBBLE_MAX);
    const bubbleH = lines.length * 26 + 24;
    const blockH = bubbleH + 28;
    blocks.push({
      kind: isPlayer ? 'player' : 'customer',
      lines,
      speaker: isPlayer ? '你' : input.customerName,
      height: blockH,
    });
    y += blockH + 8;
  }

  if (input.sessionClosed && input.dealSummary) {
    blocks.push({ kind: 'footer', lines: wrapLines(ctx, input.dealSummary, WIDTH - PAD * 2 - 48), height: 72 });
    y += 72;
  }

  y += 88;
  return { blocks, totalHeight: y };
}

export async function renderChatScreenshot(input: ChatScreenshotInput): Promise<HTMLCanvasElement> {
  const measureCanvas = document.createElement('canvas');
  measureCanvas.width = WIDTH;
  const measureCtx = measureCanvas.getContext('2d');
  if (!measureCtx) throw new Error('无法创建画布');

  const avatar = input.avatarUrl ? await loadImage(input.avatarUrl) : null;
  const { blocks, totalHeight } = measureLayout(measureCtx, input);

  const canvas = document.createElement('canvas');
  canvas.width = WIDTH;
  canvas.height = Math.max(480, totalHeight);
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('无法创建画布');

  const bg = ctx.createLinearGradient(0, 0, 0, canvas.height);
  bg.addColorStop(0, COLORS.bgTop);
  bg.addColorStop(1, COLORS.bgBottom);
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, WIDTH, canvas.height);

  ctx.strokeStyle = COLORS.divider;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(PAD, 0);
  ctx.lineTo(WIDTH - PAD, 0);
  ctx.stroke();

  let y = PAD;

  ctx.font = `700 11px ${FONT_SANS}`;
  ctx.fillStyle = COLORS.accent;
  ctx.textAlign = 'left';
  ctx.fillText(GAME_TITLE, PAD, y + 12);

  ctx.font = `700 22px ${FONT_SANS}`;
  ctx.fillStyle = COLORS.text;
  ctx.fillText(input.shopName || '无名当铺', PAD, y + 40);

  ctx.font = `400 13px ${FONT_SANS}`;
  ctx.fillStyle = COLORS.textSec;
  ctx.fillText(`第 ${input.gameDay} 天 · ${input.tradeLabel}`, PAD, y + 64);

  ctx.font = `400 12px ${FONT_SANS}`;
  ctx.fillStyle = COLORS.textWeak;
  const meta = `${input.customerName} · ${input.customerTrait} · ${input.itemRarityCn}「${input.itemName}」`;
  const metaLines = wrapLines(ctx, meta, WIDTH - PAD * 2);
  metaLines.forEach((line, i) => {
    ctx.fillText(line, PAD, y + 86 + i * 18);
  });

  const accentGrad = ctx.createLinearGradient(PAD, y + 118, PAD + 120, y + 118);
  accentGrad.addColorStop(0, COLORS.accent);
  accentGrad.addColorStop(1, COLORS.accentDim);
  ctx.fillStyle = accentGrad;
  ctx.fillRect(PAD, y + 118, 48, 2);

  y += 148;

  for (const block of blocks) {
    if (block.kind === 'narrator' && block.lines) {
      ctx.font = `italic 14px ${FONT_SERIF}`;
      ctx.fillStyle = COLORS.textWeak;
      ctx.textAlign = 'center';
      block.lines.forEach((line, i) => {
        ctx.fillText(line, WIDTH / 2, y + 16 + i * 22);
      });
      y += block.height;
      continue;
    }

    if (block.kind === 'footer' && block.lines) {
      const statusColor = input.sessionClosed === 'deal' ? COLORS.deal : COLORS.walkOut;
      const statusLabel = input.sessionClosed === 'deal' ? '交易已落定' : '顾客告辞离去';
      roundRect(ctx, PAD, y, WIDTH - PAD * 2, block.height - 8, 4);
      ctx.fillStyle = input.sessionClosed === 'deal' ? 'rgba(76,175,80,0.1)' : 'rgba(255,152,0,0.1)';
      ctx.fill();
      ctx.fillStyle = statusColor;
      ctx.font = `600 14px ${FONT_SANS}`;
      ctx.textAlign = 'left';
      ctx.fillText(statusLabel, PAD + 16, y + 26);
      ctx.font = `14px ${FONT_SERIF}`;
      ctx.fillStyle = COLORS.textSec;
      block.lines.forEach((line, i) => {
        ctx.fillText(line, PAD + 16, y + 48 + i * 22);
      });
      y += block.height + 8;
      continue;
    }

    const isPlayer = block.kind === 'player';
    const avatarSize = 40;
    const ax = isPlayer ? WIDTH - PAD - avatarSize : PAD;
    const bubbleX = isPlayer ? PAD + 48 : PAD + avatarSize + 16;
    const bubbleW = WIDTH - PAD * 2 - avatarSize - 64;

    drawAvatar(ctx, ax, y + 20, avatarSize, isPlayer ? null : avatar, block.speaker || '?');

    ctx.font = `400 11px ${FONT_SANS}`;
    ctx.fillStyle = COLORS.textWeak;
    ctx.textAlign = isPlayer ? 'right' : 'left';
    ctx.fillText(block.speaker || '', isPlayer ? WIDTH - PAD - avatarSize - 8 : PAD + avatarSize + 16, y + 14);

    const lines = block.lines || [];
    const bubbleH = lines.length * 26 + 24;
    roundRect(ctx, bubbleX, y + 22, bubbleW, bubbleH, 4);
    ctx.fillStyle = isPlayer ? COLORS.playerBg : COLORS.customerBg;
    ctx.fill();

    ctx.fillStyle = isPlayer ? COLORS.playerText : COLORS.text;
    ctx.strokeStyle = isPlayer ? COLORS.accent : COLORS.divider;
    ctx.lineWidth = 2;
    if (isPlayer) {
      ctx.beginPath();
      ctx.moveTo(bubbleX + bubbleW, y + 22);
      ctx.lineTo(bubbleX + bubbleW, y + 22 + bubbleH);
      ctx.stroke();
    } else {
      ctx.beginPath();
      ctx.moveTo(bubbleX, y + 22);
      ctx.lineTo(bubbleX, y + 22 + bubbleH);
      ctx.stroke();
    }

    ctx.font = `16px ${FONT_SERIF}`;
    ctx.textAlign = 'left';
    lines.forEach((line, i) => {
      ctx.fillText(line, bubbleX + 16, y + 46 + i * 26);
    });

    y += block.height + 8;
  }

  const footerY = canvas.height - 56;
  ctx.strokeStyle = COLORS.divider;
  ctx.beginPath();
  ctx.moveTo(PAD, footerY);
  ctx.lineTo(WIDTH - PAD, footerY);
  ctx.stroke();

  ctx.font = `400 12px ${FONT_SANS}`;
  ctx.fillStyle = COLORS.textWeak;
  ctx.textAlign = 'left';
  const playHint = input.playUrl ? `来玩：${input.playUrl}` : 'AI 文字经营 · 当铺人生';
  ctx.fillText(playHint, PAD, footerY + 22);

  ctx.textAlign = 'right';
  ctx.fillStyle = COLORS.accent;
  ctx.font = `600 12px ${FONT_SANS}`;
  ctx.fillText(GAME_TITLE, WIDTH - PAD, footerY + 22);

  return canvas;
}

export function downloadChatScreenshot(canvas: HTMLCanvasElement, filename: string) {
  const link = document.createElement('a');
  link.download = filename;
  link.href = canvas.toDataURL('image/png');
  link.click();
}

export async function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('无法导出图片'));
    }, 'image/png');
  });
}

export async function copyChatScreenshotToClipboard(canvas: HTMLCanvasElement): Promise<boolean> {
  if (!navigator.clipboard?.write || typeof ClipboardItem === 'undefined') {
    return false;
  }
  try {
    const blob = await canvasToBlob(canvas);
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
    return true;
  } catch {
    return false;
  }
}

export async function shareChatScreenshot(
  canvas: HTMLCanvasElement,
  title: string,
  text: string
): Promise<'shared' | 'unsupported' | 'failed'> {
  if (!navigator.share) return 'unsupported';
  try {
    const blob = await canvasToBlob(canvas);
    const file = new File([blob], '当铺对话.png', { type: 'image/png' });
    const payload: ShareData = { title, text };
    if (navigator.canShare?.({ files: [file] })) {
      await navigator.share({ ...payload, files: [file] });
    } else {
      await navigator.share(payload);
      return 'shared';
    }
    return 'shared';
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') return 'failed';
    return 'failed';
  }
}

export function buildScreenshotFilename(customerName: string, day: number): string {
  const safe = customerName.replace(/[\\/:*?"<>|]/g, '_').slice(0, 24);
  return `当铺代理人-${safe}-第${day}天.png`;
}
