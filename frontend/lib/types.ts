/**
 * Shared types mirroring the backend API responses
 * (see backend/app/schemas/*.py and backend/app/api/v1/*.py).
 * Datetimes are serialized as ISO 8601 strings.
 */
import axios from "axios";

export const SOURCE_CATEGORIES = [
  "Tech",
  "Business",
  "News",
  "Entertainment",
  "Science",
  "Health",
  "Sport",
] as const;

export type SourceCategory = (typeof SOURCE_CATEGORIES)[number];

/** SourceResponse */
export interface Source {
  id: number;
  user_id: number;
  name: string;
  url: string;
  category: SourceCategory | null;
  is_active: boolean;
  created_at: string;
}

/** FeedTestResponse */
export interface FeedTestResult {
  valid: boolean;
  title?: string | null;
  entries?: number;
  error?: string | null;
}

/** CategoriesResponse */
export interface CategoriesResponse {
  categories: string[];
}

/** ScheduleResponse (source_ids only present on ScheduleWithSources) */
export interface Schedule {
  id: number;
  user_id: number;
  name: string;
  cron_expression: string;
  timezone: string;
  max_articles: number;
  profile: string;
  language: string;
  is_active: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  created_at: string;
  source_ids?: number[];
}

/** POST /api/schedules/{id}/run */
export interface ScheduleRunResult {
  status: string;
  digest_id: number;
  articles_processed: number;
  message: string;
  deliveries: Record<string, string>;
}

/** GET /api/digests */
export interface Digest {
  id: number;
  schedule_id: number;
  schedule_name: string;
  content_text: string;
  status: string;
  created_at: string;
}

export type DeliveryChannelType = "discord" | "email";

export interface DiscordChannelConfig {
  webhook_url: string;
}

export interface EmailChannelConfig {
  email: string;
}

/** DeliveryChannelResponse */
export interface DeliveryChannel {
  id: number;
  schedule_id: number;
  type: DeliveryChannelType;
  is_enabled: boolean;
  config: DiscordChannelConfig | EmailChannelConfig | Record<string, unknown> | string;
  created_at: string;
}

/** DeliveryChannelWithValidation */
export interface DeliveryChannelWithValidation {
  channel: DeliveryChannel;
  valid: boolean;
  error?: string | null;
}

/** TokenResponse (POST /api/auth/login) */
export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  email: string;
}

/** FastAPI error body */
export interface ApiErrorBody {
  detail?: string;
}

/**
 * Extracts the FastAPI `detail` message from an axios error,
 * or returns undefined if not available.
 */
export function getApiErrorDetail(err: unknown): string | undefined {
  if (axios.isAxiosError<ApiErrorBody>(err)) {
    return err.response?.data?.detail;
  }
  return undefined;
}
