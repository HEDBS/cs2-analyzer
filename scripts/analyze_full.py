"""CS2 对局全量分析 A 版 v2（数据可靠性修正版）
可靠指标: 急停(速度差分) / 命中率分桶(静止vs移动) / 命中部位 / 距离 / 拉枪 / 爆头 / ADR
不可靠已砍: 逐发角度偏差(shoot_ang 语义与位置坐标系不匹配, 实测 52° 噪声)
用法: python analyze_full.py <demo路径> [输出目录]
"""
import sys
import os
import math
import numpy as np
import pandas as pd

TICK_RATE = 64
POS_X = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX"
POS_Y = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecY"
POS_Z = "CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecZ"
NON_GUN = "inferno|hegrenade|molotov|knife|flashbang|smoke|decoy|firebomb|snowball"

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else r"E:\CS2Analyzer\demos\g151-n-20260806005120942754354_de_dust2.dem"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else r"E:\CS2Analyzer\output"
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]

    from demoparser2 import DemoParser
    parser = DemoParser(path)
    print(f"[加载] {base} ...")

    # ---------- tick 级数据：位置/视角/生命 + 差分速度 ----------
    df = parser.parse_ticks([POS_X, POS_Y, POS_Z, "CCSPlayerPawn.m_angEyeAngles", "CCSPlayerPawn.m_iHealth"])
    df = df.rename(columns={POS_X: "x", POS_Y: "y", POS_Z: "z", "CCSPlayerPawn.m_iHealth": "hp"})
    ang = df["CCSPlayerPawn.m_angEyeAngles"].apply(
        lambda v: v if isinstance(v, list) and len(v) == 3 else [0.0, 0.0, 0.0])
    ang = pd.DataFrame(ang.tolist(), columns=["pitch", "yaw", "roll"])
    df = pd.concat([df.drop(columns=["CCSPlayerPawn.m_angEyeAngles"]), ang], axis=1)
    df = df.sort_values(["steamid", "tick"]).reset_index(drop=True)

    dt = 1.0 / TICK_RATE
    df["vx"] = df.groupby("steamid")["x"].diff() / dt
    df["vy"] = df.groupby("steamid")["y"].diff() / dt
    df["speed"] = np.sqrt(df["vx"] ** 2 + df["vy"] ** 2)
    df["key"] = df["steamid"].astype(str) + "_" + df["tick"].astype(str)
    key2idx = {k: i for i, k in enumerate(df["key"])}

    def lookup(steamid, tick):
        return df.iloc[key2idx[f"{int(steamid)}_{tick}"]]

    # ---------- 事件 ----------
    n_rounds = len(parser.parse_event("round_officially_ended"))
    fire = parser.parse_event("weapon_fire")
    hurt = parser.parse_event("player_hurt")
    kills = parser.parse_event("player_death")
    print(f"  回合 {n_rounds} | 开枪 {len(fire)} | 伤害 {len(hurt)} | 击杀 {len(kills)}")

    # ---------- 1) 每枪：速度分桶 + 拉枪距离 ----------
    shots = []
    prev_ang = {}
    for _, r in fire.iterrows():
        try:
            uid = int(r["user_steamid"])
        except (TypeError, ValueError):
            continue
        try:
            row = lookup(uid, r["tick"])
        except (KeyError, TypeError):
            continue
        flick = np.nan
        if uid in prev_ang:
            dp, dy = row["pitch"] - prev_ang[uid][0], row["yaw"] - prev_ang[uid][1]
            flick = math.degrees(math.acos(np.clip(
                math.cos(math.radians(dp)) * math.cos(math.radians(dy)), -1, 1)))
        prev_ang[uid] = (row["pitch"], row["yaw"])
        shots.append({"tick": r["tick"], "player": r["user_name"], "weapon": r["weapon"],
                      "speed": round(row["speed"], 1), "flick_deg": flick})
    shots_df = pd.DataFrame(shots)

    # ---------- 2) 每次伤害：攻击者速度 + 部位 + 距离 ----------
    hurt_rows = []
    for _, r in hurt.iterrows():
        try:
            aid = int(r["attacker_steamid"])
        except (TypeError, ValueError):
            continue
        try:
            arow = lookup(aid, r["tick"])
            vrow = lookup(int(r["user_steamid"]), r["tick"])
            dist = np.linalg.norm([vrow["x"] - arow["x"], vrow["y"] - arow["y"], vrow["z"] - arow["z"]])
        except (KeyError, TypeError, ValueError):
            dist = None
        hurt_rows.append({
            "tick": r["tick"], "attacker": r["attacker_name"], "victim": r["user_name"],
            "weapon": r["weapon"], "hitgroup": r["hitgroup"], "dmg": r["dmg_health"],
            "atk_speed": round(arow["speed"], 1) if 'arow' in dir() else None,
            "distance": round(dist, 1) if dist else None,
        })
    hurt_df = pd.DataFrame(hurt_rows)

    # ---------- 3) 击杀 ----------
    kill_rows = []
    for _, r in kills.iterrows():
        try:
            aid, vid = int(r["attacker_steamid"]), int(r["user_steamid"])
        except (TypeError, ValueError):
            continue
        try:
            arow = lookup(aid, r["tick"] - 1)
        except (KeyError, TypeError):
            continue
        kill_rows.append({
            "tick": r["tick"], "attacker": r["attacker_name"], "victim": r["user_name"],
            "weapon": r["weapon"], "headshot": bool(r["headshot"]),
            "penetrated": int(r["penetrated"]), "thrusmoke": bool(r["thrusmoke"]),
            "distance": round(r["distance"], 1), "kill_speed": round(arow["speed"], 1),
        })
    kills_df = pd.DataFrame(kill_rows)

    # ---------- 汇总 ----------
    print("\n" + "=" * 62)
    print(f"===== {base} 分析汇总 =====")
    print(f"回合 {n_rounds} | 开枪 {len(shots_df)} | 枪械命中(伤害事件) {len(hurt_df)} | 击杀 {len(kills_df)}")

    # 命中率（总体 + 静止/移动分桶）
    gun_shots = shots_df[~shots_df["weapon"].str.contains("knife|hegrenade|inferno|molotov|flashbang|smoke|decoy|firebomb", na=False)]
    if len(gun_shots):
        n_gun = len(gun_shots)
        hit_total = len(hurt_df)
        print(f"\n[命中率] 总 {hit_total/n_gun*100:.1f}% ({hit_total}/{n_gun})")
        for label, cond in [("静止(≤30u/s)", gun_shots["speed"] <= 30), ("移动(>30u/s)", gun_shots["speed"] > 30)]:
            n = int(cond.sum())
            if n:
                # 该桶伤害数：hurt 中 attacker 速度同桶
                hb = hurt_df["atk_speed"].dropna()
                hn = int(((hb <= 30) if label.startswith("静止") else (hb > 30)).sum())
                print(f"  {label}: {n} 枪 | 命中 {hn} → {hn/n*100:.1f}% 命中率")

    # 急停
    if len(kills_df):
        s = kills_df["kill_speed"]
        print(f"\n[急停] 静止击杀(≤10u/s): {(s<=10).sum()} ({(s<=10).mean()*100:.0f}%) | "
              f"移动开枪(>100u/s): {(s>100).sum()} ({(s>100).mean()*100:.0f}%)")

    # 拉枪距离
    f = shots_df["flick_deg"].dropna()
    if len(f):
        print(f"\n[拉枪] 平均 {f.mean():.1f}° | 中位 {f.median():.1f}° | >30°: {(f>30).mean()*100:.0f}% | >60°: {(f>60).mean()*100:.0f}%")

    # 命中部位
    if len(hurt_df):
        hg = hurt_df["hitgroup"].value_counts()
        head_n = hg.get("head", 0)
        print(f"\n[命中部位] head:{head_n} ({head_n/len(hurt_df)*100:.0f}%) | " +
              ", ".join(f"{k}:{v}" for k, v in hg.head(4).items() if k != "head"))

    # 距离分布
    if len(hurt_df):
        d = hurt_df["distance"].dropna()
        if len(d):
            print(f"\n[距离] 平均 {d.mean():.0f}u | 中位 {d.median():.0f}u | >2000u(远): {(d>2000).mean()*100:.0f}% | <200u(贴脸): {(d<200).mean()*100:.0f}%")

    # ADR
    if n_rounds and len(hurt_df):
        total_dmg = hurt_df["dmg"].sum()
        players = len(kills_df["attacker"].unique()) if len(kills_df) else 10
        print(f"\n[ADR] 全队每回合均伤 {total_dmg/n_rounds:.0f} (人均 ~{total_dmg/n_rounds/max(players,1):.0f})")

    # 击杀明细
    if len(kills_df):
        print(f"\n[击杀] 爆头率 {kills_df['headshot'].mean()*100:.0f}% | 穿墙 {kills_df['penetrated'].gt(0).sum()} | "
              f"穿烟 {kills_df['thrusmoke'].sum()}")
        ak = kills_df[kills_df["weapon"].str.contains("ak47", na=False)]
        if len(ak):
            print(f"  AK 击杀 {len(ak)}, 爆头率 {ak['headshot'].mean()*100:.0f}%")

    # ---------- 导出 ----------
    shots_df.to_csv(os.path.join(out_dir, f"{base}_shots.csv"), index=False, encoding="utf-8-sig")
    hurt_df.to_csv(os.path.join(out_dir, f"{base}_hits.csv"), index=False, encoding="utf-8-sig")
    kills_df.to_csv(os.path.join(out_dir, f"{base}_kills.csv"), index=False, encoding="utf-8-sig")
    print(f"\n[导出] {out_dir}\\{base}_shots.csv / _hits.csv / _kills.csv")

if __name__ == "__main__":
    main()
