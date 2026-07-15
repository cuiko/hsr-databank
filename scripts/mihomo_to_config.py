#!/usr/bin/env python3
"""通过 MiHoMo API 将玩家 UID 数据转为模拟器 config.json 格式

Usage:
  uv run python3 scripts/mihomo_to_config.py <UID> [output_path]
  默认输出到 stdout, 可重定向到文件
"""
import json, urllib.request, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _hsr_common import NO_REGULAR_ENERGY

UA = {'User-Agent': 'hsr-databank'}

# 副词条 type → integer ID
SUB_AFFIX = {
    'HPDelta': 1, 'AttackDelta': 2, 'DefenceDelta': 3,
    'HPAddedRatio': 4, 'AttackAddedRatio': 5, 'DefenceAddedRatio': 6,
    'SpeedDelta': 7, 'CriticalChanceBase': 8, 'CriticalDamageBase': 9,
    'StatusProbabilityBase': 10, 'StatusResistanceBase': 11,
    'BreakDamageAddedRatioBase': 12,
}

# 主词条 type → ID（按部位 type 1-6）
MAIN_BY_SLOT = {
    1: {'HPDelta': 1},                                          # 头
    2: {'AttackDelta': 1},                                      # 手
    3: {'HPAddedRatio': 1, 'AttackAddedRatio': 2, 'DefenceAddedRatio': 3,  # 躯干
        'CriticalChanceBase': 4, 'CriticalDamageBase': 5,
        'HealRatioBase': 6, 'StatusProbabilityBase': 7},
    4: {'HPAddedRatio': 1, 'AttackAddedRatio': 2, 'DefenceAddedRatio': 3,  # 脚
        'SpeedDelta': 4},
    5: {'HPAddedRatio': 1, 'AttackAddedRatio': 2, 'DefenceAddedRatio': 3,  # 球
        'PhysicalAddedRatio': 4, 'FireAddedRatio': 5, 'IceAddedRatio': 6,
        'ThunderAddedRatio': 7, 'WindAddedRatio': 8,
        'QuantumAddedRatio': 9, 'ImaginaryAddedRatio': 10},
    6: {'HPAddedRatio': 1, 'AttackAddedRatio': 2, 'DefenceAddedRatio': 3,  # 绳
        'BreakDamageAddedRatioBase': 4, 'SPRatioBase': 5},
}



def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def encode_relic(r):
    """parsed relic dict → 'id,level,main,cnt,sub1,sub2,sub3,sub4'"""
    slot = r['type']
    main_id = MAIN_BY_SLOT[slot].get(r['main_affix']['type'])
    if main_id is None:
        raise ValueError(f"Unknown main affix {r['main_affix']['type']} (slot {slot})")
    sub = r.get('sub_affix', [])
    parts = [str(r['id']), str(r['level']), str(main_id), str(len(sub))]
    for s in sub:
        sid = SUB_AFFIX.get(s['type'])
        if sid is None:
            raise ValueError(f"Unknown sub affix {s['type']}")
        parts.append(f"{sid}:{s['count']}:{s.get('step', 0)}")
    return ','.join(parts)


def convert(uid, lang='cn'):
    parsed = fetch(f'https://api.mihomo.me/sr_info_parsed/{uid}?l={lang}')
    avatar_config = []
    for c in parsed.get('characters', []):
        cid = c['id']
        lc = c.get('light_cone') or {}
        avatar_config.append({
            'name': c['name'],
            'id': int(cid),
            'hp': 100,
            'sp': 0 if cid in NO_REGULAR_ENERGY else 50,
            'level': c['level'],
            'promotion': c['promotion'],
            'rank': c['rank'],
            'lightcone': {
                'id': int(lc['id']),
                'rank': lc['rank'],
                'level': lc['level'],
                'promotion': lc['promotion'],
            } if lc.get('id') else None,
            'relics': [encode_relic(r) for r in c.get('relics', [])],
            'use_technique': True,
        })
    return {
        'avatar_config': avatar_config,
        'battle_config': {
            'battle_id': 1, 'stage_id': 0, 'cycle_count': 30,
            'monster_wave': [], 'monster_level': 95, 'blessings': [],
        },
    }


def main():
    if len(sys.argv) < 2:
        print('Usage: mihomo_to_config.py <UID> [output_path]', file=sys.stderr)
        sys.exit(1)
    uid = sys.argv[1]
    config = convert(uid)
    out = json.dumps(config, indent=2, ensure_ascii=False)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(out + '\n')
        print(f'Wrote {sys.argv[2]} ({len(config["avatar_config"])} characters)', file=sys.stderr)
    else:
        print(out)


if __name__ == '__main__':
    main()
