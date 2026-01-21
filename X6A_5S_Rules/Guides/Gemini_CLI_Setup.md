# Gemini CLI 设置指南

Gemini CLI (Google AI SDK 的命令行工具) 提供了灵活的系统提示词配置方式，支持环境变量和特定配置文件。

## 1. 项目规则 (6A 工作流)

Gemini CLI 会优先查找 `.gemini/system.md` 文件作为系统提示词。

### 配置步骤
1. 在项目根目录下创建目录 `.gemini`。
2. 在 `.gemini` 目录下创建文件 `system.md`。
3. 将 `project_rules_6A.md` 的内容复制到 `.gemini/system.md` 中。
4. 确保环境变量 `GEMINI_SYSTEM_MD` 设置为 `true` (或者默认情况下它会自动查找，视版本而定，建议显式设置)。

### 命令示例
```bash
mkdir .gemini
cp project_rules_6A.md .gemini/system.md
```

## 2. 个人规则 (5S 敏捷规范)

如果你希望 5S 规则在所有项目中生效，可以使用环境变量指定一个全局的 Markdown 文件。

### 配置步骤
1. 将 `personal_rules_5S.md` 保存到一个固定位置，例如 `~/gemini-rules/personal_rules_5S.md`。
2. 在你的 Shell 配置文件 (`.bashrc`, `.zshrc`, 或 PowerShell profile) 中设置环境变量：

**Linux/macOS:**
```bash
export GEMINI_SYSTEM_MD="/path/to/personal_rules_5S.md"
```
*注意：如果设置了全局路径，可能会覆盖项目的局部设置。为了同时使用两者，建议将 6A 和 5S 规则合并到一个文件中，或者在项目级的 `system.md` 中包含个人规则。*

**最佳实践 (合并策略)**:
在项目的 `.gemini/system.md` 中，先粘贴 `project_rules_6A.md`，然后粘贴 `personal_rules_5S.md`。这样能确保两者同时生效。

## 3. 验证
运行 `gemini "解释一下你的工作流"`。如果回复中提及了 6A 流程，说明配置成功。
