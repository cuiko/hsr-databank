#!/usr/bin/env python3
"""数据一致性自检：核对档案与映射表是否同步。

新增角色/光锥时最容易漏的一步是回头更新映射表——档案在、映射表没跟上，
查找链就会从"精确命中"退化成"模糊匹配到近似条目"，而且不报错、看起来还挺正常。
本脚本把这类静默缺口变成明确的清单。

CLAUDE.md 的「Commit / Push Workflow」与「大版本更新流程 > 收尾」都要求提交前核对，
跑这个脚本即可，别靠人肉记忆。ci_refresh.py 在生成后也会调用它。

用法：
  python3 scripts/check_consistency.py          # 有缺口时退出码 1
  python3 scripts/check_consistency.py --warn   # 只报告，始终退出 0（CI 里用）
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'references'


def char_ids():
    return {f[:-3] for f in os.listdir(REF / 'character')
            if f.endswith('.md') and 'enhanced' not in f}


def lightcone_ids():
    return {f[:-3] for f in os.listdir(REF / 'lightcone') if f.endswith('.md')}


def char2lc_ids(text):
    """映射表首列的角色 ID。开拓者用 '8001/8002' 合并写法，需拆开。"""
    ids = set()
    for m in re.finditer(r'^\|\s*([0-9/]+)\s*\|', text, re.M):
        ids.update(x for x in m.group(1).split('/') if x.isdigit())
    return ids


def main():
    warn_only = '--warn' in sys.argv
    tbl = (REF / 'mapping-char2lc.md').read_text()
    chars, lcs = char_ids(), lightcone_ids()
    mapped = char2lc_ids(tbl)
    referenced = set(re.findall(r'lightcone/(\d+)\.md', tbl))

    problems = []
    missing = sorted(chars - mapped, key=int)
    if missing:
        problems.append(f'角色有档案但未进 mapping-char2lc.md：{missing}')
    orphan = sorted(mapped - chars, key=int)
    if orphan:
        problems.append(f'mapping-char2lc.md 有条目但缺角色档案：{orphan}')
    broken = sorted(referenced - lcs, key=int)
    if broken:
        problems.append(f'mapping-char2lc.md 引用了不存在的光锥档案：{broken}')

    print(f'角色档案 {len(chars)} / 映射表收录 {len(mapped)} | 光锥档案 {len(lcs)}')
    if not problems:
        print('✓ 一致性检查通过')
        return 0
    for p in problems:
        print(f'✗ {p}')
    print('\n补齐映射表后再提交；映射表是查找链的入口，缺条目会导致查询命中到近似的错误条目。')
    return 0 if warn_only else 1


if __name__ == '__main__':
    sys.exit(main())
