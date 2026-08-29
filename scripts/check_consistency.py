#!/usr/bin/env python3
"""数据自检：把"静默错误"变成明确的清单。

这个库最危险的故障不是查不到，而是**查到了错的东西还答得很像样**——生成器漏掉整段
技能、映射表没跟上、两个角色同名。这类问题不报错、格式完好、内容自洽，只有懂这块
数据的人逐条核对才可能发现。本脚本把已经踩过的坑固化成断言，让它们下次自己冒出来。

已固化的失败案例：
  - 记忆命途角色缺整段忆灵（忆灵技能 ID 不符合 '1'+cid 前缀假设，被过滤掉）
  - 开拓者·记忆的女性形态 8008 沿用 8007 的忆灵编号，靠前缀推断会整段漏掉
  - 新角色入库但没补 mapping-char2lc.md，查询退化成模糊匹配到近似角色
  - 三月七(1001) 与 三月七•巡猎(1224) 在源数据里同名，档案标题无法区分

CLAUDE.md 的「Commit / Push Workflow」与「大版本更新流程 > 收尾」都要求提交前核对，
跑这个脚本即可，别靠人肉记忆。ci_refresh.py 在生成后也会调用它。

用法：
  python3 scripts/check_consistency.py          # 有问题时退出码 1
  python3 scripts/check_consistency.py --warn   # 只报告，始终退出 0（CI 里用）
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'references'

REQUIRED_SECTIONS = ['## 基础信息', '## 基础属性', '## 行迹', '## 技能', '## 星魂']
CORE_SKILLS = ['### 普攻', '### 战技', '### 终结技', '### 天赋']
# 开拓者的男/女形态共用名字，成对出现属正常，不算重名冲突。
TRAILBLAZER_PAIRS = {('8001', '8002'), ('8003', '8004'), ('8005', '8006'),
                     ('8007', '8008'), ('8009', '8010')}


def character_files():
    d = REF / 'character'
    return {f[:-3]: (d / f).read_text()
            for f in os.listdir(d) if f.endswith('.md') and 'enhanced' not in f}


def path_of(text):
    m = re.search(r'^\|\s*命途\s*\|\s*(\S+?)\s*\|', text, re.M)
    return m.group(1) if m else None


def title_of(text):
    return text.splitlines()[0].lstrip('# ').strip() if text else ''


def check_mapping(chars, problems):
    """映射表是查找链的入口。缺条目不会报错，但会让查询退化成模糊匹配。"""
    tbl = (REF / 'mapping-char2lc.md').read_text()
    mapped = set()
    for m in re.finditer(r'^\|\s*([0-9/]+)\s*\|', tbl, re.M):
        mapped.update(x for x in m.group(1).split('/') if x.isdigit())
    lcs = {f[:-3] for f in os.listdir(REF / 'lightcone') if f.endswith('.md')}

    missing = sorted(set(chars) - mapped, key=int)
    if missing:
        problems.append(f'角色有档案但未进 mapping-char2lc.md：{missing}')
    orphan = sorted(mapped - set(chars), key=int)
    if orphan:
        problems.append(f'mapping-char2lc.md 有条目但缺角色档案：{orphan}')
    broken = sorted(set(re.findall(r'lightcone/(\d+)\.md', tbl)) - lcs, key=int)
    if broken:
        problems.append(f'mapping-char2lc.md 引用了不存在的光锥档案：{broken}')


def check_structure(chars, problems):
    """章节缺失通常意味着生成中途失败或技能分类出错，而产物看起来仍然正常。"""
    for cid, text in sorted(chars.items()):
        miss = [s for s in REQUIRED_SECTIONS if s not in text]
        if miss:
            problems.append(f'{cid} 缺章节：{miss}')
        miss = [s for s in CORE_SKILLS if s not in text]
        if miss:
            problems.append(f'{cid} 缺核心技能条目：{miss}')


def check_memosprite(chars, problems):
    """记忆命途角色必有忆灵。整段缺失而无人察觉，是这个库最典型的静默故障。"""
    for cid, text in sorted(chars.items()):
        if path_of(text) == '记忆' and '## 忆灵' not in text:
            problems.append(f'{cid}（记忆命途）缺 ## 忆灵 段——忆灵技能未被生成器收集')


def check_names(chars, problems):
    """同名档案无法靠名字区分，查询只能撞运气；变体角色尤其容易被本体顶替。"""
    by_name = {}
    for cid, text in chars.items():
        by_name.setdefault(title_of(text), []).append(cid)
    for name, ids in sorted(by_name.items()):
        if len(ids) > 1 and tuple(sorted(ids)) not in TRAILBLAZER_PAIRS:
            problems.append(f'档案标题重名「{name}」：{sorted(ids, key=int)}'
                            f'——需在 _hsr_common.NAME_OVERRIDE 里给出可区分的名字')


def main():
    chars = character_files()
    problems = []
    for check in (check_mapping, check_structure, check_memosprite, check_names):
        check(chars, problems)

    print(f'角色档案 {len(chars)} 个')
    if not problems:
        print('✓ 一致性检查通过')
        return 0
    for p in problems:
        print(f'✗ {p}')
    print(f'\n共 {len(problems)} 处问题。这些都不会在使用时报错，只会让答案悄悄变错，请修完再提交。')
    return 0 if '--warn' in sys.argv else 1


if __name__ == '__main__':
    sys.exit(main())
