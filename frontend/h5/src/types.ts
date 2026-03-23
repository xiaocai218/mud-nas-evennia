export type BottomNavKey = "battle" | "map" | "secret" | "tower" | "more";

export type EntityType = "npc" | "player" | "enemy" | "object";

export type RoomNode = {
  id: string;
  name: string;
  active?: boolean;
};

export type RoomMapColumn = RoomNode[];

export type EntityCard = {
  id: string;
  name: string;
  type: EntityType;
  tag: string;
  note?: string;
  desc?: string;
  realm?: string;
  gender?: string;
  title?: string;
  actions?: string[];
  stats?: Array<{ label: string; value: string }>;
};

export type FeatureEntry = {
  id: string;
  label: string;
  badge?: string;
};

export type ResourcePill = {
  label: string;
  value: string;
  icon: string;
};

export type WorldCard = {
  id: string;
  name: string;
  region: string;
  realm: string;
  tag: string;
  active?: boolean;
};
