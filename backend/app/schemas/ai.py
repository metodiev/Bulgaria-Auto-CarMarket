from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TaskType = Literal["best_deals", "price_anomalies", "market_overview"]


class AISettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    enabled: bool
    base_url: str
    model_name: str
    default_task: str
    auto_analyze: bool
    include_descriptions: bool
    analyze_images: bool
    max_concurrency: int
    timeout_seconds: float
    max_attempts: int
    updated_at: datetime


class AISettingsUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    enabled: bool | None = None
    base_url: str | None = Field(default=None, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=120)
    default_task: TaskType | None = None
    auto_analyze: bool | None = None
    include_descriptions: bool | None = None
    analyze_images: bool | None = None
    max_concurrency: int | None = Field(default=None, ge=1, le=4)
    timeout_seconds: float | None = Field(default=None, ge=10, le=600)
    max_attempts: int | None = Field(default=None, ge=1, le=5)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL трябва да започва с http:// или https://")
        return value.rstrip("/") if value else value


class AIModelInfo(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None


class AIModelsOut(BaseModel):
    reachable: bool
    models: list[AIModelInfo]
    error: str | None = None


class AIHealthOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    configured: bool
    enabled: bool
    reachable: bool
    model: str
    model_available: bool
    message: str


class AIAnalyzeRequest(BaseModel):
    task_type: TaskType = "best_deals"
    filters: dict = Field(default_factory=dict)
    candidate_limit: int | None = Field(default=None, ge=5, le=100)


class AIRankingItem(BaseModel):
    listing_id: str
    rank: int = Field(ge=1)
    score: float | None = Field(default=None, ge=0, le=100)
    reasoning: str = ""
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    price_comparison: str | None = None
    confidence: int = Field(default=5, ge=0, le=10)


class AIAnalysisOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    summary: str
    methodology: str
    candidate_listing_ids: list[str] = Field(default_factory=list)
    ranking: list[AIRankingItem] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    price_comparison: str = ""
    confidence: int = Field(default=5, ge=0, le=10)
    limitations: list[str] = Field(default_factory=list)
    original_urls: list[str] = Field(default_factory=list)
    candidate_details: dict[str, dict] = Field(default_factory=dict)
    validation: dict | None = Field(default=None, alias="_validation")


class AIAnalysisRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    task_type: str
    status: str
    model_name: str
    prompt_version: str
    filter_config: dict
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    input_count: int
    output_json: dict | None = None
    error_message: str | None = None
    progress: int
    cancel_requested: bool
    attempt: int
    created_at: datetime


class AIAnalysisResultOut(AIAnalysisRunOut):
    output: AIAnalysisOutput | None = None
