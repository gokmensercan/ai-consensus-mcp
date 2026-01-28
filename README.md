# AI Consensus MCP Server

Birden fazla AI'dan (Gemini ve Codex) paralel yanıtlar alarak konsensüs sağlayan Model Context Protocol (MCP) sunucusu.

## Özellikler

- **FastMCP 3.0.0b1** altyapısı ile modern MCP desteği
- **Asenkron paralel sorgulama** - Gemini ve Codex'e eş zamanlı istek
- **4 MCP aracı** - Tekil sorgular ve konsensüs araçları
- **Modüler yapı** - Providers, tools, models ve utils ayrımı
- **Pydantic modelleri** ile yapılandırılmış çıktılar
- **Context logging** ve ilerleme raporlama

## Ön Koşullar

| Gereksinim | Açıklama |
|------------|----------|
| Python 3.11+ | Async/await ve modern tip desteği için |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | Google AI'a erişim için kurulu ve yapılandırılmış olmalı |
| [Codex CLI](https://github.com/openai/codex) | OpenAI Codex'e erişim için kurulu ve yapılandırılmış olmalı |

## Kurulum

### Bağımlılıkları Yükle

```bash
pip install "fastmcp>=3.0.0b1" pydantic
```

### Claude Code'a Ekle

```bash
claude mcp add ai-consensus -- python3 /path/to/ai-consensus-mcp/server.py
```

### Doğrulama

```bash
claude mcp list
```

## Yapılandırma

Ortam değişkenleri ile yapılandırma:

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `GEMINI_CWD` | `/tmp` | Gemini CLI çalışma dizini |
| `GEMINI_DEFAULT_MODEL` | - | Varsayılan Gemini modeli (örn: `gemini-2.0-flash`) |
| `CODEX_CWD` | `/tmp/codex-workspace` | Codex CLI çalışma dizini |
| `MCP_LOG_LEVEL` | `INFO` | Log seviyesi |
| `MCP_MASK_ERRORS` | `false` | Hata detaylarını maskele |

## Araçlar

| Araç | Açıklama | Parametreler |
|------|----------|--------------|
| `ask_gemini` | Gemini AI'a soru sor | `prompt`, `model` (opsiyonel) |
| `ask_codex` | Codex AI'a soru sor | `prompt` |
| `consensus` | Her ikisine paralel sor, iki yanıtı karşılaştır | `prompt`, `gemini_model` (opsiyonel) |
| `consensus_with_synthesis` | Paralel sor + Gemini ile sentezle | `prompt`, `gemini_model` (opsiyonel) |

## MCP İstemci Entegrasyonu

### Claude Code

```bash
claude mcp add ai-consensus -- python3 /absolute/path/to/server.py
```

### Claude Desktop

`~/.config/claude/claude_desktop_config.json` dosyasına ekleyin:

```json
{
  "mcpServers": {
    "ai-consensus": {
      "command": "python3",
      "args": ["/absolute/path/to/ai-consensus-mcp/server.py"],
      "env": {
        "GEMINI_DEFAULT_MODEL": "gemini-2.0-flash"
      }
    }
  }
}
```

## Proje Yapısı

```
ai-consensus-mcp/
├── server.py              # Ana MCP sunucusu
├── config.py              # Ortam değişkenleri yapılandırması
├── providers/
│   ├── __init__.py
│   ├── gemini.py          # Gemini CLI entegrasyonu
│   └── codex.py           # Codex CLI entegrasyonu
├── tools/
│   ├── __init__.py
│   ├── single.py          # ask_gemini, ask_codex araçları
│   └── consensus.py       # consensus, consensus_with_synthesis araçları
├── models/
│   ├── __init__.py
│   └── responses.py       # Pydantic response modelleri
└── utils/
    ├── __init__.py
    └── context_helpers.py # Context logging yardımcıları
```

## Geliştirme

### Sunucuyu Test Et

```bash
fastmcp inspect server.py
```

### MCP Inspector ile Debug

```bash
npx @anthropics/inspector python3 server.py
```

## Mimari

```
┌────────────────────────────────────────────────────────────┐
│                      MCP İstemci                           │
│              (Claude Code / Claude Desktop)                │
└─────────────────────────┬──────────────────────────────────┘
                          │ MCP Protocol (stdio)
┌─────────────────────────▼──────────────────────────────────┐
│                  AI Consensus Server                       │
│                    (FastMCP 3.0)                           │
├────────────────────────────────────────────────────────────┤
│  Tools Layer                                               │
│  ┌──────────────┐  ┌───────────────────────────────────┐  │
│  │ single.py    │  │ consensus.py                      │  │
│  │ - ask_gemini │  │ - consensus                       │  │
│  │ - ask_codex  │  │ - consensus_with_synthesis        │  │
│  └──────────────┘  └───────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│  Providers Layer (asyncio.gather ile paralel çalışır)     │
│  ┌────────────────────┐  ┌────────────────────┐           │
│  │ gemini.py          │  │ codex.py           │           │
│  │ subprocess → CLI   │  │ subprocess → CLI   │           │
│  └─────────┬──────────┘  └──────────┬─────────┘           │
└────────────┼─────────────────────────┼─────────────────────┘
             │                         │
             ▼                         ▼
      ┌─────────────┐           ┌─────────────┐
      │ Gemini CLI  │           │ Codex CLI   │
      │ (gemini)    │           │ (codex)     │
      └─────────────┘           └─────────────┘
```

## Lisans

MIT
