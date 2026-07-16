#!/usr/bin/env python3
"""从 nanoka 生成 references/lightcone/{id}.md（SRR 兜底方案）

用途：当 Mar-7th StarRailRes 尚未收录某光锥（联动/新版本刚上线）时，改用 nanoka
数据生成光锥档案。输出格式与 gen_lightcone.py 对齐，不改动原脚本。

Usage:
  python3 scripts/gen_lightcone_nanoka.py 23060
  python3 scripts/gen_lightcone_nanoka.py 23060 23061       # 指定 ID → references/
  python3 scripts/gen_lightcone_nanoka.py --beta 23063      # 指定 ID → drafts/（gitignore）
  python3 scripts/gen_lightcone_nanoka.py --beta            # 不带 ID：自动取测试服新增光锥
  python3 scripts/gen_lightcone_nanoka.py --beta --dry-run  # 只打印计划

Flags:
  --beta      输出到 drafts/（gitignore）；不带 ID 时自动从 manifest.new 取测试服新增
  --dry-run   只打印计划，不落盘
"""
import json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

UA = {'User-Agent': 'hsr-databank', 'Referer': 'https://hsr.nanoka.cc/'}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


NANOKA_VER = fetch('https://static.nanoka.cc/manifest.json')['hsr']['latest']
print(f'Nanoka HSR version: {NANOKA_VER}')

PATH_CN = {'Warrior': '毁灭', 'Rogue': '巡猎', 'Mage': '智识', 'Shaman': '同谐',
           'Warlock': '虚无', 'Knight': '存护', 'Priest': '丰饶',
           'Memory': '记忆', 'Elation': '欢愉'}


def strip_tags(s):
    if not s:
        return ''
    return re.sub(r'<[^>]+>', '', s.replace('\\n', '\n'))


def rarity_int(v):
    m = re.search(r'(\d+)', str(v))
    return int(m.group(1)) if m else 5


# ---- 渲染逻辑复制自 gen_lightcone.py（纯函数）----
def is_pct_param(desc, idx):
    return bool(re.search(rf'#{idx}\[\w*\]%', desc))


def format_param(v, is_pct):
    if is_pct:
        return f'{v*100:.1f}%' if isinstance(v, float) else f'{int(v)*100}%'
    if isinstance(v, float) and v != int(v):
        return f'{v}'
    return str(int(v))


def render_desc(desc, params, highlight=False):
    if not desc or not params:
        return desc
    def repl(m):
        whole = m.group(0)
        n = m.group(1)
        idx = int(n) - 1
        fmt = m.group(2)
        has_pct = whole.endswith('%')
        if idx >= len(params):
            return whole
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


def gen_lightcone(lc_id):
    lc_id = str(lc_id)
    d = fetch(f'https://static.nanoka.cc/hsr/{NANOKA_VER}/zh/lightcone/{lc_id}.json')
    name = strip_tags(d['name'])
    rarity = rarity_int(d.get('rarity'))
    path = PATH_CN.get(d.get('base_type'), d.get('base_type'))

    s6 = d['stats'][6]
    base = {
        'hp': int(s6['base_hp'] + s6['base_hp_add'] * 79),
        'atk': int(s6['base_attack'] + s6['base_attack_add'] * 79),
        'def': int(s6['base_defence'] + s6['base_defence_add'] * 79),
    }

    rf = d.get('refinements') or {}
    skill_name = strip_tags(rf.get('name', ''))
    skill_desc = strip_tags(rf.get('desc', ''))
    lv = rf.get('level', {})
    params_list = [lv[str(i)].get('param_list', []) for i in range(1, 6) if str(i) in lv]

    md = f'''# {name} — ID {lc_id}

> 数据来源：[nanoka](https://hsr.nanoka.cc/lightcone/{lc_id})（测试站 {NANOKA_VER} 数据）

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
        rendered = render_desc(skill_desc, params_list[0], highlight=True)
        md += f'> {rendered}\n\n'
        placeholders = sorted({int(m.group(1)) for m in re.finditer(r'#(\d+)\[', skill_desc)})
        if placeholders:
            param_pcts = [is_pct_param(skill_desc, p) for p in placeholders]
            headers = ['叠影'] + [f'参数 {p}{"(%)" if pct else ""}' for p, pct in zip(placeholders, param_pcts)]
            md += '| ' + ' | '.join(headers) + ' |\n'
            md += '|' + '|'.join(['---'] * len(headers)) + '|\n'
            for i, p in enumerate(params_list, 1):
                cells = [f'S{i}']
                for ph, pct in zip(placeholders, param_pcts):
                    if ph - 1 < len(p):
                        cells.append(format_param(p[ph - 1], pct))
                    else:
                        cells.append('—')
                md += '| ' + ' | '.join(cells) + ' |\n'
            md += '\n'
    else:
        md += f'> {skill_desc}\n\n'
    return md


def main():
    args = sys.argv[1:]
    beta = '--beta' in args    # 测试服内容：输出到 drafts/（已 gitignore），不入库
    dry = '--dry-run' in args  # 只打印计划，不写盘/不删除
    ids = [a for a in args if not a.startswith('--')]
    # --beta 不带 ID：自动从 manifest 取测试服新增光锥，并让 drafts 只保留这些新内容
    auto = beta and not ids
    if auto:
        new = fetch('https://static.nanoka.cc/manifest.json')['hsr'].get('new', {})
        ids = [str(x) for x in new.get('lightcone', [])]
        print(f'--beta 自动：测试服新增光锥 {ids}')
    if not ids:
        print('Usage: gen_lightcone_nanoka.py [--beta] [--dry-run] [id ...]'
              '  (--beta 不带 ID = 自动取测试服新增)', file=sys.stderr)
        sys.exit(1)
    sub = 'drafts' if beta else 'references'
    out_dir = ROOT / sub / 'lightcone'
    if not dry:
        out_dir.mkdir(parents=True, exist_ok=True)
    tag = '[dry-run] ' if dry else ''
    ok = 0
    errors = []
    for lc_id in ids:
        lc_id = str(lc_id)
        try:
            md = gen_lightcone(lc_id)
            if not dry:
                (out_dir / f'{lc_id}.md').write_text(md)
            ok += 1
            print(f'  {tag}wrote {sub}/lightcone/{lc_id}.md')
        except Exception as e:
            errors.append((lc_id, repr(e)))
    if auto:  # 只保留新内容：清掉 drafts 里不再属于测试服新增的光锥
        keep = {f'{i}.md' for i in ids}
        for p in out_dir.glob('*.md') if out_dir.exists() else []:
            if p.name not in keep:
                if not dry:
                    p.unlink()
                print(f'  {tag}pruned {sub}/lightcone/{p.name}')
    print(f'{tag}Generated {ok} files. Errors: {len(errors)}')
    for lc_id, e in errors:
        print(f'  {lc_id}: {e}')


if __name__ == '__main__':
    main()
