# 回译互证记录 · Back-translation corroboration record (M4.10 §3)

> 规程:双语交付的互证至少其一——回译、目标语读者复述、跨来源互校。
> 本记录覆盖案例一《两侧》的全部节点文本(16 节点)与界面文本。

## 1. 回译(Back-translation) — 已做,2026-11-10

方法:五个结局节点(回应的肯定文本)从英文渲染**不看中文原文**回译为中文,
逐意群与中文原文比对。发现与处置:

| 意群 | 英文 | 回译结果 | 判定 |
|---|---|---|---|
| e_ack 保护物 | "The room's attention moves from winning back to the work." | 会议室的注意力从输赢挪回事情本身 | 一致 ✓ |
| e_boundary 机制 | "You decline his frame and offer another rule." | 你没有接他给的框架,你给的是另一条规则 | 一致 ✓ |
| e_pause 机制 | "You hand the meeting back to the agenda." | 你把会议还给了议程 | 一致 ✓ |
| n1 初框 | "one sentence fills your head: I am right, they are wrong" | 心里只剩一句话:我对你错 | 一致 ✓(意群"只剩"被回译出来) |
| n4 放下 | "not surrender, and not generosity. Just: no longer gripping." | 不是认输,也不是大度。只是,不再攥着 | 一致 ✓ |

无触及事实/辖域/情态的偏差;未发现合并型缺陷(两意群被融为一个主张的情况)。

## 2. 目标语读者复核 — **待用户**(独立读者)

规程要求中文母语读者回答"你读到了什么"而非"翻得对不对"。
**这一步是你**:打开 dist/one-breath.html,任意走完一个情景,读中文文本——
你读到的意思与英文切屏对照即为证据。发现任何一处"两种语言说的不是一件事",
记录回此文件,即为 defect(修文本,不修测试)。

## 3. 术语表执行情况

`specs/glossary.md` 全部条目在文本中按表执行:无住/non-attachment 不译
detachment;事事无碍保留汉字;气/眼等围棋术语推迟案例占位;pass 译"虚着"。

## 4. 声明

本文档只记录案例一的互证状态;后续案例(两种赢法/未写的地图/诸多面孔)
开工时各自补一条同形记录。翻译不是风格的匹配,是**主张的匹配**——
两种语言可以说得不一样,但必须主张得一样。
---

## 5. 第零章《同气》 — 2026-11-11

覆盖:7 条教学规则 + 7 条提示 + 案例 11 个节点 + 5 个结局 + 新增界面文本。
方法:双语意群成对创作(非事后翻译);机器门禁已跑(40 项 Node 测试 + 独立 Python 校验)。

### 5.1 回译(作者本人 — 弱证据,如实标注)

同一作者先把英文渲染回中文、再逐意群与中文原文比对。这不是独立互证;
它只能发现**合并/替换型缺陷**,不能替代目标语读者。

| 意群 | 英文 | 回译 | 判定 |
|---|---|---|---|
| 规则一 | "A stone breathes through the empty points above, below, left and right. While it has a breath it stays; when the last one is filled it leaves." | 一颗子靠上下左右的空点呼吸;有气就留在盘上,最后一口气被填上就离开 | 一致;英文以 "breathes" 承担"有几口气",未改主张 |
| 规则三 | "Fill a chain's last liberty and it leaves the board: that is a capture. Not destruction — it simply has no breath left." | 填上一块棋最后一口气,它就离开棋盘:这叫提子。不是消灭——它只是没有气了 | 一致 |
| 规则六 | "Two chains breathe through the same corridor: whoever fills first hands the last breath to the other. Fill all four and the first mover's chain is gone — so here, not moving is a move." | 两块棋通过同一条走廊呼吸:谁先填,谁把最后一口交给对方。四口填完,先动手的那块棋没了——所以在这里,不动就是一手棋 | 一致;"留给/交给"为近义替换,未改主张 |
| 规则七 | "A pass is not surrender. It hands the turn over and leaves the corridor as it is. In some positions, not moving is the response." | 虚着不是投降。它把这一手交出去,让走廊保持原样。有些局面,不动就是回应 | 一致;"认输/surrender"同一主张,非教义术语 |
| 结局·边界 | "What this response protects: the boundary." | 这一回应保护的是:边界 | 一致 |

### 5.2 目标语读者复核 — **待你**

你打开 `dist/one-breath.html`,进入「同气」,读中文规则与五个结局,
回答"你读到了什么"(不是"翻得对不对")。任何一处两语说的不是一件事,记录在此。

### 5.3 术语执行

`specs/glossary.md`:眼/双活 由占位转为实用;新增 同气 / 照见 / 觉悟人生 /
活棋 / 禁入点 / 真眼 / 共享的气。`觉悟人生` 是幕名,不是证悟声明。

### 5.4 声明

本记录不声称译文质量;只记录意群未被合并或替换。第零章的教学规则是
**创作内容**,不是文献主张;其中的围棋规则由两份独立实现证明,
不由文本互证证明。
