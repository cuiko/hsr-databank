#!/usr/bin/env python3
"""CI 增量刷新：检测正式服（Mar-7th StarRailRes）已收录、但本地 references/ 缺失的
角色 / 光锥并补齐；可选刷新怪物名↔ID 索引。

只补新增、不整库重生成——请求量小、避免把数据源打到限流（429），也贴合
CLAUDE.md「大版本更新流程」的补内容思路。角色/光锥走 SRR（跟正式服），故新角色
要等 SRR 收录后才会被补进来，天然规避把测试服 beta 内容提前入库。

用法：
  python3 scripts/ci_refresh.py                # 补缺角色/光锥
  python3 scripts/ci_refresh.py --dry-run      # 只报缺口，不生成/不写盘
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index_min/cn'
UA = {'User-Agent': 'hsr-databank'}


def fetch(name):
    req = urllib.request.Request(f'{RAW}/{name}.json', headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def local_ids(subdir):
    """本地已有档案 ID（排除 -enhanced 派生档，只看主档案）。"""
    d = ROOT / 'references' / subdir
    return {p.stem for p in d.glob('*.md') if '-enhanced' not in p.stem}


def find_missing(index_name, subdir, keep=lambda k: True):
    idx = fetch(index_name)
    want = {k for k in idx if k.isdigit() and keep(k)}
    return sorted(want - local_ids(subdir), key=int)


def run_gen(script, ids):
    """逐个生成，单个失败不阻断其余；返回失败列表。"""
    fails = []
    for i in ids:
        print(f'  → {script} {i}', flush=True)
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / script), i])
        if r.returncode != 0:
            fails.append(i)
    return fails


def main():
    args = sys.argv[1:]
    dry = '--dry-run' in args

    # 角色排除 8xxx 开拓者变体（单独维护，不随此流程动）
    char_missing = find_missing('characters', 'character', keep=lambda k: int(k) < 8000)
    lc_missing = find_missing('light_cones', 'lightcone')

    print(f'缺失角色: {char_missing or "无"}')
    print(f'缺失光锥: {lc_missing or "无"}')

    if dry:
        print('[dry-run] 仅检测，不生成')
        return 0

    fails = []
    if char_missing:
        fails += [('character', i) for i in run_gen('gen_character.py', char_missing)]
    if lc_missing:
        fails += [('lightcone', i) for i in run_gen('gen_lightcone.py', lc_missing)]

    if fails:
        # SRR 索引有、但完整数据缺（刚上线数天常见）——不视为致命，人工用 nanoka 兜底
        print(f'⚠️ 以下生成失败（可能 SRR 数据未齐，改用 gen_*_nanoka.py 兜底）：{fails}')

    # 新角色/光锥入库后映射表常被漏更新，这里报出来（不阻断，PR 仍需人工补）
    print('\n--- 一致性自检 ---')
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'check_consistency.py'), '--warn'])

    print('done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
