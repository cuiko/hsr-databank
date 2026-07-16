#!/usr/bin/env python3
"""搜索 / 查询 nanoka 在线怪物库，显示弱点、韧性、相位、基础属性等机制信息。

数据来源：nanoka 测试站（每次调用在线拉取，纯内存处理，不落地）。
  - 索引：https://static.nanoka.cc/hsr/{ver}/monster.json（名称/rank/弱点/变体）
  - 单怪：https://static.nanoka.cc/hsr/{ver}/zh/monster/{id}.json（属性/韧性/相位）

Usage:
  uv run python3 scripts/search_monster.py 冰锋            # 按中文/英文名搜
  uv run python3 scripts/search_monster.py 1002011         # 按 ID 精确查（附完整属性）
  uv run python3 scripts/search_monster.py 丰饶 --full     # 每个结果都拉完整属性
  uv run python3 scripts/search_monster.py boss --rank BigBoss   # 按 rank 过滤
  uv run python3 scripts/search_monster.py 冰锋 --limit 10 --json

说明：含技能/被动机制描述与逐属性抗性、变体倍率；但技能描述多为定性（少量/大量），
无精确伤害倍率——敌人技能倍率玩家端基本查不到（BWiki 同样只有定性描述），需
MonsterSkillConfig 原始挖矿数据，而该数据源已随 DMCA 冻结。
"""
import json, re, sys, argparse, urllib.request

UA = {'User-Agent': 'hsr-databank', 'Referer': 'https://hsr.nanoka.cc/'}

ELEM_CN = {'Fire': '火', 'Ice': '冰', 'Thunder': '雷', 'Wind': '风',
           'Physical': '物理', 'Quantum': '量子', 'Imaginary': '虚数'}
RANK_CN = {'Minion': '杂兵', 'MinionLv2': '杂兵', 'Elite': '精英',
           'LittleBoss': '强敌', 'BigBoss': '首领(BOSS)'}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load_index():
    ver = fetch('https://static.nanoka.cc/manifest.json')['hsr']['latest']
    return ver, fetch(f'https://static.nanoka.cc/hsr/{ver}/monster.json')


def load_detail(ver, mid):
    try:
        return fetch(f'https://static.nanoka.cc/hsr/{ver}/zh/monster/{mid}.json')
    except Exception:
        return None


def elems(weak):
    return '/'.join(ELEM_CN.get(w, w) for w in (weak or [])) or '—'


def rank_cn(r):
    return RANK_CN.get(r, r or '—')


def search(keyword=None, rank=None, limit=None):
    ver, idx = load_index()
    results = []
    for mid, m in idx.items():
        if rank and (m.get('rank') != rank):
            continue
        zh = m.get('zh') or ''
        en = m.get('en') or ''
        if keyword:
            k = str(keyword)
            if not (k in zh or k.lower() in en.lower() or k == str(mid)):
                continue
        results.append({
            'id': mid, 'name': zh, 'en': en, 'rank': m.get('rank'),
            'weak': m.get('weak') or [],
            'desc': re.sub(r'<[^>]+>', '', m.get('desc') or ''),
        })
    results.sort(key=lambda r: str(r['id']))
    if limit:
        results = results[:limit]
    return ver, results


def print_detail(ver, r):
    """打印单个怪物的完整机制卡片（属性/韧性/相位/属性抗性/技能/变体）。"""
    print(f"\n**{r['name']}**（{r['en']}） ID {r['id']}")
    print(f"- 等级类型：{rank_cn(r['rank'])}")
    d = load_detail(ver, r['id'])
    if not d:
        print(f"- 弱点属性：{elems(r['weak'])}")
        if r['desc']:
            print(f"- 描述：{r['desc']}")
        return

    children = d.get('child') or []
    base = children[0] if children else {}

    def g(k):
        v = d.get(k)
        return v if v is not None else '—'

    print(f"- 弱点属性：{elems(base.get('stance_weak_list') or r['weak'])}")
    print(f"- 基础属性：HP {g('hp_base')} / 攻 {g('attack_base')} / 防 {g('defence_base')} / 速 {g('speed_base')}")
    print(f"- 韧性：{g('stance_base')}（韧性条 {g('stance_count')}） · 效果抵抗：{d.get('status_resistance_base') or 0}"
          + (f" · 相位数：{d['max_monster_phase']}" if d.get('max_monster_phase') else ''))

    res = base.get('damage_type_resistance') or []
    if res:
        parts = [f"{ELEM_CN.get(x['damage_type'], x['damage_type'])} {int(x['value']*100)}%" for x in res]
        print(f"- 属性抗性：{'、'.join(parts)}（未列出即 0%，多为弱点）")

    skills = {}
    for c in children:
        for s in c.get('skill_list') or []:
            nm = re.sub(r'<[^>]+>', '', s.get('skill_name', '') or '')
            de = re.sub(r'<[^>]+>', '', s.get('skill_desc', '') or '')
            skills.setdefault(nm, de)
    if skills:
        print(f"- 技能（{len(skills)}）：")
        for nm, de in skills.items():
            print(f"    · {nm}：{de}")

    if len(children) > 1:
        print(f"- 变体（{len(children)} 个）：")
        for c in children:
            mods = []
            for k, lab in [('hp_modify_ratio', 'HP'), ('attack_modify_ratio', '攻'),
                           ('defence_modify_ratio', '防'), ('speed_modify_ratio', '速'),
                           ('stance_modify_ratio', '韧')]:
                v = c.get(k)
                if v not in (1, None):
                    mods.append(f"{lab}×{v:g}")
            print(f"    · {c['id']}：{'、'.join(mods) if mods else '基准'}")

    if r['desc']:
        print(f"- 描述：{r['desc']}")


def main():
    p = argparse.ArgumentParser(description='查询 HSR 怪物（在线 nanoka 数据）')
    p.add_argument('keyword', nargs='?', help='关键字（中文/英文名 / ID）')
    p.add_argument('--rank', help='按 rank 过滤：Minion / MinionLv2 / Elite / LittleBoss / BigBoss')
    p.add_argument('--full', action='store_true', help='每个结果都拉取完整属性（较慢）')
    p.add_argument('--limit', type=int, default=30, help='最多返回条数（默认 30）')
    p.add_argument('--json', action='store_true', help='以 JSON 输出')
    args = p.parse_args()

    if not (args.keyword or args.rank):
        p.print_help()
        sys.exit(1)

    ver, res = search(args.keyword, args.rank, args.limit)
    if not res:
        print('未找到匹配怪物', file=sys.stderr)
        sys.exit(2)

    # 精确 ID 命中，或 --full，或结果很少 → 展示完整机制卡片
    exact_id = args.keyword and any(str(r['id']) == str(args.keyword) for r in res)
    if args.json:
        if args.full or exact_id:
            for r in res:
                r['detail'] = load_detail(ver, r['id'])
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    if args.full or exact_id or len(res) == 1:
        print(f'找到 {len(res)} 项（nanoka {ver}）：')
        for r in res:
            print_detail(ver, r)
        return

    # 多结果 → 简表
    print(f'找到 {len(res)} 项（nanoka {ver}，限 {args.limit}）：\n')
    print('| ID | 名称 | 类型 | 弱点 |')
    print('|----|------|------|------|')
    for r in res:
        print(f"| {r['id']} | {r['name']} | {rank_cn(r['rank'])} | {elems(r['weak'])} |")
    print('\n> 加 `--full` 或用具体 ID 查看 韧性/相位/属性 等完整机制。')


if __name__ == '__main__':
    main()
