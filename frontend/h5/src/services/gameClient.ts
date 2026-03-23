import { api } from "./api";

import type {
  CharacterListResponse,
  H5Envelope,
  LoginResponse,
  PollBatchResponse,
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
  return api.post<H5Envelope<{ active_character_id: number; bootstrap: unknown }>>(
    "/api/h5/account/characters/select/",
    { character_id: characterId },
  );
}

export async function bootstrap() {
  return api.get<H5Envelope<unknown>>("/api/h5/bootstrap/");
}

export async function getRealtimeMeta() {
  return api.get<WsMetaResponse>("/api/h5/ws-meta/");
}

export async function pollEvents(cursor?: string) {
  const search = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
  return api.get<PollBatchResponse>(`/api/h5/events/poll/${search}`);
}
