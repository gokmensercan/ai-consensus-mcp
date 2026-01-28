"""Pydantic models for structured AI responses"""

from datetime import datetime
from pydantic import BaseModel, Field


class AIResponse(BaseModel):
    """Single AI provider response"""

    provider: str = Field(description="AI provider name (gemini, codex)")
    response: str = Field(description="The AI's response text")
    success: bool = Field(description="Whether the call was successful")
    error: str | None = Field(default=None, description="Error message if failed")


class ConsensusResult(BaseModel):
    """Result from parallel AI queries"""

    gemini: AIResponse = Field(description="Gemini AI response")
    codex: AIResponse = Field(description="Codex AI response")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp of the query",
    )

    def format_markdown(self) -> str:
        """Format the result as markdown for display"""
        return f"""## Gemini Response:
{self.gemini.response if self.gemini.success else f"Error: {self.gemini.error}"}

---

## Codex Response:
{self.codex.response if self.codex.success else f"Error: {self.codex.error}"}

---
_Timestamp: {self.timestamp}_"""


class SynthesisResult(BaseModel):
    """Result from consensus with synthesis"""

    gemini: AIResponse = Field(description="Gemini AI response")
    codex: AIResponse = Field(description="Codex AI response")
    synthesis: AIResponse = Field(description="Synthesized response")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp of the query",
    )

    def format_markdown(self) -> str:
        """Format the result as markdown for display"""
        return f"""## Gemini Response:
{self.gemini.response if self.gemini.success else f"Error: {self.gemini.error}"}

---

## Codex Response:
{self.codex.response if self.codex.success else f"Error: {self.codex.error}"}

---

## Synthesis (by Gemini):
{self.synthesis.response if self.synthesis.success else f"Error: {self.synthesis.error}"}

---
_Timestamp: {self.timestamp}_"""
