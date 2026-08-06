"""校准 shoot_ang 欧拉角 -> 方向向量的约定（pitch/yaw 符号 4 变体）"""
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

def fwd_from_euler(pitch, yaw, psign=1, ysign=1):
    pr, yr = math.radians(pitch), math.radians(ysign * yaw)
    return np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), psign * math.sin(pr)])

targets, shoots = [], []
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
    targets.append(to_v / n)
    shoots.append((r["shoot_ang_x"], r["shoot_ang_y"]))

T = np.array(targets)
print(f"样本: {len(T)}")
for name, ps, ys in [("标准 z=-sin, y=+", 1, 1), ("pitch反 z=+sin", -1, 1),
                     ("yaw反", 1, -1), ("两者都反", -1, -1)]:
    errs = []
    for (p, y), tv in zip(shoots, T):
        fv = fwd_from_euler(p, y, ps, ys)
        errs.append(math.degrees(math.acos(np.clip(np.dot(fv, tv), -1, 1))))
    e = np.array(errs)
    print(f"{name}: 中位 {np.median(e):.1f}° | ≤5°: {(e<=5).mean()*100:.0f}% | ≤15°: {(e<=15).mean()*100:.0f}%")
