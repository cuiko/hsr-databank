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
| `mihomo_to_config.py` | 通过 MiHoMo API 将玩家 UID 转为战斗模拟器 config.json |

> **兜底脚本用途**：联动/新版本刚上线时 Mar-7th StarRailRes 常滞后数天，此时原 `gen_*.py`
> 会 KeyError。改用 `gen_*_nanoka.py <id>` 从 nanoka 测试站生成；SRR 追上后可用原脚本重生成交叉校验。
>
> **`--beta` / `--dry-run`**（仅 nanoka 兜底脚本）：
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

## mihomo_to_config.py

```bash
# 输出到 stdout
python3 scripts/mihomo_to_config.py 104635151

# 写入文件
python3 scripts/mihomo_to_config.py 104635151 config.json
```
