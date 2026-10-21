export type SourceLanguage = "ru" | "en";

export type EntryType =
  | "word"
  | "phrasal_verb"
  | "collocation"
  | "idiom"
  | "proverb"
  | "expression";

export interface WordFamilyItem {
  word: string;
  part_of_speech: string;
  translation: string;
}

export interface CardChunk {
  text: string;
  target: string;
  translation: string;
}

export interface Card {
  id: number;
  source_text: string;
  source_language: SourceLanguage;
  entry_type: EntryType;
  canonical_text: string;
  canonical_text_normalized: string;
  transcription: string | null;
  translation_variants: string[];
  word_family: WordFamilyItem[];
  explanation: string;
  examples: string[];
  chunks: CardChunk[];
  frequency: number;
  frequency_note: string | null;
  is_learning: boolean;
  // FSRS state ('learning' | 'review' | 'relearning'); null until the first review.
  srs_state: string | null;
  srs_due_at: string | null;
  llm_model: string;
  created_at: string;
  updated_at: string;
}

export interface CardListResponse {
  items: Card[];
  total: number;
  offset: number;
  limit: number;
}

export interface CardsQuery {
  offset?: number;
  limit?: number;
  search?: string;
  source_language?: SourceLanguage;
  entry_type?: EntryType;
  is_learning?: boolean;
}

export type CardBatchImportItemStatus =
  | "created"
  | "duplicate_source"
  | "duplicate_canonical"
  | "rejected"
  | "invalid_input"
  | "upstream_error";

export interface CardBatchImportItem {
  source_text: string;
  status: CardBatchImportItemStatus;
  card_id: number | null;
  canonical_text: string | null;
  message: string | null;
}

export interface CardBatchImportSummary {
  total: number;
  created: number;
  duplicate_source: number;
  duplicate_canonical: number;
  rejected: number;
  invalid_input: number;
  upstream_error: number;
}

export interface CardBatchImportResponse {
  items: CardBatchImportItem[];
  summary: CardBatchImportSummary;
}

export interface ReviewSummary {
  // Distinct cards answered today that are not due again; due/new are what remains.
  done_today: number;
  due_today: number;
  new_today: number;
  est_minutes: number;
  backlog: number;
  due_all: number;
  // Shares of the mature answers of the last 30 days; retention is everything but Again.
  retention_30d: number | null;
  hard_share_30d: number | null;
  again_share_30d: number | null;
  learned_total: number;
  learned_delta_7d: number;
  streak_days: number;
  best_streak_days: number;
  heatmap: number[];
  forecast_tomorrow: number;
  forecast_week_avg: number;
  days_away: number | null;
}

export type PromptKind = "chunk" | "translation";

export interface ReviewPrompt {
  kind: PromptKind;
  index: number;
  masked: string;
  hint_translation: string;
}

export interface ReviewSessionItem {
  card: Card;
  intro: boolean;
  prompt: ReviewPrompt;
  srs_due_at: string | null;
}

export interface ReviewSessionResponse {
  items: ReviewSessionItem[];
}

export type Verdict = "correct" | "typo" | "form" | "wrong";

export interface CheckRequest {
  typed: string;
  prompt_kind: PromptKind;
  prompt_index: number;
  hint_used: boolean;
}

export interface CheckResponse {
  verdict: Verdict;
  expected: string;
  auto_rating: number;
  // JSON object keys: rating "1".."4" -> interval in seconds.
  intervals: Record<string, number>;
}

export interface GradeRequest {
  rating: number;
  auto_rating: number;
  overridden: boolean;
  typed: string;
  prompt_kind: PromptKind;
  prompt_index: number;
  verdict: Verdict | "skipped";
  hint_used: boolean;
  response_ms: number;
  expected_due_at: string | null;
}

export interface GradeResponse {
  srs_due_at: string;
  srs_state: string;
}

export interface AppSettings {
  timezone: string;
  reminder_hour: number;
  reminder_anchor: string | null;
  new_per_day: number;
  reviews_per_day: number;
  desired_retention: number;
  learn_threshold: number;
  // Read-only from the server (Google TTS key set); PUT ignores it.
  readonly tts_enabled?: boolean;
}
