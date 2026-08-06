"""统计：伤害案例中 位置z 与 准星夹角 的关系"""
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

rows = []
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
    rows.append({"az": a["z"], "vz": v["z"], "err": math.degrees(math.acos(c))})

r = pd.DataFrame(rows)
print("样本:", len(r))
print("\n按攻击者 z 分区:")
r["azone"] = pd.cut(r["az"], bins=[0, 300, 600, 2000], labels=["低地<300", "中300-600", "高>600"])
print(r.groupby("azone", observed=True)["err"].agg(["count", "median", "mean"]).round(1))
print("\n按受害者 z 分区:")
r["vzone"] = pd.cut(r["vz"], bins=[0, 300, 600, 2000], labels=["低地<300", "中300-600", "高>600"])
print(r.groupby("vzone", observed=True)["err"].agg(["count", "median", "mean"]).round(1))
print("\n全部 err 分布: ≤10°:", (r['err']<=10).mean().round(3), "| 10-45°:", ((r['err']>10)&(r['err']<=45)).mean().round(3), "| >45°:", (r['err']>45).mean().round(3))
