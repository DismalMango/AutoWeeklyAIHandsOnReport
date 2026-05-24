from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, HttpUrl


class ProductCandidate(BaseModel):
    name: str = Field(min_length=1)
    url: HttpUrl | str
    description: str = ""
    source_urls: list[HttpUrl | str] = Field(default_factory=list)
    recency_signal: str = ""
    ai_native_reason: str = ""


class ProductReport(BaseModel):
    product_name: str = Field(min_length=1)
    report_date: date
    markdown: str = Field(min_length=1)
    source_urls: list[HttpUrl | str] = Field(default_factory=list)
