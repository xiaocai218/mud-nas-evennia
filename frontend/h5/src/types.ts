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

export type CommerceError = {
  code?: string;
  message?: string;
  price?: number;
  current?: number;
  currency?: string;
  target_name?: string;
  item_name?: string;
  listing_id?: string;
  status?: string;
};

export type H5Envelope<T> = {
  type?: string;
  ok: boolean;
  payload: T;
  error?: CommerceError;
};

export type ChatChannel = "aggregate" | "world" | "team" | "private" | "system";

export type ChatChannelStatusDTO = {
  channel: ChatChannel;
  key: string;
  desc: string;
  muted: boolean;
  available: boolean;
  reason?: string | null;
};

export type ChatMessageDTO = {
  channel: Exclude<ChatChannel, "aggregate">;
  sender_id?: number | null;
  sender_name?: string | null;
  sender_title?: string | null;
  target_id?: number | null;
  target_name?: string | null;
  text: string;
  ts: number;
  level?: string;
  code?: string | null;
};

export type RealmEndpoint = {
  realm_key?: string | null;
  minor_stage?: number | null;
  display_name?: string | null;
};

export type RealmRecommendationDTO = {
  mode: string;
  label: string;
  start?: RealmEndpoint | null;
  end?: RealmEndpoint | null;
};

export type RealmInfoDTO = {
  realm: string;
  realm_key?: string | null;
  realm_name?: string | null;
  minor_stage?: number | null;
  stage_bucket?: string | null;
  display_name?: string | null;
  is_peak?: boolean;
  can_breakthrough?: boolean;
  breakthrough_state?: string | null;
  cultivation_exp_total?: number;
  cultivation_exp_in_stage?: number;
  cultivation_exp_required?: number;
  next_realm_key?: string | null;
  next_minor_stage?: number | null;
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
  realm_info?: RealmInfoDTO;
  realm_display?: string;
  realm_title?: string;
  stage_bucket?: string | null;
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

export type CharacterDTO = {
  name: string;
  profile?: string | null;
  realm: string;
  realm_info?: RealmInfoDTO;
  realm_display?: string;
  realm_title?: string;
  stage_bucket?: string | null;
  hp: number;
  max_hp: number;
  stamina: number;
  max_stamina: number;
  exp: number;
  copper: number;
  effects_text: string;
  inventory_count: number;
};

export type AreaDTO = {
  id: string;
  key: string;
  desc: string;
  zone_id?: string | null;
  recommended_realm?: RealmRecommendationDTO | null;
  facilities: string[];
  rooms: string[];
  tags: string[];
};

export type RoomExitDTO = {
  key: string;
  name: string;
  destination?: string | null;
};

export type RoomEntityDTO = {
  id?: string | null;
  key: string;
  npc_type?: string;
  object_type?: string;
  realm?: string;
  realm_display?: string;
  max_hp?: number;
  damage?: number;
  drop_item_id?: string | null;
};

export type InventoryItemDTO = {
  id?: string | null;
  key: string;
  desc: string;
};

export type ShopEntryDTO = {
  item_id: string;
  key: string;
  desc: string;
  price: number;
};

export type ShopDTO = {
  id: string;
  key: string;
  desc: string;
  currency: string;
  room_id: string;
  npc_id?: string | null;
  inventory: ShopEntryDTO[];
};

export type TradeOrListingSummaryDTO = {
  id: string;
  item_name: string;
  price: number;
  currency: string;
  seller_name?: string | null;
  buyer_name?: string | null;
  sender_name?: string | null;
  target_name?: string | null;
  status?: string | null;
  status_label?: string | null;
  expires_in?: number | null;
};

export type MarketListingDTO = TradeOrListingSummaryDTO & {
  market_id: string;
  created_at?: number | null;
};

export type MarketDTO = {
  id: string;
  key: string;
  desc: string;
  currency: string;
  room_id: string;
  visible_listings?: number;
  listing_ttl_seconds?: number;
  listings: MarketListingDTO[];
  paging: {
    page: number;
    per_page: number;
    total_count: number;
    total_pages: number;
    keyword?: string | null;
  };
};

export type MarketStatusDTO = {
  market: MarketDTO | null;
  active: MarketListingDTO[];
  sold: MarketListingDTO[];
  reclaimable: MarketListingDTO[];
  pending_earnings: number;
  summary: {
    active_count: number;
    sold_count: number;
    reclaimable_count: number;
  };
};

export type TradeOfferDTO = TradeOrListingSummaryDTO;

export type TradeStatusDTO = {
  incoming: TradeOfferDTO[];
  outgoing: TradeOfferDTO[];
  expired_offers_count: number;
  summary: {
    incoming_count: number;
    outgoing_count: number;
    expired_offers_count: number;
  };
};

export type RoomDTO = {
  id: string;
  room_key: string;
  key: string;
  desc: string;
  area_id?: string | null;
  area_key?: string | null;
  exits: RoomExitDTO[];
  npcs: RoomEntityDTO[];
  objects: RoomEntityDTO[];
  enemies: RoomEntityDTO[];
  shop: ShopDTO | null;
  market: MarketDTO | null;
};

export type ZoneDTO = {
  id: string;
  key: string;
  desc: string;
  map_id?: string | null;
  recommended_realm?: RealmRecommendationDTO | null;
};

export type WorldPositionDTO = {
  map?: { id: string; key: string; desc: string } | null;
  zone?: {
    id: string;
    key: string;
    desc: string;
    map_id?: string | null;
    recommended_realm?: string | null;
  } | null;
  area?: AreaDTO | null;
  room: RoomDTO;
};

export type QuestEntryDTO = {
  key?: string;
  id?: string | null;
  state?: string | null;
  title?: string | null;
  objective?: string | null;
  giver?: string | null;
  giver_npc_id?: string | null;
  required_item_id?: string | null;
  completed?: boolean;
  available?: boolean;
};

export type QuestLogDTO = {
  main: QuestEntryDTO;
  side: QuestEntryDTO[];
};

export type BootstrapPayload = {
  character: CharacterDTO;
  position: WorldPositionDTO;
  quests: QuestLogDTO;
  inventory: InventoryItemDTO[];
};

export type ProtocolOverviewPayload = {
  version: string;
  http_base: string;
  actions: string[];
  routes: Record<string, string>;
};

export type ProtocolOverviewResponse = H5Envelope<ProtocolOverviewPayload>;

export type BootstrapResponse = H5Envelope<BootstrapPayload>;

export type QuestLogResponse = H5Envelope<{
  quests: QuestLogDTO;
}>;

export type ShopDetailResponse = H5Envelope<{
  shop: ShopDTO;
  character: CharacterDTO;
}>;

export type MarketDetailResponse = H5Envelope<{
  market: MarketDTO;
  character: CharacterDTO;
}>;

export type CharacterSelectResponse = H5Envelope<{
  active_character_id: number;
  bootstrap: BootstrapPayload;
}>;

export type ActionResponse<T> = H5Envelope<T>;

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
