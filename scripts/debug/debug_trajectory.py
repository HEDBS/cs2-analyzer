"""查小萍安->Danking t=1572 前后 30 tick 的双方位置/视角/hp 轨迹"""
from demoparser2 import DemoParser
import pandas as pd

PATH = r"E:\CS2Analyzer\demos\g151-n-20260806005120942754354_de_dust2.dem"
PX = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX"
PY = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecY"
PZ = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecZ"

p = DemoParser(PATH)
df = p.parse_ticks([PX, PY, PZ, "CCSPlayerPawn.m_angEyeAngles", "CCSPlayerPawn.m_iHealth"])
df = df.rename(columns={PX: "x", PY: "y", PZ: "z", "CCSPlayerPawn.m_iHealth": "hp"})
ang = df["CCSPlayerPawn.m_angEyeAngles"].apply(
    lambda v: v if isinstance(v, list) and len(v) == 3 else [0.0, 0.0, 0.0])
ang = pd.DataFrame(ang.tolist(), columns=["pitch", "yaw", "roll"])
df = pd.concat([df.drop(columns=["CCSPlayerPawn.m_angEyeAngles"]), ang], axis=1)

# 小萍安 76561199106560789? 从伤害事件拿 steamid
hurt = p.parse_event("player_hurt")
row = hurt[(hurt["tick"] == 1572)]
print(row[["attacker_name", "user_name", "weapon", "hitgroup", "dmg_health"]].to_string(index=False))
print()
for name, sid in [("小萍安", row["attacker_steamid"].iloc[0]), ("Danking", row["user_steamid"].iloc[0])]:
    sub = df[(df["steamid"] == int(sid)) & (df["tick"] >= 1540) & (df["tick"] <= 1585)].copy()
    sub["tick_off"] = sub["tick"] - 1572
    print(f"=== {name} (steamid {sid}) tick 相对 1572 ===")
    print(sub[["tick_off", "x", "y", "z", "pitch", "yaw", "hp"]].to_string(index=False))
