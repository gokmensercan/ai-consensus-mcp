"""Single AI query tools"""

from providers import call_gemini, call_codex


def register_single_tools(mcp):
    """Register single-AI query tools to the MCP server"""

    @mcp.tool()
    async def ask_gemini(prompt: str, model: str = None) -> str:
        """
        Ask Gemini AI a question using local Gemini CLI.

        Args:
            prompt: The prompt to send to Gemini
            model: Optional model (e.g., gemini-2.0-flash)
        """
        return await call_gemini(prompt, model)

    @mcp.tool()
    async def ask_codex(prompt: str) -> str:
        """
        Ask Codex AI a question using local Codex CLI.

        Args:
            prompt: The prompt to send to Codex
        """
        return await call_codex(prompt)
