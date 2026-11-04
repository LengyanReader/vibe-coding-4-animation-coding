# 画法与风格模拟盘点 · Painterly Styles & Art-Technique Simulation

> 与 `docs/tools.md`（工具生态）平行的第二张地图：tools.md 回答「有哪些工具能跑」，
> 本文回答「**某种画法能否被代码复现，以及用什么技术路线**」。
> 触发问题：能否做一幅中国古代山水画？当代插画？梦工厂/迪士尼级 3D？日式 2D？
> 结论先行：**能做的程度差异极大，且瓶颈不在软件，在于「画理能否被形式化」与「资产工时」**。
> 检索日期 2026-11-04；✔primary=官方/一手，○secondary=二手，⚠unverified=未回源。

---

## 0. 三档天花板（先给诚实判断）

| 目标 | 可达程度 | 真正的瓶颈 | 本项目定位 |
|---|---|---|---|
| **中国水墨/山水、浮世绘、版画、Riso、扁平插画、像素、线稿** | **高**：技法本身是分层、可枚举的程序 | 把画理写成约束（而非调滤镜） | ✅ 主战场，零/轻安装 |
| **日式 2D 动画（赛璐璐/2.5D）** | **中高**：3D 渲染 + 描边 + 分层合成是业界成熟做法 | 角色资产与作画监督的人工判断 | ⚠ 需 Blender（重安装） |
| **迪士尼/皮克斯/梦工厂级 3D 长片** | **中**：开源工业栈齐备（USD/MoonRay/Cycles/Houdini），短片可达高质量档 | **不是工具问题**：模型、绑定、灯光、表演的艺术工时以人年计 | ⚠ 只做「程序化镜头/短片」，不承诺长片质感 |
| **AI 风格模仿（Ghibli 风、名画风）** | 技术上容易 | 非确定性 + 版权/风格诉讼风险（见 §8） | ❌ 不入渲染主路径 |

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
   渲染主路径保持"代码作画"。

---

## 9. 采纳队列（风格族，需你逐项批准）

| 步骤 | 安装 | 解锁 | 风险 |
|---|---|---|---|
| S1 | **无**（Pillow+NumPy+SciPy+cv2 已装） | XDoG/素描提取、Curtis 水彩复现、水墨分层链、Riso 分色、像素量化 | 无 |
| S2 | `pip install vsketch vpype` | 笔绘仪线稿 / SVG 矢量资产 | 轻 |
| S3 | `pip install matplotlib` | `xkcd()` 手绘图表 + 数据可视化 | 轻 |
| S4 | 下载 OFL 中文字体（志莽行书/思源） | 题款、印章文字、中文海报 | 无（许可干净） |
| S5 | `pip install scikit-image` | `difference_of_gaussians` 等 NPR 滤镜全家桶 | 轻 |
| S6 | Met Open Access API 拉取参考集 | 真实古画的构图/明度统计（CC0，可安全入管线） | 无 |
| S7 | Blender 5.2 LTS | 3D 镜头、Grease Pencil 2.5D、Freestyle 描边 | 重（外部安装，非 pip） |
| S8 | Houdini Apprentice / Indie | 程序化 FX（烟/火/破坏/群集） | 重 + 许可限制（水印/营收上限） |
| S9 | **无**（本机已有 Node ✅） | `@excalidraw/cli`（官方，手绘风图示，agent 写 JSON→PNG/SVG）——已登记 `docs/tools.md` §5 | 轻（npm 包） |

---

## 10. 代谢 · 本轮未核与待办

- ⚠ **未核**：故宫名画记授权条款；Toon Boom/TVPaint 当前版本号；`roughjs` 精确版本与维护状态；
  `shader-to-ruby`（本轮检索未直接命中仓库，勿引用）；Wired Elements 活跃度；aiSKETCH 许可。
- ❌ **纠正记忆**：`Zoo Tools`（ZigZag/Bolt/Matter）是 **Create3DCharacters 的商业套件**，
  我没有找到"Weta 开源 Zoo Tools"的一手证据——不写入采纳队列。Weta 的开放贡献以 **OpenEXR**（ASWF）为凭。
- 待补：manifest 增加 `fonts`（许可证+来源+哈希）与 `style_refs`（参考作品 ID + 授权）字段。
- 待办：把 §1.2 的山水分层链做成 `ink-landscape` 样例路线——已登记为
  `docs/roadmap-development.md` §4 近环队列 **第 2 轮**（零安装），仍是本文件唯一"下一步就该写代码"的项，
  等你发话再开工。
- 交叉引用已建立：本文回答"画法能否形式化"；工具事实（版本/许可/headless）只认 `docs/tools.md`（§5–§7 已补齐手绘 2D、影视 3D、日式 2D/2.5D 三族）。
