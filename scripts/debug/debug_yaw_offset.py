"""扫描 yaw 偏移：shoot_ang 与位置坐标系间的固定旋转"""
from demoparser2 import DemoParser
import numpy as np, pandas as pd, math

PATH = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\de1.dem"
PX = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX"
PY = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecY"
PZ = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecZ"

p = DemoParser(PATH)
df = p.parse_ticks([PX, PY, PZ])
df = df.rename(columns={PX: "x", PY: "y", PZ: "z"})
df["key"] = df["steamid"].astype(str) + "_" + df["tick"].astype(str)
k2i = {k: i for i, k in enumerate(df["key"])}
bd = p.parse_event("bullet_damage")

rows = []
for _, r in bd.iterrows():
    try:
        aid, vid, t = int(r["attacker_steamid"]), int(r["victim_steamid"]), r["tick"]
    except (TypeError, ValueError):
        continue
    try:
        a = df.iloc[k2i[f"{aid}_{t}"]]
        v = df.iloc[k2i[f"{vid}_{t}"]]
    except (KeyError, TypeError):
        continue
    to_v = np.array([v["x"] - a["x"], v["y"] - a["y"], v["z"] + 40 - a["z"] - 64])
    n = np.linalg.norm(to_v)
    if n < 10:
        continue
    rows.append((r["shoot_ang_x"], r["shoot_ang_y"], to_v / n))

print(f"样本: {len(rows)}")
best = None
for off in range(-180, 181, 5):
    errs = []
    for p_, y_, tv in rows:
        pr, yr = math.radians(p_), math.radians(y_ + off)
        fv = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), math.sin(pr)])
        errs.append(math.degrees(math.acos(np.clip(np.dot(fv, tv), -1, 1))))
    e = np.array(errs)
    med = np.median(e)
    if best is None or med < best[1]:
        best = (off, med, (e <= 5).mean() * 100)
print(f"最优 yaw 偏移: {best[0]}° -> 中位 {best[1]:.1f}°, ≤5°: {best[2]:.0f}%")

# 细扫最优附近
if best:
    for off in range(best[0] - 5, best[0] + 6):
        errs = []
        for p_, y_, tv in rows:
            pr, yr = math.radians(p_), math.radians(y_ + off)
            fv = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), math.sin(pr)])
            errs.append(math.degrees(math.acos(np.clip(np.dot(fv, tv), -1, 1))))
        e = np.array(errs)
        print(f"  off={off}: 中位 {np.median(e):.1f}° ≤5°: {(e<=5).mean()*100:.0f}%")
