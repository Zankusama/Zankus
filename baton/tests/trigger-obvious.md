# 触发测试 · 明显触发（trigger-obvious）

> 样本含明确触发词，期望 skill 被路由触发（产出交接文档或进入 L2 流程）。
> 维护纪律：新增样本禁含本机路径 / 个人称呼 / 临时目录字面量（会打破包内静态断言）。

| # | 用户输入样本 | 期望判定 |
|---|---|---|
| O1 | 交接一下 | ✅ 触发 |
| O2 | 该交接了，把当前进度存下来 | ✅ 触发 |
| O3 | 帮我 handoff | ✅ 触发 |
| O4 | 新会话 resume 上一份交接 | ✅ 触发（resume 认领路径） |
| O5 | 接着干 | ✅ 触发 |

## grep 断言（锁死触发词不丢）

```bash
grep -n "交接" ../SKILL.md >/dev/null && grep -n "resume" ../SKILL.md >/dev/null && echo ✅ || echo ❌
```
