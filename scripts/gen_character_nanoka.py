#!/usr/bin/env python3
"""从 nanoka 生成 references/character/{id}.md（SRR 兜底方案）

用途：当 Mar-7th StarRailRes 尚未收录某角色（常见于联动/全新版本刚上线）时，
改用 nanoka 测试站数据生成角色档案。输出格式与 gen_character.py 对齐。

设计：不改动 gen_character.py。本脚本把 nanoka 的 per-character JSON 适配成
gen_character.py 已在使用的 5 个结构（CHARS/PROMO/SKILLS/RANKS/TREES），再复用
同一套渲染逻辑，确保产物格式一致。

Usage:
  python3 scripts/gen_character_nanoka.py 1508          # 单个角色
  python3 scripts/gen_character_nanoka.py 1508 1509 1510

已知局限（需人工复核）：
  - E3/E5 技能等级提升表由星魂描述解析重建（"战技等级+2"等），个别角色可能需校正。
  - 倍率/星魂数值以 nanoka 测试站为准，上线后建议对照正式服核对。
"""
import json, re, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hsr_common import NO_REGULAR_ENERGY

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'references' / 'character'
OUT_DIR.mkdir(parents=True, exist_ok=True)

UA = {'User-Agent': 'hsr-databank', 'Referer': 'https://hsr.nanoka.cc/'}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


NANOKA_VER = fetch('https://static.nanoka.cc/manifest.json')['hsr']['latest']
print(f'Nanoka HSR version: {NANOKA_VER}')

# ---- nanoka 数据缓存 ----
_CACHE = {}
def get_nanoka_char(cid):
    cid = str(cid)
    if cid in _CACHE:
        return _CACHE[cid]
    try:
        _CACHE[cid] = fetch(f'https://static.nanoka.cc/hsr/{NANOKA_VER}/zh/character/{cid}.json')
    except Exception:
        _CACHE[cid] = None
    return _CACHE[cid]

# ---- 适配后填充的“类 SRR”结构（键名与 gen_character.py 一致）----
CHARS, PROMO, SKILLS, RANKS, TREES = {}, {}, {}, {}, {}

def strip_tags(s):
    if not s:
        return ''
    s = s.replace('\\n', '\n')            # nanoka 用字面 \n
    return re.sub(r'<[^>]+>', '', s)

# nanoka skill.tag == SRR skill.effect；effect_text 从 SRR 现有技能表动态建映射
# （新角色的 effect 类型在老角色身上都出现过），带硬编码兜底。
_TAG_FALLBACK = {
    'SingleAttack': '单攻', 'AoEAttack': '群攻', 'Blast': '扩散', 'Bounce': '弹射',
    'Enhance': '强化', 'Summon': '召唤', 'Support': '支援', 'Impair': '妨害',
    'Defence': '防御', 'Restore': '回复', 'MazeAttack': '', 'MazeNormal': '',
}
def build_tag_cn():
    m = dict(_TAG_FALLBACK)
    try:
        srr = fetch('https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index_min/cn/character_skills.json')
        for s in srr.values():
            eff, txt = s.get('effect'), s.get('effect_text')
            if eff and txt:
                m[eff] = txt
    except Exception:
        pass
    return m
TAG_CN = build_tag_cn()


def rarity_int(v):
    m = re.search(r'(\d+)', str(v))
    return int(m.group(1)) if m else 5


def load_char(cid):
    """把 nanoka 角色 JSON 适配进 CHARS/PROMO/SKILLS/RANKS/TREES。"""
    cid = str(cid)
    d = get_nanoka_char(cid)
    if not d:
        raise KeyError(f'nanoka 无角色 {cid}')

    ranks = d.get('ranks', {})
    rank_ids = [str(ranks[str(i)]['id']) for i in range(1, 7) if str(i) in ranks]
    skill_ids = [str(k) for k in d.get('skills', {}).keys()]
    tree_ids = [str(pv['1']['point_id']) for pv in d.get('skill_trees', {}).values() if '1' in pv]

    CHARS[cid] = {
        'id': cid, 'name': strip_tags(d['name']), 'rarity': rarity_int(d.get('rarity')),
        'path': d.get('base_type'), 'element': d.get('damage_type'),
        'max_sp': d.get('sp_need'), 'ranks': rank_ids, 'skills': skill_ids,
        'skill_trees': tree_ids,
    }

    s6 = d['stats']['6']
    vals = [None] * 7
    vals[6] = {
        'hp': {'base': s6['hp_base'], 'step': s6['hp_add']},
        'atk': {'base': s6['attack_base'], 'step': s6['attack_add']},
        'def': {'base': s6['defence_base'], 'step': s6['defence_add']},
        'spd': {'base': s6['speed_base'], 'step': 0},
        'taunt': {'base': s6['base_aggro'], 'step': 0},
        'crit_rate': {'base': s6['critical_chance'], 'step': 0},
        'crit_dmg': {'base': s6['critical_damage'], 'step': 0},
    }
    PROMO[cid] = {'values': vals}

    for sid, s in d.get('skills', {}).items():
        lv = s.get('level', {})
        maxl = len(lv)
        params = [lv[str(i)].get('param_list', []) for i in range(1, maxl + 1) if str(i) in lv]
        SKILLS[str(sid)] = {
            'id': str(sid), 'name': s.get('name', ''), 'type': s.get('type'),
            'type_text': s.get('type_name', ''), 'max_level': maxl,
            'desc': strip_tags(s.get('desc', '')), 'simple_desc': s.get('simple_desc', ''),
            'effect_text': TAG_CN.get(s.get('tag', ''), ''), 'params': params,
        }

    for k in sorted(ranks.keys(), key=int):
        r = ranks[k]
        rid = str(r['id'])
        RANKS[rid] = {
            'id': rid, 'name': strip_tags(r.get('name', '')), 'rank': int(k),
            'desc': strip_tags(r.get('desc', '')), 'params': r.get('param_list', []),
            'level_up_skills': [],  # 由 rank 描述重建，见 reconstruct_eidolon_boosts
        }

    for pk, pv in d.get('skill_trees', {}).items():
        lv = pv.get('1', {})
        pid = str(lv.get('point_id'))
        props = [{'type': a['property_type'], 'value': a['value']}
                 for a in (lv.get('status_add_list') or [])]
        TREES[pid] = {
            'id': pid, 'name': lv.get('point_name') or '', 'max_level': lv.get('max_level', 1),
            'desc': strip_tags(lv.get('point_desc') or ''),
            'params': [lv.get('param_list', [])] if lv.get('param_list') else [[]],
            'levels': [{'properties': props}],
            'level_up_skill_id': lv.get('level_up_skill_id', []),
        }

    reconstruct_eidolon_boosts(cid, d)
    return d


def reconstruct_eidolon_boosts(cid, d):
    """nanoka 星魂无 level_up_skills，靠 E3/E5 描述里“XX等级+N”重建。
    "普攻等级+1" 提升所有普攻类技能（含强化/变体），与 SRR 一致。"""
    ranks = d.get('ranks', {})
    for k in ('3', '5'):
        if k not in ranks:
            continue
        rid = str(ranks[k]['id'])
        desc = ranks[k].get('desc', '')
        boosts = []
        # 最长优先匹配：先试「忆灵天赋/忆灵技/助战技」再试短词，避免「助战技」被切成
        # 「战技」、「忆灵天赋」被切成「天赋」。忆灵技/忆灵天赋属 memosprite，不在主技能
        # 列表，映射后自然 no-op。
        for typ, num in re.findall(r'(忆灵天赋|忆灵技|助战技|普攻|战技|终结技|天赋|欢愉技)等级\+(\d+)', desc):
            for sid, s in d.get('skills', {}).items():
                if s.get('type_name') == typ:
                    boosts.append({'id': str(sid), 'num': int(num)})
        if rid in RANKS:
            RANKS[rid]['level_up_skills'] = boosts


# ==========================================================================
# 以下渲染逻辑复制自 gen_character.py（纯函数，读取上面适配好的全局结构）
# ==========================================================================
def get_nanoka_skill(cid, sid):
    d = get_nanoka_char(cid)
    if not d:
        return None
    skills = d.get('skills', {})
    sid = str(sid)
    if sid in skills:
        return skills[sid]
    if sid.startswith('1') and len(sid) > 6:
        base = sid[1:]
        if base in skills:
            return skills[base]
    return None


def get_enhanced_data(cid):
    d = get_nanoka_char(cid)
    return (d.get('enhanced') or None) if d else None


def get_elation_priority(cid):
    d = get_nanoka_char(cid)
    if not d:
        return None
    for sid, s in d.get('skills', {}).items():
        if s.get('type') == 'ElationDamage':
            v = s.get('elation_priority_value')
            if v is not None:
                return v
    return None


def format_stance(stance):
    if not stance:
        return None
    labels = ['单攻', '群攻', '扩散']
    parts = [f'{l} {v}' for l, v in zip(labels, stance) if v]
    return ' / '.join(parts) if parts else None


def format_sp_change(skill_data):
    if not skill_data:
        return None
    bp_need = skill_data.get('bp_need')
    bp_add = skill_data.get('bp_add')
    if bp_add and bp_add > 0:
        return f'+{bp_add}'
    if bp_need and bp_need > 0:
        return f'-{bp_need}'
    return None


def format_energy(skill_data):
    if not skill_data:
        return None
    sp = skill_data.get('sp_base')
    return f'+{sp}' if sp else None


PATH_CN = {'Warrior': '毁灭', 'Rogue': '巡猎', 'Mage': '智识', 'Shaman': '同谐',
           'Warlock': '虚无', 'Knight': '存护', 'Priest': '丰饶',
           'Memory': '记忆', 'Elation': '欢愉'}
ELEMENT_CN = {'Physical': '物理', 'Fire': '火', 'Ice': '冰', 'Thunder': '雷',
              'Wind': '风', 'Quantum': '量子', 'Imaginary': '虚数'}
PROP_NAME = {
    'AttackAddedRatio': '攻击力', 'HPAddedRatio': '生命值', 'DefenceAddedRatio': '防御力',
    'SpeedDelta': '速度', 'CriticalChanceBase': '暴击率', 'CriticalDamageBase': '暴击伤害',
    'StatusProbabilityBase': '效果命中', 'StatusResistanceBase': '效果抵抗',
    'BreakDamageAddedRatioBase': '击破特攻', 'SPRatioBase': '能量恢复效率',
    'HealRatioBase': '治疗量加成',
    'PhysicalAddedRatio': '物理属性伤害', 'FireAddedRatio': '火属性伤害',
    'IceAddedRatio': '冰属性伤害', 'ThunderAddedRatio': '雷属性伤害',
    'WindAddedRatio': '风属性伤害', 'QuantumAddedRatio': '量子属性伤害',
    'ImaginaryAddedRatio': '虚数属性伤害',
    'ElationDamageAddedRatioBase': '欢愉度',
}
# 跳过 nanoka 数据里「类型标错 + 描述为空」的重复技能条目（非独立技能）。
# 已核对 GachaBase：150909「漫不经心」被 nanoka 标为战技，实为普攻(150901)的空重复条目。
SKILL_SKIP = {'150909'}

# 人工补充：协议模式的队友触发说明（nanoka/SRR 数据源均无，此处固化以扛住重生成）
PROTOCOL_MODE_INTRO = {
    '1510': (
        '> 姬子•启行外的**开拓同行角色**施放助战技「开拓，与你同行」时，会根据该队友触发以下其中一种协议模式：\n'
        '> - **裁决**：开拓者（所有形态）、丹恒、丹恒•饮月、丹恒•腾荒、星期日\n'
        '> - **歼破**：三月七、三月七•巡猎、长夜月、瓦尔特、姬子'
    ),
}


def is_pct_param(desc, param_idx):
    return bool(re.search(rf'#{param_idx}\[\w*\]%', desc))


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


def compute_base_stats(cid):
    p = PROMO[cid]['values'][6]
    return {
        'hp': int(p['hp']['base'] + p['hp']['step'] * 79),
        'atk': int(p['atk']['base'] + p['atk']['step'] * 79),
        'def': int(p['def']['base'] + p['def']['step'] * 79),
        'spd': int(p['spd']['base']),
        'taunt': int(p['taunt']['base']),
        'crit_rate': p['crit_rate']['base'],
        'crit_dmg': p['crit_dmg']['base'],
    }


def get_traces(cid):
    totals = {}
    for i in range(201, 211):
        tid = f'{cid}{i:03d}'
        t = TREES.get(tid)
        if not t or not t.get('levels'):
            continue
        for prop in t['levels'][0].get('properties', []):
            ptype = prop['type']
            totals[ptype] = totals.get(ptype, 0) + prop['value']
    return totals


def get_unique_effects(cid):
    d = get_nanoka_char(cid)
    if not d:
        return []
    unique = d.get('unique')
    if not unique:
        return []
    effects = []
    for sid, u in unique.items():
        name = re.sub(r'<[^>]+>', '', u.get('name', ''))
        tag = u.get('tag', '')
        desc = u.get('desc', '')
        params = u.get('param', [])
        if params and desc:
            for i, v in enumerate(params):
                pct_pat = rf'#{i+1}\[\w*\]%'
                if re.search(pct_pat, desc):
                    val = v * 100 if isinstance(v, (int, float)) else v
                    val_s = f'{val:g}%'
                else:
                    val_s = f'{v:g}' if isinstance(v, float) else str(v)
                desc = re.sub(rf'#{i+1}\[\w*\]%?', val_s, desc)
        desc = re.sub(r'<[^>]+>', '', desc)
        effects.append({'name': name, 'tag': tag, 'desc': desc})
    return effects


def get_additional_abilities(cid, enhanced=False):
    prefix = '1' + cid if enhanced else cid
    abils = []
    for i in range(101, 104):
        tid = f'{prefix}{i:03d}'
        t = TREES.get(tid)
        if not t:
            continue
        params = t.get('params', [[]])
        params = params[0] if params else []
        desc = render_desc(t.get('desc', ''), params)
        if t.get('name'):
            abils.append({'name': t['name'], 'desc': desc})
    return abils


def get_eidolon_boosts(cid):
    char = CHARS[cid]
    ranks = char.get('ranks', [])
    e3 = RANKS.get(ranks[2], {}) if len(ranks) > 2 else {}
    e5 = RANKS.get(ranks[4], {}) if len(ranks) > 4 else {}
    e3_boosts = {b['id']: b['num'] for b in e3.get('level_up_skills', [])}
    e5_boosts = {b['id']: b['num'] for b in e5.get('level_up_skills', [])}
    return e3_boosts, e5_boosts


SKILL_ORDER = ['普攻', '强化普攻', '战技', '强化战技', '终结技', '强化终结技', '天赋', '欢愉技', '秘技', '助战技']


def tree_ultimate_ids(cid):
    d = get_nanoka_char(cid)
    if not d:
        return []
    for levels in d.get('skill_trees', {}).values():
        ids = [str(i) for i in levels.get('1', {}).get('level_up_skill_id', [])]
        if ids and SKILLS.get(ids[0], {}).get('type_text') == '终结技':
            return ids
    return []


def detect_enhanced_ult(cid):
    ults = tree_ultimate_ids(cid)
    if len(ults) < 2:
        return None
    base = ults[0]
    bname = SKILLS.get(base, {}).get('name', '')
    bdesc = re.sub(r'<[^>]+>', '', SKILLS.get(base, {}).get('desc', '') or '')
    for sid in ults[1:]:
        sname = SKILLS.get(sid, {}).get('name', '')
        if not sname or sname == bname:
            continue
        if sname not in bdesc or f'终结技【{sname}】' in bdesc:
            return sid
    return None


def build_skill_map(char, prefix, cid=None):
    skill_map = {}
    for sid in char.get('skills', []):
        if not sid.startswith(prefix):
            continue
        if sid in SKILL_SKIP:
            continue  # nanoka 误标 + 空描述的重复条目，跳过
        s = SKILLS.get(sid, {})
        if not s.get('name', '').strip():
            continue  # nanoka 有空名占位技能变体，SRR 会过滤，此处对齐
        type_text = s.get('type_text', '')
        max_lvl = s.get('max_level', 1)
        if type_text == '普攻':
            if max_lvl > 1 and '普攻' in skill_map:
                skill_map.setdefault('强化普攻', sid)
            else:
                skill_map.setdefault('普攻', sid)
        elif type_text == '战技' and max_lvl > 1:
            skill_map.setdefault('强化战技' if '战技' in skill_map else '战技', sid)
        elif type_text == '终结技':
            skill_map.setdefault('终结技', sid)
        elif type_text == '天赋':  # 部分 4.4 角色有第 2 天赋（联动连携机制）
            skill_map.setdefault('天赋', []).append(sid)
        elif type_text == '秘技':
            skill_map.setdefault('秘技', sid)
        elif type_text == '欢愉技':
            skill_map.setdefault('欢愉技', sid)
        elif type_text == '助战技':  # 4.4 新增技能类型（姬子•启行等），可有多个
            dsc = s.get('desc', '')
            # 「进入【…】状态」型助战技本质是模式/状态（如姬子的裁决/歼破），单列到协议模式
            if '进入【' in dsc and '状态' in dsc:
                skill_map.setdefault('协议模式', []).append(sid)
            else:
                skill_map.setdefault('助战技', []).append(sid)
    if cid:
        enh_ult = detect_enhanced_ult(cid)
        if enh_ult and enh_ult in SKILLS:
            skill_map['强化终结技'] = enh_ult
    return skill_map


def gen_skill_section(label, sid, e3_boosts, e5_boosts, cid=None):
    s = SKILLS.get(sid, {})
    if not s:
        return ''
    sname = s.get('name', '')
    effect = s.get('effect_text', '')
    max_lvl = s.get('max_level', 1)
    desc = s.get('desc', '')
    params_list = s.get('params', [])

    base_lv = 6 if label in ('普攻', '强化普攻') else 10
    e3_b = e3_boosts.get(sid, 0)
    e5_b = e5_boosts.get(sid, 0)

    if params_list:
        idx = max(0, min(base_lv, len(params_list)) - 1)
        rendered = render_desc(desc, params_list[idx], highlight=(max_lvl > 1))
    else:
        rendered = desc

    md = f'### {label} · {sname}'
    md += f'\n\n> {rendered}\n\n'

    if cid:
        nd = get_nanoka_skill(cid, sid)
        if nd:
            stance = format_stance(nd.get('show_stance_list'))
            sp = format_energy(nd)
            bp = format_sp_change(nd)
            meta = []
            if effect:
                meta.append(f'- 技能类型：{effect}')
            if stance:
                meta.append(f'- 韧性削减：{stance}')
            if sp:
                meta.append(f'- 能量回复：{sp}')
            if bp:
                meta.append(f'- 战技点变化：{bp}')
            if nd.get('type') == 'ElationDamage' and nd.get('elation_priority_value') is not None:
                meta.append(f"- 参演编号：{nd['elation_priority_value']}")
            if meta:
                md += '\n'.join(meta) + '\n\n'

    if max_lvl > 1 and params_list:
        placeholders = sorted({int(m.group(1)) for m in re.finditer(r'#(\d+)\[', desc)})
        if not placeholders:
            md += '---\n\n'
            return md
        levels = [(base_lv, '满级 (E0)')]
        if e3_b > 0:
            levels.append((min(max_lvl, base_lv + e3_b), '星魂 3'))
        if e5_b > 0:
            levels.append((min(max_lvl, base_lv + e3_b + e5_b), '星魂 5'))
        param_pcts = [is_pct_param(desc, p) for p in placeholders]
        headers = ['等级', '解锁条件'] + [f'参数 {p}{"(%)" if pct else ""}' for p, pct in zip(placeholders, param_pcts)]
        md += '| ' + ' | '.join(headers) + ' |\n'
        md += '|' + '|'.join(['---'] * len(headers)) + '|\n'
        for lv, lbl in levels:
            if lv > len(params_list):
                continue
            p = params_list[lv - 1]
            cells = [f'Lv {lv}', lbl]
            for ph, pct in zip(placeholders, param_pcts):
                if ph - 1 < len(p):
                    v = p[ph - 1]
                    cells.append(format_param(v, pct))
                else:
                    cells.append('—')
            md += '| ' + ' | '.join(cells) + ' |\n'
        md += '\n'
    md += '---\n\n'
    return md


def gen_character(cid):
    if int(cid) >= 8000:
        return None
    char = CHARS[cid]
    name = char['name']
    rarity = char['rarity']
    path = PATH_CN.get(char['path'], char['path'])
    element = ELEMENT_CN.get(char['element'], char['element'])
    max_sp = char['max_sp']

    base = compute_base_stats(cid)
    traces = get_traces(cid)
    abils = get_additional_abilities(cid)
    e3_boosts, e5_boosts = get_eidolon_boosts(cid)
    skill_map = build_skill_map(char, cid, cid=cid)

    elation_pid = get_elation_priority(cid) if path == '欢愉' else None
    elation_row = f'\n| 参演编号 | {elation_pid} |' if elation_pid is not None else ''

    md = f'''# {name} — ID {cid}

> 数据来源：[nanoka](https://hsr.nanoka.cc/character/{cid})（测试站 {NANOKA_VER} 数据）

## 基础信息

| 项目 | 值 |
|------|-----|
| 角色 ID | {cid} |
| 中文名 | {name} |
| 稀有度 | {'★'*rarity} |
| 属性 | {element} |
| 命途 | {path} |{elation_row}
| 能量上限 | {max_sp}{"（无常规能量）" if cid in NO_REGULAR_ENERGY else ""} |

## 基础属性 (Lv80 满晋阶)

| 属性 | 数值 |
|------|------|
| 生命值 | {base['hp']:,} |
| 攻击力 | {base['atk']:,} |
| 防御力 | {base['def']:,} |
| 速度 | {base['spd']} |
| 嘲讽值 | {base['taunt']} |
| 暴击率 | {base['crit_rate']*100:.0f}% |
| 暴击伤害 | {base['crit_dmg']*100:.0f}% |

## 行迹·总属性加成

| 项目 | 总加成 |
|------|--------|
'''
    for ptype, total in traces.items():
        pname = PROP_NAME.get(ptype, ptype)
        if ptype == 'SpeedDelta':
            md += f'| {pname} | +{int(total)} |\n'
        else:
            md += f'| {pname} | +{total*100:.1f}% |\n'
    md += '\n---\n\n## 技能\n\n'
    for label in SKILL_ORDER:
        sid = skill_map.get(label)
        if not sid:
            continue
        for one in (sid if isinstance(sid, list) else [sid]):
            md += gen_skill_section(label, one, e3_boosts, e5_boosts, cid=cid)
    modes = skill_map.get('协议模式')
    if modes:
        md += '## 协议模式\n\n'
        intro = PROTOCOL_MODE_INTRO.get(cid)
        if intro:
            md += intro.rstrip() + '\n\n'
        for one in modes:
            md += gen_skill_section('协议模式', one, e3_boosts, e5_boosts, cid=cid)
    if abils:
        md += '## 附加能力\n\n'
        for i, a in enumerate(abils, 1):
            md += f'### {i}. {a["name"]}\n\n> {a["desc"]}\n\n'
        md += '---\n\n'
    uniq = get_unique_effects(cid)
    if uniq:
        md += '## 专属效果\n\n'
        for u in uniq:
            tag_s = f'（{u["tag"]}）' if u['tag'] else ''
            md += f'### {u["name"]}{tag_s}\n\n> {u["desc"]}\n\n'
        md += '---\n\n'
    md += '## 星魂\n\n'
    for i, rid in enumerate(char.get('ranks', []), 1):
        r = RANKS.get(rid, {})
        rname = r.get('name', '')
        rdesc = r.get('desc', '')
        params = r.get('params', [])
        if params:
            rdesc = render_desc(rdesc, params)
        md += f'### E{i} · {rname}\n\n> {rdesc}\n\n'
    return md


def main():
    ids = sys.argv[1:]
    if not ids:
        print('Usage: gen_character_nanoka.py <id> [id ...]', file=sys.stderr)
        sys.exit(1)
    ok = 0
    errors = []
    for cid in ids:
        cid = str(cid)
        try:
            load_char(cid)
            md = gen_character(cid)
            if md:
                (OUT_DIR / f'{cid}.md').write_text(md)
                ok += 1
                print(f'  wrote {cid}.md')
        except Exception as e:
            errors.append((cid, repr(e)))
    print(f'Generated {ok} files. Errors: {len(errors)}')
    for cid, e in errors:
        print(f'  {cid}: {e}')


if __name__ == '__main__':
    main()
