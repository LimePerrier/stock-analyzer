from typing import Literal
from pydantic import BaseModel, Field

AnalysisType = Literal["earnings", "catalyst", "twitter_feed"]


class UrlJobCreate(BaseModel):
    ticker: str = Field(min_length=1)
    title: str | None = None
    analysis_type: Literal["earnings", "catalyst"]
    urls: list[str] = Field(default_factory=list)
    model: str = "claude-sonnet-4-5"


class TextJobCreate(BaseModel):
    ticker: str = Field(min_length=1)
    title: str | None = None
    model: str = "claude-sonnet-4-5"


class PromptUpdate(BaseModel):
    content: str = Field(min_length=1)
