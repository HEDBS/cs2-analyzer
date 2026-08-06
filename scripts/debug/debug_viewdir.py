"""调试：打印击杀瞬间的视角/位置原始数据，校准 view_dir"""
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

kills = p.parse_event("player_death")
cnt = 0
for _, r in kills.iterrows():
    try:
        aid, vid, t = int(r["attacker_steamid"]), int(r["user_steamid"]), r["tick"]
    except (TypeError, ValueError):
        continue
    try:
        a = df.iloc[k2i[f"{aid}_{t-2}"]]
        v = df.iloc[k2i[f"{vid}_{t}"]]
    except (KeyError, TypeError):
        continue
    av = np.array([a["x"], a["y"], a["z"]])
    vv = np.array([v["x"], v["y"], v["z"]])
    to_v = vv - av
    pr, yr = math.radians(a["pitch"]), math.radians(a["yaw"])
    fwd = np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), -math.sin(pr)])
    ang_ = math.degrees(math.acos(np.clip(np.dot(fwd, to_v) / np.linalg.norm(to_v), -1, 1)))
    print(f"{r['attacker_name']} -> {r['user_name']} t={t}")
    print(f"  a_pos=({a['x']:.0f},{a['y']:.0f},{a['z']:.0f}) pitch={a['pitch']:.1f} yaw={a['yaw']:.1f}")
    print(f"  v_pos=({v['x']:.0f},{v['y']:.0f},{v['z']:.0f})")
    print(f"  to_v=({to_v[0]:.0f},{to_v[1]:.0f},{to_v[2]:.0f}) fwd=({fwd[0]:.2f},{fwd[1]:.2f},{fwd[2]:.2f}) 夹角={ang_:.0f}°")
    cnt += 1
    if cnt >= 6:
        break
