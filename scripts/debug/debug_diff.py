"""对比 analyze_full 与 debug_shoot_ang 的差异：打印前 8 条命中的中间量"""
from demoparser2 import DemoParser
import numpy as np, pandas as pd, math

PATH = r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\de1.dem"
PX = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX"
PY = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecY"
PZ = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecZ"

def vec3(a, b, c):
    return np.array([a, b, c], dtype=float)

def angle_between(u, v):
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu == 0 or nv == 0:
        return np.nan
    return math.degrees(math.acos(np.clip(np.dot(u, v) / (nu * nv), -1.0, 1.0)))

p = DemoParser(PATH)
df = p.parse_ticks([PX, PY, PZ, "CCSPlayerPawn.m_angEyeAngles", "CCSPlayerPawn.m_iHealth"])
df = df.rename(columns={PX: "x", PY: "y", PZ: "z", "CCSPlayerPawn.m_iHealth": "hp"})
ang = df["CCSPlayerPawn.m_angEyeAngles"].apply(
    lambda v: v if isinstance(v, list) and len(v) == 3 else [0.0, 0.0, 0.0])
ang = pd.DataFrame(ang.tolist(), columns=["pitch", "yaw", "roll"])
df = pd.concat([df.drop(columns=["CCSPlayerPawn.m_angEyeAngles"]), ang], axis=1)
df = df.sort_values(["steamid", "tick"]).reset_index(drop=True)
df["pos"] = df.apply(lambda r: vec3(r["x"], r["y"], r["z"]), axis=1)
df["key"] = df["steamid"].astype(str) + "_" + df["tick"].astype(str)
key2idx = {k: i for i, k in enumerate(df["key"])}

bd = p.parse_event("bullet_damage")
cnt = 0
for _, r in bd.iterrows():
    try:
        aid = int(r["attacker_steamid"])
        vid = int(r["victim_steamid"])
    except (TypeError, ValueError):
        continue
    t = r["tick"]
    try:
        arow = df.iloc[key2idx[f"{aid}_{t}"]]
        vrow = df.iloc[key2idx[f"{vid}_{t}"]]
    except (KeyError, TypeError):
        continue
    apos = arow["pos"] + np.array([0, 0, 64])
    vpos = vrow["pos"]
    shoot = vec3(r["shoot_ang_x"], r["shoot_ang_y"], r["shoot_ang_z"])
    target_dir = vpos + np.array([0, 0, 30]) - apos
    err = angle_between(shoot, target_dir)
    print(f"t={t} {r['attacker_name']}->{r['victim_name']}")
    print(f"  apos=({apos[0]:.0f},{apos[1]:.0f},{apos[2]:.0f}) vpos=({vpos[0]:.0f},{vpos[1]:.0f},{vpos[2]:.0f})")
    print(f"  shoot=({shoot[0]:.3f},{shoot[1]:.3f},{shoot[2]:.3f}) norm={np.linalg.norm(shoot):.3f}")
    print(f"  target=({target_dir[0]:.0f},{target_dir[1]:.0f},{target_dir[2]:.0f}) norm={np.linalg.norm(target_dir):.0f}")
    print(f"  aim_err={err:.1f}°")
    cnt += 1
    if cnt >= 8:
        break
