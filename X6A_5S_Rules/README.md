# TRAE X6A+5S 规则体系指南

本目录包含 TRAE 编辑器的通用 6A 工作流项目规则和敏捷开发 5S 个人规则配置。这套规则旨在通过标准化的流程（6A）和规范化的执行（5S），提升 AI 编程的质量、可维护性和团队协作效率。

## 包含文件

1.  **[project_rules_6A.md](./project_rules_6A.md)**: 适用于项目级别的配置，定义了完整的开发工作流。
2.  **[personal_rules_5S.md](./personal_rules_5S.md)**: 适用于个人级别的配置，定义了具体的代码风格和交互习惯。

## 如何使用

### 1. 配置项目规则 (Project Rules)
将 `project_rules_6A.md` 的内容复制到你的 TRAE 项目规则设置中，或者保存为项目根目录下的 `.traerules` (具体文件名视 TRAE 版本支持而定，通常在设置界面的 "Rules" -> "Project Rules" 中粘贴)。

### 2. 配置个人规则 (Personal Rules)
将 `personal_rules_5S.md` 的内容复制到你的 TRAE 个人规则设置中 (Settings -> Rules -> Personal Rules)。

## 规则简介

### 6A 工作流 (Project Level)
通过六个阶段严格控制开发流程：
1.  **Align (对齐)**: 明确需求，消除歧义。
2.  **Architect (架构)**: 设计技术方案和数据模型。
3.  **Atomize (拆解)**: 任务原子化，制定步骤。
4.  **Approve (确认)**: 方案确认（由用户或架构师）。
5.  **Automate (自动化)**: 生成代码和测试。
6.  **Assess (评估)**: 代码审查和质量验证。

### 5S 敏捷规范 (Personal Level)
借鉴 5S 管理法，规范 AI 的执行细节：
1.  **Seiri (整理)**: 聚焦核心上下文，排除干扰。
2.  **Seiton (整顿)**: 结构化输出，逻辑清晰。
3.  **Seiso (清扫)**: 保持代码整洁，无死代码。
4.  **Seiketsu (清洁)**: 遵循统一的编码规范。
5.  **Shitsuke (素养)**: 持续改进，文档先行。
