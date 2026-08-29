# scripts/

可复用工具脚本，无第三方依赖，仅使用 Python 标准库。

**运行方式**：优先使用 [uv](https://github.com/astral-sh/uv)，未安装则直接用 `python3`：

```bash
# 有 uv
uv run python3 scripts/<name>.py

# 无 uv
python3 scripts/<name>.py
```

> 以下示例统一使用 `python3`，如已安装 uv 请自行替换为 `uv run python3`。

| 脚本 | 用途 |
|------|------|
| `gen_character.py` | 从 Mar-7th StarRailRes 拉数据生成 `references/character/{id}.md` |
| `gen_lightcone.py` | 从 Mar-7th StarRailRes 拉数据生成 `references/lightcone/{id}.md` |
| `gen_character_nanoka.py` | **SRR 兜底**：SRR 未收录时改用 nanoka 生成角色档案（格式对齐 `gen_character.py`） |
| `gen_lightcone_nanoka.py` | **SRR 兜底**：SRR 未收录时改用 nanoka 生成光锥档案 |
| `search_achievement.py` | 直接搜索 nanoka 在线成就库（不落地大文件）|
| `search_monster.py` | 在线搜索怪物：弱点/韧性/技能/变种（关键字/ID,不落地）|
| `mihomo_to_config.py` | 通过 MiHoMo API 将玩家 UID 转为战斗模拟器 config.json |
| `ci_refresh.py` | CI 增量刷新：检测正式服(SRR)已收录、本地缺失的角色/光锥并补齐（`--dry-run`）|
| `check_consistency.py` | 提交前自检：映射表同步、章节完整、记忆命途必有忆灵、档案标题不重名（`--warn` 只报告）|

> **兜底脚本用途**：联动/新版本刚上线时 Mar-7th StarRailRes 常滞后数天，此时原 `gen_*.py`
> 会 KeyError。改用 `gen_*_nanoka.py <id>` 从 nanoka 测试站生成；SRR 追上后可用原脚本重生成交叉校验。
>
> **`--source` / `--beta` / `--dry-run`**（仅 nanoka 兜底脚本）：
> - `--source X`：选数据源,默认 **nanoka**(完整可用)。`gachabase` / `huroka` 已注册为占位、暂未实现;新增一个源 = 实现对应加载/生成函数并注册进脚本里的 `SOURCE_LOADERS` / `SOURCE_GEN`。
> - `--beta`：输出到 `drafts/`（已 gitignore）而非 `references/`，把**测试服/未上线**内容本地缓存、不入库。
>   **不带 ID 时自动**从 nanoka `manifest.json` 的 `new` 字段取测试服新增,并让 `drafts/` **只保留这些新内容**（过时的自动清除）。
> - `--dry-run`：只打印将写入/清理哪些文件，**不落盘**（配合自动清理时先看会删什么）。
> - 例：`python3 scripts/gen_character_nanoka.py --beta`（自动补齐测试服新角色到 drafts/）
> - 上正式服后去掉 `--beta` 正式生成入 `references/` 即可。

## gen_character.py

```bash
# 生成所有角色
python3 scripts/gen_character.py

# 单个角色
python3 scripts/gen_character.py 1413
```

## gen_lightcone.py

```bash
# 生成所有光锥
python3 scripts/gen_lightcone.py

# 单个光锥（如大黑塔专属 23037）
python3 scripts/gen_lightcone.py 23037
```

## search_achievement.py

```bash
# 关键字（名称 / 描述 / ID 任一匹配）
python3 scripts/search_achievement.py "光锥"

# 按 ID 精确查
python3 scripts/search_achievement.py 4010101

# 按系列筛选 (1-9)
python3 scripts/search_achievement.py --series 1

# 仅显示隐藏成就
python3 scripts/search_achievement.py --hidden

# 限制条数（默认 50）
python3 scripts/search_achievement.py "光锥" --limit 10

# 输出 JSON
python3 scripts/search_achievement.py "光锥" --json
```

每次调用直接从 nanoka 拉数据，纯内存处理，不在磁盘留任何痕迹。

## search_monster.py

```bash
# 关键字（中文/英文名 / ID）
python3 scripts/search_monster.py 冰锋

# 按 ID 精确查（附 韧性/相位/属性 完整机制卡片）
python3 scripts/search_monster.py 8015050

# 每个结果都拉完整属性
python3 scripts/search_monster.py 丰饶 --full

# 按 rank 过滤（Minion / MinionLv2 / Elite / LittleBoss / BigBoss）
python3 scripts/search_monster.py --rank BigBoss

# JSON 输出
python3 scripts/search_monster.py 冰锋 --json
```

显示弱点、韧性、相位、基础属性、逐属性抗性、**技能/被动机制**、变体倍率。技能描述多为定性（少量/大量），**无精确倍率**（敌人技能倍率玩家端基本查不到，BWiki 亦无）。


## mihomo_to_config.py

```bash
# 输出到 stdout
python3 scripts/mihomo_to_config.py 104635151

# 写入文件
python3 scripts/mihomo_to_config.py 104635151 config.json
```

## ci_refresh.py

供 `.github/workflows/refresh-skill-data.yml` 调用的增量刷新编排：检测正式服
（Mar-7th StarRailRes）已收录、本地 `references/` 缺失的角色/光锥并逐个补齐。
只补新增、不整库重生成，请求量小、规避限流；角色/光锥走 SRR（跟正式服），不会
提前引入测试服 beta。

```bash
# 只检测缺口，不生成
python3 scripts/ci_refresh.py --dry-run

# 补齐缺失角色/光锥
python3 scripts/ci_refresh.py

```

> 手动/定时触发见 `.github/workflows/refresh-skill-data.yml`（默认仅手动；定时块留了可
> 自定义的 cron 注释）。改动以 PR 交付，合并前人工核对生成局限。
