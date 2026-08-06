"""验证 tick 表位置更新频率：活跃玩家 100 tick 的位置变化模式"""
from demoparser2 import DemoParser
import numpy as np, pandas as pd

PATH = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\de1.dem"
PX = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX"
PY = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecY"
PZ = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecZ"

p = DemoParser(PATH)
df = p.parse_ticks([PX, PY, PZ])
df = df.rename(columns={PX: "x", PY: "y", PZ: "z"})
df = df.sort_values(["steamid", "tick"])

# 找一个移动活跃的玩家片段：位置总变化最大的连续 200 tick
stats = []
for sid, g in df.groupby("steamid"):
    g = g.sort_values("tick")
    g["dx"] = g["x"].diff()
    g["dy"] = g["y"].diff()
    g["dist"] = np.sqrt(g["dx"] ** 2 + g["dy"] ** 2)
    stats.append((sid, g["dist"].sum()))
stats.sort(key=lambda x: -x[1])
sid = stats[0][0]
g = df[df["steamid"] == sid].sort_values("tick").head(400)
g = g.copy()
g["dx"] = g["x"].diff()
g["dy"] = g["y"].diff()
g["dist"] = np.sqrt(g["dx"] ** 2 + g["dy"] ** 2)
print(f"最活跃玩家 steamid={sid}")
print(f"前 400 tick 位移总量: {g['dist'].sum():.0f} units")
nonzero = g[g["dist"] > 0.5]
print(f"位移>0.5u 的 tick 数: {len(nonzero)} / {len(g)}")
if len(nonzero) > 3:
    gaps = np.diff(nonzero.index)
    print(f"相邻变化 tick 间隔: 中位 {np.median(gaps):.0f}, 最大 {gaps.max():.0f}")
    print(f"单 tick 最大位移: {g['dist'].max():.1f} u (跑步≈4u/tick @64tick, 急停=0)")
# 采样打印
print(g[["tick", "x", "y", "dist"]].head(20).to_string(index=False))
