"""全组合校准：pitch符号 x 目标高度，找 shoot_ang 正确用法"""
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
bh = p.parse_event("player_bullet_hit")
# 按 tick 关联 hitgroup
hg_map = dict(zip(bh["tick"], bh["hit_group"]))

def fwd_euler(pitch, yaw, psign):
    pr, yr = math.radians(pitch), math.radians(yaw)
    return np.array([math.cos(pr) * math.cos(yr), math.cos(pr) * math.sin(yr), psign * math.sin(pr)])

TG_H = {"head": 63, "neck": 55, "chest": 45, "stomach": 30, "left_arm": 50, "right_arm": 50, "left_leg": 20, "right_leg": 20, "generic": 40}

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
    base = np.array([v["x"] - a["x"], v["y"] - a["y"], v["z"] - a["z"] - 64])
    n = np.linalg.norm(base[:2])
    if n < 10:
        continue
    hg = hg_map.get(t, "generic")
    rows.append({"p": r["shoot_ang_x"], "y": r["shoot_ang_y"],
                 "to": base, "hg": hg})

print(f"样本: {len(rows)}")
for ps in [1, -1]:
    for name, h in [("固定40", 40), ("按hitgroup", None), ("固定63头", 63), ("固定20腿", 20)]:
        errs = []
        for r_ in rows:
            th = TG_H.get(r_["hg"], 40) if h is None else h
            tv = r_["to"] + np.array([0, 0, th])
            n = np.linalg.norm(tv)
            if n == 0:
                continue
            fv = fwd_euler(r_["p"], r_["y"], ps)
            errs.append(math.degrees(math.acos(np.clip(np.dot(fv, tv) / n, -1, 1))))
        e = np.array(errs)
        print(f"pitch{'反' if ps==-1 else '正'} + {name}: 中位 {np.median(e):.1f}° | ≤5°: {(e<=5).mean()*100:.0f}% | ≤15°: {(e<=15).mean()*100:.0f}%")
