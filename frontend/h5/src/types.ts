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

export type RealtimeEvent = {
  type: "event";
  event: string;
  scope?: string;
  target_id?: number | string | null;
  ts?: number;
  payload: Record<string, unknown>;
};

export type PollBatch = {
  events: RealtimeEvent[];
  cursor: string;
  transport: "poll" | "ws";
  has_more: boolean;
  active_character_id?: number | null;
};

export type WsMetaPayload = {
  implemented: boolean;
  version: string;
  endpoint: string;
  poll_endpoint: string;
  transports: {
    websocket: {
      available: boolean;
      implemented: boolean;
      note?: string;
    };
    poll: {
      available: boolean;
      interval_ms: number;
      cursor_type: string;
    };
  };
  session: {
    authenticated: boolean;
    active_character_id: number | null;
  };
  events: {
    supported: string[];
  };
  note?: string;
  actions: string[];
  webclient_ws_port: number;
};

export type WsMetaResponse = H5Envelope<WsMetaPayload>;

export type PollBatchResponse = H5Envelope<PollBatch>;
