# 工具生态盘点 · Tooling Survey（代码驱动的媒体与游戏创作）

> 本文件是 README §3 工具矩阵的**实况版**：按 `harness_factory/reference/tool-router.md` 的四步循环
> （发现 → 评估 → 登记 → 代谢）对本项目能力池做首轮盘点。每行记录：**当前版本（探测日期）· 本机状态 ·
> 许可证 · headless/确定性要点 · 不适合用来做什么 · 来源**。
> 诚实约定：`✔primary` = 本轮到达官方一手页面/仓库；`○secondary` = 经第三方面包屑证实，采纳前须回源核对；
> `本机` 列由 `scripts/doctor.py` 于 2026-11-04 实测，规划器只能选 AVAILABLE 的能力（README §6.2）。

**Surveyed:** 2026-11-04 · 下一轮复测触发条件见 §14 代谢。
> 修法/风格能否被代码复现**不记在本文件**，见平行文件 `docs/styles.md`（画法与风格模拟盘点）。
> 「是否穷尽」的判定与分类轴见 `docs/coverage-audit.md`（媒体类型 × 风格谱系审计台账）。
> 本文件只回答「有哪些工具能跑 · 许可 · headless · 不适合什么」。

---

## 0. 本机基线（实测 2026-11-04，`scripts/doctor.py`）

| 状态 | 项 |
|---|---|
| ✅ 已装 · **解释器 A**：`C:\Python313\python.exe` = Python **3.13.5**（PATH 上的 `python`） | NumPy **2.4.6**、SciPy 1.18.0、Pillow 12.3.0（+`pillow-avif-plugin` 1.5.5 → AVIF）、OpenCV 5.0.0、**matplotlib 3.11.0**、**fonttools 4.63.0**、**playwright 1.58.0**、pypdf 6.19.0、nbconvert 7.17.1、pydantic 2.13.4、PyYAML 6.0.3、jsonschema 4.26.0、typer 0.25.1、rich、pytest 9.1.1 |
| ✅ 已装 · **解释器 B**：conda `hy_py312` = Python **3.12.13**（README §2 声明的项目环境，也是**全部 6 份 golden manifest 的实际产出环境**） | NumPy 2.3.5、SciPy 1.18.0、Pillow 12.3.0（含 AVIF）、OpenCV 5.0.0、pydantic 2.13.4、PyYAML 6.0.2、typer 0.27.0、pytest 9.1.1 —— **不含** matplotlib / fonttools / playwright / pypdf / nbconvert / jsonschema / scikit-image |
| ✅ 已装 · 与解释器无关 | FFmpeg/ffprobe **8.1.1**-full_build（gyan，winget Links；编译能力见 §0.1）、Node **v24.18.0** / npm 12.2.0、Pandoc **3.8.2.1**、MiKTeX 24.4（`latex`/`pdflatex` 4.19、`xelatex` 4.11、`lualatex`、`latexmk`）、Chrome **145.0.7632.6**（Playwright 实测启动）+ Edge 156.0.4314.58、**Playwright 浏览器包已下载**（`chromium-1208/1234`、`chromium_headless_shell-*`、自带 `ffmpeg-1011`）、系统字体 353 族（含 **Noto Sans/Serif SC 可变字体 wght 100–900**、KaiTi、STXingkai、Source Sans Pro、Monoton——逐条许可见 §0.2） |
| ❌ 未装 | scikit-image、music21、scamp、soundfile、librosa、pydub、mido、moviepy、imageio、manim、pygame/arcade/pymunk、trimesh、moderngl、cairosvg/resvg-py、Blender、LilyPond、MuseScore、FluidSynth、SoX、Csound、SuperCollider、**ImageMagick**、Inkscape、Librsvg、Ghostscript、potrace、Graphviz、OpenSCAD、Godot、Ren'Py、LÖVE、Aseprite、Tiled |
| ⚠️ 与 README / 本文早期版本记载不一致（**本轮实测纠正**） | ① 本机有**两个 Python**，能力集不同：项目声明环境（B）里 matplotlib/fonttools/playwright **都没有** → 本文与 coverage-audit 里凡写"零安装即得"的这几项，**必须先决定用哪个解释器**（`scripts/doctor.py` 已改为打印 `sys.executable`+`sys.prefix`，两个都要跑）；② README 快速开始的 `pip install -e ".[dev]"` **从未执行**（两个解释器 `pip show vcac` 均无此包，测试靠 `pyproject` 的 `pythonpath=["src"]` 通过；2026-11-05 现状：91 项，hy_py312 下 12 项浏览器/可变字体测试 skip）；③ README §3 把 ImageMagick / Graphviz / TikZ 列在能力池——池≠已装：**TikZ/LaTeX 确实已装**，ImageMagick / Graphviz 未装；④ **Windows 陷阱**：PATH 上的 `convert` 是 `C:\Windows\System32\convert.EXE`（磁盘工具），不是 ImageMagick，脚本若误调会得到完全无关的行为（doctor.py 已单列 PATH shadows）；⑤ ffmpeg 版本口径（官方 stable 8.0.x "Huffman" vs 本机 gyan 8.1.1-full，另有 git 快照 N-125875）；⑥ golden manifest 记录 `python=3.12.13`，与今天默认 `python`=3.13.5 不同——**帧内容哈希与编码器无关，故仍复现通过**，但这正是 provenance 记解释器的价值所在。 |

---

## 0.1 本机 FFmpeg 已编译能力清单（零安装即得，实测 2026-11-04）

> 发现途径：穷尽性审计时回查 `ffmpeg -version` 的 configuration 行与 `-filters/-demuxers/-encoders`。
> 意义：下面这些**本来被我归为“需安装”或“缺口”的能力，今天就可用**。先审计本机，再审计互联网。

| 能力族 | 具体项（实测存在） | 零安装解锁的路线 | 属于本文件哪一节 |
|---|---|---|---|
| **字幕/动态字排版** | `ass`、`subtitles`（均 `--enable-libass`）、demuxer：`ass/srt/webvtt/microdvd/jacosub/pjs/vplayer/mpsub/aqtitle/subviewer/sup/…` | **动态字体（kinetic typography）**、卡拉OK、多语字幕（ASS 自带 `\t`/`\pos`/`\clip`/`\k`） | §8（已改判为本机可用） |
| **Tracker 音乐（chiptune/demoscene）** | demuxer `libopenmpt`、`libmodplug`（`.mod/.xm/.it/.s3m` → 音频） | **模块文件→WAV 完全零安装**（上面 §9 登记的“需装 tracker 工具”多数已包含） | §9（修正） |
| **声→图 / 声→视（视听合成）** | `showwaves(pic)`、`showspectrum(pic)`、`showfreqs`、`avectorscope`、`volumedetect` | **音频可视化封面/乐谱动画/频谱艺术**（把现有 audio 路线直接接成图/视） | 新族：见 styles.md §12 补充 |
| **质量度量（验收！）** | `libvmaf`（VV→V，算参考/退化两路的感知差异） | **pHash/SSIM 容差的升级项**：验收规则可新增 VMAF 分值（README §12.3） | validate.py 新规则 |
| **色彩/位深管线** | `zscale`（libzimg：resize/色彩空间/位深）、`libplacebo`（HDR tone-map，GPU） | bt709/bt2100 标记、HDR→SDR、打印/流媒体色彩合规 | §4/§8 |
| **修复与质感滤镜** | `deband`、`gradfun`、`hqdn3d`、`nlmeans`、`gblur`、`tmix`、`tblend`、`rubberband`（变速/变调） | **胶片噪点/带状噪声模拟、动态模糊、场序质感、时间拉伸**（glitch/胶片族的零件库） | styles.md §12/§13 |
| **交付格式** | encoder：`gif`、`apng`、`libwebp(_anim)`、`libjxl(_anim)`、`qtrle`、`ffv1`(无损归档)、`dpx/cineform?`未逐项测 | **动图/APNG/JPEG XL 交付 + FFV1 归档母版**（本节原本是空白） | §4/§8 |
| **冷僻但有用的输入** | demuxer：`tty`（电传打印！）、`cdxl`（Commodore 图形）、`fits`（天文图像）、`iamf`（**Immersive Audio Model and Formats**）、`fsb`（FMOD 采样库） | **ASCII/ANSI 媒体有原生读入路径**；IAMF = 空间音频工业格式已在本机 | §9 / styles.md §12 |
| **其他** | `chromaprint`（音频指纹）、`libmysofa`（**SOFA HRTF** → 双耳渲染）、`quirc`（二维码）、`libjxl`、`vulkan/opencl/shaderc` | 音频指纹可用于**去重/溯源校验**；SOFA 可用现有 numpy 路线做双耳 | §9 / provenance 扩展 |
| ⚠ **存在但政策排除** | `flite`（TTS）、`whisper`（本地转写） | 本机就能做，但 README §3 将 TTS/模型生成列为排除项 → **不开**（若要开，先改非目标） | §12-C |

> GPU 相关项（`*_vulkan`、`*_opencl`、`libplacebo`）：**跨硬件不可位级复现**（轴 A3），
> 若用于验收必须改用 CPU 对应物（`zscale`/`gblur` 均有 CPU 版）。

---

## 0.2 本机第二轮审计（穷尽性审计复读时发现的第一轮漏项，实测 2026-11-04）

> 方法同 §0.1：**先查本机**。本轮把 `pip list` / `Get-Command` / 字体目录 / `ms-playwright` 目录全部扫了一遍，
> 结果是：下面四项**本机上今天就能用**，但前一轮我把它们登记成了"需安装"或"缺口"。
> 证据级别：✔primary = 本轮在本机跑出结果（命令与输出一并记在下面），可在任意机器复测。

| 新登记能力 | 实测证据 | 解锁的媒体路线 | 限定条件（诚实说明） |
|---|---|---|---|
| **浏览器作为光栅化器/排版器**（HTML·CSS·SVG·Canvas·WebGL → PNG/PDF） | `playwright 1.58.0` 可导入；`ms-playwright` 目录含 `chromium-1208/1234` + `chromium_headless_shell-*`；实跑 `sync_playwright → chromium.launch() → screenshot()` 产出 5084 字节 PNG，`browser.version = **145.0.7632.6**`；另有 Chrome 145 / Edge 156 可 `--headless --screenshot --print-to-pdf` | **第 6 条零安装路线**：网页/版式/动效作为渲染介质（Marp/Slidev/reveal.js 的依赖问题因此消失）；`page.pdf()` = 出版级版面出片；WebGL/Canvas = shader 艺术离线截图 | 仅在**解释器 A**（3.13.5）里已装；浏览器版本必须钉入 manifest（不同 build 字体 hinted 像素会变）；GPU 栅格化不可位级复现 → 用 headless_shell / `--disable-gpu` |
| **可变字体（Variable Fonts）已装 + fonttools 已装** | `C:\Windows\Fonts\NotoSansSC-VF.ttf` → `TTFont(...)['fvar'].axes == [('wght', 100.0, 900.0)]`；Noto Serif SC 同为 VF；`fontTools 4.63.0` 可导入 | **字重随时间轴变化的文字动画**（逐帧 `wght` 插值）、字重连续的标题、动态字幕（与 §0.1 的 ASS 汇流）——全部零安装 | 同样只在解释器 A；⚠ **CVE-2025-66034**：`.designspace` 可变成任意文件写 → 只处理自产文件 + 沙箱 |
| **中文/手写体字体已在系统里**（无需下载） | `matplotlib.font_manager` 注册 **353** 族，命中：`Noto Sans SC`/`Noto Serif SC`（**OFL-1.1**）、`Source Sans Pro`（OFL）、`Monoton`、`KaiTi`、`STKaiti`、`STXingkai`（行楷）、`SimHei/SimSun/SimFang/SimYou/SimLi`、`Comic Sans MS`、`Segoe Script`、`Bradley Hand ITC`、`Lucida Handwriting`、`Viner Hand ITC`、`Freestyle Script` | **题款/落款/中文海报/手写感版面**不必先联网下载（之前 S4 登记为"待下载"） | 许可分三档：OFL 可自由嵌入与分发；**Microsoft/华文系（KaiTi、STXingkai、Comic Sans…）是“可用不可转发”——成品像素可用，字体文件本身不可再分发**，逐条 EULA 未经回源核对 → 标 ⚠，商用产出前先核；嵌入位图（渲染成像素）与分发 `.ttf` 是两回事 |
| **matplotlib 已装（但 xkcd 风需要额外字体）** | `matplotlib 3.11.0`；`with plt.xkcd(): ...` 实跑 **渲染成功但刷 72 次 `findfont: Font family 'xkcd'/'xkcd Script'/'Comic Neue' not found`**，退化为默认 sans-serif | 手绘感图表（§5 中的"图表"行）仍可用，但**手绘字形不会自动出现** | 两条出路：①装 Humor Sans / Comic Neue（需下载，本轮未做）；②**自己实现抖动线**（xkcd 风的本质是抖动折线 + 种子化，那是代码的事而不是字体的事）——后者更符合本项目"代码作画"铁律 |

**另外两项与能力相关的事实**（不是媒体能力，但影响开工前提）：

- `vcac` 包**从未 editable 安装**（两个解释器 `pip show vcac` 均为空），测试靠 `pythonpath=["src"]`；
  按 README 快速开始执行前，任何"已装"说法都必须区分解释器。
- 全局 npm 包只有 agent CLI（`claude-code`/`opencode`/`qwen-code`/`dsh`/`@synsci/*`），**没有任何媒体 CLI**；
  所以 §5 里的 `@excalidraw/cli`、§8 里的 Marp/Slidev 仍属于"需 npm 安装"（但浏览器本体已不用装）。

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
| **AI 生成动画** | 文生视频/图生视频（本机有 `ai-video-generation` skill） | ❌ **不入渲染主路径** | 破坏（不可复现） | 版权/判例风险 | 见 `docs/styles.md` §8 四条理由 + 本文件 §12-C |

**诚实判断**：日式 2D 里，代码能可靠接管的是**摄影合成层、背景美术、镜头调度、描边与分层**；
「作画」本身（timing/spacing + 表演）仍是人。**「三渲二」是本项目最现实的高质感路线**——因为它把
不可自动化的作画判断，替换成了可脚本化的渲染+合成规则。

## 8. 图表·版式·地图与出版 · Diagrams, Layout, Maps & Print

> 这一族是**符号驱动媒体**：输入是文本/JSON，输出是版面。它们比绘画族更适合本项目的契约
> （文本即源、天然可 diff、可验收），且**其中四条在本机是零安装**（pandoc+MiKTeX、libass+FFmpeg、
> 浏览器排版器 Playwright/Chromium、可变字体驱动 fonttools——后两条只在**解释器 A**，见 §0.2）。

| 工具 | 版本/状态（2026-11-04） | 本机 | 许可 | Headless/确定性 | 用途定位 | 不适合 | 来源 |
|---|---|---|---|---|---|---|---|
| **pandoc** | **3.8.2.1**（实测） | ✅ | GPL-2 | `pandoc in.md -o out.pdf --pdf-engine=xelatex` 完全 headless、确定性高 | **文本→书/报/讲义/PPTX/DOCX/HTML** 的中枢 | 像素级版面掌控（交给 LaTeX 模板） | ✔实测 |
| **MiKTeX / LaTeX** | 24.4（实测，latex/xelatex 可用） | ✅ | LPPL(包)/MiKTeX 自身 GPL | 编译确定（同包集）；TikZ/PGF 可程序作图 | 出版级排版、学术海报、TikZ 示意图 | 网页风/动态版面 | ✔实测 + README §3 |
| **libass（经 FFmpeg）** | 本机 ffmpeg 8.1.1-full，configuration 含 `--enable-libass`（**实测已确认**） | ✅ | MIT-ish(LGPL 系) | `subtitles=`/`ass=` 滤镜 burn-in（实测两个滤镜均存在）；**ASS 是完整的样式/特效语言**（定位 `\pos`、时间插值 `\t`、裁剪 `\clip`、旋转 `\fr`、karaoke `\k`） | 字幕、卡拉OK、动态字卡、多语本地化 | 从数据生成图表（不是它的职责） | ✔实测 + primary(trac.ffmpeg.org HowToBurnSubtitles) |
| **Vega-Lite + vl-convert-python** | Vega-Lite v5 线；**vl-convert-python 0.6.0**（无依赖、不需浏览器） | ❌ | BSD-3 | JSON spec → SVG/PNG，**声明式语法 = 我们的 spec 哲学同构** | 统计图表、信息图、数据新闻 | 自由构图/插画 | ✔primary(github.com/vega/vl-convert + pypi) |
| **D2（Terrastruct）** | 活跃；**自动布局引擎 TALA 已于 2026-09-07 开源，与 D2 同为 MPL-2.0** | ❌ | MPL-2.0 | **`d2 in.d2 out.svg` 官方 CLI，天生 headless** | 架构/流程/关系图（主题、手绘风、动画 SVG） | 精确坐标摆放（自动布局） | ✔primary(d2lang.com + blog/tala-is-open-source) |
| **Mermaid CLI / PlantUML** | 均活跃（Mermaid 依赖 Chromium/Playwright；PlantUML 依赖 Java+Graphviz） | ❌(但**依赖已在本机**：Playwright+Chromium 145，见 §0.2) | MIT / GPL-3 | `mmdc` / `java -jar plantuml.jar` 可 CI；**Mermaid 输出随 Chromium 版本飘**（本机版本已钉：145.0.7632.6） | 已有文档生态的图（README / GitHub / Notion） | 需要位级复现的产出 | ○secondary，采前钉版本 |
| **浏览器本身作为版面引擎**（Playwright / Chrome·Edge headless） | **本机已实测可用**：playwright 1.58.0 + chromium-1208/1234；`browser.version=145.0.7632.6`；截图产出已得到 | ✅(解释器 A) | Apache-2.0(Playwright) / Google 与 Microsoft 各自的浏览器条款 | HTML/CSS/SVG/Canvas → `page.screenshot()` PNG；`page.pdf()` 出版版面；**必用 headless_shell / `--disable-gpu` 以保证跨硬件可重现** | **网页/海报/deck/信息图作为渲染介质**（包括 WebGL shader 艺术离线截图）；也是 Marp/Slidev/Mermaid 的本地执行底座 | 把“浏览器默认样式”当风格基线（升降版会变像素）——必须把版本号写进 manifest | ✔实测（本轮 `outputs/_probe/pw.png`）+ ✔primary(playwright.dev) |
| **Graphviz** | 活跃（`dot`） | ❌ | EPL/CPL | 布局确定（同版本） | DAG/依赖图、元数据可视化 | 艺术构图 | ✔primary(graphviz.org) |
| **QGIS / `qgis_process`** | QGIS 3.x LTR 线活跃；**官方文档章节「Using processing from the command line」** | ❌ | GPL-2 | **官方 headless 执行器** + PyQGIS layout 导出 PNG/PDF | 地图/地理信息、专题地图、制图 | 无地理数据时的装饰地图 | ✔primary(docs.qgis.org processing/standalone) |
| **GeoPandas / cartopy / contextily** | 均活跃 | ❌ | BSD-3 | 纯 Python + matplotlib 后端→确定 | 程序化地图（数据驱动填色/投影） | 出版级制图美化 | ○secondary，采前回源 |
| **MapLibre GL（静态图）** | 活跃（GL 渲染） | ❌(Node ✅) | BSD-3 | 需无头 GL/快照服务；**位级复现弱**（建议改用 QGIS 或卡片区） | 交互地图、瓦片服务 | 本项目确定性交付（选前者） | ✔primary(maplibre.com) |
| **fonttools（含 varLib）** | **本机实测 4.63.0**（仅解释器 A；项目声明环境 hy_py312 里没有） | ⚠ 部分已装 | MIT | 纯 Python；**可变字体插值生成 = 时间轴可驱动的参数族字体**（本机 `NotoSansSC-VF` 的 `wght 100–900` 已读出） | 字体子集化、动态字体、字标/标题生成、字形轮廓可读写 | 处理不可信 `.designspace`（**CVE-2025-66034 任意文件写**） | ✔primary(fonttools.readthedocs.io varLib) + ✔实测版本号 + ○(CVE 详情二手) |
| **Ghostscript** | **10.06.0** 文档线 | ❌ | **AGPL-3 / 商业双授权** | `gs -dPDFX` 等 CLI 成熟；**PDF/X-1a 只允许 Gray/CMYK/Separation** | 印前：转 PDF/X、分色、子集化、压缩 | 当作免费商用库（AGPL/商业双授权要算清） | ✔primary(ghostscript.com + readthedocs VectorDevices) |
| **press-ready / imposition 工具族** | 社区方案（依赖 Ghostscript） | ❌ | MIT 等 | CLI 可接；页码/出血/标记验收 | 拼版、书籍印张、卡片 | 复杂书脊/自对倒拼版（人工判断） | ○secondary(github vibranthq/press-ready)，标 directional |
| **Marp CLI / Slidev / reveal.js** | 三者均活跃（2026 对比文已采） | ❌(Node ✅，**且 Chromium 本体已在本机**，只缺 npm 包) | MIT | `marp --pdf/--pptx/--image` 一条 CLI 出片；**依赖 Chromium → 版本必须钉死（本机已钉 145.0.7632.6）** | 文本→讲义/汇报/字幕卡（deck 也是媒体） | 位级像素复现 | ○secondary(pkgpulse 对比文) + ✔primary(marp.app) |
| **MuseScore 4（乐谱排版补充）** | 4.x 活跃；**官方 handbook 有 Command line usage 章**（`-o out.pdf` / `-o out.mp3`，含分部导出） | ❌ | GPL-3 | CLI 批量转换确定 | 从 MusicXML/MIDI 出出版谱与试听音频 | 替代 LilyPond 的刻版好味（各自美学） | ✔primary(handbook.musescore.org command-line-usage) |

**为何这一族优先级高**：pandoc/MiKTeX/libass **浏览器版面器** 均已实测存在——**不装任何东西就能开第 6、6.5、7、8 条媒体路线**（文档版面、字幕排版、代码→PDF、HTML/CSS→图与 PDF）。注意后两条只在解释器 A（3.13.5），而 golden 产物产自解释器 B（3.12.13）——开工前先选定环境（§0 第①条）。它们都是典型的“符号规则生成机制”（审计轴 A3），确定性最好验收。

## 9. 捕获重建·沉浸式·实时现场 · Capture, Immersive & Live

> 此族触发两条边界：**（a）输入资产即可信根**（摄影测量需要真实照片，不是代码生成）；
> **（b）轴 A1=实时/一次在场**→ 位级确定性契约不适用，验收要换成“脚本+固定时钟+渲染摘要”。

| 工具 | 版本/状态（2026-11-04） | 本机 | 许可 | Headless/确定性 | 用途定位 | 不适合 | 来源 |
|---|---|---|---|---|---|---|---|
| **COLMAP** | 活跃（官方 changelog 更新至 2026-09）；**BSD-3** | ❌ | BSD-3 | **官方 CLI**（`feature_extractor/mapper/bundle_adjuster`）；确定性好（同输入同版本） | 摄影测量/SfM/MVS：照片→相机轨迹+稠密点云 | 无实拍素材时的建模 | ✔primary(colmap.github.io + GitHub) |
| **OpenMVG / GLOMAP** | OpenMVG 活跃；GLOMAP（2024 ECCV，作者声称开源） | ❌ | MPL-2.0 / 待核 | 多视图几何库，C++/Python | 全局 SfM 对比选项 | 未核许可就商用 | ○secondary(arXiv 2407.20219)，回源 |
| **Meshroom / AliceVision** | 活跃；**MPL-2.0**；支持本地或 farm 执行 | ❌ | MPL-2.0 | 有 CLI/pipeline（节点图=JSON，可程序化） | 一体化摄影测量、HDR 全景、相机跟踪 | 轻量需求（依赖重、CUDA） | ✔primary(alicevision.org + github alicevision/Meshroom) |
| **3D Gaussian Splatting（gsplat / SuperSplat）** | gsplat（nerfstudio，CUDA 光栅化器）；**SuperSplat Editor 3.0（2026-09，PlayCanvas）** | ❌ | Apache/BSD/MIT 系（逐库核） | 训练需 GPU；**渲染为确定输入→输出** | 实景可飞行的 3D 场景资产 | 本项目主路径——**README §3 把“神经渲染”列为排除项** | ✔primary(github nerfstudio/gsplat + cgchannel SuperSplat 3.0) |
| **Hugin + enblend/enfuse** | 活跃；**官方手册「Panorama scripting in a nutshell」就是为非 GUI 环境写的** | ❌ | GPL-2 | `normalize_py/hugin_executor/enblend/enfuse` 脚本链完全 headless | 全景接片、包围曝光融合（**不是生成，是拼合**） | 无素材时 | ✔primary(hugin.sourceforge.io docs) |
| **360/VR180/立体/WebXR** | 格式标称稳定（MMAL/HEVC 立体、WebXR 基线） | ❌ | 各异 | ffmpeg 可出等距柱状投影视频 | 沉浸式交付（需查看设备验收） | 单人可验的确定性（头显依赖） | ○secondary，未逐项回源 |
| **GLSL 离线渲染（glsl-to-mp4 等）** | 社区工具存在（多为 Shadertoy 移植） | ❌ | 各异；**Shadertoy 单件作品各有许可** | **GPU 浮点差异 → 跨硬件不可位级复现**（审计轴 A3/A4） | 噪声/光照/生成纹理、shader 艺术 | 强确定性交付（改用 numpy/CPU 实现） | ○secondary(github nabeel-oz/glsl-to-mp4) |
| **Hydra / TidalCycles / Sonic Pi（live coding）** | Hydra 活跃（JS 视觉合成器）；TidalCycles/Sonic Pi 维护 | ❌(Node ✅) | MIT / GPL-2(待逐项核) | 本质**实时**；headless 录屏可行但时钟不可重现 | 视听表演、现场编码美学 | 可重录的交付物（需改用固定帧序） | ✔primary(hydra.ojack.xyz docs) + ○(ccc 演讲 Headless Hydra 2026) |
| **Tracker 音乐（libopenmpt / OpenMPT / MilTracker / Renoise）** | **本机 ffmpeg 已含 `libopenmpt` 与 `libmodplug` demuxer（实测）**；OpenMPT 开源；Renoise **商业 €76/年** | ✅(解码部分) | LGPL/GPL 系(待逐项核) / 商业 | **`.mod/.xm/.it` → WAV 零安装**（`ffmpeg -i in.xm out.wav`） | chiptune/demoscene 音乐资产 | GUI 作曲体验（需写模块文件或用现成模组） | ✔实测(`-demuxers` 列表) + primary(renoise.com 首页价) |
| **pyroomacoustics / shroom（空间音频）** | pyroomacoustics 活跃；**shroom（Ambisonics 房间声学，arXiv 2026-03）** | ❌ | MIT / 待核 | 纯 Python/NumPy → **完全确定**；我们已有 WAV 地基 | 房间脉冲响应、二耳/Ambisonics 渲染 | 真听音验收（必须人耳） | ✔primary(arXiv 2603.27342 + semanticscholar pyroomacoustics) |
| **数据可听化（MIDITime 等）** | 社区/研究所工具，多个小库存活状态不一 | ❌ | MIT/各异 | 映射规约可写进 spec → 确定 | 把时间序列数据变成声音（与图表路线同构） | 当音乐成品交付（工具链偏研究） | ○secondary(revealnews/MIDITime)，采前回源 |

**诚实判断**：本族的“代码可控部分”是**相机轨迹、拼合、声学几何、映射规则**；“不可控部分”是**实拍素材、GPU/驱动、现场时钟**。引入它们时，manifest 必须额外记录输入素材哈希与设备指纹，否则不得称“可复现”。

## 10. 实物输出 · Physical Output（印前/增材/减材/织物）

> 轴 A4 上的另一整个输出面：**屏幕像素 → 纸/物/线**。它们的验收不是 ΔE 或 LUFS，而是
> DPI、出血、墨量、最小曲率半径、可打印性、针数——完全可写成 spec。

| 通道 | 工具 | 版本/状态（2026-11-04） | 许可 | Headless | 来源 |
|---|---|---|---|---|---|
| 笔绘 | **vsketch / vpype** | 活跃（见 styles.md §5） | MIT | `svg` 导出即可绘；无需硬件 | ✔primary(GitHub) |
| 印前 | **Ghostscript / press-ready / ICC 工具链** | 见 §8（含 PDF/X-1a 色彩空间限制） | AGPL/商业双授 | CLI | ✔primary(ghostscript docs) |
| 增材(3D 印) | **PrusaSlicer** | 活跃（含 binary G-code 演进）；**官方口号 Free & Open-source, no account**；AGPL 维权案例公开（BambuStudio 分叉侵权指控） | **AGPL-3** | **`prusa-slicer --load --export-gcode` CLI 成熟** | ✔primary(prusa3d.com/p/prusaslicer + GitHub + 创始人 X 帖) |
| 激光/雕刻 | **LaserGRBL**（免费开源，Win only）/ **LightBurn**（**$60 GCode 档 / $120 DSP 档**） | 均活跃 | GPL(待逐项核) / 商业 | 图像→GRBL 取决于工具；开源侧可脚本 | ○secondary(lasergrbl.com + craftgineer 对比文 2026-03) |
| 织物/图案 | **十字绣→提花转换**（Katze-Schwarz/CrossStitchApp、arahne.si 教程）；DMC 色板映射 | 社区工具 | 各异 | **网格=矩阵，与代码同构**（提花卡是程序化的祖先） | ✔primary(GitHub + arahne.si) |
| 减材(CNC) | **FreeCAD（`freecadcmd` + Path 工作台）/ LinuxCNC** | 活跃（本轮未逐项回源）⚠ | LGPL-2 / GPL | 参数建模 CLI 存在，但 Path 后处理链需自接 | ⚠unverified，下轮回源 |

> **本项目定位**：实物输出停在「**可审计的设计文件**」（SVG 刀线、STL、G-code、针数图、拼版 PDF）；
> 机床/印房/织机的执行与质检属于人（机器观察、人裁决）。即使无硬件，这些文件也是合法产出物。

## 11. 游戏与互动 · Games & Interactive

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

## 12. 开发模式与工程编排 · Development Modes

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

## 13. 采纳队列建议 · Onboarding Queue（供后续任务确认，非本次执行）

按 README 里程碑倒推的最小集（安装动作均属可逆本地操作，仍待你发话再装）：

| 序 | 动作 | 支撑里程碑 |
|---|---|---|
| 1 | `pip install scikit-image hypothesis`（+ jsonschema：解释器 A 已有 4.26.0，**hy_py312 需补装**；matplotlib **已在 A 装好 3.11.0**，不必再装） | P0/P1 + L0 测试 |
| 2 | `pip install manim moviepy imageio[ffmpeg]` | P3 视频线（复用本机 MiKTeX/FFmpeg） |
| 3 | `pip install music21 scamp soundfile mido midiutil` + winget 装 **FluidSynth + 一个 GM SoundFont** | P2 音频线 |
| 4 | `winget install Blender.Blender`（5.2 LTS） | P4 三维 |
| 5 | `pip install pygame-ce` + `npm i phaser`（Node ✅ 已在） | P5 游戏第一闭环（Neon Dodger） |
| 6 | （音频排版按需）LilyPond 2.26 winget/choco | 出版级乐谱时才装 |
| 7 | （观察）Revideo vs Motion Canvas 二选一后再装 | 服务端渲染需求出现时 |
| 8 | **零安装先走版面线**：pandoc + MiKTeX（✅已装）开文档/PDF 路线；libass burn-in 开字幕排版路线 | P0 版面与字幕（§8） |
| 9 | `pip install vl-convert-python`（图表语法；**fonttools 已在 A 装好 4.63.0，可变字体路线零安装可开**，但 designspace 只处自产） | 图表/字体工程（§8） |
| 10 | winget 装 **Ghostscript**（PDF/X 印前）；`npm i @marp-team/marp-cli @excalidraw/excalidraw` | 印张交付、讲义（§8） |
| 11 | （重、逐项批准）**D2 CLI / QGIS**；**COLMAP**（需实拍素材）；**PrusaSlicer**（需打印机才有意义） | 地图/捕获/实物（§9、§10） |
| 12 | **零安装**：用已有 playwright+Chromium 145 开 **HTML/CSS→PNG/PDF 版面路线**（也可先 `pip install playwright` 到 hy_py312 以统一环境） | P0 版面/deck/海报（§0.2、§8） |

## 14. 代谢 · Metabolism

- **复测触发**：每轮实质任务前跑 `scripts/doctor.py`（本机面）；**且两个解释器都要跑**（本轮发现它们能力集不同，见 §0 第①条）；每季度或里程碑切换时复采 §1–§11 版本列（网络面），旧数据不删除、就地标注 `superseded-by: <date>`。
- **不一致登记**：Tiled 版本号双源不一致、"FFmpeg 9.0" 传闻、Bevy 疑似 ≥0.19、Phaser 4 许可条款、Krita 5.3.2/6.0.2 双线当前版本计数、USD 精确版本号——六项列入下一轮回源清单。**本轮新增第七项（也是最重要一项）：本机双解释器能力集不一致 + `vcac` 从未 editable 安装 + golden 产物产自 3.12.13 而今天默认 `python` 是 3.13.5。**
- **本轮新增未核（§5–§7）**：`roughjs` 版本与维护状态、Toon Boom/TVPaint/Clip Studio 版本号、EbSynth 许可条款、Mixamo 上传素材权利、Harmony 脚本层可用性。⚠️ 已在本文件纠正的记忆错误（`shader-to-ruby` 未命中、Zoo Tools 非 Weta 开源）记于 `docs/styles.md` §17。
- **穷尽性审计新增未核（§8–§10）**：Mermaid/PlantUML 当前版本、QGIS LTR 具体号、GeoPandas/cartopy 版本、OpenMPT/MilTracker/libopenmpt 许可逐项、Hydra/Tidal 许可、FreeCAD Path 可用性、LightBurn/LaserGRBL 条款、MagicaVoxel 许可口径、Dehancer/Postshot 条款、**Microsoft/华文系字体逐条 EULA（本轮新列）**——详见 `docs/coverage-audit.md` §4 第 7 项。**审计结论：未穷尽，且已列出不可补的残余边界（现场在场/多通道感知）。**
- **本轮已把以下项从“未核/待装”改判为“实测已得”**（记入 §0.2，不再列入未核清单）：fonttools **4.63.0**、matplotlib **3.11.0**、playwright **1.58.0** + Chromium **145.0.7632.6**（已实跑出 PNG）、pypdf 6.19.0、nbconvert 7.17.1、`pillow-avif-plugin` 1.5.5、MiKTeX `pdflatex 4.19`/`lualatex`/`latexmk`、Noto Sans/Serif SC **可变字体 wght 100–900**。
- **回流工厂**：本表的列格式即 `<HF>/reference/tool-router.md` §4 "开新表模板" 的一次实例化；通用化模式（"代码驱动媒体生态盘点表"）可按 `capability-flow.md` 提案回流 `<HF>/updates/`（只提案，不直改 data|core）。
- **SSOT**：本文件为本仓库工具事实的唯一来源；README §3 是能力池愿景，版本实况只认本文件。
