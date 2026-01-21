# Codex CLI 设置指南

*注意：Codex CLI 通常指基于 OpenAI Codex 模型或类似能力的命令行工具（如 `codex` npm 包或类似的开源包装器）。以下配置基于通用的 CLI 代理配置模式。*

## 1. 配置文件位置

大多数 Codex 类的 CLI 工具会将配置存储在用户主目录下的隐藏文件夹中，例如 `~/.codex`。

## 2. 配置步骤 (通用)

### 步骤 1: 定位配置文件
查找 `~/.codex/config.yaml`, `~/.codex/settings.json` 或 `~/.codex/AGENTS.md`。如果不存在，请参考你具体使用的工具文档进行初始化 (通常是 `codex init`)。

### 步骤 2: 设置 System Prompt (系统提示词)

**方法 A: 修改 AGENTS.md (如果存在)**
如果工具使用 markdown 文件定义 Agent 行为：
1. 打开 `~/.codex/AGENTS.md`。
2. 找到默认的 `instructions` 部分。
3. 将 `project_rules_6A.md` 和 `personal_rules_5S.md` 的内容追加到 instructions 中。

**方法 B: 修改 Config 文件**
如果工具使用 JSON/YAML 配置：
1. 找到 `system_prompt` 或 `instructions` 字段。
2. 由于 JSON/YAML 不适合存放长文本，建议将规则保存为文件，然后在配置中引用路径（如果支持），或者将文本转义后粘贴。
   *推荐做法*：创建一个 `~/.codex/rules.md` 文件，将 6A 和 5S 规则合并进去。然后查阅工具文档，看是否支持通过 `--rules-file ~/.codex/rules.md` 之类的参数启动。

### 步骤 3: 别名设置 (推荐)
为了方便使用，建议创建 Shell 别名：

```bash
# 将规则合并到一个文件 rules.md 中
alias codex='codex --instructions-file ~/.codex/rules.md'
```

## 3. 验证
启动 CLI 并输入 "Who are you and what is your workflow?"。
如果配置正确，它应该回答："I am a senior software architect... following the 6A workflow..."
