# 画法与风格模拟盘点 · Painterly Styles & Art-Technique Simulation

> 与 `docs/tools.md`（工具生态）平行的第二张地图：tools.md 回答「有哪些工具能跑」，
> 本文回答「**某种画法能否被代码复现，以及用什么技术路线**」。
> 触发问题：能否做一幅中国古代山水画？当代插画？梦工厂/迪士尼级 3D？日式 2D？
> 结论先行：**能做的程度差异极大，且瓶颈不在软件，在于「画理能否被形式化」与「资产工时」**。
> 检索日期 2026-11-04；✔primary=官方/一手，○secondary=二手，⚠unverified=未回源。
> **穷尽性**由平行台账 `docs/coverage-audit.md` 管理（六条分类轴 + 逐格判定 + 残余缺口），
> 本文只回答“某画法/风格能否被代码复现”。新增风格族时，两边都要登记。

---

## 0. 三档天花板（先给诚实判断）

| 目标 | 可达程度 | 真正的瓶颈 | 本项目定位 |
|---|---|---|---|
| **中国水墨/山水、浮世绘、版画、Riso、扁平插画、像素、线稿** | **高**：技法本身是分层、可枚举的程序 | 把画理写成约束（而非调滤镜） | ✅ 主战场，零/轻安装 |
| **生成艺术基元（§11）、光学/低比特/故障（§12）、胶片质感（§13）、规则图案系统（§14）** | **最高**：它们本就是算法/对称群/曲线 | 几乎无——只靠工时 | ✅ 零/轻安装，验收最易（§11 的元胞自动机还自带时间轴） |
| **平面设计史流派（§10：瑞士/包豪斯/风格派/构成主义/Deco/Memphis/Y2K…）** | **最高且无上限**：它们从来就是**网格 + 色板 + 字阶 + 母题**的参数集 | 几乎无；只要求把具体数值写进 spec 而不是口头描述 | ✅ 零安装（接 `tools.md` §0.2 浏览器版面器）；且**不涉参考图版权** |
| **工程/专利图/轴测/体素/PS1 复古（§16）** | **高**：靠“规则正确”而非“画得像” | 线规/标号/剖面的完整性验收需自定义 | ✅ 零/中安装 |
| **动画表演与时序风格（§15）** | **中高**：12 原则可写成曲线与量化参数 | “手感”仍是人的判断 | ✅ 零安装（缓动写进帧函数即可） |
| **日式 2D 动画（赛璐璐/2.5D）** | **中高**：3D 渲染 + 描边 + 分层合成是业界成熟做法 | 角色资产与作画监督的人工判断 | ⚠ 需 Blender（重安装） |
| **漫画墨线（上墨引擎，2026-11-05 实测）** | **语法可达、作画不可达**：路径 DSL / 笔尖压力 / 网点 / 毛筋 全部实现且可复现 | **造型功力**：同一颅骨复用五次、无身体体积、无前后遮挡、无透视——这些**门禁全绿时仍然存在** | ⚠ 到 丙档 天花板为止，见 §0.1 |
| **迪士尼/皮克斯/梦工厂级 3D 长片** | **中**：开源工业栈齐备（USD/MoonRay/Cycles/Houdini），短片可达高质量档 | **不是工具问题**：模型、绑定、灯光、表演的艺术工时以人年计 | ⚠ 只做「程序化镜头/短片」，不承诺长片质感 |
| **AI 风格模仿（Ghibli 风、名画风）** | 技术上容易 | 非确定性 + 版权/风格诉讼风险（见 §8） | ❌ 不入渲染主路径 |

---

### 0.1 边界画在哪里：按「可证性」分层，不按风格（2026-11-05 实测）

上表按**风格族**列天花板，回答不了「现在能做到什么层次的作品」。真正的分界线不在风格上，
在**验收的可证性**上：一条路由能测的属性，是否就是决定它好坏的属性。四条边界，全部有实测支撑：

| 档 | 判据 | 已验证的路由/族 | 上限 |
|---|---|---|---|
| **甲** | 被验的属性 = 成败的属性，机器能证明对错 | `spectrogram-truth`（图→再读出音高）· `swiss-poster`（网格/字阶/留白比 + 突变体 `seal-invisible`/`paper-flooded`/`no-whitespace` 都见过红）· `variable-weight`（`fvar` 轴逐帧实测）· `kern-piano`（8 条音频门禁）· `dodge-headless`（状态断言）· §10–§14 各族 | **满格**：上限只受工时限制 |
| **乙** | 物理量能测，「手艺」需人眼 | `ink-landscape`（明度带/层次/留白 可测；皴法像不像某家 不可测）· `anime-eave`（镜头切换用直方图 TV 实测；表演手感不可测） | **中—中高**，且必须承认人眼是最终裁判 |
| **丙** | 语法可控，执行质量有硬天花板 | `manga-ink`（本轮）：单张脸成立，群像不成立 | **到「同一颅骨」为止**，见下 |
| **丁** | 结构上做不到 | 手绘级原创角色设计 · 多格分镜 + 跨格角色一致 · 长片 3D 质感 · 版权角色 · 任何非确定性图像生成（本机 iGPU 1 GB + `torch 2.15.0+cpu`） | — |

**丙档 的天花板是量出来的，不是感觉**。2026-11-05 的手写上墨路线（`src/vcac/manga_ink.py` +
`specs/examples/manga-guild.yaml`）在 13 轮渲染后交付了一页五人公会群像：

- ✅ 单张脸现在读得通：正确椭圆、带睫毛的眼睛、黑发的整体刘海形与 毛筋 高光、下颌投影、张口喊；
- ❌ 五张脸是**同一张脸**——为保比例把同一套颅骨坐标复用五次；胸像以下没有身体；大衣是扁平灰钟形，
  人与人之间没有分隔线，没有前后遮挡的投影，没有透视；
- ❌ 而且**以上全部发生时十二门禁是绿的**。

引擎自己的 docstring 早写过「最后那五分之一是绘画功力」；本轮把这五分之一**拆成了三个可命名的缺口**
（同一颅骨复用 / 无体积 / 无遮挡层），这是代码路线**能换来的唯一硬成果**。

**绿门禁为什么骗人——五条实测的假绿**（都可复现，探针已入库）：

| 假绿 | 报的数 | 真相 | 为什么机器看不出来 | 处置 |
|---|---|---|---|---|
| `at least 4 separate figures` | `figures=11` | 实为 5 | 脸上的嘴/下颌投影/穿过的 毛筋 把皮肤块劈成两半，每一半都还含一个纸白点 → 一张脸数成两张 | 改为读 spec 自己的 `figures:` 表（`5`），并写明它只证明「作者要了五张脸」，不证明「出来五张脸」 |
| `at least 8 drawn eyes` | `eyes=67` | 实为 10 | 「小块纸白 + 四周环墨」的定义对**一切孔洞**都成立：标志字的字腔（`y=0..13` 一整排）、黑发里打出的 毛筋 高光线、人物间的背景缝。75 个候选**每一个 `enclosed=0`**，即没有一个含瞳仁 | 不再测：`eye_count` 不再产出，规则如实报 `skipped`。第二定义「皮肤上的小墨岛」也试过，实测返回 **0**（眼睛的墨与睫毛/眉连续，不存在闭合岛），故不编造新启发式判据 |
| `ink weight spread above 1.4 px` | `2.00 px` ✅ | 栅格上真实只有 **3 个宽度值**：2.00 px 占 67.4%、4.00 占 23.7%、4.47 占 4.1% | 门禁读的是**下采样并量化之后**的成品；1.8 px 和 2.2 px 都落到 2 px，压力曲线在门禁看它之前就被毁掉了 | 改在**下采样前的硬边栅格**上量（脊判定窗口随 S 缩放）：同一页 `spread=4.00 px`、`median=2.67 px`，`run_id` 未变（`sha256:bc0d08447a3fb1cc`），即只换测量对象、没换产物 |
| `ink weight spread above 1.4 px`（**地板本身**） | 恒宽钢笔突变体 `1.84 px` ✅ | 一笔画到底的页面仍绿 | 把测量移到笔尖栅格是**必要而不充分**：1.7 px 线在 3× 栅格上是 5.1 px，半像素落点加笔尖自身抖动并不归零，1.4 的地板看不见它自己要抓的故障 | 依实测把地板抬到 **2.4 px**（恒宽 1.84 / 作者 4.00 之间，靠近故障侧）；`_pen_weight` 改为遵守 spec 的 `nib.measure_max_px`（原为硬编码 `14.0*S`）；`nib_gate_mutant_probe.py` 打印两侧 |
| `sky negative space`（黄昏页地板） | 涂两大片平滑云 `45.9→75.6` ✅；删尽云与日 `45.9→44.7` | 往天空里**画东西**反而更「空」 | 读的是**原始亮度梯度**，量到的其实是量化前的 Bayer 网点——把 4×4 交替当成了笔触，方向因此倒转 | 在 `5×5 median` 后的亮度上判忙疏（`_dither_free_edges`：消交替、保硬边）；方向单调后，十朵小硬边云把黄昏页压到 `73.5`，地板据此定在 `78%`；三页带宽按实测重定为 `78–92 / 40–72 / 60–92`（guild 旧天花板 55 甚至低于其自证值 58.9，正确页反被报红） |

> 探针：`scripts/probes/manga_count_probe.py`（逐个候选连同判定数字 + 画框叠图）·
> `scripts/probes/manga_weight_probe.py`（宽度分布）· `scripts/probes/nib_gate_mutant_probe.py`（恒宽地板两侧）·
> `scripts/probes/sky_gate_probe.py`（原始 vs median5）· `scripts/probes/ink_flatten_probe.py`（见 §8 的色数教训）。
> 五条共同形状：**门禁验的是它恰好会算的东西，不是它声称在验的东西**；数字看起来合理，就没人去问它是怎么来的。
> 甲档 之所以可靠，是因为那里被验的属性就是成败属性；丙档 里两者脱钩，绿光于是成了误导。
>
> 附一条自我更正（同一形状的第六次触发，只不过这次是我读错了自己的诊断量）：把测量移到笔尖栅格后，
> 我曾断言「脊宽样本里有三分之一宽过任何作者笔尖，是填色块肩部」，并写进了 docstring。**错了**——
> 我只拿 `figures[].parts`（最宽 3.60 px）比对，从未看 templates/backdrop/foreground。全页最宽笔尖是
> `backdrop` 一处 burst 的 **6.36 px**，我称作「块肩」的 5.33 px 众数其实是作者自画的平线，真正超宽者仅 **0.4%**。
> 教训与五条同源：**在一处测量然后推断其余，正是这个文件反复犯的错**（`nib_leak_probe.py` 打印了两候选帽下的直方图）。

---

## 1. 中国古代山水 / 水墨 · Chinese Shanshui & Ink Wash

### 1.1 画理的形式化（这是关键，不是滤镜）

传统画论已经把山水变成**可枚举的规则集**，这正是代码能吃下的东西：

| 画论概念 | 出处 | 可形式化为 | 落到我们管线 |
|---|---|---|---|
| **六法**（气韵/骨法/应物/随类/经营/传移） | 谢赫《古画品录》 | 经营位置=构图约束；随类赋彩=调色板映射；骨法=笔触轮廓 | 构图用布局 DAG，色彩用 palette（已有） |
| **三远**（高远/深远/平远） | 郭熙《林泉高致》 | 三种相机/视高与层叠深度关系 | 高度场 + 分层雾（大气透视）+ 相机规则 |
| **墨分五色**（焦浓重淡清） | 传统画论 | 明度直方图约束为 5 段 + 大量留白 | 新增验收：明度分段直方图 + 留白比例 |
| **皴法**（披麻/斧劈/折带/雨点/卷云…） | 荆浩以下诸家 | **纹理基元库** + 沿坡面法线/高度铺设 | 基元 = 参数化笔触 stamp 集合 |
| **留白** | 计白当黑 | 背景占比下限 + 无信息区允许 | 反直觉：熵下限要按区域加权，别全局卡 |
| **散点透视** | 相对焦点透视 | 多视点拼接（长卷即时间轴！） | 长卷 = 我们的帧序列退化成一维空间轴 |
| **诗书画印** | 文人画传统 | 题款（字体）+ 钤印（红色几何章）位置规则 | 字体（§6）+ 印章程序化生成 |
| **工笔 vs 写意** | 两路 | 工笔=多层薄染（可分层）；写意=一次性笔触（随机性受控） | 工笔天然更适合确定性管线 |
| **生熟宣 / 纸绢底** | 材料 | 噪声基底 + 吸收扩散系数 | 已有 value-noise 基底可直接复用 |

**核心洞察**：⿻ **多板块套色版画（饾版/拱花、浮世绘多版）本质上就是分层合成 DAG** ——
一版一色一 mask，逐层套印 = 我们的 `alpha_composite` 链。这是传统技法与代码管线最契合之处
（《十竹斋笺谱》即早期"程序化多通道印刷"）。

### 1.2 可执行技术路线（零/轻安装，纯代码）

一条确定性的"山水"渲染链，全部可用已装的 Pillow + NumPy + SciPy 实现：

1. **纸本底**：分形噪声 + 纤维方向场 → 宣纸质感（复用 `media` 的噪声原语）。
2. **地形/高度场**：fBm + 域扭曲（domain warp）→ 山体剪影；按"三远"规则选视高与层数。
3. **勾**：轮廓线 = 等值线提取（SciPy `marching squares` / `skimage.measure`）+ 抖动化
   （沿法线加种子噪声，即 Rough.js 的算法本质，可在 Python 自研，不必引 JS）。
4. **皴**：纹理基元沿坡度方向铺设（披麻=长平行弧；斧劈=短直块面；雨点=点簇）。
5. **擦/染**：低频灰阶调制 + 边缘扩散（可用 SciPy 高斯/各向异性扩散近似墨渗）。
6. **积墨**：多层薄墨叠加，每层透明度与颗粒受控 → 确定性叠加即"随类赋彩"。
7. **云气留白**：按高度与视角阈值把区域拉回纸白（不是画云，是**不画**）。
8. **题款 + 钤印**：OFL 中文书法体（§6）+ 程序化印章（红底白字/朱文白文，边缘做崩缺噪声）。
9. **验收**：分辨率 / 色域=水墨 5 段 + 印泥红 / 明度直方图 / 留白比例 / 非全局熵下限 / 确定性。

> 这条链完全落在我们已跑通的 image 路线骨架上（spec→render→measure→validate→manifest），
> 新增的只是 renderer 与几条画理型验收规则。

### 1.3 学术与开源现状（Discover 结果）

| 工作 | 类型 | 要点 | 来源 |
|---|---|---|---|
| Computational Approaches for Traditional Chinese Painting (Zhang, 2024, JCST) | **综述** | 把 TCP 计算化分三类：分析/合成/创作；含树木剪影+纹理笔触合成、花卉画生成 | ✔primary `arXiv:2307.14227` + sciopen |
| Interactive & generative Shanshui painting (Le Zhou, 2019) | 交互生成 | 依用户输入生成山水"文档"，含 6 种子风格 | ✔primary XJTLU scholar |
| Image-based synthesis of Chinese landscape painting | 基元合成 | 少量笔触纹理基元 + 图像域合成（与 §1.2 思路同构） | ○secondary scispace |
| The Synthesis of Rock Textures in CLP | **皴法专项** | 山石纹理（皴）合成 | ○secondary ResearchGate |
| Real-Time Image-Based Chinese Ink Painting Rendering (Dong, CAD&G, 浙大) | 墨扩散 | 非物理模型近似渗化，实时 | ✔primary cad.zju.edu.cn PDF |
| Simulation of Chinese Ink-Wash (LEM 局部平衡模型) | 物理墨渗 | 基于景观与树的模拟 | ○secondary |
| Color Hint-guided Ink Wash Colorization (ACM TOG 2024) | 学习法 | 线稿 + 颜色提示 → 水墨上色（**非确定性**） | ✔primary dl.acm.org 3657637 |
| IJCAI 2022 高分辨率任意尺寸山水画 GAN | 学习法 | 三阶段 GAN 系统（**非确定性**） | ✔primary ijcai proceedings |
| Paint-CUT (Applied Sciences 2024) | 学习法 | 山水画生成模型 | ○secondary MDPI |
| takara-ai Sumi-e ink painting closeups (HF dataset) | 数据 | 1250 张**合成**水墨笔触特写（LoRA 训练用） | ✔primary HF |

### 1.4 参考图与授权（引文即生命线）

| 源 | 规模/内容 | 授权 | 可用性 |
|---|---|---|---|
| **The Met Open Access** | **492,000+** 公有领域作品图像，含中国书画；官方 REST API（JSON + 高分辨率 JPEG） | **CC0，自由无限制使用** | ✅ 最适合代码调用：拉构图/取色/做统计 |
| georgeblck/art-datasets | 90+ 研究数据集、35+ 博物馆开放馆藏清单 | 列表本身开源 | ✅ 索引入口 |
| ArtBench-10 (arXiv 2206.11404) | 类别均衡的艺术风格基准 | 研究用 | ○ 风格评测参考 |
| WikiArt (huggan/wikiart, Kaggle) | 1M+ 画作，27 风格标签 | **仅限非商业研究** | ⚠ 不可用于商业产出训练/参考 |
| 故宫名画记 (dpmg.org 名画记) | 超高清中国名画（含千里江山图一类） | ⚠ **未回源核验授权条款** | 标 unverified，先按"仅个人研究"处理 |
| 东京国立博物馆 / Smithsonian Open Access | 东亚绘画、开放数据 | 各异（多为 CC/公有领域） | ○ 待逐件核验 |

---

## 2. 东亚其他画法族

| 风格 | 可确定性复现的要点 | 技术路线 | 来源 |
|---|---|---|---|
| **浮世绘（多版木版画）** | 版木=通道；key block 轮廓 + 逐色套印 + 渐变（ぼかし）由该版内墨量梯度实现 | **分层 DAG 直译**：每版一张 mask + 一色，`alpha_composite` 顺序叠加；纸纹最后叠 | ✔primary 技法通识 + 可 API 化 |
| **水墨漫画/少年志线稿** | 笔尖压力曲线 + 速度线 + 网点（screentone = 固定图案 dither） | 网点即程序化半色调；线稿即 XDoG/轮廓 + 抖动 | ○ |
| **书道 / 篆刻** | 笔顺时序（可回放）+ 飞白（速度→墨量衰减）；印章=朱文/白文 + 崩缺 | 笔触 stamp 链 + 边缘噪声；印章可形式化 | ○ |
| **工笔重彩/青绿山水** | 多层薄染（每层低不透明度）+ 矿物色板（石青/石绿/朱砂/铅白） | 天然适合确定性分层；色板可固定为已知 RGB 集 | ○ |

---

## 3. 西方传统画法的计算模型（有现成论文/实现）

| 画法 | 代表算法 | 开源实现 | 确定性 | 来源 |
|---|---|---|---|---|
| **水彩** | Curtis et al. 1997 *Computer-Generated Watercolor*（浅水方程 + 颜料沉积 + 纸高） | `inchkev/watercolor`（论文复现，Python/JS 系） | ✅ 网格化后可完全确定 | ✔primary SIGGRAPH 论文 + GitHub |
| 水彩（实时/颜料混合） | *Digital Watercolor* 系（Chu/Tai 等） | `msurguy/watercolor-playground`（浏览器湿纸模型） | 部分（GPU 浮点需固定种子） | ○secondary |
| **线稿/素描提取** | **XDoG**（Winnemöller 2012，DoG 扩展，参数 σ/k/γ/ε/φ 控制风格） | `heitorrapela/xdog`；`skimage.filters.difference_of_gaussians` 已内置 | ✅ 纯滤波，确定性 | ✔primary 论文 PDF + GitHub |
| 铅笔素描 | 灰度 + 高斯反差模糊除法（经典 OpenCV 姿势） | OpenCV（**本机已装 cv2 5.0.0**） | ✅ | ✔primary 实测 |
| 油画/笔触 | *Computational Creation of Virtual Impressionist Oil Paintings*（Lu）、Paint by Sam（Hertzmann） | 多为论文代码/教学仓库（如 THU 计算图形作业仓库） | ✅ 网格+笔触可确定 | ○secondary |
| 半色调/网点 | Floyd–Steinberg / Bayer / 蓝噪声抖动 | SciPy + 自研（我们已在 image 路线用过三角抖动） | ✅ | ✔primary 实测 |

> 落地判断：**XDoG + OpenCV 素描 + Curtis 水彩** 三者都能在我们现有 image 路线里
> 以纯代码方式跑通，且都是确定性的——这是"风格化"最低成本的入门路径。

---

## 4. 当代插画风格族

| 风格 | 代码可复现要素 | 路线 | 来源 |
|---|---|---|---|
| **Risograph** | 有限专色（荧光粉/蓝等）+ 通道错位（misregistration）+ 网点 + 纸张底色 + 叠印乘色 | **完全可确定性**：分色→每色一层→层间像素级偏移→multiply 叠印 | ✔primary `adrawerofthings/p5.risoAtHome`（用 CMYK 假 4 色逐层印） + kott.io 效果说明 |
| **扁平矢量插画 / 编辑插画** | 有限色板 + 几何构成 + 无渐变或受限渐变 | SVG 生成（`svgwrite`/`drawsvg`）→ 光栅化；或 Pillow 直绘 | ○ |
| **厚涂 / digital painterly** | 大笔触 + 色彩混合 | 笔触 stamp 链（慢，需美术先验） | ⚠ 人工判断重，确定性弱 |
| **像素艺术** | 网格量化 + 有限调色板 + 手工抖动/抗锯齿 | 完全可程序化（我们已具备 palette 量化与抖动原语） | ✅ |
| **国潮 / 装饰插画** | 传统纹样（云纹/回纹/缠枝）参数化 + 现代配色 | 纹样=可枚举的对称基元（花边/二方连续/四方连续） | ○ |
| **手绘感图表** | Rough.js 式抖动线 + 手绘字体 | `roughjs`（Node，本机有 Node ✅）；`matplotlib.pyplot.xkcd()`；`roughViz`/`d3-rough-barchart`；**Python 侧可自研抖动线算法**（Rough 的算法本质是多次抖动折线 + 种子化） | ✔primary roughjs.com + Matplotlib 3.11.2 文档 |
| **素描风 UI** | Wired Elements（hand-drawn web components） | 仓库自 2021 起未见明显更新 | ○secondary，标 ⚠维护状态未核 |

---

## 5. 「真·手绘」通道：笔绘仪（Pen Plotter）

这是最被低估的一族：**代码输出 SVG，机器代笔画在真纸上**——输出物本身就是手绘质感，
且过程完全确定、可复现、可审计。

| 工具 | 定位 | 许可 | 来源 |
|---|---|---|---|
| **vsketch** (abey79) | Python 生成艺术环境，Processing 风格 API，专为笔绘仪设计，导出 SVG | MIT | ✔primary GitHub |
| **vpype** | SVG 后处理管线（分层/排序/优化路径），CLI 可编排 | MIT | ✔primary GitHub（与 vsketch 同作者生态） |
| **AxiDraw** + `axidraw` CLI | 硬件执行；Inkscape 可直接出图 | 硬件/驱动 | ○secondary lizmelchor.com 资源页 |
| aiSKETCH | Rust 侧笔绘生成工具 | 未核 | ⚠ unverified |

> 对本项目：即使**没有硬件**，`vsketch/vpype → SVG` 也是一条高质量的"手绘线稿"产出线，
> 且 SVG 是矢量资产（可再用于插画、图标、版画分版）。安装成本：`pip install vsketch vpype`。

---

## 6. 文字与字体（题款/落款/海报必需，且是许可雷区）

| 资源 | 内容 | 许可 | 来源 |
|---|---|---|---|
| **wordshub/free-font** | 最全「免费可商用中文字体」清单仓库（含逐条授权说明与需授权项提醒） | 仓库开源；字体各自许可 | ✔primary GitHub |
| **钟齐志莽行书 (Zhi Mang Xing)** | Google Fonts 中文行书书法体，适合题款 | **SIL OFL 1.1**（可商用） | ✔primary free-font 仓库引述 + Google Fonts |
| **演示夏行楷 / 思源（Source Han Serif/Sans）** | 行楷标题 / 正文宋黑 | OFL（思源为 Adobe+Google，OFL-1.1） | ✔primary OFL-1.1 条款说明 |
| 商用需授权提醒 | 部分"免费"字体商用仍需厂商授权（方正系典型） | 逐条核验 | ✔primary wordshub 授权页 |

> 规则：**渲染管线里出现的每一个字体文件都要在 manifest 记录其许可证与来源**，
> 这是 provenance 的自然扩展（当前 manifest 尚无 fonts 字段——待补）。

---

## 7. 影视级 3D 与日式 2D（工具栈详见 `docs/tools.md` §5 手绘/2D 动画、§6 影视级 3D、§7 日式 2D/2.5D）

一句话结论：
- **3D 影视线**：开源工业底座**已经齐备**——Blender 5.2 LTS（Cycles/EEVEE Next/Geometry Nodes/Grease Pencil/Freestyle）、
  Pixar **USD**、DreamWorks **MoonRay**（Apache-2.0，2026-05 进入 ASWF 托管）、RenderMan 非商用免费、
  Houdini 22（程序化 FX，Apprentice 免费非商用/Indie 受限商用）、**Blender Studio 开放影片含全套生产文件（CC）+ 17 个 CC0 人体基础网格**。
  天花板取决于**美术工时**，不是软件缺口。
- **日式 2D/2.5D**：3D 模型 + 赛璐璐描边 + Grease Pencil 手绘叠加是业界成熟做法
  （Blender Conference 2026 有"2.5D Illustration…""anime TV series pipeline and shading"议题）；
  工具侧 Rive 官方自我定位已是 **"agent-native 2D and 3D engine"**（对我们这类 agent 驱动管线是明确信号）。

---

## 8. 诚实边界：生成模型这一族

SD/LoRA/ControlNet-lineart/中文水墨 LoRA、"Ghibli 风生成器"这类路线**技术上最容易出效果**，
但按本项目铁律**不入渲染主路径**，理由要写清楚而不是回避：

1. **非确定性**：同 prompt 不同种子/不同后端不可复现 → 破坏 manifest/remake 契约。
2. **不可审计**：无法回答"这一笔从哪来"，与"引文即生命线"冲突。
3. **许可与判例风险**：训练数据与风格模仿的版权争议仍在进行（2025 年已有针对 Ghibli 式 AI 生成
   的公开学术讨论，techrxiv DOI 10.36227/techrxiv.174353158.87082654）。
4. 可用位置：**离线参考/前期探索**（生成 mood board），产出物若含 AI 素材必须在 manifest 显式标注；
   渲染主路径保持“代码作画”。

### 8.1 模型腿的实测账（2026-11-05，不是推想）

上述四条理由过去是**先验**的。本轮把它跑成了一次真实尝试，于是「不走模型」从一条立场裁决变成了一条
带数字的约束——并且发现之前的堵点不是模型本身：

**① 本机算力经实测不够**（逐条实测，不是估计）：

| 项 | 实测值 | 含义 |
|---|---|---|---|
| `Win32_VideoController` | 仅 **AMD Radeon(TM) Graphics，AdapterRAM 1 GB** | 无独显，只有 iGPU |
| `torch` | **`2.15.0+cpu`**，`cuda False`，`mps False` | CPU-only 构建 |
| `diffusers` / `transformers` / `accelerate` / `safetensors` / `controlnet_aux` / `comfy` | **全部未安装**（`importlib.util.find_spec` 逐个核过） | 无现成推理栈 |
| 内存 / C 盘空闲 | 30.8 GB / 141.7 GB | **空间够，算不够** |
| Ollama | 已装 | 自回归文本引擎，**不跑扩散图像模型** |

→ SDXL 在纯 CPU 上是每张十分钟量级，FLUX 是几十分钟且很可能直接 OOM。**在本机这不是慢路，是死路。**

**② 之前的堵点只是「托管服务额度」**：`ImageGen code = 112 Insufficient Credits` 是宿主内置额度，
与 RunComfy 账号是两回事；`runcomfy` CLI 从未安装、无 `RUNCOMFY_API_TOKEN`，那条路**至今没真正试过一次**。
开源权重可以绕开额度，但绕不开①。

**③ 开源格局（一手来源，2026-11-05 检索）**：单幅插画确实已到「手绘层面」——SDXL 系的
Illustrious-XL / NoobAI-XL / Animagine-XL 3.1（多为 CreativeML OpenRAIL++-M，可商用），FLUX 系的
Anima（Circlestone）/ Canopus-LoRA-Flux-Anime，和轻量的 PixArt-Σ 漫画微调（2000 万张漫画页）。
来路：[mage.space 2026 对比](https://www.mage.space/blog/best-ai-anime-art-generators-2026)·
[illustrious-xl.ai](https://illustrious-xl.ai/)·
[HF Canopus-LoRA-Flux-Anime](https://huggingface.co/prithivMLmods/Canopus-LoRA-Flux-Anime)·
[PixArt 漫画开源模型](https://www.reddit.com/r/StableDiffusion/comments/1jv6c6a/a_lightweight_opensource_model_for_generating/)。
（权重体积/显存需求为二手口径，**未回源核实，作 unverified 处理**。）

**④ 开源模型也解决不了「漫画原稿」那一层**：多格分镜、同一角色跳格不变脸、网点与版面编排。
存在专门论文（[arXiv:2412.19303 Manga generation via layout-controllable diffusion](https://arxiv.org/html/2412.19303v1)）
本身就是「未解」的证据，不是调参问题。**代码路 与 模型路 在同一处碰壁，只是碰的是同一块墙的不同面。**

**⑤ 最硬的一条：点名要的三位根本没有合法开源权重**。妖尾/夏目/宫崎骏的具体角色相关同人 LoRA 普遍被版权方投诉下架；
模型能模仿的是**文法**（大眼、睫毛楔形、飞檐、赛璐璐上色），不是那几个角色。与本项目定的
「原创角色 + 文法致敬」是同一条线。

### 8.2 代码腿带回来的两个工程成果（与模型无关，永久有效）

- **`_mul` 仿射转置 bug**：`_tp` 按列存 2×2 块（`x'=a·x+c·y+e`），`_mul` 却按行乘，返回转置。纯平移、纯旋转、
  旋转∘旋转、旋转∘均匀缩放——两种算法结果相同，所以它隐形；直到**旋转∘非均匀缩放**，
  而那是页面上每一个带 `tilt` 的部件。实测：`_mul(_R(90), _D(74,13))` 把局部 (1,0) 送到 (0,**13**) 而不是 (0,**74**)——
  一根 74 长、13 宽的锁鬏，横着长成了 74 宽、13 高的板。代价：**十三轮渲染**，期间我还在 spec 注释里
  写了**两条所谓“学到的规律”作为补偿**（「剪影边上的粗根会长成鱼鳍」、「90° 旋转下 sy 变成水平根」）——
  它们都是假的，已删并换成纠正后的推理。钉在 `tests/unit/test_manga.py`。
- **两种镜像不是一件事**：`mx` 反转部件的**长轴**（它朝哪边），`flip` 反转**跨它的轴**（它往哪卷）。
  用 `flip` 做眼睛，睫毛到了下眼睑，而因为瞳仁偏移的补偿读的是同一个 flag，**两只眼睛全部往鼻子偏——一张对眼脸**。
  根因是一个字母用错了位置，不是参数不够。

### 8.3 同一形状的另一个教训（独立于 §0.1 的五条）：被钉住的数字不是物理量

`test_ink_value_band_gate_catches_a_flattened_ramp` 本来断言“色阶拉平 ⇒ `palette_distinct_colors == 6`”。
山水重做后它变成 7 且不可逆，去测了为什么（`scripts/probes/ink_flatten_probe.py`）：**把五层全部压成同一个墨色、
再把 `features:` 整块删掉，ink2/3/4/5 仍然以 4.37% / 0.05% / 0.10% / 0.02% 存在**。色数从来不是“色阶拉平”的性质，
它只是旧的三层渲染器当时留在纸上的颜色个数；色阶拉平的真信号是 `value_bands_min_pct` 与 `painted_entropy`。
同一轮里，`darkest=inks[4]` 硬写焦墨（不随本层墨色）也已改成偏移量：对出厂的五层（ink 1..4）数值完全不变，
只让“拉平”真的拉得平。

> 与 §0.1 那几条是同一个形状：**把一个“刚好能算的出口值”钉住当作断言，于是这个值变了就等于作品坏了。**
> 钉数字可以，但必须写清它是由什么决定的、以及它为什么是成败的代理量——否则门禁会在作品变好时报红。

---

## 9. 采纳队列（风格族，需你逐项批准）

| 步骤 | 安装 | 解锁 | 风险 |
|---|---|---|---|
| S1 | **无**（Pillow+NumPy+SciPy+cv2 已装） | XDoG/素描提取、Curtis 水彩复现、水墨分层链、Riso 分色、像素量化 | 无 |
| S2 | `pip install vsketch vpype` | 笔绘仪线稿 / SVG 矢量资产 | 轻 |
| S3 | **无**（解释器 A 已实测 matplotlib **3.11.0**） | `xkcd()` 手绘图表 + 数据可视化。⚠ 实测：`xkcd()` **不报错但刷 `findfont: 'xkcd'/'Comic Neue' not found`** → 手绘字形不会出现，只有抖动线出现；要真效果需 Humor Sans/Comic Neue，**或按 §4 自写抖动线** | 无（但只在 3.13.5 里有；hy_py312 需补装） |
| S4 | **无**（系统字体已实测） | 题款、落款、中文海报：**本机已有 Noto Sans/Serif SC（OFL-1.1，可变 wght 100–900）**、Source Sans Pro（OFL）、KaiTi、STXingkai、Monoton；先前"待下载 OFL 字体"的登记已作废 | 无（OFL 可直接用；Microsoft/华文系逐条 EULA **未回源 ⚠**，见 `tools.md` §0.2） |
| S5 | `pip install scikit-image` | `difference_of_gaussians` 等 NPR 滤镜全家桶 | 轻 |
| S6 | Met Open Access API 拉取参考集 | 真实古画的构图/明度统计（CC0，可安全入管线） | 无 |
| S7 | Blender 5.2 LTS | 3D 镜头、Grease Pencil 2.5D、Freestyle 描边 | 重（外部安装，非 pip） |
| S8 | Houdini Apprentice / Indie | 程序化 FX（烟/火/破坏/群集） | 重 + 许可限制（水印/营收上限） |
| S9 | **无**（本机已有 Node ✅） | `@excalidraw/cli`（官方，手绘风图示，agent 写 JSON→PNG/SVG）——已登记 `docs/tools.md` §5 | 轻（npm 包） |
| S10 | **无** | 生成艺术基元族（§11）：分形/元胞自动机/反应扩散/Voronoi/镶嵌/流场——全是 NumPy+SciPy 能算的 | 无 |
| S11 | **无** | Op art/guilloche/1-bit 阶调/glitch（§12）+ 胶片仿真 LUT 与卤化银曲线（§13） | 无（datamosh 需钉 codec） |
| S12 | **无** | 世界图案系统（§14）：对称群+网格+分层套色直译；凯尔特结/kolam/girih 均有可复现算法 | 无（参考素材授权另查） |
| S13 | **无**（fonttools **4.63.0** 已在解释器 A） | 可变字体驱动的字体动画/子集化（与 `tools.md` §8 对应）；`vl-convert-python`（图表语法）仍需装 | 轻（**designspace 只处理自产**，CVE-2025-66034） |
| S14 | **无** | **版面风格族（§10）**：网格+色板+字阶+母题四元组写进 spec → 海报/deck/PDF（接 `tools.md` §0.2 浏览器路线） | 无（流派是方法，不涉作品版权） |

---

## 10. 平面设计史风格族 · Graphic-Design Movements as Parameter Sets

> **为何这一族单独成节**：它是 coverage-audit 轴 A5 上唯一还标着「需继续采样」的那格（亚文化/设计史）。
> 而它恰好是**最参数化的一族**：每个流派都可以拆成四元组 **色板 + 网格 + 字体对 + 母题**，
> 四个都能直接写进 `spec.yaml`，因此也是**验收最容易**的风格路线（对齐率、基线整除、色板大小、字阶比率）。
> 证据级别：✔primary=本轮到达一手页面/仓库，○secondary=艺术史通识或二手资料，采纳前须回源。

| 流派 | 形式内核（四元组） | 代码路线 | 可确定性 | 来源 |
|---|---|---|---|---|
| **瑞士国际主义 / Swiss Style**（Müller-Brockmann） | 不对称网格 + 基线节奏 + 无衬线字体 + 左对齐（ragged right）+ 客观摄影 | 模块场枚举 + 可执行模数比例 | **极高**（本就是数学） | ✔primary [`longplay45/swiss-grid-generator`](https://github.com/longplay45/swiss-grid-generator)（**MIT**，浏览器内运行，导出 PDF/SVG/IDML：画布比例 DIN/ANSI、Van de Graaf 边距、模数字段、基线单位）+ ✔primary `rampstackco/swiss-style-theme`（可执行 modular scale + baseline rhythm + 可见网格） |
| **包豪斯几何 / Bauhaus** | 圆方三角 + 红黄蓝黑白 + 小写无衬线 | 基本形枚举 + 限定色板（≤6 色） | 极高 | ○（艺术史通识；仓库实现需回源） |
| **风格派 / De Stijl**（Mondrian） | 正交直线分割 + 三原色 + 白底 | **递归分割算法**：矩形二分 + 随机赋色（可枚举所有版面） | 极高 | ○（通识；实现是 20 行代码） |
| **构成主义 / Constructivism** | 对角轴线 + 红黑 + 硬边几何 + 拼贴裁切 | 旋转矩形 + 对角网格 + 布尔裁切 | 高 | ○ |
| **新艺术 / Art Nouveau** | 鞭线曲线 + 植物母题 + 边框花饰 | Bézier 链 + 触须生长（与 §11 流场/L-system 汇流） | 中高 | ○ |
| **装饰艺术 / Art Deco** | 对称阶梯 + 扇形 + 放射线 + 金边条 | 对称群 + 分层套色（与 §14 girih/藻井同族，可共用基元） | 高 | ○ |
| **企业识别规范风 / Corporate grid** | 标志构造网格 + 净空区 + 字阶表 | 输出**构造网格图**本身即作品 | 极高 | ○ |
| **Memphis / 后现代 1980s** | 撞色 + 波浪线 + 几何贴花 + 假大理石纹 | 图案库枚举 + 故意错位（与 §4 Riso 错位共用机制） | 高 | ○ |
| **Y2K / Frutiger Aero** | 气泡光泽 + 蓝绿渐变 + 拟物图标 + 水与天空 | 径向渐变 + 高光遮罩 + 玻璃质感滤波（cv2 可做） | 高 | ○（术语起源归于 Nicolle Pavlova 2023，**未回源** ⚠） |
| **Vaporwave / 蒸汽波** | 粉青渐变 + Win95 元素 + 希腊雕塑 + 全角字 | 渐变+网格地平线+扫描线（与 §12 CRT 族汇流） | 高 | ○（同上，⚠ 起源需回源） |
| **粗野主义网页 / Brutalist web** | **默认 UA 样式 + 几乎不写 CSS** | 反风格：验收指标="CSS 字节数接近 0 + 语义标签齐备" | 极高 | ○（web 通识；作为可度量约束首次登记） |
| 像素/低比特、网点/半色调、手绘感、胶片感 | —— | **已各自成节**：§12（低比特/故障）、§3（半色调/XDoG）、§5（笔绘仪）、§13（胶片） | — | 交叉引用，不重复登记 |

**这一族的落地优势**（相对绘画族）：
1. **不需要“像”**：它靠的是**规则正确**（对齐、比例、色板受限、字体配对），因此验收可以写成硬规则；
2. **参考素材零版权风险**：流派是**方法**而不是作品，不需要拿某张海报当输入（而 §1/§14 的画法族必须引参考图）；
3. **与版面类媒体天然汇流**：`tools.md` §0.2 的浏览器路线 + 本节网格系统 = 文本→海报/PDF/deck，全零安装（仅解释器 A）。

> 诚实边界：上表的"形式内核"是**教科书层面的概括**，不是对各流派原始文献的逐条考据；
> 若产出物要声称"瑞士风格"，至少应回源到 Müller-Brockmann《Grid Systems in Graphic Design》一级文献，
> 并把色板/字阶的具体数值写进 spec 而不是口头描述。

---

## 11. 生成艺术数学基元 · Algorithmic Primitives

> 这一族不是「风格」而是**风格的下层词汇**：它们本就是算法，所以下入代码管线最天然。
> **全部零/轻安装、全部可定种**（轴 A3=几何/统计采样，轴 A6=最好验收）。

| 基元 | 可形式化要点 | 实现（已装优先） | 可当风格使用 |
|---|---|---|---|
| **分形**（Mandelbrot/Julia/IFS/fractal flame） | 迭代函数系 + 逃逸时间 + 配色域 | NumPy 直接算（向量化）；flame = IFS 概率选择 | 背景、纹理、封面美学 |
| **奇怪吸引子**（Lorenz/Henon/Clifford/De Jong） | 递推方程 + 轨道采样 + 密度渲染 | NumPy 迭代；轨道即线稿 | 科学美、细线云 |
| **元胞自动机**（Life/Rule 30/扩展 Neighbourhood） | 网格+局部规则+**时间轴自然产生** | NumPy 位运算（已验证的确定套路）；可接 mp4 | 纹理、有机花纹、生成动画 |
| **反应扩散**（Gray-Scott） | 双通道扩散+反应（珊瑚/指纹类形态） | SciPy 卷积/拉普拉斯核，固定步数=固定帧 | 贝壳纹理、水墨渗化近似（与 §1.2 第 5 步汇流） |
| **噪声与域扭曲**（value/Perlin/simplex + domain warp） | 多倍频叠加 + 坐标扭曲 | **已实现**（`media`/`image_sample` 的 fBm） | 一切背景的基础层 |
| **流场 / 粒子轨迹** | 噪声向量场 + 定步进积分 | NumPy；与游戏路线共用固定 timestep 思想 | 发丝、烟雾、水纹、花瓣轨迹 |
| **Voronoi / Delaunay** | 对偶剖分（**细胞=区域，可逐面填色**） | **SciPy `spatial` 已装**（直用） | 彩窗玻璃、细胞风、地图分区 |
| **镶嵌与周期/非周期铺砌** | Truchet（硬币两面拼接）、Wang tiles、**Penrose（胖/瘦菱形）** | NumPy + 对称群枚举 | 装饰纹样、伊斯兰几何的下层（§14） |
| **L-System / 植物生长** | 重写规则 + turtle 解释（与 kolam 同工具链） | Python 字符串重写 → 线段集 → SVG | 枯木、藤蔓、缠枝纹（青花） |
| **半色调/阶调** | Bayer/Floyd–Steinberg/蓝噪声 | **已实现三角抖动**（§3） | 印刷质感、网点漫画 |

> **关键洞察**：元胞自动机与反应扩散自带**时间轴**——它们能把“静帧风格”直接抬到“风格动画”，
> 而且不需要任何新工具：同一网格递推 N 步 = N 帧（我们的 image 路线只需把循环包上）。

## 12. 光学·低比特·故障美学 · Op Art, 1-bit & Glitch

| 风格 | 算法本质 | 确定性 | 来源/实现 |
|---|---|---|---|
| **Op art / moiré** | 两组周期图案叠加产生差频条纹（正弦栅 + 旋转/位移） | 完全确定（纯数学） | Vasarely 体系通识；NumPy 相位差直接算 |
| **变形投影画 anamorphosis** | 射影/柱面反变换（观看条件写进逆变换） | 确定（坐标变换可逆） | ○待回源具体算法仓库 |
| **Guilloché / 机刻雕花（钞票防伪）** | **内/外旋轮线（hypotrochoid/epitrochoid）+ Lissajous 叠加**，多层相位错开 | **完全确定且可笔绘输出** | ✔primary GeoPatternLab guilloche 工具、Ornamatic 站点、Horopedia 工艺说明 |
| **玫瑰窗 / 神圣几何** | 圆规直尺作图（相交圆 + 对称群）→ 构图图可完全枚举 | 确定 | ○（作图法为几何通识） |
| **1-bit / 早期计算机美学** | 阈值化 + **有序抖动矩阵**；限定调色板（CGA/EGA/Amiga/mac 1-bit） | 确定（我们已有 palette 基础） | ✔primary 已有实践（§3 半色调） |
| **ASCII / ANSI / Unicode 块艺术** | 亮度→字符映射（**已有 `entropy`/亮度工具链**）；ANSI = 色彩+字符网格 | 确定；输出面是终端/文本 | ○secondary（pypi 多个小库，许可不一，采前回源） |
| **Pixel sorting** | 按行/列用亮度阈值选范围后排序（Asendorf 式） | **完全确定**（纯数组操作） | ✔primary GlitchKernel（GitHub scriptkittie）、glitchology 算法说明 |
| **Databending** | 对文件字节做变换后强行重解（**依赖格式解码器行为**） | 条件确定（同文件+同解码器=同果） | ○secondary filescorrupter 说明：“每种技术复现一种特定的解码失败” |
| **Datamosh** | 丢 I 帧/只留运动矢量 → 拖影 | **依赖编码器→必须钉死 codec/版本参数** | ○（需专实测试，列入代谢） |
| **CRT / VHS 模拟** | 扫描线 + 色度二次采样 + 时序抖动 + 桶形畸变 | 确定（滤波器链） | ○secondary TouchDesigner 教程描述技术本身 |
| **demoscene 视觉语法** | 卷动字、铜条（copper bars）、等离子体（plasma）、15px 位图字 | 确定（plasma=正弦叠加；字库=网格） | ○；tracker 音频侧见 `docs/tools.md` §9 |

> 诚实提醒：**故障类是“美学靠失真”的族**，失真机制必须写成显式参数（阈值、交换字节区间、丢帧模式），
> 否则“不可复现性”会从风格问题变成契约问题。

## 13. 摄影与胶片质感族 · Photographic & Film Looks

这族的优点是：**成品就是像素操作**（LUT + 噪声 + 几何），我们已有全套地基；且**不需要模型**。

| 风格 | 形式化要点 | 本机可算？ | 来源 |
|---|---|---|---|
| **胶片正片仿真（print emulation）** | Kodak **2383** 类 LUT（参考片基密度曲线）+ 包围映射 | ✅（cv2 LUT + NumPy 插值） | ✔primary Juan Melara 公开 PFE LUT 包（行业事实上的免费源）、Lowepost 论坛文档 |
| **物理级胶片模拟** | **H&D（特性）曲线** + 卤化银颗粒统计 + **halation**（红光透过片基底回散） | ✅ 思路确定，实现工时中 | ✔primary silverhalide.pro（声明“由特性曲线/颗粒/halation 构建而非预设”）+ ○ComfyUI `film-emulation` topic（161 stocks，含真 Capture One 曲线数据） |
| **gate weave（门框摆动）/ flicker（闪烁）** | 低频随机位移 + 亮度调制（固定种子） | ✅ | ○secondary（Juan Melara 描述含 halation/grain/gate weave） |
| **蓝晒 cyanotype / 铁银 / 银版 / 物影 photogram** | 单色色调曲线 + 高对比边缘 + 接触印相的“无镜头”几何（投影=直接 mask） | ✅ | ○（工艺通识；物影止于“相机无关”，代码里就是 alpha 投印） |
| **长曝 / 光绘** | 时间轴亮度叠加（可用我们帧序列代替） | ✅（需素材或模拟光源轨迹） | ○ |
| **Dehancer / 商业插件级** | 同物理思路 | ❌ 商业，条款未回源 | ⚠unverified，不入产出链 |

> 本项目定位：**不假装有胶片，而是把胶片的可测属性（曲线、颗粒、halation）写成代码约束**。
> 验收可新增：特性曲线拟合误差、颗粒度 PSD（功率谱）、halation 红边强度。

## 14. 世界传统图案系统 · Rule-Based Ornament Traditions

> 与 §1.1 同构的发现：**传统图案系统几乎都是「网格 + 对称群 + 分层套色」**，
> 因而可形式化程度极高。下表只登记**可程序化的那部分**，不主张能替代工艺本身。

| 传统 | 可形式化的内核 | 可落地技术 | 授权/资料注意 | 来源 |
|---|---|---|---|---|
| **中国·界画**（直尺建筑画） | 线段=轴测投影下的建筑构件；**界尺=直线约束** | 与 §16 轴测图共用几何（可直接接 SVG/线稿） | 参考图多为公有领域画作 | ○（画论通识，待专题回源） |
| **中国·年画**（杨柳青/桃花坞） | **线版 + 多张分色版套印**（与浮世绘饾版同族！） | 分层 DAG（§1.2/§2 已有模型）；线版=XDoG轮廓 | 现代重印本版权属出版社 | ○secondary |
| **中国·敦煌藻井/团花** | 同心分层 + 旋转对称（4/8/12 重）+ 莲瓣/云纹基元 | 极坐标对称铺砌（基元=可枚举曲线） | **数字敦煌（e-dunhuang）素材授权未明**；《敦煌纹样数字化——以“三兔共耳”为例》论文可参 | ✔primary dha.ac.cn/e-dunhuang 页面存在，授权条款待核 |
| **中国·唐卡 iconometry** | **度量网格**：`cha chung`（小度量单位）/`cha chen`（大度量单位）、`tik-khang` 起线格；坐佛有固定比例 | 网格生成 + 镜像对称 + 锚点约束（最可验证的一族） | 图像本体多为宗教资产，慎用 | ✔primary himalayanart.org Iconometry 词条 + digitalthangka Grids 101 + 《npj Heritage Science》2026 佛面点云研究 |
| **中国·剪纸/皮影** | **对称群（折纸=反射/旋转群）+ 可剪连性（拓扑约束）** | 镜像/轮转布尔运演 + 最小桥宽约束 | 干净 | ○ |
| **中国·拓片/锦灰堆/博古图** | 拓片=凹凸光照反演+噪声；锦灰堆=多源碎片拓片拼贴（**可枚举的 collage DAG**） | 高度图→光照（已有）+ 随机布局 | 干净 | ○ |
| **伊斯兰 girih** | **多边形网格 + 5 种 girih 砖 + 星形/多边形基元**；学术建模成熟 | 镶嵌→叠加切线→双向线交织 | 无版权障碍（几何） | ✔primary `nature.com/articles/s40494-022-00852-w`（综述）、`TheBeachLab/islamic-geometry`、Bridges 2025 PDF |
| **印度 kolam/rangoli** | **点阵 + 连续环（一笔画约束）**、turtle 程序生成 | Python turtle/线段生成；数学框架已有论文 | 民间传统，无个体版权 | ✔primary arXiv 2507.02874（Hridaya kolam 拓展）、algorithmicpattern 2025 论文 |
| **凯尔特结** | **Bain 法：网格上画“断点”，自动上下交织** | 已有 JS/Python 实现可参考 | 干净 | ✔primary `evoluteur/celtic-knot-maker`、CelticGraph arXiv 2309.02852 |
| **西非 kente / adinkra** | 条带拼接=**周期性列向量**；adinkra=符号集（可枚举） | 矩阵图案 + 有限色板 | 文化符号使用语境需谨慎（标注来源与脉络） | ○secondary |
| **拉美 papel picado** | 镂空=**二值 mask**（可展开成对称群） | 与剪纸同族 | 干净 | ○ |
| **澳洲原住民点画** | 点阵+密度映射（需尊重文化语境与地域限制） | 程序化 stippling；可参照 §11 流场 | **文化敏感：不得仿作圣地图** | ○secondary |
| **欧洲手抄本装饰 / 丢勒式版画排线** | 叶状边饰=周期函数；铜刻排线=**沿法线的密度场** | 已有笔触基元库可接 | 公有领域作品为主 | ○ |

> **日本小纹/型染、织锦纹样、唐草**与 §2 饾版同属“纹样=可枚举基元 + 二方/四方连续”，
> 直接归入本节实现集合（二方连续=沿 x 平移群；四方连续=二维平移群）。

## 15. 动画表演与时序风格 · Timing as Style

> 之前所有族都在回答“**画面长什么样**”，本节回答“**动作长什么样**”——风格不只是色彩与笔触，
> 还是**时间函数**。幸而 12 原则几乎都能写成曲线与约束。

| 原则（Disney 12） | 可形式化为 | 落到我们管线 |
|---|---|---|
| Squash & Stretch | **体积守恒的异步缩放**（sx·sy ≈ 1）+ 速度方向对齐 | 已有帧函数，只需改变换矩阵 |
| Anticipation / Follow-through | 主运动前的反向位移 + 事后过冲阻尼（二阶弹簧） | 缓动函数参数化 |
| Timing / Spacing | **帧数=快慢；缓动曲线=性格**（线性=机械，ease=有机） | 时间重映射函数（纯代码，确定） |
| Arcs | 轨迹走贝塞尔/抛物而非直线 | 控制点生成 |
| Secondary action | 副通道驱动（延迟+低通） | 多通道状态机 |
| **On-ones / On-twos** | **时间量化**（每帧刷新 vs 隔帧） | `sample(t // q)`——与我们的“帧序列”天然同构 |
| Straight-ahead vs Pose-to-pose | 递推生成 vs 关键帧插值（=我们的 spec 插值） | 两种渲染器变体 |
| Exaggeration / Appeal | 幅度因子与形态先验（参数，不是玄学） | spec 里的风格旋钮 |

| 流派（时序风格） | 特征参数 | 可达性 |
|---|---|---|
| **Full animation**（Disney） | on-ones + 完整中间帧 + 高形变 | ⚠ 作画工时（见 `tools.md` §5 诚实判断） |
| **Limited animation**（Hanna-Barbera/手冢治虫） | **on-threes + 局部动（嘴/眼）+ 循环口型 + 固定背景** | **高**：它本质是“省帧策略”，最可程序化 |
| **Rubber hose**（1930s） | 四肢无关节、圆端、同步摆动 | 高（正弦驱动链） |
| **Sakuga 冲击帧** | 抖动位移、拉伸、**白闪/黑帧**、速度线 | 高（纯时序特效） |
| **Kinetic typography / motion graphics** | 文字属性（位置/缩放/透明度）的时间函数 + 缓动曲线 | 高（ASS `\t` 已能直接表达！`tools.md` §8） |
| **定格/黏土感** | 每帧小量随机偏移 + 质感噪点（固定种子） | 中高 |
| **spring 物理 UI** | 临界阻尼弹簧参数（质量/刚度/阻尼） | 高 |

> 结论：**“风格=时间函数”这一层我们几乎零成本就能做**（只需把缓动写进帧函数），
> 而它恰好是“看起来专业”与“看起来像机器”的主要分界。

## 16. 工程、建筑、复古 3D 与序贯版面

| 风格族 | 规则内核 | 可程序化程度 | 来源/实现 |
|---|---|---|---|
| **轴测 / 等距（2:1 dimetric）** | 固定投影矩阵 + **画家算法按深度排序** + 三面 shade | **极高**（纯几何） | ○（iso 通识）；与游戏美术汇流 |
| **专利图（patent drawings）** | USPTO/EPO **线宽与剖面线规则 + 附图标记 + 黑白线稿** | **极高**：规则强、无色彩、可验证 | ○secondary（PatViz 商业工具存在⇒需求真实；本路线可用 §16 轴测+线稿自行实现） |
| **Blueprint / CAD 线重** | 白线深蓝底 + 线型（虚线/点划线）+ 标题栏 | 高 | ○ |
| **低多边形 / 白模 / 黏土渲染** | 平面着色 + 无纹理 + AO | 高（需 Blender 或自写光栅） | ○ |
| **Voxel / 体素** | 网格体 + 三面 shade；`.vox` 格式有开源解析 | 高 | ✔primary MagicaVoxel（免费，许可口径待核 ⚠）+ `tommyettinger/IsoVoxel`/SpotVox（.vox→等距像素图） |
| **像素艺术细分族** | pixel-kerning、pre-rendered iso（街机风）、色板限制 | 高（已有 palette/抖动） | ○ |
| **PS1 复古美学** | **顶点整屏坐标吸附 + affine 纹理映射（不做透视校正）+ 低内部分辨率** | **高**：三个可写代码的退化规则 | ✔primary pixelwolf 2026-08 文章（GLSL 复现）、threejs/Unity 社区实现、`ps1-graphics-rust` |
| **漫画/序贯页面** | 页面网格（分格布局）+ 气泡+尾巴几何 + 网点（screentone） | 中高（布局可枚举；内容需人） | ✔primary ACM 3440053（自动分格/气泡布局研究）、RecipeComics（CEUR 2026 多代理）、Laubrock《Computational Approaches to Comics Analysis》 |
| **分镜 / animatic** | 板+时长+临时配音 = 我们的 **timeline DAG** | 高 | 本仓库结构自然支持（roadmap §2.3） |
| **信息图 / 数据新闻** | 图表语法 + 版式网格 + 层级文字 | 高 | `tools.md` §8（Vega-Lite/D2/pandoc） |

> 本族的共同点：**它们不靠“画得像”，靠“规则正确”**——所以最适合由代码交付，
> 也最容易被验收（线宽、标号完整性、色板大小、像素网格对齐）。

---

## 17. 代谢 · 本轮未核与待办

- ⚠ **未核（§1–§9）**：故宫名画记授权条款；Toon Boom/TVPaint 当前版本号；`roughjs` 精确版本与维护状态；
  `shader-to-ruby`（本轮检索未直接命中仓库，勿引用）；Wired Elements 活跃度；aiSKETCH 许可。
- ⚠ **未核（§10 平面设计史族，本轮新增）**：Frutiger Aero 术语起源（归于 Nicolle Pavlova 2023）与 vaporwave 起源叙事均未回源；
  各流派的具体色值/字阶数值未从原始文献采数（上表只给形式内核）；`swiss-style-theme`/`swiss-grid-generator` 除 MIT 外无其他约束（已读 README，但未逐文件核 LICENSE 依赖）。
- ⚠ **未核（§11–§16，穷尽性审计本轮新增）**：anamorphosis 算法仓库；guilloche 开源实现（现仅有在线工具）；
  2383 LUT 包的具体授权与下载页；`film-emulation` ComfyUI 仓库（含 ML 属性，待判）；MagicaVoxel 正式 LICENSE；
  IsoVoxel/SpotVox 许可；celtic-knot-maker 与 islamic-geometry 仓库可得性；kolam/girih 论文附带代码；
  ACM 3440053 漫画生成系统的代码可用性；数字敦煌/敦煌纹样论文素材授权；PatViz 等专利图工具的条款（仅作为需求存在证据引用）。
- ⚠ **文化敏感项**（需显式规则而非默认）：澳洲原住民点画、宗教图像（唐卡/藻井）、民族符号（adinkra）——
  产出前需先定“不仿作”的硬约束，并在 manifest 记来源脉络。
- ❌ **纠正记忆**：`Zoo Tools`（ZigZag/Bolt/Matter）是 **Create3DCharacters 的商业套件**，
  我没有找到"Weta 开源 Zoo Tools"的一手证据——不写入采纳队列。Weta 的开放贡献以 **OpenEXR**（ASWF）为凭。
- 待补：manifest 增加 `fonts`（许可证+来源+哈希）与 `style_refs`（参考作品 ID + 授权）字段；
  新增风格路线时同时登记 `docs/coverage-audit.md` 判定行。
- 待办（候选，零安装优先）：① §1.2 山水分层链 → `ink-landscape` 样例；② §11 元胞自动机/反应扩散 → **风格动画**
  （把 image 路线的循环包上就是帧序列）；③ §12 guilloche/pixel sorting；④ §15 缓动与 on-twos 写进现有帧函数；
  ⑤ §14 图案系统（二方连续/对称群）。全部**等你选一个再开工**（人不发话，机器不自定方向）。
- 交叉引用已建立：本文回答"画法能否形式化"；工具事实（版本/许可/headless）只认 `docs/tools.md`
  （§5–§7 手绘 2D/影视 3D/日式 2.5D；§8–§10 图表版面与出版/捕获与实时/实物输出；**§0.2 本机第二轮实测：浏览器版面器、可变字体、系统字体清单**）。
- ⚠ **本轮重要纠正（影响所有"零安装"说法）**：本机有**两个 Python**——项目声明环境 conda `hy_py312`（3.12.13，也是全部 golden manifest 的产出环境）里
  **没有** matplotlib / fonttools / playwright；PATH 默认的 `C:\Python313`（3.13.5）里才有。凡本节标注"零安装"的风格路线，
  **开工前必须先用 `scripts/doctor.py` 在目标解释器里复核**（本文件早前版本把 S3/S4/S13 记成了"需安装"，已按实测改判）。
