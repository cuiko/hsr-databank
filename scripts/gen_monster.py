#!/usr/bin/env python3
"""生成 references/monster/{id}.md —— 怪物档案（弱点/韧性/相位/属性/抗性/技能/变种）。

数据来源：nanoka（索引 monster.json + 单怪 zh/monster/{id}.json）。

Usage:
  python3 scripts/gen_monster.py 1002011 2013010 8015050   # 指定 ID
  python3 scripts/gen_monster.py --all                     # 全量(628 个,较慢)
  python3 scripts/gen_monster.py --all --dry-run           # 只报计划,不写盘

已知局限：技能描述为定性（少量/大量），无精确伤害倍率（玩家端不可得）。
"""
import json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {'User-Agent': 'hsr-databank', 'Referer': 'https://hsr.nanoka.cc/'}

ELEM_CN = {'Fire': '火', 'Ice': '冰', 'Thunder': '雷', 'Wind': '风',
           'Physical': '物理', 'Quantum': '量子', 'Imaginary': '虚数'}
RANK_CN = {'Minion': '杂兵', 'MinionLv2': '杂兵', 'Elite': '精英',
           'LittleBoss': '强敌', 'BigBoss': '首领(BOSS)'}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


NANOKA_VER = fetch('https://static.nanoka.cc/manifest.json')['hsr']['latest']
INDEX = fetch(f'https://static.nanoka.cc/hsr/{NANOKA_VER}/monster.json')


def clean(s):
    return re.sub(r'<[^>]+>', '', (s or '').replace('\\n', ' ')).strip()


def elems(weak):
    return '/'.join(ELEM_CN.get(w, w) for w in (weak or [])) or '—'


def res_str(c):
    return '、'.join(f"{ELEM_CN.get(x['damage_type'], x['damage_type'])}{int(x['value']*100)}%"
                     for x in (c.get('damage_type_resistance') or []))


def gen_monster(mid):
    mid = str(mid)
    meta = INDEX.get(mid) or {}
    d = fetch(f'https://static.nanoka.cc/hsr/{NANOKA_VER}/zh/monster/{mid}.json')
    name = clean(d.get('name')) or meta.get('zh') or mid
    en = meta.get('en', '')
    rank = RANK_CN.get(d.get('rank') or meta.get('rank'), d.get('rank') or meta.get('rank') or '—')
    children = d.get('child') or []
    base = children[0] if children else {}

    def g(k):
        v = d.get(k)
        return v if v is not None else '—'

    uniform_weak = len({tuple(c.get('stance_weak_list') or []) for c in children}) <= 1
    uniform_res = len({res_str(c) for c in children}) <= 1
    weak_cell = elems(base.get('stance_weak_list') or meta.get('weak')) if uniform_weak else '各变种不同（见「变种」）'

    md = f'''# {name}（{en}）

> 数据来源：[nanoka](https://hsr.nanoka.cc/monster/{mid})（测试站 {NANOKA_VER} 数据）

## 基础信息

| 项目 | 值 |
|------|-----|
| 怪物 ID | {mid} |
| 中文名 | {name} |
| 英文名 | {en} |
| 等级类型 | {rank} |
| 弱点属性 | {weak_cell} |

## 基础属性（随敌人等级缩放，此为基准值）

| 项目 | 值 |
|------|-----|
| 生命值 | {g('hp_base')} |
| 攻击力 | {g('attack_base')} |
| 防御力 | {g('defence_base')} |
| 速度 | {g('speed_base')} |
| 韧性 | {g('stance_base')}（韧性条 {g('stance_count')}） |
| 效果抵抗 | {d.get('status_resistance_base') or 0} |
| 相位数 | {d.get('max_monster_phase') or 1} |
'''
    if uniform_res and res_str(base):
        md += f'| 属性抗性 | {res_str(base)}（未列出即 0%） |\n'
    elif not uniform_res:
        md += '| 属性抗性 | 各变种不同（见「变种」） |\n'

    # 技能
    # 同名技能可能有不同描述（如变体触发成功/失败），按 名→去重后的描述列表 收集，全部保留
    skills = {}
    for c in children:
        for s in c.get('skill_list') or []:
            nm = clean(s.get('skill_name'))
            de = clean(s.get('skill_desc'))
            lst = skills.setdefault(nm, [])
            if de not in lst:
                lst.append(de)
    if skills:
        md += '\n---\n\n## 技能\n\n'
        for nm, descs in skills.items():
            md += f'### {nm}\n\n'
            for de in descs:
                md += f'> {de}\n\n'

    # 变种
    if len(children) > 1:
        md += '---\n\n## 变种\n\n'
        cols = ['变种 ID']
        if not uniform_weak:
            cols.append('弱点')
        if not uniform_res:
            cols.append('属性抗性')
        cols.append('属性倍率')
        md += '| ' + ' | '.join(cols) + ' |\n'
        md += '|' + '|'.join(['---'] * len(cols)) + '|\n'
        for c in children:
            # 变种都是本怪的形态（子变体无独立 md），链回本怪档案
            row = [f"[{c['id']}]({mid}.md)"]
            if not uniform_weak:
                row.append(elems(c.get('stance_weak_list')))
            if not uniform_res:
                row.append(res_str(c) or '全 0%')
            mods = []
            for k, lab in [('hp_modify_ratio', 'HP'), ('attack_modify_ratio', '攻'),
                           ('defence_modify_ratio', '防'), ('speed_modify_ratio', '速'),
                           ('stance_modify_ratio', '韧')]:
                v = c.get(k)
                if v not in (1, None):
                    mods.append(f'{lab}×{v:g}')
            row.append('、'.join(mods) if mods else '基准')
            md += '| ' + ' | '.join(row) + ' |\n'

    desc = clean(meta.get('desc'))
    if desc:
        md += f'\n---\n\n## 描述\n\n> {desc}\n'
    return md


def gen_index():
    """生成 references/mapping-monster.md：怪物名 ↔ ID 速查表（名称链到 monster/{id}.md）。"""
    rows = []
    for mid in sorted(INDEX, key=lambda x: int(x) if x.isdigit() else 0):
        m = INDEX[mid]
        name = clean(m.get('zh') or '') or mid
        rank = RANK_CN.get(m.get('rank'), m.get('rank') or '—')
        rows.append(f"| {mid} | [{name}](monster/{mid}.md) | {rank} | {elems(m.get('weak'))} |")
    return (f"# 怪物映射表\n\n"
            f"> 名称链接到 `references/monster/{{id}}.md`；数据源 nanoka（{NANOKA_VER}），共 {len(INDEX)} 个。\n\n"
            f"## 用法\n\n"
            f"本表用于「怪物名 ↔ ID」速查：拿到 ID 后读 `references/monster/{{id}}.md` 取完整档案"
            f"（弱点/韧性/相位/抗性/技能/变种）。\n\n"
            f"- **表很长，别整表通读**：按关键字/弱点/类型用 `scripts/search_monster.py <关键字>` 精确定位，"
            f"或在本表内检索名称。\n"
            f"- **同名多条目**：同一名称常有多个 ID（不同关卡/难度/变种，如「银鬃尉官（完整）」「银鬃尉官（错误）」），"
            f"按类型与弱点区分，逐一确认再取档案。\n"
            f"- 表按 ID 升序排列，非按类型分组。\n\n"
            f"## 速查表\n\n"
            f"| ID | 名称 | 类型 | 弱点 |\n|----|------|------|------|\n"
            + "\n".join(rows) + "\n")


def main():
    args = sys.argv[1:]
    dry = '--dry-run' in args
    if '--index' in args:
        md = gen_index()
        if not dry:
            (ROOT / 'references' / 'mapping-monster.md').write_text(md)
        print(f"{'[dry-run] ' if dry else ''}wrote references/mapping-monster.md ({len(INDEX)} 行)")
        if not ('--all' in args or [a for a in args if not a.startswith('--')]):
            return
    allm = '--all' in args
    ids = [a for a in args if not a.startswith('--')]
    if allm:
        ids = sorted(INDEX.keys(), key=lambda x: int(x) if x.isdigit() else 0)
    if not ids:
        print('Usage: gen_monster.py [--all] [--index] [--dry-run] [id ...]', file=sys.stderr)
        sys.exit(1)
    out_dir = ROOT / 'references' / 'monster'
    if not dry:
        out_dir.mkdir(parents=True, exist_ok=True)
    tag = '[dry-run] ' if dry else ''
    ok, errors = 0, []
    for mid in ids:
        try:
            md = gen_monster(mid)
            if not dry:
                (out_dir / f'{mid}.md').write_text(md)
            ok += 1
            if not allm:
                print(f'  {tag}wrote references/monster/{mid}.md')
        except Exception as e:
            errors.append((mid, repr(e)))
    print(f'{tag}Generated {ok} files. Errors: {len(errors)}')
    for mid, e in errors[:10]:
        print(f'  {mid}: {e}')


if __name__ == '__main__':
    main()
