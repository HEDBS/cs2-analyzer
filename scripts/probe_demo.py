"""CS2 demo 数据源验证 v2：事件流字段 + 差分速度"""
import sys
import time
import numpy as np
import pandas as pd

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else r"E:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\de1.dem"
    from demoparser2 import DemoParser
    parser = DemoParser(path)
    t0 = time.time()
    TICK_RATE = 64

    # ---- 事件流：不带字段参数，先看默认返回什么列 ----
    for ev_name in ["weapon_fire", "player_hurt", "player_death"]:
        try:
            ev = parser.parse_event(ev_name)
            print(f"[{ev_name}] {len(ev)} 条, 列: {list(ev.columns)}")
            print(ev.head(2).to_string())
            print()
        except Exception as e:
            print(f"[{ev_name}] 失败: {e}\n")

    # ---- tick 数据 + 差分速度 ----
    t1 = time.time()
    df = parser.parse_ticks(["CCSPlayerPawn.origin", "CCSPlayerPawn.m_angEyeAngles", "CCSPlayerPawn.m_iHealth"])
    print(f"[ticks] {len(df)} 行, 用时 {time.time()-t1:.1f}s")

    # origin 是 [x,y,z] 列表列，拆成三列（某些 tick 可能为 None，兜底为 0）
    def split_vec(col, names):
        cleaned = col.apply(lambda v: v if isinstance(v, list) and len(v) == 3 else [0.0, 0.0, 0.0])
        return pd.DataFrame(cleaned.tolist(), columns=names)

    origin = split_vec(df["CCSPlayerPawn.origin"], ["ox", "oy", "oz"])
    ang = split_vec(df["CCSPlayerPawn.m_angEyeAngles"], ["pitch", "yaw", "roll"])
    df = pd.concat([df[["tick", "steamid", "name", "CCSPlayerPawn.m_iHealth"]], origin, ang], axis=1)
    df = df.rename(columns={"CCSPlayerPawn.m_iHealth": "hp"})
    df = df.sort_values(["steamid", "tick"]).reset_index(drop=True)

    # 差分速度 (units/s)，只对同一玩家相邻 tick 计算
    dt = 1.0 / TICK_RATE
    df["vx"] = df.groupby("steamid")["ox"].diff() / dt
    df["vy"] = df.groupby("steamid")["oy"].diff() / dt
    df["vz"] = df.groupby("steamid")["oz"].diff() / dt
    df["speed"] = np.sqrt(df["vx"]**2 + df["vy"]**2 + df["vz"]**2)

    alive = df[df["hp"] > 0]
    print(f"\n[速度差分] 存活样本 {len(alive)} 行")
    print(f"  水平速度 90 分位: {alive['speed'].quantile(0.9):.0f} u/s (CS2 跑步≈250u/s, 急停后<10)")
    print(f"  视角 yaw 范围: [{alive['yaw'].min():.1f}, {alive['yaw'].max():.1f}]")
    print("\n[示例] 某玩家急停片段（速度骤降→开火前）:")
    one = alive[alive["name"] == "HeK1ng"].head(400)
    print(one[["tick", "speed", "pitch", "yaw"]].head(8).to_string(index=False))

    print(f"\n总耗时 {time.time()-t0:.1f}s")

if __name__ == "__main__":
    main()
