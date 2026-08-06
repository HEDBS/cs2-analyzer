"""CS2 demo 击杀事件 + 急停速度分析（可直接运行）
用法: python analyze_kills.py [demo路径]
默认 demo: E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\de1.dem
输出: 每次击杀一行(含开枪时速度) + 急停统计汇总
"""
import sys
import numpy as np
import pandas as pd

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\de1.dem"
    from demoparser2 import DemoParser
    parser = DemoParser(path)
    TICK_RATE = 64

    # 1) tick 级数据：位置 + 视角 + 生命
    df = parser.parse_ticks([
        "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX",
        "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecY",
        "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecZ",
        "CCSPlayerPawn.m_angEyeAngles",
        "CCSPlayerPawn.m_iHealth",
    ])
    df = df.rename(columns={
        "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX": "x",
        "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecY": "y",
        "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecZ": "z",
        "CCSPlayerPawn.m_iHealth": "hp",
    })
    # 视角拆列（None 兜底为 0）
    ang = df["CCSPlayerPawn.m_angEyeAngles"].apply(
        lambda v: v if isinstance(v, list) and len(v) == 3 else [0.0, 0.0, 0.0]
    )
    ang = pd.DataFrame(ang.tolist(), columns=["pitch", "yaw", "roll"])
    df = pd.concat([df.drop(columns=["CCSPlayerPawn.m_angEyeAngles"]), ang], axis=1)
    df = df.sort_values(["steamid", "tick"]).reset_index(drop=True)

    # 2) 差分水平速度（units/s）—— CS2 demo 无速度字段，只能差分
    dt = 1.0 / TICK_RATE
    df["vx"] = df.groupby("steamid")["x"].diff() / dt
    df["vy"] = df.groupby("steamid")["y"].diff() / dt
    df["speed"] = np.sqrt(df["vx"] ** 2 + df["vy"] ** 2)

    # 3) 击杀事件
    kills = parser.parse_event("player_death")
    print(f"击杀事件: {len(kills)} 条")

    # 4) 对每次击杀取击杀者开枪前 1 tick 的速度（急停判定）
    rows = []
    for _, k in kills.iterrows():
        atk = k["attacker_steamid"]
        t = k["tick"]
        # 坑: 事件 steamid 是 str, tick 表是 uint64, 必须转 int
        try:
            atk = int(atk)
        except (TypeError, ValueError):
            continue
        # 坑: 死亡事件 tick 略晚于开枪 tick, 查 t-1
        m = df[(df["steamid"] == atk) & (df["tick"] == t - 1)]
        if len(m):
            rows.append({
                "tick": t,
                "attacker": k["attacker_name"],
                "victim": k["user_name"],
                "weapon": k["weapon"],
                "headshot": k["headshot"],
                "penetrated": k["penetrated"],
                "thrusmoke": k["thrusmoke"],
                "distance": round(k["distance"], 1),
                "开枪时速度": round(m["speed"].iloc[0], 1),
            })
    res = pd.DataFrame(rows)
    print(f"成功 join 击杀者速度: {len(res)}/{len(kills)}")

    print("\n===== 全部击杀(含速度) =====")
    print(res.to_string(index=False))

    print("\n===== 汇总: 击杀瞬间速度分布 =====")
    s = res["开枪时速度"]
    print(f"  样本数: {len(s)}")
    print(f"  静止击杀(≤10u/s, 急停成功): {(s <= 10).sum()} ({(s <= 10).mean()*100:.0f}%)")
    print(f"  移动击杀(>100u/s, 移动中开枪): {(s > 100).sum()} ({(s > 100).mean()*100:.0f}%)")
    print(f"  中位数: {s.median():.0f} u/s | 90分位: {s.quantile(0.9):.0f} u/s")
    print(f"  穿墙击杀: {res['penetrated'].astype(bool).sum()} | 穿烟击杀: {res['thrusmoke'].astype(bool).sum()} | 爆头: {res['headshot'].astype(bool).sum()}")

if __name__ == "__main__":
    main()
