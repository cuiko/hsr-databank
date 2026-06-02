# Project Guidelines

## 工具脚本（优先使用）

涉及数据生成 / 查询 / 转换时，**优先活用 `scripts/` 下的现成脚本，不要手写或手动抓数据**（手写易漏字段、格式不一致）。开始相关任务前先阅读 [`scripts/README.md`](scripts/README.md) 了解可用脚本及用法。

> 若现有脚本不满足需求，先考虑扩展脚本而非临时手工操作，保证流程可复现。

## Commit / Push Workflow

当用户要求提交或推送时，**必须先 review 所有本次变更涉及的文档**：

1. 检查是否存在歧义、不理解、重复的内容
2. 若发现问题，列出问题及可供参考的操作选项，等待用户确认
3. 用户确认后，重复上述流程，直到文档逻辑无误
4. 确认无问题后才可执行 `git commit` / `git push`

### 内容追加确认

每当文档更新时，需同步确认是否有新增内容（角色 / 光锥 / 遗器）。对照正式服当前版本，检查本地数据是否已覆盖最新内容；若有缺失，列出待补充项并等待用户确认后再处理。完整流程见下文「大版本更新流程」。

### 推送前版本号更新

每次执行 `git push` 前，需要获取当前正式服版本号，更新 README.md 顶部的版本徽标。版本号统一使用 `vx.y.z` 格式。目前只需要正式服版本号。

依次尝试以下三个站点（SKILL.md「六、参考链接 > 测试服」），任一成功即可：

1. **nanoka.cc** (`https://hsr.nanoka.cc/`)（推荐，零点击）
   - 使用浏览器打开首页，首页中部直接显示：
     - `Live Version` → 正式服版本号
     - `Latest Data Version` → 测试服版本号
   - 右上角版本下拉菜单中，标记 `(live)` 的为正式服，标记 `(latest)` 的为测试服

2. **GachaBase** (`https://hsr.gachabase.net/characters?lang=chs`)
   - 使用浏览器打开角色页，左侧边栏底部直接显示当前分支的版本标签
   - 正式服：默认即显示，如 `v4.2.0 (REL)`
   - 测试服：点击左上角 Settings → Branch Select 选择 `Beta` → Save Settings，页面刷新后侧边栏底部显示如 `v4.2.53 (BETA)`

3. **Huroka** (`https://www.huroka.com/`)
   - 使用浏览器打开首页，点击右上角 Settings 按钮
   - `Data Branch` 下拉菜单中同时显示 `Prod (x.x.x)` 和 `Beta (x.x.x)`
   - `Prod` 为正式服版本，`Beta` 为测试服版本

**兜底方案**：若以上三个站点均无法访问，从 [BWiki 版本历史页](https://wiki.biligame.com/sr/版本历史) 获取正式服版本号。

## 大版本更新流程

当出现新的正式服大版本（如 4.2 → 4.3）时，按以下流程补充数据：

### 1. 确认正式服当前版本

- **不要只信单一来源**：nanoka.cc 首页的 `Live Version` 字段存在滞后（曾在 4.3 已上线时仍显示 4.2）。
- **权威来源**：[BWiki 版本历史页](https://wiki.biligame.com/sr/版本历史) 的「新增内容一览」表格，最新一行即当前/最近版本，含上线日期与该版本新增的 角色 / 光锥 / 遗器 / 敌人 / 装饰。以「更新时间 ≤ 今日」判断是否已上正式服。
- 版本号查询站点见上文「推送前版本号更新」。

### 2. 梳理本版本新增内容（从测试网站）

角色 / 光锥 / 遗器 的清单与详细数据从**测试网站**获取（见「参考链接 > 测试服」：nanoka.cc、GachaBase、Huroka），它们的最新/beta 分支会先于正式服收录新内容，且数据更完整（含削韧、能量等字段）。需要入库的三类（场景/敌人/装饰暂不入库）：

- **角色**、**光锥**、**遗器 / 位面饰品**

用 BWiki 该版本行（步骤 1）核对哪些条目属于当前正式服版本，避免把更靠后的测试服内容误当本版本。

### 3. 对照本地数据，确认缺口

- 角色数据文件：`references/character/{id}.md`
- 光锥数据文件：`references/lightcone/{id}.md`
- 遗器：仅维护在映射表 `references/mapping-relic.md`（无独立文件）
- 角色↔光锥映射：`references/mapping-char2lc.md`

逐项检查「映射表是否已含」与「数据文件是否存在」，列出真正缺失项后再补充。

### 4. 生成数据文件

用生成器脚本产出数据文件（脚本优先原则见顶部「工具脚本」章节）：

- 角色：`python3 scripts/gen_character.py {id}` → 写 `references/character/{id}.md`（及 `-enhanced.md`）
- 光锥：`python3 scripts/gen_lightcone.py {id}` → 写 `references/lightcone/{id}.md`

脚本数据来源：[Mar-7th StarRailRes](https://github.com/Mar-7th/StarRailRes)（基础属性/技能倍率/星魂）+ nanoka（测试网站，补充削韧 `show_stance_list`、能量 `sp_base`、战技点 `bp_add`、专属效果 `unique`、参演编号等）。nanoka 版本由脚本读 `manifest.json` 的 `latest`（即测试服分支），故新角色上 beta 后即可生成。

> 已知局限：①「强化战技」等技能若 StarRailRes 源数据 desc 为空，生成结果只有元信息无描述（数据缺口，需人工补描述）；②「强化终结技」靠 nanoka 技能盘终结技节点 `level_up_skill_id` + 主终结技描述自动识别——候选技名「未出现在主终结技描述中」（银枝/昔涟）或以「终结技【技名】」形式出现（千冶刃"获得全新终结技【…】"）即判为强化终结技；以子技能形式被调用（黄泉"发动N次【啼泽雨斩】"、飞霄"发动【闪裂刃舞】"）则为多段终结技的子段，跳过。生成后人工核对即可。

### 5. 收尾

- 更新映射表（如缺）：`mapping-char2lc.md`（角色↔光锥）、`mapping-relic.md`（遗器套装）。
- 版本号（README.md 顶部徽标）以 **BWiki** 正式服版本为准，按「推送前版本号更新」更新为 `vx.y.z`。
- 走「Commit / Push Workflow」review 后再提交。
