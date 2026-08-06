# mechanism.md — 7 层处方表（症状 → 分级 → 修法选项）

> 定位：康复流程「2 分级处方」的查表依据——评估器未过项（源一）+ 完整性缺口（源二）在此查修法。
> 结构：7 层（定位/触发/骨架/质量/安全/工程/生命周期）对应评估器 v4.0.0 LAYERS；每检查项 = 评估器 item 名（查表键）。
> 名称约定：与行业一致（Anthropic 官方 / trailofbits / SkVM·SkCC / Prompt Failure Mode Atlas），不用个人口径。
> 打分原则：P0 必改 5 分（必过）/ P1 建议 3 分 / P2 备选 1 分（可选）/ info 跳过 0 分（报告呈现，永不扣分）；层权重 = 项之和，总分 149（机器 127 + 评审 22）。

---

## 分级四档（与评估器 P0/P1/P2/info 对齐）

> info 跳过档不设修法条目（不修=无需修法），故下方各检查项标注只有前三档；四档口径在「分级说明」段统一。

| 评估器级别 | 处方档 | 治疗策略 |
|:--:|:---|:---|
| **P0** | **必改** | **修**（死规矩 9「只修必改」= 治疗对象）——影响运行/触发/正确性/安全 |
| **P1** | **建议** | 给建议，附在交付里不实施（死规矩 9）|
| **P2** | **备选** | 记录备选不强制；注意档位迁移（备选会随时间变建议→必改）|
| **info** | **跳过** | **识别即跳过（不修，连备选都不记）**——省资源（v5.0.0 补入，对应评估器 0 分档）|

## ① 定位层 Positioning（16 分）· 机制：skill 身份与职责边界

### name 命名规范（l1_name_naming · M层 · P1 3 分）

- 判定词：name 字段 kebab-case（小写连字符）+ 具体动词短语，非 vague 词
- 未过条件：name 非 kebab-case 或过泛（helper/utils/tools 类）
- 症状：skill 名与目录不一致/过泛，触发与检索识别困难
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 改 kebab-case：具体动词短语（如 analyze-contracts，非 contract-analyzer）——trailofbits「Prefer gerund form, Be specific」
  1. 与目录名一致（~/.claude/skills/<name>/SKILL.md），避免 install/sync 工具 mis-key
  1. 避免保留词（anthropic/claude）与 vague 名（helper/utils）

### description 职责声明（l1_desc_mission · M层 · P0 5 分）

- 判定词：description 第一句第三人称说明 skill 解决什么（「This skill should be used when…」）
- 未过条件：description 无职责声明或第一人称（I help you…）
- 症状：模型不知道这个 skill 干什么，无法决定是否激活
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 第三人称重写：'This skill should be used when the user asks to…'——Anthropic 官方
  1. 一句话职责 + 触发场景，不用营销口号（'The best linter' = 无可匹配）
  1. 200-800 字符，说明能力边界

### description 触发接口一致性（l1_desc_consistency · R层 · P0 5 分）

- 判定词：description 关键词/职责在正文有支撑（塔尖=正文概括，不夸大不缩水）
- 未过条件：description 说的能力正文没有，或正文有 description 没提（触发判断错位）
- 症状：模型按 description 激活 skill 后正文对不上，触发与执行脱节
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. description 逐句对照正文：每句能力在正文有章节支撑
  1. 正文新增能力时同步更新 description（防漂移）
  1. 用触发实测（goldens）验证 description 触发词真的能激活

### 职责单一性（l1_single_responsibility · R层 · P1 3 分）

- 判定词：description 只讲一件事（单一职责），NOT for 排除相邻场景
- 未过条件：一个 skill 塞多个不相关职责
- 症状：职责混杂，触发边界模糊，维护困难
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 拆分为多个 skill（每个单一职责）——软件工程 SRP
  1. 相关子任务合并为流程步骤而非独立职责
  1. 相邻 skill 用 NOT for 划界

## ② 触发层 Triggering（16 分）· 机制：什么时候激活/不激活

### 触发短语（l2_trigger_phrases · M层 · P0 5 分）

- 判定词：description 含具体触发短语（用户可能说的原话），非泛词
- 未过条件：无触发短语或过泛（'Use this skill when working with hooks'）
- 症状：触发词太泛：什么都触发或永远不触发
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 列具体短语：'create a hook' / 'add a PreToolUse hook'——lobehub Strong Triggering
  1. 覆盖变体：不同问法都列（用户怎么问的原文）
  1. 避免泛词：'hooks help' 改为具体动作短语

### 负向触发 NOT for（l2_negative_trigger · M层 · P0 5 分）

- 判定词：description 尾部 NOT for / When NOT to Use 排除不该接的场景
- 未过条件：无 NOT for——相邻 skill 会互相抢活
- 症状：该触发的不触发、不该触发的乱触发（近邻 skill 抢占）
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. description 尾部加 'NOT for…' 排除相邻场景——Anthropic 官方
  1. 正文头部 'When NOT to Use' 段（trailofbits 必需章节）
  1. 列出近邻 skill 名，明确边界

### 跨平台一致性（l2_cross_platform · R层 · P1 3 分）

- 判定词：声明测试过的平台（WorkBuddy/Claude Code/GPT/Gemini）+ 验证记录
- 未过条件：无平台声明或声明无验证记录（'多模型兼容'一句摆设）
- 症状：同一 skill 跨框架行为差异大（SkVM：格式敏感性致性能波动 40%）
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 声明测试过的平台与版本（'Tested on: Claude Code v2.x'）
  1. 跨平台跑触发实测（正/负用例在多个客户端验证）——agent-compat 模式
  1. 单一平台使用则明确写死（'WorkBuddy only'），不假装兼容

### 触发实测（l2_trigger_testing · M层 · P1 3 分）

- 判定词：tests/ 含触发正/负用例（该触发的问法 + 不该触发的问法）
- 未过条件：无触发测试集，触发行为未验证
- 症状：触发行为靠猜，实际使用才发现误触发/漏触发
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 建 tests/trigger-positive.md（≥5 条该触发问法）+ trigger-negative.md（≥3 条不该触发）
  1. 触发词逐条测试（grep description 关键词 vs 用例）
  1. 实际使用后把误触发/漏触发反馈进测试集（真实路径校准）

## ③ 骨架层 Skeleton（27 分）· 机制：skill 结构六零件

### 分步推进（l3_step_flow · M层 · P0 5 分）

- 判定词：主流程 ≥3 连续编号步骤（1./### 1./阶段N/Step N）
- 未过条件：最长连续步骤 <3——不分步=一步到位
- 症状：长上下文单步质量必降，错在哪一步查不出
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 主流程拆 ≥3 连续编号步骤——CoT 研究共识
  1. 用阶段/Step 标题编号（### 阶段N / #### Step N）
  1. 步骤标题写动作（做什么），不写状态

### 输出格式声明（l3_output_format · M层 · P0 5 分）

- 判定词：产出物/输出/格式/示例 关键词 ≥2 或输出 schema 段
- 未过条件：无输出格式声明——产物随心所欲
- 症状：下游解析/验收无从谈起（Missing output schema 反模式）
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 每步/整体写 '产出物：xxx'（文件名/表格/JSON 结构）——digitalapplied
  1. 给输出模板/示例（'Respond using exactly this structure:'）
  1. 关键字段与命名规则写明（schema 显式化）

### 渐进披露（l3_progressive_disclosure · M层 · P1 3 分）

- 判定词：SKILL.md 留决策骨架，细节外置 references/（references/ 引用 ≥1）
- 未过条件：全塞 SKILL.md（>500 行）或细节不外置
- 症状：上下文窗口被细节占满，核心指令被稀释（token 浪费）
- 分级：**建议（特例：>500 行升必改）**（评估器级别 P1）
- 修法选项：
  1. 细节移 references/（SKILL.md 留决策骨架）——Anthropic 三级加载
  1. SKILL.md ≤500 行，references/ 按需加载
  1. 不重复：信息只在 SKILL.md 或 references/ 一处（lobehub Never duplicate）

### 材料/模板（l3_material_template · M层 · P1 3 分）

- 判定词：指定固定数据源/模板（references/ 模板文件或数据源声明）
- 未过条件：无固定材料——每次现场找/现场编
- 症状：输入不稳定，产出不稳定（隐式上下文假设反模式）
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 固定数据源声明（'数据来自 references/xxx.md'）
  1. 固定模板文件（输出模板/工单模板）
  1. 每 prompt 自包含：所需材料全在 references/ 指定，不假设模型记得

### 确定性转移（脚本化）（l3_scriptized · M层 · P0 5 分）

- 判定词：scripts/ 目录存在 + SKILL.md 引用脚本真实存在 + 可机器化验收声明节
- 未过条件：无 scripts/ 或引用假脚本（提一句脚本名=作弊）
- 症状：可机器化操作靠 AI 手敲，概率判断必错（手算 hash/手写解析）
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 可机器化操作固化为 scripts/ 脚本（确定性可靠性）——Anthropic Complete Guide
  1. SKILL.md 引用脚本必须真实存在（防引用假脚本）
  1. 加「可机器化验收」声明节（脚本管什么/退出码判定）

### 确定性护栏（hook）（l3_deterministic_guardrail · R层 · P1 3 分）

- 判定词：高违规代价操作（改核心/发布/删数据）有无 hook 物理拦截
- 未过条件：满足 ①违规代价高 ②AI 靠自觉易漏 双条件但无 hook
- 症状：关键违规操作只靠文字约束（AI 自觉），跳步/忘跑前置系统不拦截
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. PreToolUse 拦截：settings.json hooks 匹配特定文件操作，不满足返回 block
  1. UserPromptSubmit 检测：检测流程跳步（无 G(N-1) 产物进 G(N)）
  1. 显式不挂（留 AI）：收益不足时标 [显式留AI✓] 写明理由——Anthropic「指令是错的工具，护栏要确定性」

## ④ 质量层 Quality（52 分）· 机制：执行正确性核心

### 验收可执行（l4_judgeable_acceptance · M层 · P0 5 分）

- 判定词：验收命令/grep/diff/exit/断言 ≥3 处
- 未过条件：验收主观化（'看看效果'）——模型自己判自己必自欺
- 症状：做完没做完说不清，部分完成当完成
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 验收写成可执行命令（退出码断言）——OpenAI eval '先定义 success'
  1. 冒烟测试脚本化（三步带退出码）
  1. 验收标准数字化（'≥2'/'0 命中'）

### 锚定（l4_anchoring · M层 · P1 3 分）

- 判定词：关键约束出现 ≥2 次（开头声明 + 任务段重提）
- 未过条件：关键约束只出现 1 次（长上下文后必被淹没）
- 症状：关键规则开头说一次，任务中段被 lost-in-the-middle 吞掉
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 关键约束开头声明 + 任务指令处重提（2 处）——Anthropic Context Engineering
  1. 约束前置（金字塔：constraints first，identity 后置）
  1. 约束用定值表达（'必须全'/'至少 N'）

### 来源锚定（l4_source_grounding · M层 · P0 5 分）

- 判定词：断言带来源/实测/日期/引用 ≥2 处
- 未过条件：断言无锚点（在没依据的地方裸断言）
- 症状：幻觉是概率生成的自然结果——无锚点处必编造（Ungrounded CoT）
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 每条断言带来源（URL/路径/实测命令）——aivoid Ungrounded CoT 反模式
  1. 调研类操作写来源（联网/知识库/实测）
  1. 禁止裸断言（'根据经验'不算来源）

### 未验证标注（l4_unverified_marking · M层 · P1 3 分）

- 判定词：假设/未验证/待核实/猜的 标注 ≥1 处
- 未过条件：查不到的东西当结论输出（无标注）
- 症状：查不到硬编，误导执行（Confidence Inflation）
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 查不到标 '假设，未验证'（显式）——Atlas 'Mark unverified claims with Unverified:'
  1. 不确定项给置信度（high/medium/low）
  1. 待查清单：查不到的项自动进补盲候选，不静默消失

### 替代方案考虑（l4_alternatives · R层 · P1 3 分）

- 判定词：Alternatives/替代方案/为什么不选 段存在
- 未过条件：无替代方案段——决策没交代为什么
- 症状：拍脑袋选方案，模型看到替代不瞎选
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 头部加 '替代方案' 表（候选/为什么不用/为什么选）
  1. 回应 '禁止 X' 时给替代动作（禁带替代）
  1. 决策透明：列 2-3 候选 + 选中理由

### 指令一致性（l4_instruction_consistency · M层 · P0 5 分）

- 判定词：硬指令（必须/禁止/不得）与软指令（应该/建议）比 ≤3；无冲突仲裁
- 未过条件：指令分级失衡（全硬指令）或冲突无仲裁
- 症状：规则互相打架时模型随机选（Conflicting Instructions 反模式）
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 指令分级：红线级（必须）/建议级（应该）/默认级——promptolis Instruction Stacking
  1. 冲突约束写仲裁规则（'冲突时 X 优先'）
  1. 关键约束重复=锚定（好）；冗余指令重复=稀释（坏）——与锚定划界

### 祈使句式（l4_imperative_style · M层 · P0 5 分）

- 判定词：关键指令动词开头（祈使句），被动条件句（等…再/需要时…才）≤5
- 未过条件：关键动作被被动条件化，无限推迟
- 症状：动作被条件化（'如果 X 就 Y'）流程卡死——被动词>5
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 关键动作用祈使句（'Create the directory.'）——Anthropic Imperative Writing Style
  1. '如果 X 就 Y' 改 '默认做 Y，X 时跳过'（主动优于被动）
  1. 有条件延迟写触发条件（何时才发生），不许悬空

### 占位符泄漏（l4_placeholder_leakage · M层 · P0 5 分）

- 判定词：xxx/TBD/待补充/TODO 0 命中
- 未过条件：模糊占位符残留（未填实）
- 症状：占位符被模型照抄进产物（Missing-Info Filler）
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 占位符全部填实（真实示例值）——Atlas Missing-Info Filler
  1. 真示例标 '示例'（明说），不写模糊占位
  1. 输出规范声明 '不许输出占位符'

### 输出可执行性（l4_output_executability · M层 · P1 3 分）

- 判定词：代码围栏内是纯可执行命令（无 $ 提示符/伪代码占位）
- 未过条件：围栏内带 $ 提示符或伪代码——复制运行必错
- 症状：命令示例复制即错（$ 提示符被当字面输出）
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 命令示例包进围栏，围栏内是纯可执行命令（无 $ 前缀）
  1. 伪代码/不可直接跑的示例标 '示例' 或说明先替换再跑
  1. 命令说明 '复制运行' 时保证脱离围栏可直接跑

### 止损熔断（l4_fuse_mechanism · M层 · P1 3 分）

- 判定词：熔断/止损/连败/超时/回滚 关键词 ≥2
- 未过条件：无熔断/止损——连败/超时无限烧
- 症状：出问题停不下来，反复试错烧资源
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 定义连败换项（'同一验收连败 3 次换下一项'）
  1. 定义超时停（'满 5 轮即停，如实汇报'）
  1. 定义回滚（'结果比开工差就回滚'）——OpenHands stuck detection

### 状态物化（l4_state_materialization · M层 · P1 3 分）

- 判定词：PROGRESS/BLOCKED/output/ 落盘 ≥2 处
- 未过条件：跨步状态不落盘——模型无状态，断会话即失忆
- 症状：断了/换会话重做，进度丢失
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 每步产出落盘（PROGRESS.md/BLOCKED.md）
  1. 产物路径规则（'output/' 下，禁裸名——产物放 AI 当前会话工作区，禁落 skill 源目录）
  1. 续接指引（'断了先读 PROGRESS.md 接着做'）

### 产出载体（l4_output_carrier · M层 · P1 3 分）· v4.2.0 新增（交接包 D1/D5）

- 判定词：声明具体产出载体（画像/知识包/HTML/SVG/Excel/报告/.md 文件）≥1 处
- 未过条件：无具体产出载体——体验型 skill 跑完零交付
- 症状：陪伴/对话型 skill 聊完一场，用户两手空空（confidant 翻车主因）
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 声明「收敛 → 必出 X」（X 为具体文件名/格式）——最小交付保证
  1. 产出模板落 references/（如 report_template.html），SKILL.md 引用
  1. 对话轨迹 → 交付物的映射写进流程（达根因即输出画像）

### 收敛终端（l4_convergence_terminal · M层 · P1 3 分）· v4.2.0 新增（交接包 D1/D5）

- 判定词：轮次/时长上限或终止条件 ≥1 处
- 未过条件：无收敛终端——对话无限延展，没有「跑完」的边界
- 症状：对话型 skill 没有轮次预算/终止条件，AI 陪聊无终局
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 声明轮次软上限（'12–15 轮收敛'）
  1. 声明终止条件（'达根因即输出，不再追问'）
  1. 声明时长/预算上限（'单次 ≤30 分钟'）

### 运行时行为校验（l4_runtime_check · M层 · P1 3 分）· v4.2.0 新增（交接包 D3）

- 判定词：scripts/check_*.py 校验脚本被引用 ≥1 个
- 未过条件：「必须 X 才 Y」类行为规则留 AI 自觉——违背「模型自判必自欺」确定性原则
- 症状：运行时行为规则（如 RAG 失守必标注）只写文字不写脚本，AI 执行方差大
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 行为规则脚本化：扫机制关键词 + 白名单 → 退码判定（confidant check_rag.py 已验证）
  1. 行为测试 tests/behavior-*.md（grep 断言风格）对齐触发测试
  1. 禁止「显式留 AI 理由」作为确定性规则兜底——确定性交脚本，不确定性明确标注

## ⑤ 安全层 Safety（16 分）· 机制：越权与危险操作防护

### 最小权限工具白名单（l5_allowed_tools · M层 · P0 5 分）

- 判定词：frontmatter allowed-tools 字段声明（Read/Grep 等最小集）
- 未过条件：无 allowed-tools——默认全工具可用（越权风险）
- 症状：skill 能调任意工具，改文件/执行命令无边界
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. frontmatter 加 allowed-tools（只读 skill 限 Read/Grep）——trailofbits 最小权限
  1. 按需声明：需要什么工具列什么（least privilege）
  1. 危险操作（写/执行/删）不默认开放

### 危险操作防护（l5_dangerous_op_guard · M层 · P0 5 分）

- 判定词：危险操作（删/发/写敏感/发布）有确认或禁止声明
- 未过条件：危险操作无防护声明
- 症状：AI 执行破坏性操作无拦截（删文件/发消息/改敏感数据）
- 分级：**必改**（评估器级别 P0）
- 修法选项：
  1. 危险操作分级：🔴 阻止（删库/发布）/🟡 确认（删文件）/🟢 自主
  1. 写保护：核心文件改动前备份/快照
  1. PreToolUse hook 拦截危险命令（dev.to command firewall）

### 可逆性分级（l5_reversibility_grading · M层 · P1 3 分）

- 判定词：操作按可逆性分级（🟢🟡🔴 / 自主/确认/阻止）
- 未过条件：操作无分级，全自主或全确认
- 症状：要么乱跑要么烦死（无风险感知）
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 操作分级表：🟢 自主（可逆）/🟡 确认（不可逆）/🔴 阻止（高危）
  1. 不可逆操作强制确认（OpenHands ConfirmationPolicy）
  1. 每步输出经确认进入下一步（产出物锁）

### 注入防护（l5_injection_guard · R层 · P1 3 分）

- 判定词：外部输入（文件/网页/用户内容）与指令隔离声明
- 未过条件：无注入隔离——外部内容可劫持指令
- 症状：prompt/skill 注入：文件里的恶意指令覆盖系统指令（SkCC Anti-Skill Injection）
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 外部输入与指令显式分隔（'### 指令 / ### 内容'）
  1. 外部内容当数据处理不当指令执行（信任边界声明）
  1. 输出前校验（不执行外部内容里的命令）

## ⑥ 工程层 Engineering（7 分）· 机制：可维护性

### 版本管理（l6_versioning · M层 · P1 3 分）

- 判定词：frontmatter version 字段 + 变更记录（CHANGELOG/版本表）
- 未过条件：无 version 或变更记录
- 症状：改了什么没记录，版本无法追溯
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. frontmatter version 语义化（semver）——claudskills
  1. 建变更记录表（日期/更新内容）
  1. 升级走版本管理（guard.sh snapshot/verify/check）

### 测试集（l6_test_suite · M层 · P1 3 分）

- 判定词：tests/ 目录存在或验收命令 ≥2
- 未过条件：无测试集——改坏了没人知道
- 症状：回归无保障，迭代不可信
- 分级：**建议**（评估器级别 P1）
- 修法选项：
  1. 建 tests/（正/负用例 + 期望结果）——OpenAI golden test set
  1. 升级必跑测试集（防越改越瞎）
  1. 测试与执行分离（独立子代理/脚本断言，不自批）

### 文档化（l6_documentation · M层 · P2 1 分）

- 判定词：README 含安装/使用/贡献 + 文件清单
- 未过条件：无 README 或只有作者能看懂
- 症状：分享出去别人装不上/用不了
- 分级：**备选**（评估器级别 P2）
- 修法选项：
  1. README 面向陌生人（安装/使用/贡献四段）
  1. 加文件清单表（skill 目录表）
  1. 分享前私有内容扫描（路径/人名/品牌零残留）

## 完整性条目 · 事件层缺口（hook 候选 · 来自 completeness.md 六零件骨架）

> 归属：完整性清单（completeness.md「通用六零件骨架·触发零件」）开出的缺口，非评估器未过项。
> 定位：评估器不查此条（静态文本判不了运行时事件），由完整性清单诊断时逐项核对开出。

### event_layer_hook（完整性 · 触发零件的事件层）

- 判定词：某操作满足 ①违规代价高（改核心文件/发布/删数据）②AI 靠自觉容易漏（跳步/忘跑前置）
- 未过条件：满足双条件但无 hook 物理拦截（`~/.workbuddy/settings.json` hooks 字段无对应规则）
- 症状：关键违规操作只靠 SKILL.md 文字约束（AI 自觉），跳步/忘跑前置时系统不拦截，静默事故
- 分级：**建议**（不挂也能跑，挂了更硬；三层骨架的强制层是加分不是必需）
- 修法选项：
  1. **PreToolUse 拦截**：settings.json hooks 加规则——匹配特定文件操作（如改 skill_eval.py 前检查 guard snapshot 存在），不满足返回 block
  2. **UserPromptSubmit 检测**：检测流程跳步（如无 G(N-1) 产物进 G(N)），拦截提醒
  3. **显式不挂（留 AI）**：评估后判定收益不足（已有脚本强制/低频场景），标 `[显式留AI✓]` 写明理由，不进治疗

> ⚠️ hook 是全局生效（settings.json，所有会话），matcher 必须精确防误伤；已有脚本强制的地方不必重复挂。

---

## 快速索引（未过项 → 分级 → 去哪修）

| 未过项（诊断输出里的键） | 默认分级 | 对应层 | 对应 golden 样本（验收标准↔测试映射） | 表内位置 |
|:---|:---:|:---|:---|:---|
| l1_name_naming | 建议 | ① | g01-g02 无直接样本（脚本化相关），命名正例待补 | ↑ |
| l1_desc_mission | 必改 | ① | g35(g36 反例) | ↑ |
| l1_desc_consistency | 必改 | ① | g35_desc_ok / g36_desc_fail | ↑ |
| l1_single_responsibility | 建议 | ① | 无样本（评审层，待补） | ↑ |
| l2_trigger_phrases | 必改 | ② | g07_trigger_folded / g08_trigger_none | ↑ |
| l2_negative_trigger | 必改 | ② | g37_boundary_ok / g38_boundary_fail | ↑ |
| l2_cross_platform | 建议 | ② | g53_platform_ok / g54_platform_fail | ↑ |
| l2_trigger_testing | 建议 | ② | g47-g54 无直接样本，tests/trigger-*.md 实测 | ↑ |
| l3_step_flow | 必改 | ③ | g03_steps_arabic / g04_steps_phase / g05_steps_step / g06_steps_none | ↑ |
| l3_output_format | 必改 | ③ | g43_output_ok / g44_output_fail | ↑ |
| l3_progressive_disclosure | 建议 | ③ | g32_extrusion_ok / g33_extrusion_fail / g34_extrusion_multi | ↑ |
| l3_material_template | 建议 | ③ | 无样本（待补） | ↑ |
| l3_scriptized | 必改 | ③ | g01_scriptized_ok / g02_scriptized_fake | ↑ |
| l3_deterministic_guardrail | 建议 | ③ | 无样本（评审层 hook，待补） | ↑ |
| l4_judgeable_acceptance | 必改 | ④ | g39_judge_ok / g40_judge_fail / g41_accept_ok / g42_accept_fail | ↑ |
| l4_anchoring | 建议 | ④ | g14_anchor_repeat_ok / g15_anchor_repeat_fail / g16_anchor_repeat_multi | ↑ |
| l4_source_grounding | 必改 | ④ | g17_source_ok / g18_source_fail | ↑ |
| l4_unverified_marking | 建议 | ④ | g19_unverified_ok / g20_unverified_fail | ↑ |
| l4_alternatives | 建议 | ④ | g21_alternatives_ok / g22_alternatives_fail | ↑ |
| l4_instruction_consistency | 必改 | ④ | g09/g10/g23-g28/g13（合并后判定） | ↑ |
| l4_imperative_style | 必改 | ④ | g51_imperative_ok / g52_imperative_fail | ↑ |
| l4_placeholder_leakage | 必改 | ④ | g11_placeholder_ban / g12_placeholder_real | ↑ |
| l4_output_executability | 建议 | ④ | g45_fence_ok / g46_fence_fail | ↑ |
| l4_fuse_mechanism | 建议 | ④ | 无样本（待补） | ↑ |
| l4_state_materialization | 建议 | ④ | g29_progress_ok / g30_progress_fail / g31_progress_multi | ↑ |
| l5_allowed_tools | 必改 | ⑤ | g47_allowed_ok / g48_allowed_fail | ↑ |
| l5_dangerous_op_guard | 必改 | ⑤ | g49_danger_ok / g50_danger_fail | ↑ |
| l5_reversibility_grading | 建议 | ⑤ | 无样本（待补） | ↑ |
| l5_injection_guard | 建议 | ⑤ | 无样本（评审层，待补） | ↑ |
| l6_versioning | 建议 | ⑥ | 无样本（待补） | ↑ |
| l6_test_suite | 建议 | ⑥ | g43-g46 相关（output/fence 兼测） | ↑ |
| l6_documentation | 备选 | ⑥ | 无样本（待补） | ↑ |
> 分级说明：**P0 必改** = 影响运行/触发/正确性/安全，必须修（死规矩 9「只修必改」= 治疗对象）；**P1 建议** = 提升质量，建议不强制；**P2 备选** = 记录备选（档位迁移：会随时间变建议→必改）；**info 跳过**（v5.0.0）= 识别即跳过，连备选都不记（用户不在意的项，如跨模型测试）；**info 档不设修法条目**（不修=无需修法），故机制表各检查项标注只有前三档。
> 特例：SKILL.md 行数 >500 时，l3_progressive_disclosure 从建议升为必改（必须拆）。
