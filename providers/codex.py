"""Codex CLI provider"""

import asyncio


async def call_codex(prompt: str) -> str:
    """
    Call Codex CLI with the given prompt.

    Args:
        prompt: The prompt to send to Codex

    Returns:
        Codex's response text
    """
    cmd = ["codex", "exec", prompt]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/tmp"
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8").strip()

        if not output and stderr:
            output = f"Error: {stderr.decode('utf-8').strip()}"

        return output or "(empty)"

    except asyncio.TimeoutError:
        return "Error: Timeout (120s)"
    except FileNotFoundError:
        return "Error: codex command not found"
    except Exception as e:
        return f"Error: {e}"
