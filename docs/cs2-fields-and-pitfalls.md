# CS2 demo 字段清单与踩坑细节（2026-08 实测于 de_inferno 比赛 demo, 337MB）

## demoparser2 版本探测
```
from demoparser2 import DemoParser
p = DemoParser(path)
dir(DemoParser): ['list_game_events','list_updated_fields','parse_event','parse_events',
  'parse_grenades','parse_header','parse_item_drops','parse_player_info','parse_skins',
  'parse_ticks','parse_voice']
```
- `parse_header()` 返回 dict: map_name, tick_rate, tick_count, ...（旧版 `header()` 已删）
- `parse_player_info()` 返回 DataFrame，含 name/steamid
- `parse_event(name)` 不带字段参数时返回全部默认列
- `list_updated_fields()` 返回该 demo 中实际更新过的 969 个字段（网络属性 delta 编码，只在变化时出现）

## 字段名（CS2 新实体系统，与 CS:GO 完全不同）
可用 tick 字段（parse_ticks 传这些）：
- `CCSPlayerPawn.CBodyComponentBaseAnimGraph.m_vecX/Y/Z` — 位置（三个独立 float 列）。**`CCSPlayerPawn.origin` 全是 None，不可用**
- `CCSPlayerPawn.m_angEyeAngles` — 视角，向量列 [pitch, yaw, roll]
- `CCSPlayerPawn.m_iHealth` — 生命值
- 速度字段不存在（m_vecVelocity 不在字段表）。可用: m_flLastLandedVelocityX/Y/Z(落地速度, 仅跳跃时更新)、m_flFallVelocity(垂直)、m_vecBaseVelocity(基础速度, 通常 0)。移动速度必须用位置差分

事件字段（parse_event）：
- weapon_fire: silenced, tick, user_name, user_steamid, weapon
- player_hurt: armor, attacker_name, attacker_steamid, dmg_armor, dmg_health, health, hitgroup(stomach/chest/head...), tick, user_name, user_steamid, weapon
- player_death: assistedflash, assister_name, assister_steamid, attacker_name, attacker_steamid, attackerblind, attackerinair, distance, dmg_armor, dmg_health, dominated, headshot, hitgroup, noreplay, noscope, penetrated(0/1/2=穿墙层数), revenge, thrusmoke(布尔), tick, user_name, user_steamid, weapon, weapon_fauxitemid, weapon_itemid, weapon_originalowner_xuid, wipe

## 实测数据样例
- de_inferno 比赛, 7-9 名玩家, 168 击杀, 4006 次 weapon_fire, 710 次 player_hurt
- tick 范围 1~140718, 每 tick 每存活玩家一行（tick=1000 时 10 行）
- 性能: parse_ticks 140 万行 1.4s; 全管线(含事件 join) 5.9s

## 踩坑明细
1. **origin 是死的**: `CCSPlayerPawn.origin` 全量 None(140 万行 100%)。位置在 `CBodyComponentBaseAnimGraph.m_vecX/Y/Z`, 非零 132 万行、每 tick 更新、范围 0~1024(地图坐标)
2. **类型不匹配**: kills['attacker_steamid'] dtype=str ('76561198120682143'), ticks['steamid'] dtype=uint64 → `df['steamid']==atk` 恒 False。修复: `atk = int(atk)`
3. **向量列 None**: 死亡后的玩家 m_angEyeAngles/origin 为 None, `pd.DataFrame(col.tolist())` 抛 `TypeError: object of type 'NoneType' has no len()`。修复: `col.apply(lambda v: v if isinstance(v,list) and len(v)==3 else [0.0,0.0,0.0])`
4. **tick 对齐**: 击杀瞬间速度应查击杀者 `tick-1` 行（死亡事件记录晚于开枪 ~1 tick）
5. **事件 steamid 空值**: 环境击杀(attacker 为 NaN)需 try/except int() 跳过
6. **Windows 管道**: PowerShell `python x.py 2>&1 | Select-Object -First N` 截断会触发 SIGPIPE 类退出码 4294967295, 结果已完整输出, 非真实错误

## 定位角度/拉枪距离算法备忘（字段已验证, 几何计算待做）
- 定位角度: 开枪 tick 的 (pitch,yaw) 转方向向量 vs (目标位置+t头高 − 击杀者位置+眼睛高度) 向量, 夹角 = acos(点积)。眼睛高度 CS 人物站立 ≈ 64 units
- 拉枪距离: 相邻 weapon_fire 事件间 viewangles 大圆角距离; 拉枪耗时 = 视角开始变化到开火的 tick 数
- 目标位置: 被击杀者(tick 表的 victim steamid)在死亡 tick 的位置即可用——比赛 demo 就能算, 不一定要练枪 demo

## 产品方向备忘
- 录屏+事件检测(ShadowPlay/Medal 路线): 官匹无 API、GSI 无击杀流、内存读取=VAC 红线、图像识别有误判——红海且难
- demo 解析路线: 零风险、100% 精确、无实时压力、穿墙/穿烟字段直接给——练枪分析细分市场空白
- logaddress 服务器日志: 仅自建房/社区服可用, 可作实时补充
