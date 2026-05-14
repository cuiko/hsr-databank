# Project Guidelines

## Commit / Push Workflow

当用户要求提交或推送时，**必须先 review 所有本次变更涉及的文档**：

1. 检查是否存在歧义、不理解、重复的内容
2. 若发现问题，列出问题及可供参考的操作选项，等待用户确认
3. 用户确认后，重复上述流程，直到文档逻辑无误
4. 确认无问题后才可执行 `git commit` / `git push`

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
