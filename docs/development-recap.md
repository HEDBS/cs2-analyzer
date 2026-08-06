# CS2Analyzer 开发复盘：壁垒与解决记录

> 从零到 GitHub 的完整技术旅程。记录每个壁垒、排查思路、最终结论，供日后回顾与扩展参考。
> 日期：2026-08 | 状态：v0.1 可用（A 版）

---

## 一、方向选择：最大的决策壁垒

**初始想法**：做 CS2 录屏软件——环形缓冲缓存 + 击杀事件触发自动保存（ShadowPlay/Outplayed 模式）。

**壁垒分析**（为什么放弃）：
| 方案 | 问题 |
|---|---|
| 官方匹配实时击杀事件 | **没有任何官方 API**。GSI 只给状态快照无事件流；logaddress 服务器日志仅自建房/社区服可用 |
| 读游戏内存 | VAC 封号红线，不可碰 |
| 图像识别 kill feed | 有误判、穿烟/穿墙细分条件识别难、性能开销 |
| 驱动级捕获 | ShadowPlay 结构性特权，第三方永远追不上 |

**转折**：发现 **CS2 demo 文件包含一切**——每 tick 位置/视角/速度（可差分）、每次开枪/命中/击杀事件、**穿墙/穿烟/爆头直接给字段**。零风险（不碰进程）、100% 精确、无实时压力。
**结论**：录屏赛道是红海且被大厂压制；练枪/对局分析细分市场空白，demo 解析是唯一干净路线。

---

## 二、数据层壁垒（逐个攻破）

### 2.1 demo 文件在哪
**坑**：CS2 demo 不在 Steam userdata 里（那里只有 cfg），在游戏安装目录：
`<Steam库>\steamapps\common\Counter-Strike Global Offensive\game\csgo\*.dem`
（本机 `E:\SteamLibrary\...`，库路径查 `steamapps\libraryfolders.vdf`）

### 2.2 demoparser2 API 变化
新版（0.12+）方法名改了：`parse_header()`（旧 `header()` 会 AttributeError）、`list_game_events()`、`list_updated_fields()`。**先 `dir(DemoParser)` 再写代码**。

### 2.3 CS2 字段名完全重构（最大数据坑）
CS2 新实体系统，CS:GO 时代的字段全废：
- `CCSPlayerPawn.origin` → **全是 None，永远别用**（140 万行 100% 空）
- 位置在：`CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX/Y/Z`（三个独立列）
- 视角：`CCSPlayerPawn.m_angEyeAngles`（[pitch, yaw, roll] 向量列）
- 生命：`CCSPlayerPawn.m_iHealth`
- **速度字段不存在** → 必须位置差分：`速度 = 位置差 / (1/64s)`

**方法论**：字段名变化时用 `list_updated_fields()` 全量拉出来，按关键字（origin/veloc/eye/health/BodyComponent）过滤探测，别猜。

### 2.4 steamid 类型不匹配（join 全失败的元凶）
事件表 `attacker_steamid` 是 **str**，tick 表 `steamid` 是 **uint64**。直接 `==` 比较永远 False（0/168 join 成功）。
**修复**：`int(steamid)` 统一转类型。排查过程：先怀疑 key 重复→验证无重复→打印原始数据才发现 dtype 差异。

### 2.5 向量字段 None
死亡后玩家的位置/视角为 None，`pd.DataFrame(col.tolist())` 直接崩。
**修复**：`col.apply(lambda v: v if isinstance(v,list) and len(v)==3 else [0,0,0])` 兜底。

### 2.6 5E 平台 demo 缺事件（数据源差异）
**实测**：`bullet_damage`/`player_bullet_hit` 在 5E 平台 demo 返回**空 list**，GOTV/官方 demo 才有。
**修复**：自动检测 `isinstance(bd, pd.DataFrame) and len(bd)>0`，回退 `player_hurt` 做命中分析。
**连带坑**：player_hurt 字段名不同（受害者是 `user_name` 不是 `victim_name`）、无 `distance`（用位置算）、含火焰/雷/刀伤害（命中率分析前必须过滤 weapon: `inferno|hegrenade|molotov|knife|...`）。

---

## 三、定位角度分析：一次完整的技术侦查（重点案例）

**目标**：算出"命中时准星与目标的偏差角"（定位质量的核心指标）。

**第 1 轮**：用 tick 表视角（`m_angEyeAngles`）算 → 命中偏差中位 **98.6°**。命中了准星必然在目标上，这数据明显错。

**第 2 轮**：怀疑 view_dir 公式（pitch/yaw → 方向向量）的 yaw 约定 → 4 种符号变体全测 → 全 ~90°，排除。

**第 3 轮**：怀疑 victim 位置 → 打印原始数据，发现"站桩玩家视角微动但位置冻结 0.6 秒"的异常案例 → 但位置整体每 tick 精确（验证过），排除低频快照假设。

**第 4 轮**：换用 `bullet_damage.shoot_ang`（服务器记录的开枪角度）→ 直接当向量用得到 64% ≤2° "完美结果" → **后来发现是 clip bug**（shoot 没归一化，长度>1 全被 clip 成 0°）——数值巧合，虚惊一场。

**第 5 轮**：确认 shoot_ang 是**欧拉角 (pitch, yaw, roll)** 不是方向向量 → 转方向后重测，4 种符号组合 × 4 种目标高度（按 hitgroup 修正）全 ~52°。

**第 6 轮**：扫描 360° yaw 偏移（固定旋转假设）→ 无改善（最优 -15° 仍是 50°）。**结论定案**：`shoot_ang` 的语义/坐标系与 tick 表位置不匹配（可能含后坐力或独立参考系），**逐发角度偏差在现有数据下不可计算**。

**最终决策**：放弃逐发角度，改用**事件级定位代理指标**（全部可靠）：
- 命中率分桶（静止 vs 移动开枪）
- 命中部位分布（head 占比）
- 交战距离分布
- 爆头率（按武器）

**方法论提炼**：
1. 数据异常先验证**数据本身**（打印原始行），别急着改公式
2. 数值"完美结果"要检查**归一化**（clip 会把 bug 藏起来）
3. 假设要能**证伪**：每种假设（符号/旋转/高度）都要有对应实验
4. 时间盒：6 轮调试无果就换指标，产品价值优先于技术执念

---

## 四、环境与工程壁垒

| 壁垒 | 解决 |
|---|---|
| Python 3.14 装 demoparser2 | 有预编译 wheel，直接可装（新版库对新技术栈友好） |
| PowerShell 5.1 编码 | UTF-8 中文 .ps1 被按 ANSI 读 → 乱码破坏引号。**验证脚本全英文** |
| winget 不存在 | gh CLI 装不了 → 下载 zip 又被墙 |
| GitHub 下载被墙（api 通、release 不通） | 本地代理未开 → 放弃下载 |
| **最终方案** | SSH 走 443 端口（已配置 `ssh.github.com`）+ **网页手动建空仓库** + `git push`——最干净，不需要 gh/token/代理 |

---

## 五、数据可靠性分层（结论沉淀）

| 数据 | 可靠性 | 说明 |
|---|---|---|
| 位置（m_vecX/Y/Z） | ✅ 高 | 每 tick 精确更新（跑步≈2.9u/tick 平滑） |
| 速度（位置差分） | ✅ 高 | 移动/静止判定可靠，精确值有轻微低估 |
| 事件流（fire/hurt/death） | ✅ 高 | 官方记录，含穿墙/穿烟/爆头字段 |
| 视角（m_angEyeAngles） | ⚠️ 中 | 部分案例与位置不自洽（滞后/低精度快照）；**相邻差值（拉枪）可用** |
| shoot_ang（开枪角度） | ❌ 低 | 欧拉角，与位置坐标系不匹配，逐发角度不可算 |
| 5E demo 的 bullet_damage | ❌ 缺失 | 自动回退 player_hurt |

---

## 六、产品定位复盘（为什么值得做）

- 商业判断：通用录屏 = 红海死路（ShadowPlay/Medal/Outplayed 压制）；练枪分析 = 空白细分，但天花板有限（决策>枪法、平台自带复盘、无社区基准）
- 正确定位：**训练反馈闭环工具**（练前测→练→练后测，数据验证训练有没有效）+ 简历级技术项目
- 已验证的价值：6 秒出全量报告（337MB demo）、穿墙/穿烟自动标注、急停质量量化
- 下一步（如果继续）：HTML 报告（B 版）→ 练枪 demo 验证 BOT 数据 → 训练前后对比功能

---

## 七、复用清单（下次直接抄）

- `scripts/analyze_full.py`：主分析管线（字段/索引/事件 join 全在里面）
- `scripts/plot_report.py`：可视化模板
- `docs/cs2-fields-and-pitfalls.md`：字段与坑速查
- skill `cs2-demo-analysis`（Hermes 侧）：同内容机器可读版
- 录 demo：控制台 `record 名字` / `stop`，文件在游戏目录 csgo\ 下
