# Cursor 设置指南

Cursor 是目前最流行的 AI 编辑器之一，通过 `.cursorrules` 文件支持强大的上下文控制。

## 1. 项目规则 (6A 工作流)

Cursor 主要通过项目根目录下的 `.cursorrules` 文件来加载项目规则。

### 配置步骤
1. 在项目根目录下创建一个名为 `.cursorrules` 的文件。
2. 将 `project_rules_6A.md` 的内容**完整复制**到 `.cursorrules` 文件中。
3. **重要**：为了确保 AI 严格遵守，建议在文件开头添加一行强指令：
   ```markdown
   YOU MUST FOLLOW THESE RULES IN ALL RESPONSES.
   ```

## 2. 个人规则 (5S 敏捷规范)

Cursor 允许在全局设置中配置通用规则，或者你可以将其合并到项目的 `.cursorrules` 中（不推荐，因为个人习惯不应污染项目配置）。

### 推荐配置方式 (全局设置)
1. 打开 Cursor 设置 (Ctrl+Shift+J 或 Cmd+Shift+J)。
2. 找到 **General** -> **Rules for AI** (或类似名称的 System Prompt 设置)。
3. 将 `personal_rules_5S.md` 的内容粘贴到这里。
4. 这样配置后，这些规则将应用于你打开的所有项目。

### 替代方式 (合并文件)
如果你希望强制项目成员也遵守 5S 规范，可以将 `personal_rules_5S.md` 的内容追加到 `.cursorrules` 文件的末尾。

## 3. 验证
打开 Chat 面板 (Ctrl+L / Cmd+L)，输入 "我们现在的开发流程是怎样的？"。如果 AI 回复了 6A 流程，说明配置生效。
