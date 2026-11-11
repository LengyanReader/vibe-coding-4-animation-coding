# One Breath Mentor MVP · 构建规划(双语)
# One Breath Mentor MVP · Build Plan (bilingual)

> 依据:`docs/One_Breath_Mentor_MVP_Plan.docx`(通信简报 v1.0)与 `docs/Beyond_the_Opposites_PhD_Proposal.docx`(博士计划 v1.0),两文均 2026-11-10。
> Basis: the two documents in this directory, both dated 10 November 2026.
> 本规划只回答"怎么做",不改变两份文档已经定下的"做与不做"。开工每个 Sprint 仍需人工点头。
> This plan only answers *how*; it does not reopen what the two documents already fixed as in/out of scope. Each sprint starts on an explicit go-ahead.

---

## 0. 定位 / Positioning(两份文档的硬约束,原样继承)

- **研究演示器,不是迷你商业游戏**:让一个设计主张在 6–10 分钟内可被导师"玩懂"——
  A research demonstrator, not a miniature commercial game: one design proposition, legible in 6–10 minutes.
- **四乐章**:Encounter(遭遇)→ Interrelate(互系)→ Release(放下)→ Respond(回应);第四乐章必须存在——放下 ≠ 无为 ≠ 和稀泥。
- **两个案例**:围棋主案例(策展局面)+ 《Two Sides》迁移小样(证明框架不绑死于棋)。
- **明确的"不做"清单**:无 Harmony Index、无道德评分、无悟道分数、无 AI 导师、无遥测收集、无 LLM(第一版)。
- **明确的话术边界**(§11):不说"净化心灵/证悟",只说"研究互动体验能否支持去固着与反思"。

## 1. 交付形态 / Delivery form

**单一自包含 HTML 文件(`dist/one-breath.html`),双击即开,无服务器、无构建依赖、无网络请求。**
A single self-contained HTML file — double-click to open; no server, no build tools on the reader's machine, no network calls.

- 源码为可读的 ES modules(`app/`),由 `tools/build.py`(确定性脚本)内联为单文件产物,产物 sha256 记录入册——**可复现构建**与仓库(vcac)的 provenance 契约同构。
- Source lives as readable ES modules under `app/`; a deterministic `tools/build.py` inlines them into the single-file artifact and records its sha256 — the same provenance contract the vcac repo uses.
- 平板/触控可用(简报要求 browser-first, touch-capable)。

## 2. 体验蓝图 / Experience blueprint(2026-11-10 两次决策的合成)

**人工决策(2026-11-10,两次):**
1. 先不做完整围棋对弈,做二元对立情景;
2. **每个生活情景配一盘"对照棋局"(譬喻模型层)**——情景是案例,棋局是让关系结构
   可见的模型;下棋的内容以此进入 MVP。
   **先做一个案例**(The Two Sides 两侧)供人工查看,再定其余情景。

**棋局譬喻层(Mirror board)——核心机制:**
- 生活叙事推进时,棋盘同步呈现与之**同构**的棋形:玩家的处境 = 一块棋;
  批评/压力 = 对方压过来的那块棋;两者的"气"共享。
- **Interrelate 可交互**:玩家可以在棋盘上亲手试"显然的杀招"(点在对方的气上)
  ——引擎实时演算:这一手同时把两块棋推入险境(**动两块,而非动一块**);
  亦可回退重来("回到此刻")。
- **Release 在棋盘上是一个真实的手**:虚着(pass)或守自身的一手,不是认输——
  选择后棋形安定为**双活**(两块棋谁也杀不死谁);这正是吴清源"中"的全盘观:
  好手是让所有棋子都有效率的那一手(《中的精神》,glossary 已录)。
- **Respond 回到生活文本**;棋盘以安定的双活形作为余象一闪(全盘呼吸一次,
  reduced-motion 则静帧)——**玩家的"认知升级"由这个亲手经历的结构对比承载,
  游戏不宣讲结论**。
- 局面的三条性质由引擎 + Python 交叉验证器证明(见 §5):杀招 → 两败;
  留手 → 双活;全程合法。
- **候选 #2(The Two Ways)的棋局层设计预告**:对照棋局是"同一局面两手并置"——
  算力手由确定性微引擎(纯函数,无 LLM)真实计算(提子最大化),全盘手按"中"
  的原则选定;引擎如实报告两手各自的棋盘后果,玩家两手都下一遍再回到生活文本。
  该案例于 2026-11-11 经人工决策提为优先(先于其余情景)。**风格令牌:清雅温馨**——
  暖纸色底、圆角剪影、柔光、雾绿/琥珀点缀;参照治愈系 2D 作画的形状语言(圆、缓曲线、
  两色柔涂),替代案例一的冷峻墨色。**棋局层的自指设计**:"算力手"由确定性微引擎在
  运行时真实计算(提子最大化,无 LLM、无硬编码),"全盘手"按「中」的原则人工指定;
  两种账本(目数差 vs 呼吸的棋块数)并列呈现,游戏不裁决。

| 情景 | 二元对立(初框) | 对照棋局(譬喻模型) | 放下的可能 | 回应(全部正当) |
|---|---|---|---|---|
| **The Two Sides 两侧**(本轮实现;人际冲突,简报 §3.2) | "我对你错"——会上被公开批评 | 5×5 局面:己方棋 = 你的方案,对方棋 = 批评;两块棋共享气——点杀会动两块,留手则双活 | 放下"必须当场赢回" | 认错部分/请求证据/设边界/异议/事后沟通/暂停 |
| **The Two Ways 两种赢法**(候选 #2,**2026-11-10 增补**;算力 vs 参悟)——**2026-11-11 人工决策:提为当前优先案例** | "机器靠算力赢了,所以下棋没意义了?" | 同一局面下两手并排:**算力手**(确定性微引擎真实计算的最大提子/杀招)与**全盘手**(中的精神:让每一子都有效率的那一手)——两手都成立,意义不同 | 放下"由记分板裁决我的修行是否算数" | 用引擎研究/为悟而下/教一个人下/停一段时间 |
| The Unwritten Map 未写的地图(候选,博士计划 §7.2) | "按计划 vs 失控" | 一张被打断的大飞布局:厚势失效后如何就地做活 | 放下地图 ≠ 放弃目标 | 改道/求助/暂停/原路试探 |
| The Many Faces 诸多面孔(候选,博士计划 §7.2) | "真我 vs 角色扮演" | 一子两用之形:同一子在不同方向承担不同意义 | 放下"唯一真我" | 坦露/协调/设界/保持 |

每情景内嵌四乐章:Encounter(呈现二元)→ Interrelate(选择是否深入揭示)→
Release(可选的放下,不作道德加分)→ Respond(具体回应)。余象:一次克制的
呼吸意象(水墨语汇,reduced-motion 降级),无"证书"感。

## 3. 双语方案 / Bilingual approach(按 M4.10 意群规程)

这是本规划引用的唯一跨语言纪律:**译的是意群,不是词**。

1. **意群对齐创作,而非事后翻译**:小样与提示文本按意义单元成对创作——每节点存
   `{id, zh, en}`,两语**同期撰写**(同一位作者一次写两语,或两位作者对齐后互证),
   不做"先中后英"的流水线。
   Content is authored as meaning-unit pairs (`{id, zh, en}` per node), written together — not translated after the fact.
2. **术语表先行(Sprint 0 交付)**:围棋术语气/liberties、眼/eye、双活/mutual life、
   虚着/pass、劫/ko;哲学术语 无住/non-attachment、去固着/de-fixation、事事无碍/
   unobstructed action(事事无碍保留汉字 + 英文释义,音译加注,不悄悄换词)。
   A bilingual term table ships in Sprint 0; culture-bound terms are transliterated + glossed, never silently substituted.
3. **互证(§3 规程)**:英文侧做**回译**(不看原文,逐单元 diff);中文侧由母语读者
   做"你读到了什么"复述;两种互证至少各一次,记录在小样文件旁。
   Back-translation on the English side, a native-reader comprehension pass on the Chinese side — at least one each, recorded.
4. **自动门禁**(机器可证的部分):每个 i18n 键 zh/en **同时存在**、无空串、占位符一致、
   小样每个节点两语齐备——CI 级测试,缺一即红。
   A completeness gate: every key present in both languages, placeholders identical, every vignette node bilingual — red if not.
5. **界面语言切换**:标题屏可选 中/EN,选择存 localStorage;默认跟随浏览器语言;
   数字与棋谱记号(go terms)不翻译。

## 4. 技术架构 / Architecture(零框架,可测性优先)

```
One Breath MVP/
├── docs/                      # 两份源文档 + 本规划(既有)
├── specs/                     # 一切"内容"皆数据,Sprint 0 冻结
│   ├── vignettes/
│   │   ├── two-sides.yaml     # 情景一:两侧(故事图,节点/选项/旗标,双语)
│   │   ├── unwritten-map.yaml # 情景二:未写的地图
│   │   └── many-faces.yaml    # 情景三:诸多面孔
│   ├── strings.yaml           # {key: {zh, en}} 全部界面文本
│   └── glossary.md            # 双语术语表(M4.10 §4)
├── app/                       # 源码 ES modules(可读、可测)
│   ├── vignette.js            # 故事图运行时(只解释图,无道德评分逻辑)
│   ├── i18n.js                # 双语运行时 + 切换
│   ├── visuals.js             # 呼吸/余象(canvas,水墨语汇,reduced-motion)
│   └── main.js                # 场景机:标题/情景选择/四乐章/余象/回访
├── tools/
│   └── build.py               # 内联 → dist/one-breath.html(确定性,记 sha256)
└── tests/                     # node --test + 红例
    ├── vignette.test.js       # 每个结局可达、无死枝/孤儿节点、无 score 变量
    ├── i18n.test.js           # 双语完整性(缺一即红,占位符一致)
    └── determinism.test.js    # 同一选择序列 → 同一结局(无隐藏随机)
```

- **引擎与内容分离**:vignette.js 只解释故事图(节点/选项/旗标/转移),不含任何
  情景文本或评分逻辑——情景全部在 specs/ 里,评审 diff 即设计 diff。
  The engine only interprets the story graph; all content lives in specs/.
- **无隐藏随机**:同一选择序列必须到达同一结局(determinism.test.js 证死)——
  这是"研究演示器"的本分,也是严肃游戏可测干预的根基。
- **视觉语言**:水墨气质(暖纸底、墨色文字层次、呼吸脉动的圆相),向 vcac ink
  路线的视觉语汇致意;余象是**艺术假设**(简报 §5 原话),reduced-motion 下退化为
  一次安静的呼吸。
- **音频(可选,默认关)**:如做,由 vcac 音频路线确定性合成一段呼吸式环境床
  (felt-piano 引擎的副产物),内嵌为 wav,一键静音。
- **无 LLM、无遥测、无数据收集**;`vignette.js` 里不存在 score/正确答案变量——
  这一条由静态测试证明,而非口头承诺。

## 5. 测试与门禁 / Gates(仓库纪律的移植)

| 门 | 性质 | 红例 |
|---|---|---|
| 规则合法性(提子/禁着/简单劫) | 纯函数单测 | 非法劫回、自杀手必须被拒 |
| 策展局面合法性 | verify.py × JS 交叉 | 任一实现判非法即红 |
| 小样可达性 | 图遍历 | 死枝/孤儿节点即红 |
| **无道德评分** | 静态检查(vignette.js 无 score/正确路径变量) | 引入计分即红 |
| **双语完整性** | i18n 键位对齐 | 缺一语即红 |
| 确定性 | 同一输入脚本 → 终局哈希一致 | 哈希漂移即红 |
| 构建可复现 | dist 产物 sha256 入册 | 二次构建哈希漂移即红 |

## 6. Sprint 计划 / Sprint plan(单人 + AI 协作节奏,较简报的 4–6 周压缩)

| Sprint | 内容 | 交付 |
|---|---|---|
| **S0 设计冻结**(2026-11-10 会话内完成) | 三情景故事图 zh/en 成对初稿;双语术语表;安全话术 | specs/ 全套 |
| **S1 灰盒可玩** | vignette.js 运行时 + 场景机 + 语言切换 | 双语灰盒,可发 |
| **S2 观想层** | 呼吸视觉、余象(reduced-motion)、可选音频 | 完整 6–10 分钟体验 |
| **S3 双语互证 + 构建** | 回译互证记录;build.py → 单文件 dist | 导师沟通包的核心(S3 为本轮交付终点) |
| **S4 形成性试玩** | 6–10 人试玩(观察/访谈),修订 | **暂缓(2026-11-10 人工决策)**,启动前先交付双语观察表 |

S0+S1 合计预计 2–3 个工作会话;S2/S3 各 1–2 个;S4 需要真人参与,由你安排。

## 7. 需要你拍板的三件事 / Three decisions for you

1. ~~棋盘 5×5 还是 7×7~~ → **已决(2026-11-10):先不做棋**,做三个二元对立情景
   (两侧/未写的地图/诸多面孔),围棋案例推迟为研究变体。
2. ~~音频~~ → **已决:S2 可选项**(默认静音,一键开,vcac 音频引擎确定性合成)。
3. ~~S4 试玩~~ → **已决:暂缓**,交付到 S3;启动前先交付双语观察表与访谈提纲。

## 8. 与 vcac 仓库的关系 / Relationship to the vcac repo

本目录(`One Breath MVP/`)将成为一个**自足的子项目**,复用仓库的方法论而非代码:
spec 驱动、验收门、golden、确定性构建、双语意群规程(其中 IF 故事图即
`docs/research-games-2026-11-07.md` 候选 #3 的首个落地,围棋主案例兼具候选 #1 的
严肃游戏形态)。两份源文档里的来源(吴清源、Gobet、Rusch & Phelps 等)在
S0 全部登记进 glossary,并按简报 §6 的"负责任引用"方式标注。

*English executive summary — One Breath Mentor MVP: a self-contained, bilingual
(zh/en) browser demonstrator proving the Four-Movement contemplative design
grammar (Encounter → Interrelate → Release → Respond) on a curated 5×5 Go
scenario plus "The Two Sides" transfer vignette; zero frameworks, deterministic
build, spec-driven content, node-tested rules and vignette, no AI, no scoring,
no data collection. Sprints S0–S4 as tabled above; board size, audio and
playtest logistics await your decisions.*
