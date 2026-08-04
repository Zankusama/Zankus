# 触发负用例（skill-rehab 不该被触发的场景）

> 用途：验证 NOT for 边界能正确排除。评估器 l2_trigger_testing 检查 tests/trigger-*.md 存在。

## 负用例（不应触发）

| # | 用户说 | NOT for 依据 |
|:--:|:---|:---|
| 1 | 帮我设计一个全新的 skill | NOT for 从 0 设计新 skill |
| 2 | 这段文案合规吗 | NOT for 文案/合规审核类任务 |
| 3 | 你觉得 skill 怎么样（闲聊）| NOT for 纯闲聊 → 先跑评估器再说话 |
| 4 | 帮我写个产品文案 | NOT for 文案类 |
