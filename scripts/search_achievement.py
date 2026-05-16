#!/usr/bin/env python3
"""按关键字搜索 nanoka 在线成就库（每次调用从 nanoka 拉取，纯内存处理）

Usage:
  uv run python3 scripts/search_achievement.py <keyword>
  uv run python3 scripts/search_achievement.py "光锥"
  uv run python3 scripts/search_achievement.py 4010101            # 按 ID 精确查
  uv run python3 scripts/search_achievement.py --series 1         # 整个系列
  uv run python3 scripts/search_achievement.py --hidden           # 仅隐藏成就
  uv run python3 scripts/search_achievement.py "光锥" --limit 10  # 限制返回条数
"""
import json, re, sys, argparse, urllib.request

UA = {'User-Agent': 'hsr-databank', 'Referer': 'https://hsr.nanoka.cc/'}
RARITY_JADE = {'Low': 5, 'Mid': 10, 'High': 20}
RARITY_NAME = {'Low': '低', 'Mid': '中', 'High': '高'}

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def load_data():
    ver = fetch('https://static.nanoka.cc/manifest.json')['hsr']['latest']
    return fetch(f'https://static.nanoka.cc/hsr/{ver}/zh/achievement/achievement.json')

def render_desc(desc, params):
    if not desc: return desc
    if params:
        def repl(m):
            idx = int(m.group(1)) - 1
            fmt = m.group(2)
            if idx >= len(params): return m.group(0)
            v = params[idx]
            if fmt == 'i': return str(int(round(v))) if isinstance(v,(int,float)) else str(v)
            if fmt and fmt.startswith('f'):
                n = int(fmt[1:]) if len(fmt)>1 else 1
                return f'{v:.{n}f}'
            return str(v)
        desc = re.sub(r'#(\d+)\[(\w*)\]', repl, desc)
    return re.sub(r'<[^>]+>', '', desc)

def search(keyword=None, series=None, hidden=False, limit=None):
    data = load_data()
    results = []
    for sid, g in data.items():
        if series and str(series) != sid: continue
        for a in g['list']:
            if hidden and a.get('show_type') not in ('ShowAfterFinish', 'HiddenDesc'): continue
            name = a.get('name') or ''
            desc = render_desc(a.get('desc') or '', a.get('param_list') or [])
            if keyword:
                k = str(keyword)
                if not (k in name or k in desc or k == str(a.get('id'))):
                    continue
            results.append({
                'id': a['id'], 'name': name, 'desc': desc,
                'rarity': a.get('rarity'), 'jade': RARITY_JADE.get(a.get('rarity'), 0),
                'hidden': {'ShowAfterFinish':'完全隐藏','HiddenDesc':'描述隐藏'}.get(a.get('show_type'), ''),
                'series_id': sid, 'series': g['name'],
            })
    if limit: results = results[:limit]
    return results

def main():
    p = argparse.ArgumentParser(description='搜索 HSR 成就（在线 nanoka 数据）')
    p.add_argument('keyword', nargs='?', help='关键字（名称/描述/ID）')
    p.add_argument('--series', help='系列 ID (1-9)')
    p.add_argument('--hidden', action='store_true', help='仅隐藏成就')
    p.add_argument('--limit', type=int, default=50, help='最多返回条数（默认 50）')
    p.add_argument('--json', action='store_true', help='以 JSON 输出')
    args = p.parse_args()

    if not (args.keyword or args.series or args.hidden):
        p.print_help(); sys.exit(1)

    res = search(args.keyword, args.series, args.hidden, args.limit)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if not res:
        print('未找到匹配成就', file=sys.stderr); sys.exit(2)
    print(f'找到 {len(res)} 项（限 {args.limit}）：\n')
    print(f"| ID | 名称 | 描述 | 稀有度 | 星琼 | 隐藏 | 所属系列 |")
    print(f"|----|------|------|--------|------|------|----------|")
    for r in res:
        hidden = r['hidden'] or ''
        rcn = RARITY_NAME.get(r['rarity'], r['rarity'])
        desc = r['desc'].replace('|', '\\|').replace('\n', ' ')
        print(f"| {r['id']} | {r['name']} | {desc} | {rcn} | {r['jade']} | {hidden} | {r['series']} |")

if __name__ == '__main__':
    main()
