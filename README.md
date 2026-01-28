# AI Consensus MCP Server

Gemini CLI ve Codex CLI'ı paralel çalıştırarak konsensüs sağlayan MCP sunucusu.

## Araçlar

| Tool | Açıklama |
|------|----------|
| `ask_gemini` | Gemini CLI'a soru sor |
| `ask_codex` | Codex CLI'a soru sor |
| `consensus` | Her ikisine paralel sor, iki yanıtı döndür |
| `consensus_with_synthesis` | Paralel sor + Gemini ile sentezle |

## Gereksinimler

- Python 3.10+
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- [Codex CLI](https://github.com/openai/codex)

```bash
pip install mcp
```

## Kurulum

### Claude Code'a Ekle

```bash
claude mcp add ai-consensus -- python3 /path/to/server.py
```

### Doğrulama

```bash
claude mcp list
```

## Mimari

```
                    ┌─────────────┐
                    │   Claude    │
                    │    Code     │
                    └──────┬──────┘
                           │ MCP
                    ┌──────▼──────┐
                    │ ai-consensus│
                    │   server    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌──────────┐
        │ Gemini  │  │ Codex   │  │ Parallel │
        │  CLI    │  │  CLI    │  │  Both    │
        └─────────┘  └─────────┘  └──────────┘
```

## Lisans

MIT
