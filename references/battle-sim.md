# 战斗模拟配置（Battle Simulation）

> 本文件从 SKILL.md「四、战斗模拟配置」抽离。涉及「UID 转 config」「战斗模拟」「config.json 字段/遗器编码/引导流程」时读取。字段格式以 [`config.schema.json`](../config.schema.json) 为准（其余相对路径均相对仓库根目录）。

### ⚠️ 数值计算原则（必读）

`references/character/{id}.md` 里每个技能段的「韧性削减 / 能量回复 / 战技点变化」**只是基础值**（来自 nanoka `show_stance_list` / `sp_base` / `bp_add` 字段），**不能直接当最终值用**。模拟战斗时必须把以下来源叠加进去再算：

| 增量来源 | 在哪里读 | 典型例子 |
|---------|---------|---------|
| **附加能力（行迹）** | 角色档案的「## 附加能力」段 | 花火附加能力 1「岁时记」：普攻额外 +10 能量 → 实际普攻 = 20+10 = 30 |
| **星魂效果** | 角色档案的「## 星魂」段 | 大黑塔 E2「穿过锁孔之风」：进战斗 +1 灵感 |
| **专属光锥被动** | `references/lightcone/{id}.md` 叠影描述 | 「向着不可追问处」S1：终结技消耗 ≥140 能量后 +1 战技点 |
| **遗器套装效果** | `references/mapping-relic.md` | 「晨昏交界的翔鹰」4pc：终结技后行动提前 25% |
| **位面饰品 2pc** | 同上 | 「翁瓦克」2pc：能量恢复效率 +5% |
| **环境 buff / 关卡机制** | nanoka 终局节查询 | 末日幻影赛季 buff、忆灵紊流、阿哈裁决象限等 |
| **队友提供的增益** | 队友档案 | 花火战技：使队友造成的伤害提高 X% |
| **能量恢复效率乘区** | 角色总属性加成 + 装备 + 队友 | 最终能量回复 = 基础能量 × (1 + 能量恢复效率%) |

**常见错误**：
- ❌ 直接将花火普攻段的「能量回复：+20」作为最终回能
- ✅ 正确做法：以花火为例，普攻回能 = 技能基础值（20）+ 附加能力1（10）= **30**，最终回能 = 30 × (1 + 能量恢复效率%)

**关键技能伤害计算**同理：
- 角色档案里技能描述写的倍率 = E0 满级**基础倍率**
- 实际伤害还要考虑：星魂解锁的额外效果、角色的技能倍率、buff 加成（如光锥「向着不可追问处」终结技后战技伤害 +60%）、敌方韧性击破状态、易伤、增伤、抗性、防御系数等

> **建议工作流**：模拟前先逐一过角色的 附加能力 + 星魂 + 光锥 + 套装 + 队友增益，整理成一份"buff 清单"，注意各 buff 的持续回合，然后在每一回合的伤害/能量计算时把对应项叠进去。

### 4.1 数据获取

#### 方式 A：用户提供 config.json

直接进入引导流程。

#### 方式 B：通过 UID 拉取（**主路径**）

询问玩家 UID 与区服后，调用脚本：

```bash
python3 scripts/mihomo_to_config.py <UID> [output_path]
```

底层调用 `https://api.mihomo.me/sr_info_parsed/{UID}?l=cn`，返回展柜全部角色（约 7~8 个，含支援），脚本按 4.2 解析规范自动拼装为 config.json。

> 若需要更原始数据：`/sr_info/{UID}`（Enka 原始结构）；玩家近期完成的高难关卡：`/sr_activity/{UID}?l=cn`。

### 4.2 引导流程

**第一步：选择队伍**

展示导入的角色列表后，提示：

```
导入完成，共 N 个角色：

| 编号 | 角色 | 等级 | 星魂 |
|------|------|------|------|
| 1 | xxx | 80 | E0 |
| ... | ... | ... | ... |

请选择队伍（1~4 个角色），用逗号分隔编号，可附加修饰符：

- `y`/`n` — 是否使用秘技（默认 y）
- 数字 — 初始能量百分比（默认 50）
- `a` — 由该角色攻击怪物（默认第一个）

示例：
- `1,2,3,4` → 全默认
- `1,2a,3n,4` → 角色 2 攻击，角色 3 不用秘技
- `1y0,2n60a,3,4` → 角色 1 能量 0%，角色 2 不秘技 + 60% 能量 + 攻击
```

解析规则：
- `编号` 必填，可选修饰符顺序固定为 秘技 → 能量 → 攻击
- 编号可拼接（`1234` ≡ `1,2,3,4`，仅限单位数）
- 无常规能量角色 `sp` 自动 0，能量设置忽略

**第二步：确认遗器**

询问是否沿用导入的遗器配置（y/n）；`n` 进入手动调整。

**生成完成后**展示概览：

```
| 角色 | 星魂 | 光锥 | 秘技 | 能量 | 攻击 |
|------|------|------|------|------|------|
| xxx  | E0   | xxx S1 | y  | 50%  | ✓    |
```

### 4.3 config.json 字段规范

#### avatar_config

| 字段 | 类型 / 默认 | 说明 |
|------|------------|------|
| `id` | int | 角色 ID（[映射表](references/mapping-char2lc.md)） |
| `name` | string | 中文名（仅辅助阅读，以 `id` 为准） |
| `level` / `promotion` | int | 等级 / 晋阶 |
| `rank` | int 0-6 | 星魂数（E0-E6） |
| `hp` | int = 100 | 初始 生命值%（满血 100） |
| `sp` | int 0-100 | 初始能量%（默认 50；无常规能量角色固定 0） |
| `use_technique` | bool = true | 是否使用秘技入场 |
| `lightcone` | object | `{id, rank, level, promotion}` |
| `relics` | string[] | 6 件遗器，每件按下方编码 |
| `buff_id_list` | int[] 可选 | 角色生效的 Buff ID 列表（秘技/星魂 buff） |

#### relic 字符串编码

```
{遗器ID},{等级},{主词条ID},{初始副词条数},{副词条1},{副词条2},{副词条3},{副词条4}
```

- **遗器 ID** = `6{套装ID 3位}{部位 1-6}`（套装 ID 见 [mapping-relic.md](references/mapping-relic.md)）
- **部位**：1=头, 2=手, 3=躯干, 4=脚, 5=位面球, 6=连结绳
- **副词条**：`{属性ID}:{词条数}:{最高档位数}`
- 5★ Lv15 满级时，4 个副词条 cnt 之和 = 9（4 初始 + 5 强化）；`initialSubCount` 为 3 或 4

**主词条 / 副词条 ID 表**：详见 [`references/mapping-affix.md`](references/mapping-affix.md)（含按部位的主词条 ID 与各档位数值）。

#### battle_config

| 字段 | 默认 | 说明 |
|------|------|------|
| `battle_id` | 1 | 战斗编号 |
| `stage_id` | 0 | 关卡 ID（指定具体关卡时填） |
| `cycle_count` | 30 | 回合上限 |
| `monster_wave` | `[]` | 二维数组，每子数组为一波怪物 ID |
| `monster_level` | 95 | 怪物等级 |
| `blessings` | `[]` | 祝福列表（混沌回忆/虚构叙事等） |

> 用户指定关卡时，按对应 endgame 节查 nanoka 拿 `monster_wave` 与 `monster_level`。

### 4.4 MiHoMo parsed → config.json 映射表

转换逻辑已封装在 `scripts/mihomo_to_config.py`，关键映射如下：

#### 副词条 type → ID（`SUB_AFFIX`）

```
HPDelta=1, AttackDelta=2, DefenceDelta=3,
HPAddedRatio=4, AttackAddedRatio=5, DefenceAddedRatio=6,
SpeedDelta=7, CriticalChanceBase=8, CriticalDamageBase=9,
StatusProbabilityBase=10, StatusResistanceBase=11,
BreakDamageAddedRatioBase=12
```

#### 主词条 type → ID（按部位 `MAIN_BY_SLOT`）

| 部位 (type) | type 字符串 → ID |
|-------------|------------------|
| 1 头 | `HPDelta=1` |
| 2 手 | `AttackDelta=1` |
| 3 躯干 | `HPAddedRatio=1, AttackAddedRatio=2, DefenceAddedRatio=3, CriticalChanceBase=4, CriticalDamageBase=5, HealRatioBase=6, StatusProbabilityBase=7` |
| 4 脚 | `HPAddedRatio=1, AttackAddedRatio=2, DefenceAddedRatio=3, SpeedDelta=4` |
| 5 球 | `HPAddedRatio=1, AttackAddedRatio=2, DefenceAddedRatio=3, PhysicalAddedRatio=4, FireAddedRatio=5, IceAddedRatio=6, ThunderAddedRatio=7, WindAddedRatio=8, QuantumAddedRatio=9, ImaginaryAddedRatio=10` |
| 6 绳 | `HPAddedRatio=1, AttackAddedRatio=2, DefenceAddedRatio=3, BreakDamageAddedRatioBase=4, SPRatioBase=5` |

