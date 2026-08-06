"""用 bullet_damage 的 shoot_ang（服务器记录的真实射击方向）验证定位偏差算法"""
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
print(f"bullet_damage: {len(bd)} 条")

errs, rows = [], 0
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
    shoot = np.array([r["shoot_ang_x"], r["shoot_ang_y"], r["shoot_ang_z"]])
    to_v = np.array([v["x"] - a["x"], v["y"] - a["y"], v["z"] + 40 - a["z"] - 64])
    n = np.linalg.norm(to_v)
    if n < 10:
        continue
    c = np.clip(np.dot(shoot, to_v) / n, -1, 1)
    errs.append(math.degrees(math.acos(c)))
    rows += 1

e = np.array(errs)
print(f"有效样本: {rows}")
print(f"定位偏差(用 shoot_ang): 中位 {np.median(e):.1f}° | 均值 {e.mean():.1f}°")
print(f"≤2°: {(e<=2).mean()*100:.0f}% | ≤5°: {(e<=5).mean()*100:.0f}% | ≤15°: {(e<=15).mean()*100:.0f}%")

# 对照：同一批子弹用 tick 表视角（t 时刻）算
df2 = p.parse_ticks([PX, PY, PZ, "CCSPlayerPawn.m_angEyeAngles"])
df2 = df2.rename(columns={PX: "x", PY: "y", PZ: "z"})
ang = df2["CCSPlayerPawn.m_angEyeAngles"].apply(
    lambda v: v if isinstance(v, list) and len(v) == 3 else [0.0, 0.0, 0.0])
ang = pd.DataFrame(ang.tolist(), columns=["pitch", "yaw", "roll"])
df2 = pd.concat([df2.drop(columns=["CCSPlayerPawn.m_angEyeAngles"]), ang], axis=1)
df2["key"] = df2["steamid"].astype(str) + "_" + df2["tick"].astype(str)
k2i2 = {k: i for i, k in enumerate(df2["key"])}

def view_dir(p, y):
    pr, yr = math.radians(p), math.radians(y)
    return np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), -math.sin(pr)])

errs2 = []
for _, r in bd.iterrows():
    try:
        aid, vid, t = int(r["attacker_steamid"]), int(r["victim_steamid"]), r["tick"]
    except (TypeError, ValueError):
        continue
    try:
        a = df2.iloc[k2i2[f"{aid}_{t}"]]
        v = df2.iloc[k2i2[f"{vid}_{t}"]]
    except (KeyError, TypeError):
        continue
    to_v = np.array([v["x"] - a["x"], v["y"] - a["y"], v["z"] + 40 - a["z"] - 64])
    n = np.linalg.norm(to_v)
    if n < 10:
        continue
    fwd = view_dir(a["pitch"], a["yaw"])
    c = np.clip(np.dot(fwd, to_v) / n, -1, 1)
    errs2.append(math.degrees(math.acos(c)))
e2 = np.array(errs2)
print(f"\n对照(tick表视角): 中位 {np.median(e2):.1f}° | ≤5°: {(e2<=5).mean()*100:.0f}% | ≤15°: {(e2<=15).mean()*100:.0f}%")
