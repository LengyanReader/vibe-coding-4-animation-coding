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
