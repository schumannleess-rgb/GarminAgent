# CHANGELOG

## 2026-05-18

### [新增] garmin_cli.py CLI 入口
- **修改文件**：scripts/garmin_cli.py（新建）
- **原因**：让 Claude Code 能直接调用佳明 Agent 的数据获取能力
- **改动内容**：创建 16 个 CLI 命令（latest/today/week/activities/detail/splits/classify/intervals/health/capacity/status/hr/rhr/sleep/hrv）
- **测试结果**：通过

### [新增] JiaJia（佳佳）角色定义
- **修改文件**：~/.claude/roles/jiajia.md（新建）
- **原因**：为佳明 Agent 创建专属飞书 bot，场景驱动的角色定义
- **改动内容**：7 个工作场景（跑完了/身体状态/能力评估/比赛准备/训练计划/完善Agent/历史查询）+ 解读框架 + 工具速查
- **测试结果**：通过
