# 工具生态盘点 · Tooling Survey（代码驱动的媒体与游戏创作）

> 本文件是 README §3 工具矩阵的**实况版**：按 `harness_factory/reference/tool-router.md` 的四步循环
> （发现 → 评估 → 登记 → 代谢）对本项目能力池做首轮盘点。每行记录：**当前版本（探测日期）· 本机状态 ·
> 许可证 · headless/确定性要点 · 不适合用来做什么 · 来源**。
> 诚实约定：`✔primary` = 本轮到达官方一手页面/仓库；`○secondary` = 经第三方面包屑证实，采纳前须回源核对；
> `本机` 列由 `scripts/doctor.py` 于 2026-11-04 实测，规划器只能选 AVAILABLE 的能力（README §6.2）。

**Surveyed:** 2026-11-04 · 下一轮复测触发条件见 §11 代谢。
> 修法/风格能否被代码复现**不记在本文件**，见平行文件 `docs/styles.md`（画法与风格模拟盘点）。
> 本文件只回答「有哪些工具能跑 · 许可 · headless · 不适合什么」。

---

## 0. 本机基线（实测 2026-11-04，`scripts/doctor.py`）

| 状态 | 项 |
|---|---|
| ✅ 已装 | Python 3.12.13（conda `hy_py312`，实测存在于 `C:\Users\data\miniconda3\envs\hy_py312`）、NumPy 2.3.5、SciPy 1.18.0、Pillow 12.3.0、OpenCV 5.0.0、pydantic 2.13.4、PyYAML 6.0.2、typer 0.27.0、pytest 9.1.1、FFmpeg/ffprobe（winget：gyan full_build **8.1.1** 在 PATH Links；另有 git 快照 N-125875 于 WinGet Packages）、Node **v24.18.0** / npm（`C:\Program Files\nodejs`）、Pandoc 3.8.2.1、MiKTeX 24.4（latex/xelatex） |
| ❌ 未装（README 曾列为"可用"之外的一切） | matplotlib、scikit-image、jsonschema、hypothesis、music21、scamp、soundfile、librosa、pydub、mido、moviepy、imageio、manim、pygame/pygame-ce、arcade、pymunk、trimesh、moderngl、Blender、LilyPond、FluidSynth、SoX、Csound、SuperCollider、ImageMagick、Inkscape、Graphviz、OpenSCAD、Godot、Ren'Py、LÖVE、Aseprite、Tiled |
| ⚠️ 与 README 记载不一致 | ① README §7 表格声称"已确认可用"的仅 6 项属实，但 **ffmpeg 版本口径不同**（官方 stable 为 8.0.x "Huffman"，本机 gyan 构建自称 8.1.1-full，git 快照 N-125875 也并存）；② README 快速开始假设 `pip install -e ".[dev]"`，包尚不存在；③ 大部分"按需安装"项并未安装——这与"能力池≠强制依赖"的设计一致，无碍。 |

---

## 1. 图像与图形 · Still Image & Generative Graphics

| 工具 | 版本/状态（2026-11-04） | 本机 | 许可 | Headless/确定性 | 用途定位 | 不适合 | 来源 |
|---|---|---|---|---|---|---|---|
| **Pillow** | 12.3.0 已装 | ✅ | MIT-CMU | 纯 Python，完全确定性 | 逐帧渲染、拼图、海报、接触表 | 复杂矢量/排版 | 实测 |
| **NumPy/OpenCV/SciPy** | 2.3.5 / 5.0.0 / 1.18.0 已装 | ✅ | BSD/Apache-2 | 数组级确定性 | 程序化像素、后处理、探针 | 当创作主接口（保留给底层） | 实测 |
| **matplotlib** | 活跃发布（未装） | ❌ | PSF-like(BSD) | `Agg` 后端出 PNG/SVG，rcParams+seed 可控 | 数据可视化、示意图 | 逐帧动画（慢） | ○secondary |
| **SVG（纯文本）** | 无版本问题 | ✅(手写) | — | 文本即源，天然 diff 友好 | 海报、图标、精灵源图 | 光栅滤镜复杂场景 | — |
| **cairosvg / resvg** | 均活跃 | ❌ | LGPL / MIT | CLI/py 转换确定性 | SVG→PNG 光栅化 | 交互动画 | ○secondary |
| **ImageMagick 7** | 7.x 活跃（`magick`） | ❌ | Apache-2.0(类) | CLI 批处理 | 格式转换、特效、contact sheet | 精确像素级复现（版本敏感） | ✔primary(imagemagick.org/download) |
| **Inkscape 1.x** | 1.4 系（CLI `--export-filename`） | ❌ | GPL-2 | CLI 导出成熟 | 矢量精修批处理 | 无 GUI 环境下的复杂编辑 | ✔primary(wiki.inkscape.org CLI) |
| **Graphviz** | 活跃（`dot`） | ❌ | CPL-1.0 | 布局确定性(同版本) | 关系图/DAG 可视化 | 艺术构图 | 本机未装 |
| **p5.js** | v2.3.0 stable，**2.4 即将发布**（官方 releases 提示） | ❌(需Node) | LGPL-2.1 | node 无头 + canvas 抓取可行 | 创意编码、粒子、noise | CI 轻量渲染（重） | ✔primary(p5js.org, GitHub releases) |
| **Processing** | 4.x 维护态 | ❌ | LGPL | headless 较弱 | 教学向 sketch | 本项目管线 | ○secondary |
| **GLSL shader** | 语言级（moderngl/ShaderToy 移植） | ❌ | — | 需固定 GPU/驱动才能复现 | 噪声、灯光、生成纹理 | 跨硬件位级复现 | — |

## 2. 三维 · 3D

| 工具 | 版本/状态（2026-11-04） | 本机 | 许可 | Headless/确定性 | 用途定位 | 不适合 | 来源 |
|---|---|---|---|---|---|---|---|
| **Blender** | **5.2 LTS**（2026-07-14 首发，支持至 2028-07；5.1 为其前一版序列） | ❌ | GPL-2 | `blender -b -P script.py` 成熟；Cycles 固定 seed 位级复现（同版本+同硬件） | 建模/材质/灯光/三维动画静帧与序列 | 实时小游戏 | ✔primary(blender.org/releases/5-2) |
| **Blender 官方 MCP server** | 2026 年上线（Blender Lab） | ❌ | 开源 | ⚠️ 官方页面自述：**直接执行 LLM 代码、无护栏** → 接入前必须按本项目沙箱纪律包装 | agent 驱动 3D 场景 | 未审计即授权写入/外发（M6.11） | ✔primary(blender.org/lab/mcp-server) |
| **ahujasid/mcp-for-blender**（社区版） | 活跃 | ❌ | 开源 | 同上，视为不可信只读直到源码审计 | 发现/学习路径 | 直接引用为事实 | ○secondary(多来源) |
| **OpenSCAD** | 2021.01 后由社区快照版延续（RC 持续出） | ❌ | GPL-2 | CLI `-o out.png/stl`，参数化确定性强 | 机械/几何参数化模型 | 有机造型、贴图材质 | ✔primary(openscad.org/downloads) |
| **trimesh / pywavefront** | 活跃 | ❌ | MIT | 纯 Python 网格处理 | 网格程序化操作、OBJ 读写 | 渲染（需配 Blender/moderngl） | ○secondary |
| **POV-Ray** | 3.7 维护态 | ❌ | AGPL-ish | 光线追踪确定性好 | 数学/几何渲染 | 生态萎缩，优先级低 | 项目知识，未本轮核验 |

## 3. 符号音乐与音频 · Symbolic Music & Audio

| 工具 | 版本/状态（2026-11-04） | 本机 | 许可 | Headless/确定性 | 用途定位 | 不适合 | 来源 |
|---|---|---|---|---|---|---|---|
| **music21** | **v10.5.x**（PyPI 最新 2026-10-22；v11 迁移指南已在官网挂出=即将大版本；BSD/LGPL 双许可） | ❌ | BSD-3 / LGPL-3 | 纯 Python，corpus→MusicXML/MIDI 确定性 | 作曲/和声/分析核心 | 直接出声（需下游合成器） | ✔primary(music21.org, PyPI) + ○(v10.5.2 修复通告经 pkgsrc 转述, 回源核对) |
| **SCAMP** | 0.13.0 | ❌ | MIT | `ScampServer`(SuperCollider) 或导出 MIDI/WAV；`scamp_extensions` 提供音阶/风格库 | 时间轴上的作曲引擎（节奏网格强） | 出版级排版（交给 LilyPond） | ✔primary(scamp.marcevanstein.com) |
| **LilyPond** | **stable 2.26.0**（2026-04-21，终结 2.22/2022 老稳定线）；dev 2.27.4（2026-10-20） | ❌ | GPL-2 | `lilypond file.ly -o out` PDF/PNG/MIDI 全确定 | 出版级乐谱 engraving | 快速迭代预览（编译慢） | ✔primary(lilypond.org news) |
| **FluidSynth** | **2.6.2**（2026-11-01，2.6 系 8 月开启） | ❌ | LGPL-2.1 | `fluidsynth -ni sf2 mid -wav out` 确定性 | MIDI→WAV 渲染（需 SoundFont） | 复杂合成器音色设计 | ✔primary(fluidsynth.org/download) |
| **SoundFont 素材** | e.g. GeneralUser GS / MuseScore-GM（许可各异） | ❌ | 看具体 | — | FluidSynth 的音色库 | 商用未核许可的 SF2 | 待登记 assets/ |
| **SuperCollider** | **3.14.1**（官网当前版） | ❌ | GPL-2 | `scsynth` headless + sclang；离线渲染 `-d` 到 WAV；FFT 级确定性需固定 seed | 合成器/音效/算法作曲 | Windows 无 GUI 一键装（二进制包偏 mac） | ✔primary(supercollider.github.io) |
| **Csound** | **7.0.0 已发布**（官网头版，ICSC 2026 同期） | ❌ | LGPL-2.1 | CLI `.csd`→WAV 确定性强 | 乐器级 DSP、音频合成 | 快速原型（学习曲线） | ✔primary(csound.com) |
| **SoX → sox_ng** | 原版 SoX 上游停更（14.4.20185 系）；**活性延续在 Codeberg 分叉 `sox_ng`**（Ubuntu 已收录为 man page 主体） | ❌ | GPL-2 | CLI 效果链确定 | 响度归一、淡入淡出、格式转换 | 新项目首选（选 sox_ng 或 ffmpeg filters） | ✔primary(codeberg.org/sox_ng/sox_ng + Ubuntu manpage) |
| **FFmpeg (音频侧)** | 本机 8.1.1-full 实测；官方 stable 分支 8.0.x "Huffman"（8.0.3，2026-06-18）。⚠️ 社区有 "FFmpeg 9.0" 传闻贴（2026-08，secondary，未回源） | ✅ | GPL/LGPL | `loudnorm`/`alimiter` 滤镜链、两遍法 LUFS 达标 | 混音、封装、探针 | 符号音乐创作 | ✔primary(ffmpeg.org/download) + 实测 |
| **soundfile / librosa / pydub / mido / midiutil** | 均活跃 | ❌ | MIT/various | 纯 Python | 读写/分析/MIDI 构造 | librosa 在 CI 里慢（按需） | ○secondary |

## 4. 视频与动画 · Video & Animation

| 工具 | 版本/状态（2026-11-04） | 本机 | 许可 | Headless/确定性 | 用途定位 | 不适合 | 来源 |
|---|---|---|---|---|---|---|---|
| **Manim (Community)** | **v0.22.1**（stable docs；0.21/0.22 持续演进） | ❌ | MIT | `manim -a` CLI；scene 构造确定性；依赖 Cairo(+新后端) 与 LaTeX（本机 MiKTeX 可复用） | 数学动画、精确时间轴 | 实拍剪辑 | ✔primary(docs.manim.community) |
| **ManimGL (3b1b)** | 独立线，破坏性变更频繁 | ❌ | MIT | 交互强、CI 弱 | 参考学习 | 生产管线（与 CE 不兼容） | ✔primary(docs 提示两线不兼容) |
| **MoviePy** | **v2.x**（v1 已停止维护；`moviepy.editor` 导入路径在 v2 已移除——旧教程大量失效） | ❌ | MIT | 纯 Python + ffmpeg | 剪辑、拼接、叠加、mux | v1 风格代码直接照抄 | ✔primary(PyPI moviepy) |
| **Remotion** | 4.0.x 持续发布（大版本仍 4.0；近期 changelog 含 Chromium 157 升级）；React 19 需 ≥4.0 | ❌(Node ✅) | 特殊许可(Remotion License：公司>3人需付费，个人/非营利免费) | `npx remotion render` CLI 出 MP4；帧函数 `useCurrentFrame` 天然确定性 | React 生态视频、数据驱动、模板化批量 | 当作纯免费商用库（许可！） | ✔primary(remotion.dev/docs/releases 口径) |
| **Motion Canvas** | v2.x 维护（生成器式逐帧动画，MIT） | ❌(Node ✅) | MIT | 内置导出器可 headless（`npx mc collect/export`） | 编排感强的讲解动画 | 服务端 API 批量（不如 Revideo） | ○secondary(bestofjs + 对比文) |
| **Revideo** | Motion Canvas 官方精神分叉：渲染 REST API、服务端渲染、模板系统，**为自动化管线设计**（midrender.com/revideo） | ❌(Node ✅) | Apache-2.0 | headless 渲染是其第一场景 | 本项目"服务端渲染视频"候选 | 需要 Motion Canvas 编辑器协作时 | ○secondary(pkgpulse/rendercomp 双源一致, 回源核对许可) |
| **FFmpeg (视频侧)** | 同 §3 | ✅ | — | 帧序列→成片、mux、探针、滤镜 | 装配时钟（README §6.6） | 内容生成 | 实测 |
| **imageio [+ ffmpeg]** | 活跃 | ❌ | BSD | 帧数组→mp4 便捷 | 快速封装 Pillow 帧 | 复杂时间轴 | ○secondary |
| **Lottie (rlottie/skia)** | 格式生态稳定 | ❌ | MIT(Apache) | JSON→帧确定性 | UI 动效资产 | 长片 | 项目知识 |
| **OpenSequencer / Rendiv 等新兴** | 2026 年出现多个"AI 原生剪辑"开源项目（search 发现，未审计） | ❌ | 各异 | 未核验 | 观察名单 | 现阶段引入 | ○secondary，标 unverified |

> §4 是**装配与代码驱动**的动画线；**手工作画/手绘质感**那一族（OpenToonz、Krita、Rough.js…）
> 与**影视级 3D**、**日式 2D/2.5D** 分别见下面新增的 §5 / §6 / §7。

## 5. 手绘质感与 2D 动画 · Hand-drawn Look & 2D Animation

> 传统 2D 动画工业的主力工具几乎都**不是 headless**（画师交互为轴心）。本节按「**可否被脚本驱动**」排序，
> 而不是按名气：能写脚本的才进得了本项目的管线。

| 工具 | 版本/状态（2026-11-04） | 本机 | 许可 | Headless/可脚本性 | 用途定位 | 不适合 | 来源 |
|---|---|---|---|---|---|---|---|
| **Krita** | 线在 **5.3.2** 与 **6.0.2**（6.x 为新一代引擎）双支并行；⚠️ 精确当前版本号未回源核验 | ❌ | GPL-3 | **PyQt/Python 脚本接口 + `krita -render` 命令行渲染**；笔触（brush stroke）数据可由脚本生成 → 是「代码作画」最现实的落点 | 程序化笔触/图层→成图、绘画质感 | 逐帧动画的时序精度（时间轴非确定性） | ✔primary(krita.org 下载页与公告；版本号计数标 directional) |
| **OpenToonz** | **1.8**（2024-01 起为当前主线；Ghibli/Toonz 血统，Est. 由 Wayback 捐赠） | ❌ | BSD-3(类) | 场景为 XML（`.toonzscx`）**可程序化生成/改写**；headless 渲染弱（需 GUI 会话） | 正牌 2D 赛璐璐工作流（扫描→线条清理→上色→摄影） | 无人值守批量（AMI/scripting 有但脆） | ✔primary(opentoonz.github.io) |
| **Pencil2D** | **0.7.2** | ❌ | Apache-2.0 | 自有格式，脚本化几乎无；GUI-only | 极简逐帧手绘原型 | 管线自动化（不可驱动） | ✔primary(pencil2d.org) |
| **Synfig Studio** | **1.5.5**（"Alegreya"系 1.5 线） | ❌ | GPL-3 | `.synfig`/`.sfp` XML 可生成；**`synfig` CLI 可直接渲染序列**（`-c` 命令行） | 矢量逐帧/补间动画 | 手绘质感（矢量平滑风） | ✔primary(synfig.org 下载 + wiki CLI 页) |
| **Rough.js / rough-notation** | 版本与维护状态**未回源核验**（标 ⚠unverified）；算法本质已被广泛复述 | ❌(Node ✅) | MIT | JS 库，node 可 headless 出 SVG；**同一 seed 确定** | 「手绘抖动线」这一视觉语法的标准实现 | 严肃排版（线宽不可精控） | ○secondary(roughjs.com)，采纳前回源 |
| **Excalidraw CLI（官方）** | 官方已发布 **`@excalidraw/cli`**，README 自我定位含 **"for humans and agents"** | ❌(Node ✅) | MIT（库）/ 组件另有口径 | `.excalidraw` JSON → PNG/SVG，**纯 CLI、天然 headless** | agent 写 JSON → 手绘风图示成片 | 当图表库用（它画的是线框，不是数据） | ✔primary(npm @excalidraw/cli + excalidraw.com 文档) |
| **matplotlib `xkcd()`** | 随 matplotlib（本机未装） | ❌ | PSF/BSD | `Agg` 后端 + rcParams + seed → **完全确定性**，零 JS 依赖 | 手绘风图表/示意图（Python 侧首选，替代 Rough.js） | 非图表类自由构图 | ✔primary(matplotlib 3.11.2 docs: stylesheet/xkcd) |
| **Tangram / Sketching 类滤镜** | 学术算法（Cumming 素描建模等） | — | — | 论文代码多、工程化弱 | 线稿/明暗生成的算法参考 | 直接投产 | ○secondary，仅索引 |
| **OpenCV `sketch` / XDoG** | **cv2 5.0.0 已装**；XDoG = Winnemöller 2012；`skimage.filters.difference_of_gaussians` 需 scikit-image | ✅(cv2) / ❌(skimage) | Apache-2 / BSD | 纯滤波，**确定性、零新依赖** | 照片→素描/线稿（L0 就能跑） | 从空白生成构图（只转换不创作） | ✔primary(实测 + 论文) |
| **Spine** | **4.2**（骨骼 2D 动画工业事实标准） | ❌ | 商业（按席位） | 导出/编辑器非 headless；运行时库（C++/ts）开源可用 | 角色骨骼动画资产 | 本项目预算与自动化（商业 GUI 为主） | ○secondary(esotericsoftware.com)，采纳前核价 |
| **Live2D Cubic** | **5.3.05 beta 1** 线 | ❌ | 商业（免费档有营收上限） | `.cmo3` 私有；运行时 SDK 可用 | 立绘呼吸/伪 3D（VTuber 姿势） | 程序化生成（编辑依赖 GUI） | ✔primary(live2d.com 下载/公告，营收上限条款要回源) |
| **Rive** | 官方当前自我定位已是 **"agent-native 2D and 3D engine"** | ❌(Node ✅) | MIT(运行时)/编辑器服务条款 | `.riv` 状态机 + 运行时；**官方明确欢迎 agent 驱动**；导出可 CLI | 交互式/状态机动画、UI 动效 | 长片线性动画 | ✔primary(rive.app 文档/首页口径) |
| **python-lottie / lottie 生态** | 活跃（CuebiX/python-lottie 面向 Blender 导出） | ❌ | MIT/Apache-2 | **JSON→帧完全确定**（rlottie/skia 光栅） | 程序化生成 Lottie 资产（矢量动效） | 长片、位图笔触 | ○secondary(pypi python-lottie)，回源核对维护度 |
| **Cascadeur** | **2026.2**（AI 辅助关键帧姿态物理自动补全） | ❌ | 商业（免费档非商用条款） | GUI 为轴；导出 FBX 可下游 | 角色动作可信度（物理修正） | 无人值守管线 | ✔primary(cascadeur.com 下载页) |
| **EbSynth** | **2** | ❌ | 商业（免费可试用，条款需回源） | 有 CLI 用法（社区记录，非官方文档主路径）⚠️ | 单帧风格化→传播到序列（**转描/风格化**） | 全新创作（必须有美术关键帧输入） | ○secondary，标 directional |
| **Dragonframe** | **DF2026**（定格动画工业标准） | ❌ | 商业（硬件绑定） | 有远程控制 API（面向自家设备） | 定格/实物逐帧 | 本项目（硬件+商业授权） | ✔primary(dragonframe Depo 口径) |
| **Adobe Animate** | **已宣布停用**：2026-03-01 停止支持（EOL） | ❌ | 商业订阅 | — | ❌ 不再作为选项登记 | 任何新管线（上游已终止） | ✔primary(Adobe 官方支持页 EOL 通告) |
| **Toon Boom Harmony / TVPaint** | 工业 2D 双巨头；**本轮未取得可信当前版本号** | ❌ | 商业 | 有脚本层（Harmony Python/TSF）但许可重 | 参考认知（知道存在） | 本项目引入（成本+许可） | ⚠unverified，勿引用具体版本 |

**这一族的诚实判断**：2D 动画的瓶颈**不是缺工具**，而是「逐帧作画」本质上是**人的时序判断**（timing/spacing、表演、作画监督）。代码能稳定接管的是三件事：**(a) 手绘视觉语法**（Rough/xkcd/Excalidraw CLI/XDoG）、**(b) 矢量与骨骼资产的程序化生成**（Synfig XML、Lottie JSON、SVG）、**(c) 装配与摄影**（FFmpeg、合成层）。真正的原画/动画师环节，本项目**不承诺替代**。

## 6. 影视级 3D 动画工业栈 · Feature-3D Pipeline

> 结论：**开源工业底座已齐备**（USD + MoonRay + Cycles + Blender），迪士尼/梦工厂级短片的**技术闸门不存在**，
> 天花板是**美术工时**（模型、绑定、灯光、表演以人年计）。故本节只登记「能跑、许可干净」的部件，不承诺长片质感。

| 部件 | 版本/状态（2026-11-04） | 本机 | 许可 | 可脚本/确定性 | 用途定位 | 不适合 | 来源 |
|---|---|---|---|---|---|---|---|
| **Blender（3D 侧）** | **5.2 LTS**（2026-07-14，支持至 2028-07）——见 §2 | ❌ | GPL-2 | `blender -b -P` + Cycles 固定 seed（**同版本同硬件**才位级复现）+ Geometry Nodes 全程序化 | 唯一的「建模→绑定→灯光→渲染→合成」一站式 | 影视级大规模 farm 调度（需配 USD） | ✔primary(blender.org/releases/5-2) |
| **Universal Scene Description (USD/Pixar)** | AOUSD 标准；OpenPulse/pxr 持续发布（精确版本号未回源，标 ⚠) | ❌ | Apache-2.0 | **纯文本/二进制场景合成**，Python API 强、天然可 diff/可组合 | 场景分层合成与跨软件交换（本项目的 DAG 思路即同构） | 小项目（体系偏重） | ✔primary(pixar.github.io/usd + aousd.org) |
| **MoonRay（DreamWorks/Weta 系）** | **Apache-2.0 开源**，**2026-05 进入 ASWF 托管** | ❌ | Apache-2.0 | 有 batch 渲染能力；需自行接场景 | 影视级 CPU 光线追踪（真·工业级血缘） | 短期投产（集成工时） | ✔primary(aswf.org 公告 / LF 新闻) |
| **Houdini** | **22**（2026-07-16 发布线） | ❌ | 商业；**Apprentice 免费非商用（含水印/分辨率限制）**、**Indie 受限营收上限** | `hython`/`hscript` headless 成熟，**程序化 FX 的天花板** | 烟/火/破坏/流体/群集 | 商用交付（许可层级要先算清） | ✔primary(sidefx.com 产品与许可页) |
| **RenderMan** | **26** 系列；**Non-Commercial 免费** | ❌ | NCR（非商用）/ 商业订阅 | `renderman` CLI + Python；RIS 场景确定性好 | 学习工业渲染语义 | 商用（NCR 条款） | ✔primary(renderman.pixar.com 下载/条款) |
| **OpenVDB** | 活跃（ASWF） | ❌ | Apache-2.0 | 体素数据（云/烟/雪）程序化 | 大体积特效承载 | 直接当渲染器 | ✔primary(openvdb.org) |
| **OpenEXR / ILM 血统** | ASWF 托管，3.x 线 | ❌ | BSD-3 | HDR 多通道帧文件；**Weta/ILM 的开放贡献以此为凭** | 帧序列中间格式（比 png 更适合合成） | 当交付物（需转码） | ✔primary(aswf.org/projects/openexr) |
| **MetaHuman** | ⚠️ **Web Creator 应用 2026-11-05 起停用**（即本文档登记日的**次日**）；改由 UE 内/新流程承接 | ❌ | **UE EULA 约束**（须在 UE 生态内使用为典型限制） | 生成偏 GUI/云 | 高保真人脸（若接受 UE 路线） | 独立管线/非 UE 交付（许可不符） | ✔primary(unrealengine.com 元人类支持页 sunset 通告) |
| **SMPL-X / 人体参数模型** | 活跃（MPI/MAX 系） | ❌ | **非商业研究许可**（商用须另行授权） | Python 工具链完善，参数化体型/姿态 | 程序化人体姿态/动作研究 | **任何商用产出** | ✔primary(mpi-inf.mpg.de / smplx 项目许可页) |
| **Mixamo** | 仍免费提供自动绑定 + 动作库 | ⚠️ 需账号/网络 | Adobe 条款（上传素材权利条款要读） | **官方自动姿态/绑定服务**（无公开批量 API） | 快速拿到能动的角色 | 需完全离线/可复现的资产（不可控） | ○secondary(mixamo.com)，采纳前核条款 |
| **VRoid Studio / VRM** | 活跃（VRM 规范由 OpenVRM Consortium 维护） | ❌ | 软件免费；**VRM 元数据内含再分发许可位** | GUI 生成为主，VRM/glTF 解析可脚本 | 动漫风人型角色（许可结构清晰） | 影视级写实质感 | ✔primary(vrm.org / openvrm GitHub) |
| **CC0 基础资产** | **Blender Studio 开放影片**（含全套生产文件，CC-BY 系）+ **17 个 CC0 人体基础网格**；另有 Poly Haven / ambientCG（CC0 HDRi/PBR） | ❌(需下载) | CC0 / CC-BY（逐件核验） | 资产可入库、可哈希、可审计 | 直接拿到「已生产验证」的场景/角色/材质 | 未逐件核对授权就用 | ✔primary(blender.org/studio/open-movies + polyhaven.com) |

**采纳纪律**：本表**没有任何一行是本机可用的**（全 ❌）。按 `docs/roadmap-development.md` §1 原则 6，外部 DCC 只能作为**同一契约下的替代渲染器**接入（`spec → render → measure → validate → manifest` 不改），且需你逐项批准安装。

## 7. 日式 2D / 2.5D（赛璐璐与「三渲二」）· Anime Look

| 路线 | 技术要点 | 工具（本机） | 确定性 | 许可/风险 | 来源 |
|---|---|---|---|---|---|
| **真·2D 赛璐璐** | 原画→动画(中割)→上色→**撮影**(合成/摄影) | OpenToonz 1.8 / Krita / Clip STUDIO EX（版本未核 ⚠） | 低（作画是人工时序判断） | 工具许可 OK；**参考素材（动画截图）不可直接复用** | ✔primary 各官网；撮影流程为业界通识 |
| **2.5D（3D 渲二）** | 低模 + toon shader + 描边 + 分层合成；「角色 3D / 背景手绘」混拍 | **Blender**：Grease Pencil + Freestyle + EEVEE/Cycles toon；社区着色器（如 CyclesTooner / bpy-renderer 系；**`shader-to-ruby` 本轮未命中仓库，勿引用**） | 中高（渲染确定；描边参数可钉） | GPL 工具；导入素材逐件核验 | ✔primary(blender.org Grease Pencil/Freestyle 手册) + ○secondary |
| **背景美术（背景画）** | 数字绘景 = 画法问题，不是动画问题 | 走 `docs/styles.md` §1.2 山水链 / §3 Curtis 水彩 / XDoG 线稿 + 平涂上色 | **高**（纯代码分层可确定） | 干净 | ✔primary styles.md 已核实 |
| **立绘/伪 3D** | Live2D 形变、VRM 动漫人型 | Live2D 5.3.05 beta1 / VRoid | 低（GUI 编辑） | Live2D 营收上限条款；VRM 元数据许可位 | ✔primary 官网条款页 |
| **状态机/交互动效** | Rive "agent-native 2D and 3D engine" | Rive 运行时(MIT) + Node ✅ | 中（.riv 为二进制资产，可哈希） | 编辑器服务条款 | ✔primary(rive.app) |
| **转描/风格化传播** | 关键帧风格化 → EbSynth 传到序列 | EbSynth 2 | 低（需美术关键帧 + 非官方 CLI 文档） | 商业免费试用，条款未回源 | ○secondary，标 ⚠unverified |
| **AI 生成动画** | 文生视频/图生视频（本机有 `ai-video-generation` skill） | ❌ **不入渲染主路径** | 破坏（不可复现） | 版权/判例风险 | 见 `docs/styles.md` §8 四条理由 + 本文件 §9-C |

**诚实判断**：日式 2D 里，代码能可靠接管的是**摄影合成层、背景美术、镜头调度、描边与分层**；
「作画」本身（timing/spacing + 表演）仍是人。**「三渲二」是本项目最现实的高质感路线**——因为它把
不可自动化的作画判断，替换成了可脚本化的渲染+合成规则。

## 8. 游戏与互动 · Games & Interactive

| 工具 | 版本/状态（2026-11-04） | 本机 | 许可 | Headless/确定性 | 用途定位 | 不适合 | 来源 |
|---|---|---|---|---|---|---|---|
| **pygame-ce** | **2.5.8**（2026-08-09；首发支持 Py3.14；原版 pygame 停滞，社区共识迁 CE） | ❌ | LGPL-2.1 | `SDL_VIDEODRIVER=dummy` 无头跑逻辑帧；固定 timestep 可脚本回放 | P5 游戏线主力（README 目标） | 3D、Web 导出（配 pygbag 可行但重） | ✔primary(PyPI + GitHub releases) |
| **Python Arcade** | **3.3.3** | ❌ | BSD-3 | 类似 pygame；OpenGL 后端 | 教学向 2D 备选 | 与 CE 同时引入（选一个） | ✔primary(api.arcade.academy) |
| **Godot** | stable **4.7**（2026-06-18，4.7.2 维护版 2026-08-15 为当前）；4.8-beta2（2026-10-29）；3.6.x LTS 仍在维护 | ❌ | MIT | `--headless --export-release` CI 官方姿势；`--path` 项目化 | Web/桌面包、3D 原型 | 小脚本级游戏（重） | ✔primary(godotengine.org/download/archive, releases/4.7) |
| **Phaser** | **4.1 "Salusa"**（4.0 "Caladan" 2026-04-11，4.1 2026-04-30） | ❌(Node ✅) | MIT(no)→ Phaser 3 为 MIT；**Phaser 4 许可需回源确认** | 纯前端，Playwright 冒烟（README §12.7） | 网页小游戏主力 | 无 Node 环境 | ○secondary(tech-insider 对比文, 回源 phaser.io) |
| **Three.js** | **r186**（2026-09-08；月度 r 号节奏） | ❌(Node ✅) | MIT | node + headless-gl/puppeteer 可截图 | 3D 网页场景 | 完整游戏框架（自己搭逻辑） | ○secondary(utsubo 博客, 回源 GitHub releases) |
| **Babylon.js** | **9.0**（2026-04-13 官宣） | ❌(Node ✅) | Apache-2.0 | 编辑器之外的 NullEngine headless | 全功能 3D web 引擎 | 极简项目 | ✔primary(babylonjs.com 首页 + 论坛官宣) |
| **Bevy** | **0.18**（bevy.org/news 2026-01-13；0.17 2025-09；节奏约一季度一版，本轮应已有 ≥0.19 — directional） | ❌(Rust 未装) | MIT/Apache-2 | ECS + fixed timestep 天然确定性；headless 测试成熟 | Rust 线（远期） | 短期引入（工具链成本高） | ✔primary(bevy.org/news) 0.18 条 |
| **Ren'Py** | **8.5.3** "We Can Go to the Moon"（2026-05-15；官方推荐 8.x 用于所有新项目） | ❌ | MIT | CLI 构建 + `renpy.sh`；有测试钩子 | 视觉小说/互动叙事 | 实时动作玩法 | ✔primary(renpy.org) |
| **Ink (inkle) / Twine** | Ink 编辑器开源、运行时多语言；Twine 活跃（社区 fork 谱系复杂） | ❌ | MIT(GPL for editor?) | 纯文本 .ink 故事 → 运行时脚本，天然可 diff/可测 | 分支叙事内容层 | 画面表现（套 Ren'Py/网页） | ○secondary，回源核对 |
| **LÖVE** | **11.5** stable（12.x 长期 beta） | ❌ | zlib-2 | `love` headless 弱（需虚拟显示） | Lua 线备选 | CI 自动试玩 | ✔primary(love2d.org) |
| **Aseprite** | v1.3.x stable（1.3 系自 2023-12；GitHub Actions 显示持续修复） | ❌ | **源码 GPL，官方二进制付费**（可自编译） | `aseprite -b` CLI 导出精灵表/动画成熟 | 像素素材管线 | 当作免费二进制采购 | ✔primary(aseprite.org/docs + repo) |
| **Tiled** | 1.11.x 线（官方 blog 1.11.1；第三方百科称 1.10.2 —— **计数不一致，directional**；1.11 支持直接装载 .ase 图层） | ❌ | GPL-3(编辑器)/BSD(运行时 libtiled) | `tiled --export-map` CLI 存在 | 瓦片地图编辑 | 无编辑器环境的程序化地图（直接写 TMJ JSON） | ✔/○混合(mapeditor.org) |
| **pygbag** | pygame-ce→WebAssembly 通道，活跃随 CE | ❌ | BSD | 构建后可 Playwright 冒烟 | pygame 网页构建 | 大项目性能 | 项目知识，未本轮核验 |
| **Godot Export skill（skillsdirectory）** | 社区 Agent Skill 已存在（2026-09） | — | — | — | 发现路径：玩法导出可复用 | 未审计直接用 | ○secondary |

## 9. 开发模式与工程编排 · Development Modes

**A. 「Vibe Coding 做媒体」的模式层**（与 README 核心原则对应，均已在生态中有成熟做法）：

1. **代码即资产（code-as-asset）**：产物由 `spec→plan→code` 三级生成物构成，代码入库、媒体走 `outputs/`。Remotion 官方口号已把 "Use agents" 写进首页——agent 写 React Video 已是主流用法。
2. **确定性三件套**：固定 seed + 钉死工具版本 + 内容哈希缓存键（README §6.5）。要点：Blender Cycles 位级复现要求同版本**同硬件**；GPU/GL 路线跨硬件难位级复现——验收改用 pHash/SSIM 容差（README §12.3 已如此设计）。
3. **Headless 姿势表**（CI 无窗口运行）：Blender `-b`、Godot `--headless`、Unity 不引入、LilyPond `lilypond file.ly`、FluidSynth `-ni`、Manim `-a`/`-s`、Remotion `npx remotion render`、Tiled `--export-map`、pygame-ce `SDL_VIDEODRIVER=dummy`、Web 构建用 Playwright/Puppeteer。Linux CI 补 `xvfb-run`；本机 Windows 对应物：ConPTY/虚拟桌面（远期）。
4. **DAG 编排**：本项目自研 `pipeline.py`（README 定位）。可借鉴而勿引入重型框架：Make/Just（任务图）、Snakemake/Airflow（模式参考，不必上船）；缓存键 = 节点输入哈希。
5. **自修复回路**：结构化诊断（规则 ID+期望+实际+日志尾）回灌 LLM、最小补丁、≤3 轮（README §5.2-8）。与 harness_factory M3/M5 同构，落 `.harness/gates.md` 即可。
6. **试玩即测试**：脚本化输入 `{frame,key,action}` + 状态快照断言 + 3 次确定性回放（README §6.8/§12.7）；Godot 官方即支持 CI headless export，py 线用 dummy video driver。

**B. Agent/Skill/MCP 生态（本任务族的"外挂器"，probed 2026-11-04）**：

| 器 | 种类 | 状态 | 门 |
|---|---|---|---|
| Blender 官方 MCP（blender.org/lab/mcp-server） | MCP server | 上线，官方自述无执行护栏 | 接入前按 M6.11 沙箱化 + 只读起步 |
| ahujasid/mcp-for-blender | MCP server（社区） | 流行 | 源码审计前 untrusted |
| `remotion-best-practices`（本机已装 Skill） | Agent Skill | ✅ 本机可用 | 直接可用于 Remotion 线 |
| Remotion Upgrade / Godot Export（skillsdirectory 等市场） | Agent Skill | 存在性已发现 | 装前审计描述注入风险（工具投毒，Invariant Labs 2025-04） |
| `blender-cli`（renezander030） | 单文件 CLI 包装 | 新发现（star 少） | 观察名单，不即采 |
| MCP Registry（registry.modelcontextprotocol.io `/v0/servers`） | 发现面 | 机器可读 JSON（<HF> tool-router §2 已探） | 聚合器只作发现，不作引用 |

**C. 明确排除**（对齐 README §13 非目标）：RunComfy 类 `ai-video-generation` / `ai-music` / `ai-image-generation` skills 虽在本机技能列表中，但其路线是**多模态模型直接生成媒体**——与本仓库"代码做媒体"的根本路线相反，登记为「知道存在，本项目不使用」；扩散模型、云端文生图 API 同理。

## 10. 采纳队列建议 · Onboarding Queue（供后续任务确认，非本次执行）

按 README 里程碑倒推的最小集（安装动作均属可逆本地操作，仍待你发话再装）：

| 序 | 动作 | 支撑里程碑 |
|---|---|---|
| 1 | `pip install matplotlib jsonschema hypothesis` + `scikit-image`（conda-forge） | P0/P1 + L0 测试 |
| 2 | `pip install manim moviepy imageio[ffmpeg]` | P3 视频线（复用本机 MiKTeX/FFmpeg） |
| 3 | `pip install music21 scamp soundfile mido midiutil` + winget 装 **FluidSynth + 一个 GM SoundFont** | P2 音频线 |
| 4 | `winget install Blender.Blender`（5.2 LTS） | P4 三维 |
| 5 | `pip install pygame-ce` + `npm i phaser`（Node ✅ 已在） | P5 游戏第一闭环（Neon Dodger） |
| 6 | （音频排版按需）LilyPond 2.26 winget/choco | 出版级乐谱时才装 |
| 7 | （观察）Revideo vs Motion Canvas 二选一后再装 | 服务端渲染需求出现时 |

## 11. 代谢 · Metabolism

- **复测触发**：每轮实质任务前跑 `scripts/doctor.py`（本机面）；每季度或里程碑切换时复采 §1–§8 版本列（网络面），旧数据不删除、就地标注 `superseded-by: <date>`。
- **不一致登记**：Tiled 版本号双源不一致、"FFmpeg 9.0" 传闻、Bevy 疑似 ≥0.19、Phaser 4 许可条款、Krita 5.3.2/6.0.2 双线当前版本计数、USD 精确版本号——六项列入下一轮回源清单。
- **本轮新增未核（§5–§7）**：`roughjs` 版本与维护状态、Toon Boom/TVPaint/Clip Studio 版本号、EbSynth 许可条款、Mixamo 上传素材权利、Harmony 脚本层可用性。⚠️ 已在本文件纠正的记忆错误（`shader-to-ruby` 未命中、Zoo Tools 非 Weta 开源）记于 `docs/styles.md` §10。
- **回流工厂**：本表的列格式即 `<HF>/reference/tool-router.md` §4 "开新表模板" 的一次实例化；通用化模式（"代码驱动媒体生态盘点表"）可按 `capability-flow.md` 提案回流 `<HF>/updates/`（只提案，不直改 data|core）。
- **SSOT**：本文件为本仓库工具事实的唯一来源；README §3 是能力池愿景，版本实况只认本文件。
