# 游戏 · 游戏化 · 严肃游戏 · 互动叙事 — 调研与候选规划(2026-11-07)

> 回答四个问题:这个领域现在是什么格局?结合本仓库的能力(确定性 spec 驱动、
> 13 条媒体路线、无头游玩测试机器),哪些东西**有意义且有趣**、可以做草稿或
> 小样?按什么顺序?每个候选的验收门怎么设计?
> 本文是规划文档,不含实现;候选开工仍走"每个 loop 一个 spec + 门禁 + golden
> + 突变红例"的仓库惯例(M0.3/M0.8:开工需人工点头)。

## 1. 格局检索摘要(2026-11 检索,来源见文末)

**互动叙事(IF)**:四大家格局多年未变——
- **Twine**:无代码选项超文本,HTML 产物;最适合分支叙事原型;
- **Inform 7**:解析器型文字冒险,自然语言编程,世界模拟能力最强;
- **Ink**(Inkle):商业级分支叙事脚本(《80 Days》《Heaven's Vault》),JSON 导出可嵌引擎;
- **Ren'Py**:Python 系视觉小说引擎,立绘/音频/发行链成熟。
  选型由**交互模型**(选项 vs 解析器)与呈现需求决定,而非新旧。

**严肃游戏**:文献一致支持**单目标、紧切口的微游戏**最有效——
- 短期学习效果证据充分(健康专业教育综述),长期保持需课程化配合;
- 范例形态:Flowy(惊恐发作管理,单一呼吸机制)、Rage Control(愤怒管理,
  单一心率反馈)、EndeavorRX(FDA 批准的 ADHD 治疗游戏)——共同点是
  **一个行为目标 + 一个核心循环 + 可测量的状态**;
- 设计模式词汇(问题求解型严肃游戏与 MR 训练的模式目录)可作为设计语言。

**对本仓库的含义**:我们天生就是"微游戏工厂"——确定性模拟、脚本化输入、
状态断言、可复现回放,这些恰是严肃游戏文献要求的"可测量"本体。缺的不是
工程,是**选题与玩法的创作判断**(M0.4:机器观察,人决定实质)。

## 2. 仓库独特优势(为什么是我们做,而不是别人)

1. **跨路线资产管线**:立绘/插画(illustration)、水墨(ink)、配乐(audio
   fluidsynth)、未来 SFX(音频队列 #4)——游戏**消费**其他路线的产物,这是
   普通游戏原型没有的杠杆(roadmap §2.4 asset pipeline 原案);
2. **无头游玩测试机器已存在**:game_sample 的 scripted input → 状态断言 →
   3× 确定性回放 → 试玩渲染(dodge-headless,golden `c67acbf8…`),甲乙丙丁
   分级里的**甲级**——新玩法接上就自动获得同一套验收纪律;
3. **spec 即玩法契约**:YAML 事件/关卡/断言,评审 diff 就是设计 diff;
4. **确定性种子**:程序化关卡/掉落/敌人刷新全部可回放,恰合 roguelike 与
   严肃游戏"可测干预"的根基。

## 3. 候选清单(可行性 × 可达等级 × 跨路线消费 × 趣味)

| # | 候选 | 装机 | 可达 | 消费路线 | 趣味/意义 | 核心循环 |
|---|---|---|---|---|---|---|
| 1 | **诗词山水鉴赏·严肃游戏**(看画猜诗/看诗辨画/印章识别) | 零装 | **甲** | ink、illustration | 美术教育;紧切口单目标=文献最优形态 | 出题(从 spec 元数据生成)→ 作答 → 状态断言 → 计分 |
| 2 | **听音辨音程/和弦训练微游戏** | 零装 | **甲** | audio(引擎直出音,确定性) | 听觉训练,教育实证强 | 播音程 → 四选一 → 断言正确率与反应 |
| 3 | **自研微型 IF 引擎 + 视觉小说样例** | 零装 | 甲(引擎)/乙(文本艺术) | manga/illustration 立绘、piano 配乐、ebook 导出 | **战略底座**:YAML 故事图=spec,walk-through 脚本=playtest,死枝可达性=门 | 节点状态机 + 条件 + 背包/旗标 |
| 4 | **pygame-ce 微街机**(dodge 的真 runtime 化) | 轻装(需同意) | 乙 | image 精灵、audio SFX | roadmap §2.4 原案;sim 与真引擎**对拍** | 同一输入脚本双跑,断言最终状态哈希一致 |
| 5 | **程序化地牢 roguelike 微样例** | 零装 | 乙 | audio SFX、image 纹理 | 种子确定性关卡天然契合;win/lose 可达性门 | 房间生成 → 移动/拾取 → 胜负断言 |
| 6 | gamification 元层(为 pipeline run 发徽章/进度) | 零装 | 乙 | — | 有趣但属"产品层",暂缓 | run 完成度 → 徽章断言 |

**推荐队列**:1 或 2 先行(零装、强跨路线、甲级可达、各一晚上工作量);
3 第二(IF 引擎是叙事与视觉小说的通用底座,且能把 manga/illust 的产出真正
"用起来");4/5 随后;6 记录不做。**每个候选开工都需你点头**(M0.8)。

## 4. 各候选的验收门草案(延续 roadmap §2.4 已承诺的门)

- **通用**(全部候选):win/lose 双路径可达性;不变量(无 NaN/越界);帧预算
  或 ticks/sec;required-asset 存在;3× 确定性回放;asset sha256 入 manifest。
- 候选 1:题库覆盖(每类题型 ≥N 题)、答案-题干一致性、错题可复现(种子);
- 候选 2:音程频率比精确(spec 声明 → 实测频谱核对,甲式"声音可读回");
- 候选 3:故事图可达性(死枝=fail)、旗标状态机不变量、walk-through 覆盖
  每个结局、立绘/配乐 asset 存在性;
- 候选 4:sim↔pygame 状态哈希逐 tick 对拍;帧预算(p95);
- 候选 5:种子扫描 N 关全可通关(自动求解器或脚本通关)。

## 5. 与既有文档的衔接

- 现有 game harness 的契约与缺口:`docs/roadmap-development.md` §2.4;
- 能力分级(为何 1/2 是甲级):`docs/capability-2026-11-07.md` §1;
- dodge-headless 的验收实录:README §0 表 game 行。

## 6. 来源

- IF 引擎格局与对比:[Prose Poetry Code](https://prosepoetrycode.potterpcs.net/tag/interactive-fiction)、
  [Twine](https://twinery.org)、[intfiction.org 2025 讨论](https://intfiction.org/t/twine-or-inform-7/74263)、
  [Game Developer: free narrative tools](https://www.gamedeveloper.com/game-platforms/the-best-free-tools-for-narrative-games)
- 严肃游戏:[健康专业教育综述 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6697512)、
  [JMIR Serious Games 2025 关键原则](https://games.jmir.org/2025/1/e54075)、
  [JMIR 2025 Health Unit in Focus](https://games.jmir.org/2025/1/e66289)、
  [McGill 小切口康养游戏(Flowy/Rage Control)](https://www.mcgill.ca/ihdw/research/working-groups/ghdw/serious-games-well-being)、
  [8D Games 案例集](https://8d.nl/en/examples-of-serious-games)、
  [Indie Game Business 2025 综述](https://indiegamebusiness.com/serious-games-shaping-education-and-training)
