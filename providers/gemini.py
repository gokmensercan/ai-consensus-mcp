"""Gemini CLI provider"""

import asyncio


async def call_gemini(prompt: str, model: str = None) -> str:
    """
    Call Gemini CLI with the given prompt.

    Args:
        prompt: The prompt to send to Gemini
        model: Optional model (e.g., gemini-2.0-flash)

    Returns:
        Gemini's response text
    """
    cmd = ["gemini", "-p", prompt, "-o", "text"]
    if model:
        cmd.extend(["-m", model])

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
        return "Error: gemini command not found"
    except Exception as e:
        return f"Error: {e}"
