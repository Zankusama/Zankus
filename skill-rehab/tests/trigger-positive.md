# 触发正用例（skill-rehab 该被触发的问法）

> 用途：验证 description 触发词能正确激活 skill-rehab。评估器 l2_trigger_testing 检查 tests/trigger-*.md 存在。

## 正用例（应触发）

| # | 用户说 | 触发词命中 |
|:--:|:---|:---|
| 1 | 帮我修一下这个 skill | 修 skill |
| 2 | 用 skill-rehab 诊断一下 second-brain | 诊断 skill |
| 3 | 这个 skill 体检一下 | skill 体检 |
| 4 | 打磨一下 leader-translator | 打磨 skill |
| 5 | 康复师，看看这个 skill 哪里不好 | 康复师 |

## 负用例（不应触发）——见 trigger-negative.md
