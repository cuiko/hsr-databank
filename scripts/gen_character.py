#!/usr/bin/env python3
"""批量生成 references/character/{id}.md, 数据来源 Mar-7th StarRailRes

Usage:
  uv run python3 scripts/gen_character.py [character_id]
  不带参数时生成所有角色
"""
import json, re, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hsr_common import NO_REGULAR_ENERGY

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'references' / 'character'
OUT_DIR.mkdir(parents=True, exist_ok=True)
RAW = 'https://raw.githubusercontent.com/Mar-7th/StarRailRes/master/index_min/cn'

def fetch(name):
    url = f'{RAW}/{name}.json'
    req = urllib.request.Request(url, headers={'User-Agent': 'hsr-databank'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def fetch_url(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'hsr-databank',
        'Referer': 'https://hsr.nanoka.cc/',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

print('Fetching Mar-7th data...')
CHARS = fetch('characters')
PROMO = fetch('character_promotions')
SKILLS = fetch('character_skills')
RANKS = fetch('character_ranks')
TREES = fetch('character_skill_trees')

# 获取 nanoka 最新版本号 (用于补充欢愉角色「参演编号」字段)
try:
    NANOKA_VER = fetch_url('https://static.nanoka.cc/manifest.json')['hsr']['latest']
    print(f'Nanoka HSR version: {NANOKA_VER}')
except Exception as e:
    print(f'Warning: nanoka manifest unavailable ({e}); 参演编号将无法获取')
    NANOKA_VER = None

# 缓存 nanoka 角色 JSON
_NANOKA_CACHE = {}
def get_nanoka_char(cid):
    """拉取 nanoka 的角色完整 JSON"""
    if not NANOKA_VER: return None
    if cid in _NANOKA_CACHE: return _NANOKA_CACHE[cid]
    try:
        url = f'https://static.nanoka.cc/hsr/{NANOKA_VER}/zh/character/{cid}.json'
        _NANOKA_CACHE[cid] = fetch_url(url)
    except Exception:
        _NANOKA_CACHE[cid] = None
    return _NANOKA_CACHE[cid]

def get_nanoka_skill(cid, sid):
    """获取 nanoka 中某个技能的元数据。加强状态技能 ID 形如 '1{cid}xxx'，nanoka 不单独存放这些，回退到去前缀的 base ID"""
    d = get_nanoka_char(cid)
    if not d: return None
    skills = d.get('skills', {})
    sid = str(sid)
    if sid in skills:
        return skills[sid]
    # 加强状态技能：1{cid}xxx → 去掉首位的 '1' 试 base
    if sid.startswith('1') and len(sid) > 6:
        base = sid[1:]
        if base in skills:
            return skills[base]
    return None

def get_enhanced_data(cid):
    """获取角色的加强效果数据 (nanoka enhanced 字段)"""
    d = get_nanoka_char(cid)
    if not d: return None
    enh = d.get('enhanced')
    return enh if enh else None

def get_elation_priority(cid):
    """欢愉角色的参演编号；非欢愉角色返回 None"""
    d = get_nanoka_char(cid)
    if not d: return None
    for sid, s in d.get('skills', {}).items():
        if s.get('type') == 'ElationDamage':
            v = s.get('elation_priority_value')
            if v is not None: return v
    return None

def format_stance(stance):
    """show_stance_list [a, b, c] → '单攻 a / 群攻 b / 扩散 c'，0 值省略"""
    if not stance: return None
    labels = ['单攻', '群攻', '扩散']
    parts = [f'{l} {v}' for l, v in zip(labels, stance) if v]
    return ' / '.join(parts) if parts else None

def format_sp_change(skill_data):
    """普攻 +1，战技 -1，其他 — """
    if not skill_data: return None
    bp_need = skill_data.get('bp_need')
    bp_add = skill_data.get('bp_add')
    if bp_add and bp_add > 0: return f'+{bp_add}'
    if bp_need and bp_need > 0: return f'-{bp_need}'
    return None

def format_energy(skill_data):
    if not skill_data: return None
    sp = skill_data.get('sp_base')
    return f'+{sp}' if sp else None

PATH_CN = {'Warrior':'毁灭','Rogue':'巡猎','Mage':'智识','Shaman':'同谐',
           'Warlock':'虚无','Knight':'存护','Priest':'丰饶',
           'Memory':'记忆','Elation':'欢愉'}
ELEMENT_CN = {'Physical':'物理','Fire':'火','Ice':'冰','Thunder':'雷',
              'Wind':'风','Quantum':'量子','Imaginary':'虚数'}
PROP_NAME = {
    'AttackAddedRatio':'攻击力','HPAddedRatio':'生命值','DefenceAddedRatio':'防御力',
    'SpeedDelta':'速度','CriticalChanceBase':'暴击率','CriticalDamageBase':'暴击伤害',
    'StatusProbabilityBase':'效果命中','StatusResistanceBase':'效果抵抗',
    'BreakDamageAddedRatioBase':'击破特攻','SPRatioBase':'能量恢复效率',
    'HealRatioBase':'治疗量加成',
    'PhysicalAddedRatio':'物理属性伤害','FireAddedRatio':'火属性伤害',
    'IceAddedRatio':'冰属性伤害','ThunderAddedRatio':'雷属性伤害',
    'WindAddedRatio':'风属性伤害','QuantumAddedRatio':'量子属性伤害',
    'ImaginaryAddedRatio':'虚数属性伤害',
    'ElationDamageAddedRatioBase':'欢愉度',
}

def is_pct_param(desc, param_idx):
    """判断 #N 占位符在 desc 中是否后跟 %"""
    pattern = rf'#{param_idx}\[\w*\]%'
    return bool(re.search(pattern, desc))

def format_param(v, is_pct):
    if is_pct:
        return f'{v*100:.1f}%' if isinstance(v, float) else f'{int(v)*100}%'
    if isinstance(v, float) and v != int(v):
        return f'{v}'
    return str(int(v))

def render_desc(desc, params, highlight=False):
    """替换 #N[fmt] 占位符为具体数值。highlight=True 时高亮数值并标记参数序号。"""
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
        if not t or not t.get('levels'): continue
        for prop in t['levels'][0].get('properties', []):
            ptype = prop['type']
            totals[ptype] = totals.get(ptype, 0) + prop['value']
    return totals

def get_unique_effects(cid):
    """专属效果（仓库技）：nanoka unique 字段"""
    d = get_nanoka_char(cid)
    if not d: return []
    unique = d.get('unique')
    if not unique: return []
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
    """附加能力。enhanced=True 时取加强状态版本（树节点 ID 前缀加 '1'）"""
    prefix = '1' + cid if enhanced else cid
    abils = []
    for i in range(101, 104):
        tid = f'{prefix}{i:03d}'
        t = TREES.get(tid)
        if not t: continue
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

SKILL_ORDER = ['普攻','强化普攻','战技','强化战技','终结技','强化终结技','天赋','欢愉技','秘技','助战技']

# 人工补充：协议模式的队友触发说明（nanoka/SRR 数据源均无，此处固化以扛住重生成）
PROTOCOL_MODE_INTRO = {
    '1510': (
        '> 姬子•启行外的**开拓同行角色**施放助战技「开拓，与你同行」时，会根据该队友触发以下其中一种协议模式：\n'
        '> - **裁决**：开拓者（所有形态）、丹恒、丹恒•饮月、丹恒•腾荒、星期日\n'
        '> - **歼破**：三月七、三月七•巡猎、长夜月、瓦尔特、姬子'
    ),
}

def tree_ultimate_ids(cid):
    """从 nanoka skill_trees 的终结技节点取规范终结技 ID 列表（按盘面顺序）。
    该列表只含游戏技能盘展示的终结技，自动排除 Mar-7th 里的空占位条目（如乱破 131714-717）。"""
    d = get_nanoka_char(cid)
    if not d: return []
    for levels in d.get('skill_trees', {}).values():
        ids = [str(i) for i in levels.get('1', {}).get('level_up_skill_id', [])]
        if ids and SKILLS.get(ids[0], {}).get('type_text') == '终结技':
            return ids
    return []

def detect_enhanced_ult(cid):
    """识别「真·第二终结技」（强化终结技）。返回技能 ID 或 None。
    判据（数据驱动，无需枚举）：取技能盘终结技节点的技能列表，主体为第一个；
    其余每个候选，若其技名「未出现在主终结技描述中」（银枝/昔涟，独立终结技），
    或以「终结技【技名】」形式出现（千冶刃"获得全新终结技【…】"），即为强化终结技；
    若以子技能形式被调用（黄泉"发动N次【啼泽雨斩】"、飞霄"发动【闪裂刃舞】"）则为
    多段终结技的子段，跳过。同名变体（飞霄充能态）一并跳过。"""
    ults = tree_ultimate_ids(cid)
    if len(ults) < 2: return None
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
    """按 type_text 给技能分类。prefix = 技能 ID 前缀（常规 = cid；加强状态 = '1'+cid）。
    普攻/战技 的第二个自动归为「强化xxx」（其子技能/变体不属普攻/战技，不会污染）。
    终结技只取第一个为主体；强化终结技经 detect_enhanced_ult 判定后由 cid 传入时补入。"""
    skill_map = {}
    for sid in char.get('skills', []):
        if not sid.startswith(prefix): continue
        s = SKILLS.get(sid, {})
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
        elif type_text == '天赋': skill_map.setdefault('天赋', sid)
        elif type_text == '秘技': skill_map.setdefault('秘技', sid)
        elif type_text == '欢愉技': skill_map.setdefault('欢愉技', sid)
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
    if not s: return ''
    sname = s.get('name', '')
    effect = s.get('effect_text', '')
    max_lvl = s.get('max_level', 1)
    desc = s.get('desc', '')
    params_list = s.get('params', [])

    # E0 满级（默认值，所有玩家都能达到）
    base_lv = 6 if label in ('普攻', '强化普攻') else 10
    e3_b = e3_boosts.get(sid, 0)
    e5_b = e5_boosts.get(sid, 0)

    # 描述用 E0 满级 params 渲染（不带星魂加成，反映通用基线）
    # 可升级技能用 highlight 标记参数索引以对照参数表；不可升级（秘技等）不标
    if params_list:
        idx = max(0, min(base_lv, len(params_list)) - 1)
        rendered = render_desc(desc, params_list[idx], highlight=(max_lvl > 1))
    else:
        rendered = desc

    md = f'### {label} · {sname}'
    md += f'\n\n> {rendered}\n\n'

    # 元信息（从 nanoka 拉）：技能效果 / 韧性削减 / 能量回复 / 战技点变化
    if cid:
        nd = get_nanoka_skill(cid, sid)
        if nd:
            stance = format_stance(nd.get('show_stance_list'))
            sp = format_energy(nd)
            bp = format_sp_change(nd)
            meta = []
            if effect: meta.append(f'- 技能类型：{effect}')
            if stance: meta.append(f'- 韧性削减：{stance}')
            if sp: meta.append(f'- 能量回复：{sp}')
            if bp: meta.append(f'- 战技点变化：{bp}')
            # 欢愉技额外标参演编号
            if nd.get('type') == 'ElationDamage' and nd.get('elation_priority_value') is not None:
                meta.append(f"- 参演编号：{nd['elation_priority_value']}")
            if meta:
                md += '\n'.join(meta) + '\n\n'

    if max_lvl > 1 and params_list:
        # 找占位符
        placeholders = sorted({int(m.group(1)) for m in re.finditer(r'#(\d+)\[', desc)})
        if not placeholders:
            md += '---\n\n'
            return md
        # 等级
        levels = [(base_lv, '满级 (E0)')]
        if e3_b > 0:
            levels.append((min(max_lvl, base_lv + e3_b), '星魂 3'))
        if e5_b > 0:
            levels.append((min(max_lvl, base_lv + e3_b + e5_b), '星魂 5'))
        # 表头: 标注每个 placeholder 是否 %
        param_pcts = [is_pct_param(desc, p) for p in placeholders]
        headers = ['等级', '解锁条件'] + [f'参数 {p}{"(%)" if pct else ""}' for p, pct in zip(placeholders, param_pcts)]
        md += '| ' + ' | '.join(headers) + ' |\n'
        md += '|' + '|'.join(['---']*len(headers)) + '|\n'
        for lv, lbl in levels:
            if lv > len(params_list): continue
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
    if int(cid) >= 8000: return None
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
    
    # 跳过克隆版本（1xxxxxx 形式），只处理本角色 cid 前缀的技能
    skill_map = build_skill_map(char, cid, cid=cid)

    elation_pid = get_elation_priority(cid) if path == '欢愉' else None
    elation_row = f'\n| 参演编号 | {elation_pid} |' if elation_pid is not None else ''

    md = f'''# {name}

> 数据来源：[Mar-7th StarRailRes](https://github.com/Mar-7th/StarRailRes)（cn 索引）

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

def gen_enhanced(cid):
    """对有 nanoka enhanced 字段的角色生成 -enhanced.md，包含加强效果的完整技能组 + 加强要点 + 专属星魂"""
    enh = get_enhanced_data(cid)
    if not enh: return None
    char = CHARS[cid]
    name = char['name']
    # 加强状态星魂 ID 形式：'1' + 常规 rank id（如常规 131003 → 加强 1131003）
    enh_e3_id = f'1{cid}03'
    enh_e5_id = f'1{cid}05'
    e3 = RANKS.get(enh_e3_id, {})
    e5 = RANKS.get(enh_e5_id, {})
    e3_b = {b['id']: b['num'] for b in e3.get('level_up_skills', [])}
    e5_b = {b['id']: b['num'] for b in e5.get('level_up_skills', [])}

    # 加强状态技能 ID 形式：'1' + cid + 后缀（如 1131001 = 流萤加强状态普攻）
    enh_prefix = '1' + cid
    enh_skill_map = build_skill_map(char, enh_prefix)

    # 共享数据（属性/命途/基础属性/行迹/附加能力 与未加强状态一致）
    rarity = char['rarity']
    path = PATH_CN.get(char['path'], char['path'])
    element = ELEMENT_CN.get(char['element'], char['element'])
    max_sp = char['max_sp']
    base = compute_base_stats(cid)
    traces = get_traces(cid)
    abils = get_additional_abilities(cid, enhanced=True)  # 加强状态附加能力
    elation_pid = get_elation_priority(cid) if path == '欢愉' else None
    elation_row = f'\n| 参演编号 | {elation_pid} |' if elation_pid is not None else ''

    md = f'''# {name} (加强状态)

> 数据来源：[Mar-7th StarRailRes](https://github.com/Mar-7th/StarRailRes) + nanoka.cc。
> 未加强状态见 [`{cid}.md`]({cid}.md)。

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

    # 强化要点
    md += '\n---\n\n'
    for v_key in sorted(enh.keys()):
        v = enh[v_key]
        descs = [x for x in v.get('descs', []) if x]
        clean_descs = [re.sub(r'<[^>]+>', '', d) for d in descs]
        if clean_descs:
            md += f'## 强化 V{v_key} 要点\n\n'
            for d in clean_descs:
                md += f'- {d}\n'
            md += '\n'

    # 加强状态技能组
    if enh_skill_map:
        md += '---\n\n## 技能（加强状态）\n\n'
        for label in SKILL_ORDER:
            sid = enh_skill_map.get(label)
            if not sid:
                continue
            for one in (sid if isinstance(sid, list) else [sid]):
                md += gen_skill_section(label, one, e3_b, e5_b, cid=cid)

    # 附加能力（与未加强状态一致）
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

    # 加强状态星魂（替代常规星魂）
    for v_key in sorted(enh.keys()):
        v = enh[v_key]
        ranks = v.get('ranks', {})
        if not ranks: continue
        md += '## 星魂\n\n'
        for rk in sorted(ranks.keys(), key=int):
            r = ranks[rk]
            rname = r.get('name', '')
            rdesc = r.get('desc', '')
            p = r.get('param_list', [])
            rdesc = re.sub(r'<[^>]+>', '', rdesc)
            if p:
                rdesc = render_desc(rdesc, p)
            md += f'### E{rk} · {rname}\n\n> {rdesc}\n\n'
    return md

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    cids = [target] if target else sorted(CHARS.keys(), key=lambda x: int(x) if x.isdigit() else 99999)
    ok = 0; errors = []
    for cid in cids:
        if int(cid) >= 8000: continue
        try:
            md = gen_character(cid)
            if md:
                (OUT_DIR / f'{cid}.md').write_text(md)
                ok += 1
            enh_md = gen_enhanced(cid)
            if enh_md:
                (OUT_DIR / f'{cid}-enhanced.md').write_text(enh_md)
                ok += 1
        except Exception as e:
            errors.append((cid, str(e)))
    print(f'Generated {ok} files. Errors: {len(errors)}')
    for cid, e in errors[:5]:
        print(f'  {cid}: {e}')

if __name__ == '__main__':
    main()
