"""验证：用 player_hurt 校准——伤害瞬间 attacker 视角 vs victim 位置方向"""
from demoparser2 import DemoParser
import numpy as np, pandas as pd, math

PATH = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\de1.dem"
PX = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX"
PY = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecY"
PZ = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecZ"

p = DemoParser(PATH)
df = p.parse_ticks([PX, PY, PZ, "CCSPlayerPawn.m_angEyeAngles"])
df = df.rename(columns={PX: "x", PY: "y", PZ: "z"})
ang = df["CCSPlayerPawn.m_angEyeAngles"].apply(
    lambda v: v if isinstance(v, list) and len(v) == 3 else [0.0, 0.0, 0.0])
ang = pd.DataFrame(ang.tolist(), columns=["pitch", "yaw", "roll"])
df = pd.concat([df.drop(columns=["CCSPlayerPawn.m_angEyeAngles"]), ang], axis=1)
df["key"] = df["steamid"].astype(str) + "_" + df["tick"].astype(str)
k2i = {k: i for i, k in enumerate(df["key"])}

hurt = p.parse_event("player_hurt")
gun = hurt[~hurt["weapon"].str.contains("inferno|hegrenade|molotov|knife|flashbang|smoke|decoy", na=False)]

def view_dir(p, y):
    pr, yr = math.radians(p), math.radians(y)
    return np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), -math.sin(pr)])

errs = []
rows = 0
for _, r in gun.iterrows():
    try:
        aid, vid, t = int(r["attacker_steamid"]), int(r["user_steamid"]), r["tick"]
    except (TypeError, ValueError):
        continue
    try:
        a = df.iloc[k2i[f"{aid}_{t-1}"]]
        v = df.iloc[k2i[f"{vid}_{t-1}"]]
    except (KeyError, TypeError):
        continue
    to_v = np.array([v["x"] - a["x"], v["y"] - a["y"], v["z"] + 40 - a["z"] - 64])
    n = np.linalg.norm(to_v)
    if n < 10:  # 太近（刀/贴脸）跳过
        continue
    fwd = view_dir(a["pitch"], a["yaw"])
    c = np.clip(np.dot(fwd, to_v) / n, -1, 1)
    errs.append(math.degrees(math.acos(c)))
    rows += 1

e = np.array(errs)
print(f"枪械伤害样本: {len(gun)} (过滤后计算 {rows})")
print(f"命中时准星偏差: 中位 {np.median(e):.1f}° | 均值 {e.mean():.1f}°")
print(f"≤5°: {(e<=5).mean()*100:.0f}% | ≤15°: {(e<=15).mean()*100:.0f}% | ≤30°: {(e<=30).mean()*100:.0f}%")
