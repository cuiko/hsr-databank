#!/usr/bin/env python3
"""批量生成 references/lightcone/{id}.md, 数据来源 Mar-7th StarRailRes

Usage:
  uv run python3 scripts/gen_lightcone.py [lightcone_id]
  不带参数时生成所有光锥
"""
import json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'references' / 'lightcone'
OUT_DIR.mkdir(parents=True, exist_ok=True)
RAW = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index_min/cn'

def fetch(name):
    url = f'{RAW}/{name}.json'
    req = urllib.request.Request(url, headers={'User-Agent': 'hsr-databank'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

print('Fetching Mar-7th data...')
LC = fetch('light_cones')
LCR = fetch('light_cone_ranks')
LCP = fetch('light_cone_promotions')

PATH_CN = {'Warrior':'毁灭','Rogue':'巡猎','Mage':'智识','Shaman':'同谐',
           'Warlock':'虚无','Knight':'存护','Priest':'丰饶',
           'Memory':'记忆','Elation':'欢愉'}

def render_desc(desc, params, highlight=False):
    """替换 #N[fmt]% 占位符。highlight=True 时高亮数值并标记参数序号。"""
    if not desc or not params: return desc
    def repl(m):
        whole = m.group(0)
        n = m.group(1)
        idx = int(n) - 1
        fmt = m.group(2)
        has_pct = whole.endswith('%')
        if idx >= len(params): return whole
        v = params[idx]
        if has_pct:
            val = v * 100 if isinstance(v, (int, float)) else v
            if fmt and fmt.startswith('f'):
                k = int(fmt[1:]) if len(fmt) > 1 else 1
                display = f'{val:.{k}f}'
            else:
                display = f'{val:g}' if isinstance(val, float) else str(int(val))
        elif fmt == 'i':
            display = str(int(round(v)))
        elif fmt and fmt.startswith('f'):
            k = int(fmt[1:]) if len(fmt) > 1 else 1
            display = f'{v:.{k}f}'
        else:
            display = f'{v:g}' if isinstance(v, float) else str(v)
        result = display + ('%' if has_pct else '')
        if highlight:
            return f'**{result}**<sup>{n}</sup>'
        return result
    return re.sub(r'#(\d+)\[(\w*)\]%?', repl, desc)

def is_pct_param(desc, idx):
    return bool(re.search(rf'#{idx}\[\w*\]%', desc))

def format_param(v, is_pct):
    if is_pct:
        return f'{v*100:.1f}%' if isinstance(v, float) else f'{int(v)*100}%'
    if isinstance(v, float) and v != int(v):
        return f'{v}'
    return str(int(v))

def compute_base_stats(lc_id):
    p = LCP[lc_id]['values'][6]  # P6
    return {
        'hp': int(p['hp']['base'] + p['hp']['step'] * 79),
        'atk': int(p['atk']['base'] + p['atk']['step'] * 79),
        'def': int(p['def']['base'] + p['def']['step'] * 79),
    }

def gen_lightcone(lc_id):
    lc = LC[lc_id]
    name = lc['name']
    rarity = lc['rarity']
    path = PATH_CN.get(lc['path'], lc['path'])
    desc_lore = lc.get('desc', '').strip()
    
    base = compute_base_stats(lc_id)
    
    rank = LCR.get(lc_id, {})
    skill_name = rank.get('skill', '')
    skill_desc = rank.get('desc', '')
    params_list = rank.get('params', [])
    
    md = f'''# {name} — ID {lc_id}

> 数据来源：[Mar-7th StarRailRes](https://github.com/Mar-7th/StarRailRes)（cn 索引）

## 基础信息

| 项目 | 值 |
|------|-----|
| 光锥 ID | {lc_id} |
| 中文名 | {name} |
| 稀有度 | {'★'*rarity} |
| 命途 | {path} |

## 基础属性 (Lv80 满晋阶)

| 属性 | 数值 |
|------|------|
| 生命值 | {base['hp']:,} |
| 攻击力 | {base['atk']:,} |
| 防御力 | {base['def']:,} |

---

## 叠影效果 · {skill_name}

'''
    if params_list:
        # 用 S1 渲染描述（默认抽卡成本，S5 不普及）
        rendered = render_desc(skill_desc, params_list[0], highlight=True)
        md += f'> {rendered}\n\n'
        
        # 列出每个叠影的关键参数
        placeholders = sorted({int(m.group(1)) for m in re.finditer(r'#(\d+)\[', skill_desc)})
        if placeholders:
            param_pcts = [is_pct_param(skill_desc, p) for p in placeholders]
            headers = ['叠影'] + [f'参数 {p}{"(%)" if pct else ""}' for p, pct in zip(placeholders, param_pcts)]
            md += '| ' + ' | '.join(headers) + ' |\n'
            md += '|' + '|'.join(['---']*len(headers)) + '|\n'
            for i, p in enumerate(params_list, 1):
                cells = [f'S{i}']
                for ph, pct in zip(placeholders, param_pcts):
                    if ph - 1 < len(p):
                        v = p[ph - 1]
                        cells.append(format_param(v, pct))
                    else:
                        cells.append('—')
                md += '| ' + ' | '.join(cells) + ' |\n'
            md += '\n'
    else:
        md += f'> {skill_desc}\n\n'
    return md

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    ids = [target] if target else sorted(LC.keys(), key=lambda x: int(x) if x.isdigit() else 99999)
    ok = 0; errors = []
    for lc_id in ids:
        try:
            md = gen_lightcone(lc_id)
            (OUT_DIR / f'{lc_id}.md').write_text(md)
            ok += 1
        except Exception as e:
            errors.append((lc_id, str(e)))
    print(f'Generated {ok} files. Errors: {len(errors)}')
    for lc_id, e in errors[:5]:
        print(f'  {lc_id}: {e}')

if __name__ == '__main__':
    main()
