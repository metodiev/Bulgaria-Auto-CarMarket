export interface SourceBrief {
  id: string;
  slug: string;
  name: string;
}

export interface Source extends SourceBrief {
  base_url: string;
  robots_url: string | null;
  terms_url: string | null;
  status: string;
  enabled: boolean;
  notes: string | null;
  capabilities: Record<string, unknown>;
  config: Record<string, unknown>;
  last_health_status: string | null;
  last_health_checked_at: string | null;
  listing_count: number;
  created_at: string;
  updated_at: string;
}

export interface ListingImage {
  id: string;
  original_url: string;
  storage_key: string | null;
  checksum_sha256: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  download_status: string;
  downloaded_at: string | null;
}

export interface Listing {
  id: string;
  source_id: string;
  source: SourceBrief;
  source_listing_id: string;
  canonical_url: string;
  title: string;
  make: string | null;
  model: string | null;
  generation: string | null;
  year: number | null;
  price: number | null;
  currency: string | null;
  mileage_km: number | null;
  fuel_type: string | null;
  engine_volume: number | null;
  power_kw: number | null;
  power_hp: number | null;
  transmission: string | null;
  body_type: string | null;
  drivetrain: string | null;
  condition: string | null;
  color: string | null;
  city: string | null;
  region: string | null;
  seller_type: string | null;
  description: string | null;
  first_seen_at: string;
  last_seen_at: string;
  last_checked_at: string | null;
  status: string;
  primary_image_url: string | null;
  images?: ListingImage[];
  duplicate_of_id?: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface StatBucket {
  key: string;
  count: number;
  avg_price: number | null;
}

export interface MarketStats {
  total_active: number;
  new_last_7_days: number;
  price_changes_30d: number;
  avg_price: number | null;
  median_price: number | null;
  by_source: StatBucket[];
  by_make: StatBucket[];
  by_model: StatBucket[];
  by_region: StatBucket[];
  by_fuel: StatBucket[];
  by_year: StatBucket[];
}

export interface ScraperError {
  id: string;
  run_id: string;
  source_id: string;
  url: string | null;
  error_type: string;
  message: string;
  occurred_at: string;
}

export interface ScrapeRun {
  id: string;
  source_id: string;
  search_job_id: string | null;
  status: string;
  triggered_by: string;
  started_at: string | null;
  completed_at: string | null;
  pages_fetched: number;
  listings_found: number;
  listings_created: number;
  listings_updated: number;
  listings_unchanged: number;
  errors_count: number;
  error_message: string | null;
  stats: Record<string, unknown>;
  created_at: string;
  errors?: ScraperError[];
}

export interface SearchJob {
  id: string;
  source_id: string;
  source: SourceBrief;
  name: string;
  filters: Record<string, unknown>;
  enabled: boolean;
  interval_minutes: number;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ListingFilterOptions {
  makes: string[];
  models: string[];
  regions: string[];
  fuel_types: string[];
  transmissions: string[];
  sources: SourceBrief[];
  years: number[];
}

export interface DedupListingBrief {
  id: string;
  title: string;
  price: number | null;
  currency: string | null;
  year: number | null;
  mileage_km: number | null;
  canonical_url: string;
  source: SourceBrief & { status?: string };
}

export interface DedupCandidate {
  id: string;
  score: number;
  reasons: Record<string, number | string>;
  status: string;
  created_at: string;
  resolved_at: string | null;
  listing_a: DedupListingBrief;
  listing_b: DedupListingBrief;
}

export interface AISettings {
  enabled: boolean;
  base_url: string;
  model_name: string;
  default_task: string;
  auto_analyze: boolean;
  include_descriptions: boolean;
  analyze_images: boolean;
  max_concurrency: number;
  timeout_seconds: number;
  max_attempts: number;
  updated_at: string;
}

export interface AIModel {
  name: string;
  size: number | null;
  modified_at: string | null;
}

export interface AIModelsResponse {
  reachable: boolean;
  models: AIModel[];
  error: string | null;
}

export interface AIHealth {
  configured: boolean;
  enabled: boolean;
  reachable: boolean;
  model: string;
  model_available: boolean;
  message: string;
}

export interface AIRankingItem {
  listing_id: string;
  rank: number;
  score: number | null;
  reasoning: string;
  pros: string[];
  cons: string[];
  price_comparison: string | null;
  confidence: number;
}

export interface AIAnalysisOutput {
  summary: string;
  methodology: string;
  candidate_listing_ids: string[];
  ranking: AIRankingItem[];
  pros: string[];
  cons: string[];
  price_comparison: string;
  confidence: number;
  limitations: string[];
  original_urls: string[];
  candidate_details?: Record<
    string,
    {
      title: string;
      url: string;
      price: number | null;
      currency: string | null;
      year: number | null;
      mileage_km: number | null;
      make: string | null;
      model: string | null;
    }
  >;
  _validation?: { warnings: string[] };
  validation?: { warnings: string[] };
}

export interface AIAnalysisRun {
  id: string;
  task_type: string;
  status: string;
  model_name: string;
  prompt_version: string;
  filter_config: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  input_count: number;
  output_json: Record<string, unknown> | null;
  error_message: string | null;
  progress: number;
  cancel_requested: boolean;
  attempt: number;
  created_at: string;
}

export interface AIAnalysisResult extends AIAnalysisRun {
  output: AIAnalysisOutput | null;
}

export interface PricePoint {
  price: number;
  currency: string;
  observed_at: string;
  source: string;
}
