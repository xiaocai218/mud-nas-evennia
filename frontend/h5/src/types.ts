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

export type H5Envelope<T> = {
  type?: string;
  ok: boolean;
  payload: T;
  error?: {
    code?: string;
    message?: string;
  };
};

export type AccountSummary = {
  id: number;
  username: string;
  is_authenticated: boolean;
};

export type CharacterSummary = {
  id: number;
  key: string;
  realm: string;
  hp?: number;
  max_hp?: number;
  stamina?: number;
  max_stamina?: number;
  area?: { id?: string; key?: string } | null;
  room?: { id?: string; key?: string; desc?: string } | null;
};

export type LoginResponse = H5Envelope<{
  account: AccountSummary;
  characters: CharacterSummary[];
  active_character_id: number | null;
}>;

export type CharacterListResponse = H5Envelope<{
  account: AccountSummary;
  characters: CharacterSummary[];
  active_character_id: number | null;
}>;
