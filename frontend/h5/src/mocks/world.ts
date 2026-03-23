import type { EntityCard, FeatureEntry, ResourcePill, RoomMapColumn, WorldCard } from "@/types";

export const topResources: ResourcePill[] = [
  { label: "灵石", value: "1510", icon: "◆" },
  { label: "铜钱", value: "150", icon: "◎" },
];

export const roomMap: RoomMapColumn[] = [
  [{ id: "shadow", name: "幽暗角落" }],
  [{ id: "herb", name: "药草铺", active: true }],
  [
    { id: "chief", name: "村长宅邸" },
    { id: "square", name: "村中广场" },
    { id: "village_gate", name: "村口" },
  ],
  [{ id: "forge", name: "铁匠铺" }],
  [{ id: "storage", name: "仓库" }],
];

export const roomEntities: EntityCard[] = [
  {
    id: "npc_yaopo",
    name: "药婆婆",
    type: "npc",
    tag: "NPC",
    note: "!",
    title: "采药人",
    gender: "女",
    realm: "凡人",
    desc: "常年在山中采药的老婆婆，对各种草药了如指掌，出售基础丹药和材料。",
    actions: ["交流", "购买"],
    stats: [
      { label: "称号", value: "采药人" },
      { label: "姓名", value: "药婆婆" },
      { label: "性别", value: "女" },
      { label: "境界", value: "凡人" },
    ],
  },
  {
    id: "player_xiaocai",
    name: "坐忘道",
    type: "player",
    tag: "玩家",
    title: "并肩先驱",
    gender: "男",
    realm: "炼气化神·炼己期",
    actions: ["交流", "私聊"],
    stats: [
      { label: "气血上限", value: "2926" },
      { label: "灵气上限", value: "960" },
      { label: "物攻", value: "292" },
      { label: "法攻", value: "169" },
      { label: "物防", value: "72" },
      { label: "法防", value: "47" },
    ],
  },
  {
    id: "player_lili",
    name: "李李李",
    type: "player",
    tag: "玩家",
    title: "外门弟子",
    gender: "女",
    realm: "炼气四层",
    actions: ["交流", "私聊"],
  },
];

export const featureEntries: FeatureEntry[] = [
  { id: "bag", label: "背包" },
  { id: "companion", label: "伙伴" },
  { id: "skills", label: "功法" },
  { id: "realm", label: "境界" },
  { id: "quests", label: "任务" },
  { id: "sect", label: "宗门" },
  { id: "market", label: "坊市" },
  { id: "team", label: "组队" },
  { id: "monthly", label: "月卡" },
  { id: "battle_order", label: "战令" },
  { id: "arena", label: "竞技" },
  { id: "ranking", label: "排行" },
  { id: "achievement", label: "成就", badge: "1" },
  { id: "afk", label: "挂机" },
  { id: "character", label: "角色" },
];

export const worldCards: WorldCard[] = [
  { id: "qingyun", name: "青云村", region: "东洲", realm: "凡人", tag: "大世界", active: true },
  { id: "outskirts", name: "青云村外", region: "东洲", realm: "凡人", tag: "大世界" },
  { id: "stone", name: "断碑遗迹", region: "东洲", realm: "炼精化炁·养气期", tag: "大世界" },
  { id: "wolf", name: "苍狼巢穴", region: "试炼秘境", realm: "炼精化炁·养气期", tag: "秘境" },
  { id: "tower", name: "千层塔", region: "活动", realm: "凡人", tag: "活动" },
];
