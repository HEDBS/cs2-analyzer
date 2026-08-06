"""调试：打印 10 条枪械伤害的视角/位置原始数据"""
from demoparser2 import DemoParser
import numpy as np, pandas as pd, math

PATH = r"E:\CS2Analyzer\demos\g151-n-20260806005120942754354_de_dust2.dem"
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

cnt = 0
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
    if n < 10:
        continue
    fwd = view_dir(a["pitch"], a["yaw"])
    c = np.clip(np.dot(fwd, to_v) / n, -1, 1)
    ang_ = math.degrees(math.acos(c))
    print(f"{r['attacker_name']}->{r['user_name']} w={r['weapon']} hg={r['hitgroup']} t={t}")
    print(f"  a=({a['x']:.0f},{a['y']:.0f},{a['z']:.0f}) pitch={a['pitch']:.1f} yaw={a['yaw']:.1f}")
    print(f"  v=({v['x']:.0f},{v['y']:.0f},{v['z']:.0f}) to_v=({to_v[0]:.0f},{to_v[1]:.0f},{to_v[2]:.0f}) 夹角={ang_:.0f}°")
    cnt += 1
    if cnt >= 10:
        break
