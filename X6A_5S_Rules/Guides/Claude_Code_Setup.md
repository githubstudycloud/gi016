# Claude Code 设置指南

Claude Code (Anthropic 的 CLI 工具) 支持通过 `CLAUDE.md` 文件来管理项目上下文和规则。

## 1. 项目规则 (6A 工作流)

### 配置步骤
1. 在项目根目录下创建一个名为 `CLAUDE.md` 的文件。
2. 将 `project_rules_6A.md` 的内容复制到 `CLAUDE.md` 中。
3. Claude Code 会在运行任务时自动读取此文件作为项目上下文。

### 提示
`CLAUDE.md` 不仅仅是规则，还可以包含常用命令和架构简介。建议在 6A 规则下方添加项目的构建和测试命令，例如：
```markdown
## 常用命令
- Build: npm run build
- Test: npm test
```

## 2. 个人规则 (5S 敏捷规范)

Claude Code 目前主要通过 `CLAUDE.md` 或命令行参数加载配置。为了实现全局个人规则，可以使用 CLI 的配置功能或别名。

### 方式一：合并到 CLAUDE.md (推荐用于单人项目)
将 `personal_rules_5S.md` 的内容追加到每个项目的 `CLAUDE.md` 文件底部。

### 方式二：使用全局配置 (如果支持)
检查 `~/.claude/config.json` 或类似的全局配置文件，查看是否有 `system_prompt` 字段。如果有，将 5S 规则的精简版放入其中。

### 方式三：Shell Alias (高级)
可以在 `.zshrc` or `.bashrc` 中创建一个别名，每次调用 Claude Code 时注入 System Prompt：
```bash
alias claude='claude --system-prompt-file /path/to/personal_rules_5S.md'
```
*注意：具体参数请参考 `claude --help`，不同版本参数可能不同。*

## 3. 验证
在终端运行 `claude "规划一下用户登录功能的开发"`。如果输出包含 "Align", "Architect" 等阶段的术语，说明规则已生效。
