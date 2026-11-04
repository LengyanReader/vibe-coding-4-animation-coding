# 穷尽性审计 · Coverage Audit（媒体类型 × 风格谱系）

> 回答的问题：**「所有内容 / 媒体类型 / 风格都穷尽了吗？」**
> 诚实前提：**穷尽性不可证明**。能给的是：①可重复执行的分类轴 ②逐格判定 ③已知残余缺口。
> 审计日期：2026-11-04（**同日两轮**：第一轮向互联网要清单，第二轮按 §5 第 0 步先审计本机）·
> 依据：README §3 矩阵（14 模态）、`docs/tools.md` §0–§14、`docs/styles.md` §0–§17、
> `src/vcac/` 实测已跑通的 5 条路线 + 6 份 golden manifest。
> **[2026-11-05 注]** 本节计数已过时：现 8 条路线、7 份 golden、91 项测试——本文其余部分作为
> 2026-11-04 快照保留（按 §5 规则 5），现状以 `docs/audit-2026-11-05.md` 为准。✔primary=本轮到达一手页面或**本机实跑出结果**，
> ○secondary=二手，⚠unverified=未回源。

---

## 0. 结论先行

**没有穷尽。** 本轮之前两张地图的偏向是：工具侧偏「影像与游戏」，风格侧偏「绘画」——
两侧都漏了**符号驱动版面类**（图/表/地图/版式/印刷）、**捕获与实时现场类**、**实物输出类**，
以及风格侧的**数学/生成艺术基元、低比特与故障美学、摄影胶片族、世界传统图案系统、动画表演时序族、工程与复古 3D 族**。
**本轮（第二轮）又补了两块：风格侧的「平面设计史流派族」（styles.md §10，A5 轴上最后一格待采样的），与工具侧始终未做的「本机能力全面盘点」。**

本轮判定汇总（详见 §2、§3）：

| 类别 | 本轮前 | 现登记处 | 剩余真缺口 |
|---|---|---|---|
| 媒体类型 | 14 类里 5 类跑通、9 类只登记 | tools.md §1–§10（新增 §8/§9/§10 三节） | 现场表演、多通道在场（见 §4） |
| 风格谱系 | 绘画族为主（水墨/水彩/版画/Riso/插画） | styles.md §1–§16（新增 §11–§16 六节 + **本轮 §10 平面设计史族**） | 亚文化/微风格长尾（按季度采样，不承诺穷尽） |
| 许可风险 | 已列 WikiArt/SMPL-X/Live2D 等 | 本文件 §6（新增 fonttools CVE、MagicaVoxel、Postshot、 trackers 商业档） | **Microsoft/华文系字体逐条 EULA**（本轮新列） |
| **本机隐藏能力** | ❌ **未查过** | tools.md **§0.1（ffmpeg 编译面）+ §0.2（pip/字体/浏览器面）** | 无——但得靠实测而不是猜；**且必须逐解释器实测** |
| **项目环境一致性** | ❌ **本轮才发现** | tools.md §0 第①②⑥条 + §14 | 需你先定一个解释器（见 §4 第 8 项） |

> **审计方法上的两次教训（同一个错误的两次发作）**：审计不能只向互联网提问，**先审计本机**。
> 第一轮回查 `ffmpeg -version` 的 configuration 行后，发现相于“需安装”的一批能力**今天就可用**：
> `libass`（字幕/动态字体）、`libopenmpt`+`libmodplug`（tracker 音乐→WAV）、
> `showwaves/showspectrum/showfreqs/avectorscope`（**声→图/声→视**）、`libvmaf`（**感知质量验收**）、
> `zscale/libplacebo`（色彩/HDR）、`deband/hqdn3d/nlmeans/tmix/tblend/rubberband`（质感与修复）、
> `gif/apng/libwebp/libjxl/qtrle/ffv1`（**动图与无损归档交付**）、`tty`（电传打印）、`iamf`（沉浸音频格式）、
> `libmysofa`（SOFA HRTF 双耳）、`chromaprint`（音频指纹→溯源）——详见 `docs/tools.md` §0.1。
>
> **第二轮（本轮）把同一把尺量到 pip / 字体 / 浏览器上，又抓出四项漏登 + 一项重大不一致**（详见 `docs/tools.md` §0.2）：
> ① **playwright 1.58.0 + 已下载 Chromium（实测 `browser.version=145.0.7632.6`，已实跑出 PNG）**
> → 网页/HTML-CSS/Canvas/WebGL 作为渲染与排版介质今天就可用（第 6 条零安装路线）；
> ② **fonttools 4.63.0 + `NotoSansSC-VF`（实测 `wght 100–900`）** → 可变字体驱动的文字动画零安装；
> ③ **系统字体 353 族已含 OFL 中文（Noto Sans/Serif SC）与手写体** → 题款/中文海报不必先下载（推翻了 styles.md 旧 S4）；
> ④ **matplotlib 3.11.0 已装**，但实测 `xkcd()` **因缺 Humor Sans/Comic Neue 而退化**（只刷 72 次 findfont 警告不报错）
> → “工具在 = 风格在”是错的，**风格还需要素材（字体）支撑**；
> ⑤ ❗ **重大不一致（本轮之前不知道）**：本机有**两个 Python**——项目声明环境 conda `hy_py312`（3.12.13，
> 也是**全部 6 份 golden manifest 的产出环境**）里**没有** matplotlib/fonttools/playwright；PATH 默认的 `C:\Python313`（3.13.5）里才有。
> 所以“零安装”必须先回答“在哪个解释器”；`vcac` 包本身也**从未 editable 安装**（测试靠 `pythonpath=["src"]`）。
> 已把 `scripts/doctor.py` 改为**输出 `sys.executable`+`sys.prefix`**，并新增 playwright/浏览器目录、字体与排版类包、
> Chrome/Edge 非 PATH 路径、**PATH 阴影清单**（`convert` 其实是 System32 磁盘工具而非 ImageMagick）探测。

---

## 1. 审计轴（这是可重复执行的检查程序，不是一次性结论）

任何"新内容/新风格"要能被判定为「已覆盖 / 缺口 / 政策排除」，必须落在六条轴上：

| 轴 | 取值 | 判定含义 |
|---|---|---|
| **A1 时间性** | 静态 / 线性时序 / 交互 / 实时 / 生成中 / **一次物理在场** | 前三类我们已有契约；**实时/现场**需要新的时钟与验收；**一次在场**不可复现 → 天然在确定性契约之外 |
| **A2 维度与通道** | 1D 文本 / 2D / 2.5D / 3D / 4D 时空 / 体积场 / **多通道（声像·触·味·嗅）** | 声像（Ambisonics）可代码化；触觉以下**不能由代码交付**（§4） |
| **A3 生成机制** | 符号规则 / 几何 / 物理模拟 / 统计采样(可定种) / 捕获重建 / **生成模型** | 前四种都在本项目射程；捕获重建需列"输入即资产"；生成模型=🚫政策排除 |
| **A4 输出面** | 屏幕像素 / 纸张印张 / 实物 / 扬声器 / 佩戴设备 / 网页运行时 / **矢量与文本源** | 印刷/实物/矢量的验收完全不同（DPI、出血、ΔE00、G-code 可打印性） |
| **A5 文化-历史谱系** | 传统画法 / 工艺美术 / 现代流派 / 亚文化 / 数字原生 | 每一格都可展开成族；本轮补的是「规则驱动」的那批（§3） |
| **A6 可验收性** | 能否写成 spec + 度量？ | **只有能验收的才算一条路线**，否则只是灵感板 |

状态图例：✅ 已跑通（有 golden hash）｜📝 已登记未跑｜⚠ 待核（版本/许可未回源）｜🚫 政策排除｜❌ 真缺口

---

## 2. 媒体类型矩阵（A1–A4 × 现状）

| 媒体类型 | 本轮前状态 | 现登记处 | 判定 |
|---|---|---|---|
| 静帧图像（位图） | ✅ image 路线 | tools.md §1 / styles.md §1–§4 | ✅ |
| 音频（合成/母带） | ✅ audio 路线 | tools.md §3 | ✅ |
| 视频（装配/探针） | ✅ video + film 路线 | tools.md §4 | ✅ |
| 游戏（无头仿真） | ✅ game 路线 | tools.md §11 | ✅ |
| 符号音乐 / 乐谱排版 | 📝 music21/LilyPond 已核 | tools.md §3 | 📝 **MuseScore 4 CLI 本轮补登**（`-o` 转 PDF/MP3，GPL） |
| 三维静帧/镜头 | 📝 Blender 5.2 LTS 已核 | tools.md §2、§6 | 📝 |
| 2D 手绘质感动画 | 📝 本轮上轮补登 | tools.md §5 / styles.md §15 | 📝 |
| 影视级 3D / 日式 2.5D | 📝 本轮上轮补登 | tools.md §6、§7 | 📝 |
| 互动叙事（视觉小说） | 📝 Ren'Py/Ink/Twine | tools.md §11 | 📝 |
| **图示 DSL（diagram-as-code）** | ❌ **缺** | tools.md §8 | 本轮补：Mermaid CLI、**D2（MPL-2.0，自动布局 TALA 2026-09-07 开源）**、PlantUML、Graphviz（§1 已有） |
| **统计图表语法（Vega-Lite/Altair）** | ❌ **缺**（只登了 matplotlib） | tools.md §8 | 本轮补：**vl-convert-python 0.6.0（免依赖、无浏览器，BSD）** |
| **幻灯片/讲义（文本→deck→PDF/PPTX/PNG）** | ❌ **缺** | tools.md §8 | 本轮补：Marp CLI、Slidev、reveal.js（依赖 Chromium → 复现性要钉版本） |
| **书籍/学术排版（代码→PDF）** | ❌ **缺——且本机已具备** | tools.md §8 | **pandoc 3.8.2 + MiKTeX 实测已装**，这是零安装即可开通的第 6 条路线 |
| **地图与地理媒体** | ❌ **缺** | tools.md §8 | `qgis_process`（官方 headless CLI，GPL-2）、GeoPandas/cartopy、MapLibre（离线渲染） |
| **字体工程 / 可变字体 / 动态字体** | ❌ **缺** | tools.md §8、styles.md §6 | fonttools `varLib`（⚠ CVE-2025-66034：恶意 `.designspace` 任意文件写 → 必须沙箱） |
| **字幕/卡拉OK 排版（ASS）** | ❌ **缺**（只在 video 提过 burn-in） | tools.md §8、§0.1 | **改判 ✅ 本机已具备**（实测 `ass`/`subtitles` 滤镜存在、`--enable-libass` 已编译）→ 零安装路线；ASS 是完整的样式/特效语言（`\pos`、`\t`、`\clip`、`\k`） |
| **声→图 / 声→视（视听合成）** | ❌ **连登记都没有** | tools.md §0.1 | **本轮新发现，且零安装**：`showwaves(pic)`/`showspectrum(pic)`/`showfreqs`/`avectorscope`；频谱艺术/封面/节拍可视化 |
| **质量度量作为验收（VMAF）** | ❌ 未登记 | tools.md §0.1 | **零安装**：`libvmaf` → 可升级为 validate.py 的感知质量规则（比 pHash/SSIM 更接近人眼） |
| **动图与无损交付格式** | ❌ 未登记 | tools.md §0.1、§4 | **零安装**：`gif`/`apng`/`libwebp(_anim)`/`libjxl(_anim)`/`qtrle`/`ffv1`（归档母版） |
| **双耳/空间音频（SOFA）** | ❌ **缺** | tools.md §0.1、§9 | 本机已含 `libmysofa`（HRTF 读取）；完整渲染仍建议 numpy 自算（可定种） |
| **印前与印刷品（PDF/X、分色、拼版）** | ❌ **缺** | tools.md §8、§10 | Ghostscript（AGPL/商业双授权）、press-ready、ICC 色彩管理、出血/分辨率/墨量验收 |
| **捕获重建（摄影测量 / SfM / MVS）** | ❌ **缺** | tools.md §9 | **COLMAP（BSD-3，CLI）**、OpenMVG、Meshroom/AliceVision（MPL-2.0） |
| **高斯泼溅 / 神经渲染** | ❌ **缺** | tools.md §9 | gsplat（nerfstudio，CUDA）、SuperSplat 3.0（PlayCanvas，2026-09）；⚠ README §3 把"神经渲染"列为**排除项**——须先由你裁决是否解禁 |
| **全景 / 360 / 立体 / WebXR** | ❌ **缺** | tools.md §9 | **Hugin 官方"非 GUI 拼接脚本"文档**（enblend/enfuse，GPL）→ headless 全景是成熟路径 |
| **着色器艺术 / 实时 AV / demoscene** | ⚠ 只提过 GLSL 一句 | tools.md §9、§0.1、styles.md §12 | glsl-to-mp4（离线出片）、Shadertoy（许可=单件作品）、tracker 音乐（**本机已含 libopenmpt/libmodplug，零安装**；Renoise 商业）；plasma/卷动字可纯 numpy 算 |
| **现场编码（live coding）视听** | ❌ **缺** | tools.md §9 | Hydra（JS 视觉）、TidalCycles、Sonic Pi；A1=实时 → 验收要换"脚本+固定时钟"而非位级复现 |
| **空间音频（Ambisonics/双耳）** | ❌ **缺** | tools.md §9 | pyroomacoustics（MIT）、shroom（arXiv 2026）；这是**可代码化的听觉维度**，不是模型 |
| **数据可听化（sonification）** | ❌ **缺** | tools.md §9 | MIDITime 等；与图表路线同构，输出通道换成时间轴 |
| **笔绘仪 / SVG 矢量资产** | 📝 上轮 styles.md §5 | styles.md §5 | 📝 `pip install vsketch vpype` |
| **3D 打印 / 激光 / CNC（实物 G-code）** | ❌ **缺** | tools.md §10 | PrusaSlicer（AGPL-3，CLI 无头切片）、LaserGRBL（免费开源/Win）、LightBurn（商业 $60/$120） |
| **织物/十字绣/提花图样（矩阵即图案）** | ❌ **缺** | tools.md §10、styles.md §14 | CrossStitchApp（DMC 色板映射）、十字绣→提花转换教程（arahne.si）——**Jacquard 卡就是二值矩阵**，与代码同构 |
| 漫画/序贯版面 | ❌ **缺** | styles.md §16 | 学术：ACM 3440053 全自动漫画生成、RecipeComics（CEUR 2026）；版面=网格+气泡，规则强 |
| 分镜/动态样片（animatic） | ❌ **缺** | styles.md §15、roadmap | 板+临时配音+时间标记 → 是我们的 timeline DAG 的自然扩展 |
| **网页 / HTML·CSS·SVG·Canvas 作为渲染与排版介质** | ❌ **本轮前完全未当作媒体类型考虑**（只在 §8 当作 Marp/Mermaid 的依赖） | tools.md §0.2、§8 | **改判 ✅ 本机已具备**：playwright 1.58.0 + chromium-1208/1234，实跑 `chromium.launch()→screenshot()` 得到 PNG（`browser.version=145.0.7632.6`）；`page.pdf()` 可出版面；Chrome 145 / Edge 156 亦可 `--headless --print-to-pdf`。这是**零安装的第 6 条路线**（仅在解释器 A） |
| **可变字体 / 动态字体（字重轴随时轴变化）** | ❌ 本轮前只登记了“字体许可”问题 | tools.md §0.2、§8、styles.md §6 | **改判 ✅ 本机已具备**：fonttools 4.63.0 + `NotoSansSC-VF`（实测 `fvar.axes=[('wght',100.0,900.0)]`）；与 ASS 的 `\t` 动画汇流 |
| **PDF / 长文档作为成品（书/讲义/学术海报）** | ⚠ 只在“印前”里提过 | tools.md §8 | ✅ 本机已具备（pandoc 3.8.2.1 + MiKTeX `latex/pdflatex/xelatex/lualatex/latexmk` 全部实测在 PATH）；另有 pypdf 6.19.0 / nbconvert 7.17.1 可后处理 |

---

## 3. 风格谱系补集（A5 × 可形式化程度）

本轮新增七族（正文见 `docs/styles.md` §10–§16），此处只给判定摘要（§10 为**本轮（第二轮）新增**，其余为第一轮）：

| 新族 | 代表 | 可确定性 | 装机成本 | 判定 |
|---|---|---|---|---|
| **§10 平面设计史流派（参数集族）** | 瑞士国际主义（网格/基线节奏/模数，**`swiss-grid-generator` MIT** 已回源）、包豪斯几何原色、De Stijl 递归分割、构成主义对角线、Art Nouveau 鞭线、Art Deco 对称阶梯、企业识别构造网格、Memphis 撞色、Y2K/Frutiger Aero、Vaporwave、**粗野主义网页（“不写 CSS”作为可度量约束）** | **最高**：它们就是**色板+网格+字体对+母题**四元组，可直接写进 spec | **零**（接浏览器版面器） | **本轮补上 A5 轴最后待采样的一格**；流派是方法不是作品 → **无参考图版权风险**；术语起源与具体色值均标 ⚠ |
| **§11 生成艺术数学基元** | 分形(Julia/IFS/flame)、奇怪吸引子、元胞自动机(Life/Rule30)、反应扩散、流场、Voronoi/Delaunay、镶嵌(Truchet/Wang/Penrose)、L-system | **极高**（本就是算法） | 零/轻 | A6 最优，优先级最高 |
| **§12 光学·低比特·故障美学** | Op art/moiré、变形字画(anamorphosis)、**guilloche 玫瑰线/钞票雕版**、1-bit/MacPaint/CGA 阶调抖动、pixel sorting / databending / datamosh、ASCII/ANSI、CRT-VHS 模拟、demoscene 卷动字 | 高（datamosh 依赖编码器 → 须钉 codec） | 零 | 已登记；datamosh 标 ⚠ |
| **§13 摄影与胶片质感** | 2383 正片仿真 LUT、H&D 特性曲线物理模拟、halation/grain/gate weave、蓝晒/银版/铁盐/物影、长曝与光绘 | 高（LUT+噪声+晕影=纯滤波，确定） | 零(已装 cv2/numpy) | 已登记；实物级 Dehancer=商业 ⚠ |
| **§14 世界传统图案系统** | 中国：**界画**（直尺建筑画）、**年画**（线版+分色版=多版套印，与浮世绘同构）、**敦煌藻井/团花**（数字敦煌资源）、**唐卡 iconometry**（cha chung/cha chen 度量网格）、剪纸（对称布尔）、博古图、锦灰堆、拓片、青花缠枝；伊斯兰 **girih**（论文与 workshop 齐备）；印度 **kolam/rangoli**（点阵连续环、turtle 生成）；**凯尔特结**（Bain 法）；非洲 kente/adinkra；papel picado（孔洞=mask）；原住民点画 | **高**（网格+对称群+分层套色，正是代码长项） | 零/轻 | 已登记；故宫名画记/数字敦煌授权仍 ⚠ |
| **§15 动画表演与时序风格** | **12 原则可形式化**（squash&stretch=体积守恒缩放、anticipation/follow-through=阻尼、arcs=贝塞尔、timing/spacing=缓动曲线、on-ones/on-twos=时间量化）；流派：rubber-hose、limited animation(Hanna-Barbera/手冢)、full animation、sakuga 冲击帧、kinetic type、spring UI、定格抖动 | 中高（曲线可钉死，表演判断仍属人） | 零 | 已登记；这是「风格=参数」的最后一块 |
| **§16 工程·建筑·复古 3D 与序贯版面** | 轴测/2:1 等距、**专利图**（USPTO/EPO 线规+剖面线+标号，规则极强）、blueprint/线框/白模/黏土渲染、low-poly、voxel（MagicaVoxel + IsoVoxel/SpotVox）、**PS1 复古**（affine UV + 顶点整屏吸附）、爆炸图、漫画页网格与气泡 | 高（多为几何+规则） | 零/中 | 已登记；MagicaVoxel 许可口径需回源 ⚠ |

---

## 4. 已知残余缺口（诚实清单：这些**不是**"再查一遍就能补上"的）

1. **一次物理在场的媒体**：舞台/灯光秀、装置、行为、舞蹈、现场演奏、实物交互装置。
   A1=「一次在场」→ 没有可重跑的输入源，**位级确定性契约不成立**；代码能做的是预可视化（previz）与控台时间码，不是作品本身。
2. **触觉/味觉/嗅觉交付**：代码可生成配方与工艺参数，但**成品的感知验收必须由人完成**（与 M0「机器观察、人裁决」一致）。
3. **实体手工成品**：陶、漆、金工、食物造型、装裱印刷实操——我们的输出物止于图纸/刀线/切片文件。
4. **交互式长时程音频/音乐引擎**（游戏中间件 Wwise/FMOD 级别的自适应音乐）：已识别未登记细节，需专门一轮取证。
5. **项目治理类产物**：剧本、选角、排期、预算——它们是产出链的上游，不是媒体类型。
6. **亚文化/微风格长尾**：A5 轴上"数字原生"仍在快速增殖（当前只能按季度采样，不承诺穷尽）。
7. **未回源项**（合计入 tools.md §14 / styles.md §17 代谢）：MagicaVoxel 许可口径、Postshot/Renoise/OpenMPT 商业与许可细节、Dehancer 条款、数字敦煌与故宫素材授权、girih/kolam 论文的代码可得性、Hydra/Tidal 的 headless 出片可行性、**Frutiger Aero / vaporwave 术语起源**、**Microsoft/华文系字体逐条 EULA**（本轮新增；fonttools 精确版本已从“未核”改判为实测 4.63.0）。
8. **环境治理缺口（本轮新增，不是媒体问题但阻塞全部“零安装”声明）**：本机两个 Python（conda `hy_py312`=3.12.13 与 `C:\Python313`=3.13.5）能力集不同，
   而**全部 golden manifest 产自 3.12.13**；`vcac` 包从未 editable 安装。需你先定一个交付环境（建议把 A 的新能力装进 B，或以 A 重跑 golden 后再正式切换），
   否则任何“已装即可用”的说法都不可靠。本项属 M0「机器观察、人裁决」——机器只报告差异，**不自定切换环境**。

---

## 5. 复审计程序（下一轮请照此执行，而不是重新凭印象）

0. **先审计本机**（本文件 §0 的两轮教训都来自这一步）：
   - `scripts/doctor.py` —— **每个解释器都要跑一次**（它现在会打印 `sys.executable` + `sys.prefix`）；
   - `python -m pip list` 全量扫（别只看自己记得的那几个包）；
   - `ffmpeg -version` 的 configuration 行 + `-filters/-demuxers/-encoders`；
   - **`Get-Command` 逐个探**（包括不在 PATH 上但装在固定路径的 Chrome/Edge）；
   - **字体目录与已注册字体族**（`matplotlib.font_manager` 一比就发现 353 族，含可变字体）；
   - `LOCALAPPDATA\ms-playwright`（浏览器本体已下载这件事，只看 `pip list` 是看不出来的）；
   - **PATH 阴影检查**：`convert` 之类重名命令先 `Get-Command` 看它到底指向哪个二进制。
   本轮证明“向互联网要能力清单”会漏掉已装在本机的一大批（见 §0 两轮发现）。
1. 用 §1 六条轴各自枚举一遍取值，对每个取值问：**"本项目现在有没有对应路线？"**（✅/📝/⚠/🚫/❌ 五态之一）。
2. 新增候选必须先过 **A6 可验收性**：写不出 spec + 度量的，只登记为灵感板，不进采纳队列。
3. 许可三查：模型许可 / 素材许可 / **字体与参考图许可**（三者都要进 manifest，见 styles.md §6）。
4. 任何 🚫 政策排除项（生成模型、神经渲染、TTS/歌声合成）若要有条件解禁，**必须先改 README 非目标**再改代码，不可反过来。
5. 每次审计产物落本文件，旧判定不删除、就地标 `superseded-by: <date>`。

---

## 6. 许可与安全提醒（本轮新增）

| 项 | 风险 | 处置 |
|---|---|---|
| **fonttools varLib** | ⚠ **CVE-2025-66034**：恶意 `.designspace` 可变成任意文件写原语 | 只处理自产 designspace；沙箱 + 路径白名单（README §6.4） |
| **神经渲染 / 3DGS** | README §3 明确列为排除项（"神经渲染"） | 解禁需你先改非目标；否则只做 COLMAP 经典摄影测量（BSD，可审计） |
| **TTS / 歌声合成** | README §3 明确排除 | 不做；旁白若需人声 → 真人录制或不用 |
| **MagicaVoxel** | 站点口径"Free to use for any project"，**未见正式 LICENSE 文件** | 标 ⚠unverified，商用前先回源 |
| **Renoise / Postshot / LightBurn / Dehancer / Spine / Live2D / Cascadeur** | 商业或免费-非商用混合 | 逐件核条款，未核前不入产出链 |
| **WikiArt / SMPL-X / 故宫名画记 / 数字敦煌** | 非商业研究 / 授权条款未明 | 只作个人研究参考；产出物不引用 |
| **pandoc + MiKTeX 组合** | LaTeX 包许可（LPPL/OFL 混布） | 已装可用；正式产出时把用到的 cls/sty 与字体记入 manifest |
| **系统字体（非 OFL 部分）**：KaiTi、STXingkai、SimHei/SimSun、Comic Sans MS、Bradley Hand 等 | 属 Microsoft/华文字库：**可用不可转发**——渲染成像素一般可行，分发 `.ttf` 那么需逐条 EULA 授权 | 逐条 EULA **未回源** ⚠；商用产出前先核，并把字体名+版本+许可写入 manifest 的 `fonts` 字段 |
| **OFL 字体（已在本机）**：Noto Sans/Serif SC VF、Source Sans Pro | OFL-1.1：可自由使用、嵌入、再分发（字体本身不得单独出售） | ✅ 许可干净，可直接入产出链；manifest 仍须记录 |
| **Playwright / Chromium** | Playwright **Apache-2.0**；Chrome/Edge 各自产品条款（不限制你用浏览器渲染自己的内容） | 浏览器**版本必须钉入 manifest**（不同 build 像素会变）；用 headless_shell/`--disable-gpu` 保证跨硬件可重现 |
| **设计史流派风格（styles.md §10）** | 流派=方法，不受版权保护；但**具体作品**（某张海报/某个商业字体）受保护 | 只从§10 的“形式内核”自行实现，**不拿现成海报当输入**；如需引用作品先查授权 |
