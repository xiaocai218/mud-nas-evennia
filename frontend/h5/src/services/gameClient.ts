import { api } from "./api";

import type {
  ActionResponse,
  BootstrapResponse,
  CharacterDTO,
  CharacterListResponse,
  CharacterSelectResponse,
  H5Envelope,
  InventoryItemDTO,
  LoginResponse,
  MarketDTO,
  MarketDetailResponse,
  MarketStatusDTO,
  PollBatchResponse,
  ProtocolOverviewResponse,
  QuestLogResponse,
  RoomDTO,
  ShopDetailResponse,
  TradeStatusDTO,
  WsMetaResponse,
} from "@/types";

export async function login(username: string, password: string) {
  return api.post<LoginResponse>("/api/h5/auth/login/", { username, password });
}

export async function logout() {
  return api.post<H5Envelope<{ logged_out: boolean }>>("/api/h5/auth/logout/");
}

export async function listCharacters() {
  return api.get<CharacterListResponse>("/api/h5/account/characters/");
}

export async function selectCharacter(characterId: number) {
  return api.post<CharacterSelectResponse>("/api/h5/account/characters/select/", {
    character_id: characterId,
  });
}

export async function bootstrap() {
  return api.get<BootstrapResponse>("/api/h5/bootstrap/");
}

export async function getProtocolOverview() {
  return api.get<ProtocolOverviewResponse>("/api/h5/");
}

export async function getQuestLog() {
  return api.get<QuestLogResponse>("/api/h5/quests/");
}

export async function getShopDetail(shopId: string) {
  return api.get<ShopDetailResponse>(`/api/h5/shops/${encodeURIComponent(shopId)}/`);
}

export async function getMarketDetail(marketId: string, params?: { page?: number; keyword?: string }) {
  const search = new URLSearchParams();
  if (params?.page) {
    search.set("page", String(params.page));
  }
  if (params?.keyword) {
    search.set("keyword", params.keyword);
  }
  const suffix = search.size ? `?${search.toString()}` : "";
  return api.get<MarketDetailResponse>(`/api/h5/markets/${encodeURIComponent(marketId)}/${suffix}`);
}

export async function getRealtimeMeta() {
  return api.get<WsMetaResponse>("/api/h5/ws-meta/");
}

export async function pollEvents(cursor?: string) {
  const search = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
  return api.get<PollBatchResponse>(`/api/h5/events/poll/${search}`);
}

type ActionPayloadMap = {
  look: Record<string, never>;
  move: { direction: string };
  buy_item: { target: string };
  market_listings: { page?: number; keyword?: string };
  market_status: Record<string, never>;
  market_create_listing: { target: string; price: number };
  market_buy_listing: { listing_id: string };
  market_cancel_listing: { listing_id: string };
  market_claim_earnings: Record<string, never>;
  trade_status: Record<string, never>;
  trade_create_offer: { target: string; item_name: string; price?: number };
  trade_accept_offer: { target?: string };
  trade_reject_offer: { target?: string };
  trade_cancel_offer: { target?: string };
};

type ActionResponseMap = {
  look: { room: RoomDTO };
  move: { room: RoomDTO };
  buy_item: {
    result: {
      price: number;
      remaining: number;
      currency: string;
      summary?: {
        item_name: string;
        price: number;
        currency: string;
        remaining: number;
      };
    };
    inventory: InventoryItemDTO[];
  };
  market_listings: { market: MarketDTO };
  market_status: { status: MarketStatusDTO; inventory: InventoryItemDTO[] };
  market_create_listing: {
    result: { listing: MarketStatusDTO["active"][number] };
    inventory: InventoryItemDTO[];
    market: MarketDTO | null;
    status: MarketStatusDTO | null;
  };
  market_buy_listing: {
    result: { listing: MarketDTO["listings"][number] };
    inventory: InventoryItemDTO[];
    market: MarketDTO | null;
  };
  market_cancel_listing: {
    result: { listing: MarketDTO["listings"][number] };
    inventory: InventoryItemDTO[];
    market: MarketDTO | null;
    status: MarketStatusDTO | null;
  };
  market_claim_earnings: {
    result: { amount: number; currency: string; current: number };
    character: CharacterDTO;
    status: MarketStatusDTO | null;
  };
  trade_status: { status: TradeStatusDTO; inventory: InventoryItemDTO[] };
  trade_create_offer: {
    result: { offer: TradeStatusDTO["outgoing"][number] };
    inventory: InventoryItemDTO[];
    status: TradeStatusDTO | null;
  };
  trade_accept_offer: {
    result: { offer: TradeStatusDTO["incoming"][number] };
    inventory: InventoryItemDTO[];
    status: TradeStatusDTO | null;
  };
  trade_reject_offer: {
    result: { offer: TradeStatusDTO["incoming"][number] };
    status: TradeStatusDTO | null;
  };
  trade_cancel_offer: {
    result: { offer: TradeStatusDTO["outgoing"][number] };
    status: TradeStatusDTO | null;
  };
};

export async function sendAction<TAction extends keyof ActionPayloadMap>(
  action: TAction,
  payload: ActionPayloadMap[TAction],
) {
  return api.post<ActionResponse<ActionResponseMap[TAction]>>("/api/h5/action/", {
    type: "action",
    action,
    payload,
  });
}

export function look() {
  return sendAction("look", {});
}

export function move(direction: string) {
  return sendAction("move", { direction });
}

export function buyItem(target: string) {
  return sendAction("buy_item", { target });
}

export function getMarketListings(page?: number, keyword?: string) {
  return sendAction("market_listings", { page, keyword });
}

export function getMyMarketStatus() {
  return sendAction("market_status", {});
}

export function createMarketListing(target: string, price: number) {
  return sendAction("market_create_listing", { target, price });
}

export function buyMarketListing(listingId: string) {
  return sendAction("market_buy_listing", { listing_id: listingId });
}

export function cancelMarketListing(listingId: string) {
  return sendAction("market_cancel_listing", { listing_id: listingId });
}

export function claimMarketEarnings() {
  return sendAction("market_claim_earnings", {});
}

export function getTradeStatus() {
  return sendAction("trade_status", {});
}

export function createTradeOffer(target: string, itemName: string, price?: number) {
  return sendAction("trade_create_offer", { target, item_name: itemName, price });
}

export function acceptTradeOffer(target?: string) {
  return sendAction("trade_accept_offer", target ? { target } : {});
}

export function rejectTradeOffer(target?: string) {
  return sendAction("trade_reject_offer", target ? { target } : {});
}

export function cancelTradeOffer(target?: string) {
  return sendAction("trade_cancel_offer", target ? { target } : {});
}
