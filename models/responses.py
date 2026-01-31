"""Pydantic models for structured AI responses"""

from datetime import datetime
from pydantic import BaseModel, Field


class AIResponse(BaseModel):
    """Single AI provider response"""

    provider: str = Field(description="AI provider name (gemini, codex, copilot)")
    response: str = Field(description="The AI's response text")
    success: bool = Field(description="Whether the call was successful")
    error: str | None = Field(default=None, description="Error message if failed")


class ConsensusResult(BaseModel):
    """Result from parallel AI queries"""

    gemini: AIResponse = Field(description="Gemini AI response")
    codex: AIResponse = Field(description="Codex AI response")
    copilot: AIResponse | None = Field(default=None, description="Copilot AI response")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp of the query",
    )

    def format_markdown(self) -> str:
        """Format the result as markdown for display"""
        parts = [
            f"## Gemini Response:\n{self.gemini.response if self.gemini.success else f'Error: {self.gemini.error}'}",
            "---",
            f"## Codex Response:\n{self.codex.response if self.codex.success else f'Error: {self.codex.error}'}",
        ]
        if self.copilot is not None:
            parts.append("---")
            parts.append(
                f"## Copilot Response:\n{self.copilot.response if self.copilot.success else f'Error: {self.copilot.error}'}"
            )
        parts.append("---")
        parts.append(f"_Timestamp: {self.timestamp}_")
        return "\n\n".join(parts)


class SynthesisResult(BaseModel):
    """Result from consensus with synthesis"""

    gemini: AIResponse = Field(description="Gemini AI response")
    codex: AIResponse = Field(description="Codex AI response")
    copilot: AIResponse | None = Field(default=None, description="Copilot AI response")
    synthesis: AIResponse = Field(description="Synthesized response")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp of the query",
    )

    def format_markdown(self) -> str:
        """Format the result as markdown for display"""
        parts = [
            f"## Gemini Response:\n{self.gemini.response if self.gemini.success else f'Error: {self.gemini.error}'}",
            "---",
            f"## Codex Response:\n{self.codex.response if self.codex.success else f'Error: {self.codex.error}'}",
        ]
        if self.copilot is not None:
            parts.append("---")
            parts.append(
                f"## Copilot Response:\n{self.copilot.response if self.copilot.success else f'Error: {self.copilot.error}'}"
            )
        parts.append("---")
        parts.append(
            f"## Synthesis (by Gemini):\n{self.synthesis.response if self.synthesis.success else f'Error: {self.synthesis.error}'}"
        )
        parts.append("---")
        parts.append(f"_Timestamp: {self.timestamp}_")
        return "\n\n".join(parts)
