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

## 改写场景（同义改写仍应触发）

> 用途：验证 description 触发词在用户换说法时不漏触发（l2_trigger_test_coverage 三场景之一）。

| # | 用户说（改写） | 触发词命中 |
|:--:|:---|:---|
| 1 | 我这个工具最近老出岔子，帮我瞅瞅 | 修→瞅瞅（改写"修 skill"） |
| 2 | 那套流程文件总觉得哪里不对劲，给我过一遍 | 诊断→过一遍（改写"诊断 skill"） |
| 3 | 这套玩法写得太糙了，收拾收拾 | 打磨→收拾收拾（改写"打磨 skill"） |
| 4 | 看下我封装的这套东西还差在哪 | 康复师→看下（改写"康复师"） |

## 负用例（不应触发）——见 trigger-negative.md
