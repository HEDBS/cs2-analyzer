# CS2Analyzer — CS2 对局数据分析工具

基于官方 demo 文件解析的 **Counter-Strike 2 对局/练枪数据分析工具**。
零风险（不碰游戏进程）、100% 精确（官方数据）、无实时性压力（练完 6 秒出报告）。

## 功能

对任意 CS2 demo（`.dem`）输出完整对局分析：

| 维度 | 指标 |
|---|---|
| **急停** | 每击杀瞬间的开枪速度：静止击杀占比（急停成功）vs 移动中开枪占比（急停失败） |
| **命中率** | 总命中率 + **静止 vs 移动分桶命中率**（急停价值的直接证据） |
| **拉枪** | 相邻开枪的视角变化：平均/中位/大角度拉枪占比 |
| **命中部位** | head/chest/stomach 分布（瞄头还是瞄身体） |
| **交战距离** | 平均/中位距离、远距离与贴脸占比 |
| **效率** | ADR（每回合均伤）、爆头率（按武器）、穿墙/穿烟击杀 |
| **数据导出** | 每枪 / 每次命中 / 每击杀 三张 CSV，可二次分析 |

## 快速开始

```powershell
# 安装依赖（Python 3.10+）
pip install -r requirements.txt

# 分析任意 demo
python scripts\analyze_full.py <demo路径> [输出目录]

# 快速击杀+急停分析
python scripts\analyze_kills.py <demo路径>
```

输出示例（5E de_dust2 对局，46 回合）：
```
[命中率] 总 16.7% (821/4915)
  静止(≤30u/s): 2672 枪 | 命中 470 → 17.6% 命中率
  移动(>30u/s): 2243 枪 | 命中 351 → 15.6% 命中率
[急停] 静止击杀(≤10u/s): 150 (63%) | 移动开枪(>100u/s): 26 (11%)
[拉枪] 平均 16.9° | 中位 1.9° | >30°: 17% | >60°: 11%
[命中部位] head:130 (16%) | chest:335, stomach:137
[击杀] 爆头率 45% | 穿墙 6 | 穿烟 11 | AK 爆头率 60%
```

## 录 demo 方法

游戏内控制台（~）：
```
record 名字    # 开始录制（练枪图 / 比赛都行）
stop          # 停止
```

demo 默认生成在 `Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo\`，复制到 `demos\` 文件夹即可（demo 不入库，git 已忽略）。

## 目录结构

```
CS2Analyzer/
├── demos/          # 放 .dem 文件（不入库）
├── output/         # 分析结果 CSV（不入库）
├── scripts/
│   ├── analyze_full.py    # 全量分析（主入口）
│   ├── analyze_kills.py   # 击杀+急停快速分析
│   ├── probe_demo.py      # 字段探测（验证任意 demo 能读出什么）
│   └── debug/             # 数据质量校准脚本（shoot_ang 坐标系验证等）
└── docs/
    └── cs2-fields-and-pitfalls.md  # 字段清单与踩坑记录
```

## 技术要点（全部实测）

- 数据源：`demoparser2`（Rust 核心，337MB demo 全量解析约 6 秒）
- 位置字段：`CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX/Y/Z`（每 tick 精确更新）
- 视角字段：`CCSPlayerPawn.m_angEyeAngles`
- 速度：demo 无速度字段，用位置差分（64 tick 精度足够）
- 穿墙/穿烟/爆头：`player_death` 事件直接给 `penetrated` / `thrusmoke` / `headshot` 字段
- 详细字段清单见 `docs/cs2-fields-and-pitfalls.md`

## 已知限制（实测结论）

1. **逐发"准星-目标偏差角"不可用**：`bullet_damage.shoot_ang` 为欧拉角，与 tick 表位置坐标系不匹配（实测中位 52° 噪声，符号/旋转扫描均无法修正）。定位质量改用事件级代理：命中率分桶、命中部位、距离分布。
2. **5E 平台 demo 缺少 `bullet_damage`/`player_bullet_hit` 事件**（GOTV/官方 demo 有），脚本已自动回退到 `player_hurt`。
3. `m_angEyeAngles` 在部分场景为低精度快照（部分玩家视角与位置不自洽），拉枪距离（相邻视角差）不受影响。

## License

MIT
