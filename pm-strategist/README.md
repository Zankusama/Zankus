# pm-strategist · 产品军师

帮 PM 在真实业务场景下做决策：判可逆性 → 用户先说判断 → 五场景路由（S1-S5/C类）选框架 → 输出含依据与反方的建议6要素 → 3 轮熔断收敛为决策记录。决策是目的，方法论只是弹药。

## 安装

权威源即本目录。把本目录放到（或软链接到）目标客户端的 skills/ 目录即可，例如：

```bash
ln -s <本目录的绝对路径> ~/.workbuddy/skills/pm-strategist
```

各客户端的 skills 目录位置不同，按其文档放置；本技能为纯本地文件，无需联网、无需安装第三方依赖。

> ⚠️ 本包含 `config/local_profile.md`（行业身份层，预置空模板）。若将本技能包分享给他人，请先排除或清空 config/ 目录，避免带入个人品牌信息。

## 使用

对它说：新品评估 / 产品决策 / 帮我决策 / 该不该做 / 怎么取舍 / 值不值得做 / 优先做哪个 / 定价 / 上市 / 复盘……（完整触发词见 SKILL.md description）。
NOT for：「为什么/根因」类归因分析、需求澄清与任务书撰写、纯闲聊、纯代码编辑。

## 测试与验收

```bash
bash tests/run_tests.sh                  # 结构+触发+红线用例（退出码 0=全绿）
python3 scripts/check_output.py --self   # 输出不变量校验器自检
```

运行时机器化验收（「可机器化验收」节，详见 SKILL.md）：
```bash
python3 scripts/scene-router.py --self   # 场景路由自检
python3 scripts/kano-classify.py --self  # KANO 分类自检
python3 scripts/decision-record.py --self  # 决策记录自检
python3 scripts/risk-check.py --help     # 风险6维度复核
python3 scripts/stage-gate-check.py --help  # 五闸过闸检查
python3 scripts/unknown-info-check.py --help  # 盲区/未知信息检查
```

## 依赖

纯 Markdown + Python 标准库（json/argparse/datetime/re），零第三方依赖、零网络请求。

## 版本

v3.2.0（2026-09-01）｜ 版本号以 SKILL.md frontmatter 为唯一准
