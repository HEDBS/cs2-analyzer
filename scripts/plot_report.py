"""CS2 分析结果可视化：读 output/ 下的 CSV 生成综合报告图
用法: python scripts/plot_report.py <demo名> [输出png路径]
例:   python scripts/plot_report.py g151-n-20260806005120942754354_de_dust2 docs/report_example.png
"""
import sys
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"E:\CS2Analyzer\output"

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "g151-n-20260806005120942754354_de_dust2"
    out_png = sys.argv[2] if len(sys.argv) > 2 else r"E:\CS2Analyzer\docs\report_example.png"
    os.makedirs(os.path.dirname(out_png), exist_ok=True)

    shots = pd.read_csv(os.path.join(OUT, f"{base}_shots.csv"))
    hits = pd.read_csv(os.path.join(OUT, f"{base}_hits.csv"))
    kills = pd.read_csv(os.path.join(OUT, f"{base}_kills.csv"))

    # 命中率分桶：开枪速度 vs 命中速度
    n_still = int((shots["speed"] <= 30).sum())
    n_move = int((shots["speed"] > 30).sum())
    h_still = int((hits["atk_speed"].dropna() <= 30).sum())
    h_move = int((hits["atk_speed"].dropna() > 30).sum())
    rate_still = h_still / n_still * 100 if n_still else 0
    rate_move = h_move / n_move * 100 if n_move else 0

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle(f"CS2 对局分析报告 — {base[:20]}", fontsize=15, fontweight="bold")

    # 1. 命中率分桶
    ax = axes[0][0]
    bars = ax.bar(["静止开枪\n(≤30 u/s)", "移动开枪\n(>30 u/s)"], [rate_still, rate_move],
                  color=["#2e9e5b", "#d9534f"], width=0.55)
    for b, v in zip(bars, [rate_still, rate_move]):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.4, f"{v:.1f}%", ha="center", fontweight="bold")
    ax.set_ylabel("命中率 %")
    ax.set_title("命中率：静止 vs 移动", fontweight="bold")
    ax.set_ylim(0, max(rate_still, rate_move) * 1.25 + 1)

    # 2. 急停分布
    ax = axes[0][1]
    s = kills["kill_speed"].dropna()
    ax.hist(s, bins=24, color="#4c72b0", edgecolor="white")
    ax.axvline(10, color="#2e9e5b", ls="--", lw=1.5, label="急停成功 ≤10")
    ax.axvline(100, color="#d9534f", ls="--", lw=1.5, label="移动开枪 >100")
    ax.set_xlabel("击杀瞬间速度 (u/s)")
    ax.set_ylabel("击杀数")
    ax.set_title(f"急停分析（静止击杀 {(s<=10).mean()*100:.0f}%）", fontweight="bold")
    ax.legend(fontsize=8)

    # 3. 拉枪距离
    ax = axes[0][2]
    f = shots["flick_deg"].dropna()
    ax.hist(f[f < 90], bins=30, color="#dd8452", edgecolor="white")
    ax.axvline(30, color="#d9534f", ls="--", lw=1.5, label="大拉枪 >30°")
    ax.set_xlabel("相邻开枪视角变化 (°)")
    ax.set_ylabel("开枪次数")
    ax.set_title(f"拉枪距离（中位 {f.median():.1f}°）", fontweight="bold")
    ax.legend(fontsize=8)

    # 4. 命中部位
    ax = axes[1][0]
    hg = hits["hitgroup"].value_counts().head(6)
    colors = ["#55a868", "#c44e52", "#4c72b0", "#8172b3", "#ccb974", "#64b5cd"]
    ax.barh(hg.index[::-1], hg.values[::-1], color=colors[:len(hg)])
    ax.set_xlabel("次数")
    ax.set_title("命中部位分布", fontweight="bold")

    # 5. 交战距离
    ax = axes[1][1]
    d = hits["distance"].dropna()
    ax.hist(d, bins=30, color="#8172b3", edgecolor="white")
    ax.set_xlabel("交战距离 (units)")
    ax.set_ylabel("命中次数")
    ax.set_title(f"交战距离（中位 {d.median():.0f} u）", fontweight="bold")

    # 6. 汇总
    ax = axes[1][2]
    ax.axis("off")
    hs_rate = kills["headshot"].mean() * 100 if len(kills) else 0
    pen = int(kills["penetrated"].gt(0).sum())
    smoke = int(kills["thrusmoke"].sum())
    ak = kills[kills["weapon"].str.contains("ak47", na=False)]
    ak_hs = ak["headshot"].mean() * 100 if len(ak) else 0
    total_dmg = hits["dmg"].sum()
    n_rounds = 46  # 回合数来自分析输出，可按需传入
    lines = [
        f"击杀 {len(kills)}  |  爆头率 {hs_rate:.0f}%",
        f"穿墙击杀 {pen}  |  穿烟击杀 {smoke}",
        f"AK 爆头率 {ak_hs:.0f}%  |  ADR ≈{total_dmg/n_rounds/max(len(kills['attacker'].unique()),1):.0f}",
        f"总命中率 {len(hits)/max(len(shots),1)*100:.1f}%",
        "",
        f"静止击杀占比 {(s<=10).mean()*100:.0f}%（急停质量）",
        f"移动中开枪占比 {(s>100).mean()*100:.0f}%（需改善）",
    ]
    ax.text(0.05, 0.95, "\n".join(lines), va="top", ha="left", fontsize=12)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(out_png, dpi=150)
    print(f"已保存: {out_png}")

if __name__ == "__main__":
    main()
