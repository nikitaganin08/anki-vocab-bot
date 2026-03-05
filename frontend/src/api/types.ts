export type SourceLanguage = "ru" | "en";

export type EntryType =
  | "word"
  | "phrasal_verb"
  | "collocation"
  | "idiom"
  | "expression";

export type AnkiSyncStatus = "pending" | "synced" | "failed";

export interface Card {
  id: number;
  source_text: string;
  source_language: SourceLanguage;
  entry_type: EntryType;
  canonical_text: string;
  canonical_text_normalized: string;
  transcription: string | null;
  translation_variants: string[];
  explanation: string;
  examples: string[];
  frequency: number;
  frequency_note: string | null;
  eligible_for_anki: boolean;
  anki_sync_status: AnkiSyncStatus;
  anki_note_id: number | null;
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

export interface HealthResponse {
  status: string;
}

export interface CardsQuery {
  offset?: number;
  limit?: number;
  search?: string;
  source_language?: SourceLanguage;
  entry_type?: EntryType;
  anki_sync_status?: AnkiSyncStatus;
  eligible_for_anki?: boolean;
}

export type CardBatchImportItemStatus =
  | "created"
  | "duplicate_source"
  | "duplicate_canonical"
  | "rejected"
  | "invalid_input"
  | "upstream_error";

export interface CardBatchImportRequest {
  source_texts: string[];
}

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
