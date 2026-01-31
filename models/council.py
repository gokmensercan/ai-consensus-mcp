"""Pydantic models for LLM Council pipeline"""

from datetime import datetime

from pydantic import BaseModel, Field

from .responses import AIResponse


class PeerReview(BaseModel):
    """Peer review of another model's response"""

    reviewer: str = Field(description="Reviewer model name (gemini, codex, or copilot)")
    review: str = Field(description="Review text")
    success: bool = Field(description="Whether the review call was successful")
    error: str | None = Field(default=None, description="Error message if failed")


class CouncilResult(BaseModel):
    """Result from the 3-stage LLM Council pipeline"""

    # Stage 1 - Initial opinions
    gemini: AIResponse = Field(description="Gemini AI response")
    codex: AIResponse = Field(description="Codex AI response")
    copilot: AIResponse | None = Field(default=None, description="Copilot AI response")
    # Stage 2 - Peer reviews
    gemini_review: PeerReview = Field(
        description="Gemini's review of other responses"
    )
    codex_review: PeerReview = Field(
        description="Codex's review of other responses"
    )
    copilot_review: PeerReview | None = Field(
        default=None, description="Copilot's review of other responses"
    )
    # Stage 3 - Chairman synthesis
    chairman: str = Field(description="Chairman model name (gemini, codex, or copilot)")
    chairman_synthesis: AIResponse = Field(description="Chairman's final synthesis")
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp of the query",
    )

    def format_markdown(self) -> str:
        """Format the council result as markdown for display"""
        gemini_text = (
            self.gemini.response
            if self.gemini.success
            else f"Error: {self.gemini.error}"
        )
        codex_text = (
            self.codex.response
            if self.codex.success
            else f"Error: {self.codex.error}"
        )
        gemini_review_text = (
            self.gemini_review.review
            if self.gemini_review.success
            else f"Error: {self.gemini_review.error}"
        )
        codex_review_text = (
            self.codex_review.review
            if self.codex_review.success
            else f"Error: {self.codex_review.error}"
        )
        synthesis_text = (
            self.chairman_synthesis.response
            if self.chairman_synthesis.success
            else f"Error: {self.chairman_synthesis.error}"
        )

        has_copilot = self.copilot is not None

        # Build Stage 1
        parts = [
            "# LLM Council Result",
            "## Stage 1: First Opinions",
            f"### Gemini Response:\n{gemini_text}",
            f"### Codex Response:\n{codex_text}",
        ]

        if has_copilot:
            copilot_text = (
                self.copilot.response
                if self.copilot.success
                else f"Error: {self.copilot.error}"
            )
            parts.append(f"### Copilot Response:\n{copilot_text}")

        parts.append("---")

        # Build Stage 2
        parts.append("## Stage 2: Peer Reviews")

        if has_copilot:
            parts.append(
                f"### Gemini's Review (of Codex & Copilot):\n{gemini_review_text}"
            )
            parts.append(
                f"### Codex's Review (of Gemini & Copilot):\n{codex_review_text}"
            )
            if self.copilot_review is not None:
                copilot_review_text = (
                    self.copilot_review.review
                    if self.copilot_review.success
                    else f"Error: {self.copilot_review.error}"
                )
                parts.append(
                    f"### Copilot's Review (of Gemini & Codex):\n{copilot_review_text}"
                )
        else:
            parts.append(
                f"### Gemini's Review (of Codex's response):\n{gemini_review_text}"
            )
            parts.append(
                f"### Codex's Review (of Gemini's response):\n{codex_review_text}"
            )

        parts.append("---")

        # Build Stage 3
        parts.append(
            f"## Stage 3: Chairman Synthesis (by {self.chairman}):\n{synthesis_text}"
        )
        parts.append("---")
        parts.append(f"_Timestamp: {self.timestamp}_")

        return "\n\n".join(parts)
