# AI Consensus MCP Server

Birden fazla AI'dan (Gemini, Codex ve Copilot) paralel yanıtlar alarak konsensüs sağlayan Model Context Protocol (MCP) sunucusu.

## Özellikler

- **FastMCP 3.0.0b1** altyapısı ile modern MCP desteği
- **Asenkron paralel sorgulama** - Gemini, Codex ve Copilot'a eş zamanlı istek
- **18 MCP aracı** - Tekil sorgular, konsensüs, council pipeline ve multi-agent orchestration
- **Modüler yapı** - Providers, tools, models ve utils ayrımı
- **Pydantic modelleri** ile yapılandırılmış çıktılar
- **Context logging** ve ilerleme raporlama

## Ön Koşullar

| Gereksinim | Açıklama |
|------------|----------|
| Python 3.11+ | Async/await ve modern tip desteği için |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | Google AI'a erişim için kurulu ve yapılandırılmış olmalı |
| [Codex CLI](https://github.com/openai/codex) | OpenAI Codex'e erişim için kurulu ve yapılandırılmış olmalı |
| [Copilot CLI](https://github.com/github/copilot-cli) | GitHub Copilot'a erişim için kurulu ve yapılandırılmış olmalı |

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
| `GEMINI_DEFAULT_MODEL` | - | Varsayılan Gemini modeli (örn: `gemini-2.0-flash`) |
| `MCP_LOG_LEVEL` | `INFO` | Log seviyesi |
| `MCP_MASK_ERRORS` | `false` | Hata detaylarını maskele |

## Araçlar

### Tekil Sorgular

| Araç | Açıklama | Parametreler |
|------|----------|--------------|
| `ask_gemini` | Gemini AI'a soru sor | `prompt`, `model` (opsiyonel) |
| `ask_codex` | Codex AI'a soru sor | `prompt` |
| `ask_copilot` | Copilot AI'a soru sor | `prompt` |

### Konsensüs

| Araç | Açıklama | Parametreler |
|------|----------|--------------|
| `consensus` | Üçüne paralel sor, yanıtları karşılaştır | `prompt`, `gemini_model`, `use_cache` |
| `consensus_with_synthesis` | Paralel sor + Gemini ile sentezle | `prompt`, `gemini_model`, `use_cache` |
| `consensus_with_elicitation` | Paralel sor, çakışmada kullanıcıya sor | `prompt`, `gemini_model` |
| `get_last_consensus` | Son cache'lenmiş sonucu getir | - |
| `clear_consensus_cache` | Tüm cache'i temizle | - |

### LLM Council Pipeline

[karpathy/llm-council](https://github.com/karpathy/llm-council)'dan ilham alan 3 aşamalı pipeline:

| Araç | Açıklama | Parametreler |
|------|----------|--------------|
| `council` | 3 aşamalı konsey pipeline | `prompt`, `gemini_model`, `chairman`, `use_cache` |

**3 Aşama:**
1. **Stage 1 - İlk Görüşler:** Gemini, Codex ve Copilot'a paralel sorgu
2. **Stage 2 - Peer Review:** Her model, diğer modellerin yanıtlarını anonim olarak değerlendirir
3. **Stage 3 - Başkan Sentezi:** Seçilen başkan model (varsayılan: Gemini) tüm yanıtları + değerlendirmeleri alarak nihai sentez üretir

### Multi-Agent Orchestration

| Araç | Açıklama | Parametreler |
|------|----------|--------------|
| `agent_handoff` | Senkron agent delegasyonu | `agent_name`, `prompt`, `timeout` |
| `agent_assign` | Asenkron görev atama | `agent_name`, `prompt`, `timeout` |
| `check_task` | Async görev durumu kontrolü | `task_id` |
| `list_tasks` | Tüm görevleri listele | `agent_name`, `status` (opsiyonel) |
| `send_agent_message` | Agent inbox'a mesaj gönder | `agent_name`, `content` |
| `read_agent_inbox` | Agent mesajlarını oku | `agent_name` |
| `inbox_summary` | Agent inbox özeti | `agent_name` |
| `list_agents` | Kayıtlı agent'ları listele | - |
| `cleanup_tasks` | Eski görevleri temizle | `max_age_hours` |

## Slash Commands

Claude Code içinden slash command olarak kullanım:

| Komut | Açıklama |
|-------|----------|
| `/consensus <soru>` | Paralel sorgu + karşılaştırma |
| `/consensus-synthesize <soru>` | Paralel sorgu + sentez |
| `/council <soru>` | 3 aşamalı LLM Council pipeline |
| `/orchestrate <görev>` | Multi-agent orchestration |

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
│   ├── codex.py           # Codex CLI entegrasyonu
│   ├── copilot.py         # Copilot CLI entegrasyonu
│   └── subprocess_runner.py # Subprocess yönetimi
├── tools/
│   ├── __init__.py
│   ├── single.py          # ask_gemini, ask_codex, ask_copilot araçları
│   ├── consensus.py       # consensus, synthesis, elicitation araçları
│   ├── council.py         # 3 aşamalı LLM Council pipeline
│   └── orchestration.py   # Multi-agent orchestration araçları
├── models/
│   ├── __init__.py
│   ├── responses.py       # AIResponse, ConsensusResult, SynthesisResult
│   ├── council.py         # PeerReview, CouncilResult
│   └── orchestration.py   # Agent/task modelleri
├── agents/
│   ├── __init__.py
│   ├── base.py            # BaseAgent soyut sınıfı
│   ├── gemini_agent.py    # Gemini worker agent
│   ├── codex_agent.py     # Codex worker agent
│   ├── copilot_agent.py   # Copilot worker agent
│   └── registry.py        # Agent registry
├── skills/
│   ├── consensus/         # /consensus slash command
│   ├── consensus-synthesize/ # /consensus-synthesize slash command
│   ├── council/           # /council slash command
│   └── orchestrate/       # /orchestrate slash command
└── utils/
    ├── __init__.py
    ├── context_helpers.py # Context logging yardımcıları
    └── state.py           # Session state ve cache yönetimi
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
│  ┌──────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │ single.py    │  │ consensus.py     │  │ council.py  │ │
│  │ - ask_gemini │  │ - consensus      │  │ - council   │ │
│  │ - ask_codex  │  │ - synthesis      │  │  (3-stage)  │ │
│  │ - ask_copilot│  │ - elicitation    │  └─────────────┘ │
│  └──────────────┘  └──────────────────┘                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ orchestration.py                                     │  │
│  │ - handoff, assign, messaging, task management        │  │
│  └─────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│  Providers Layer (asyncio.gather ile paralel çalışır)     │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────┐ │
│  │ gemini.py      │  │ codex.py       │  │ copilot.py  │ │
│  │ subprocess→CLI │  │ subprocess→CLI │  │ subprocess  │ │
│  └───────┬────────┘  └───────┬────────┘  │  → CLI      │ │
└──────────┼───────────────────┼───────────┴──┬──────────┘─┘
           │                   │              │
           ▼                   ▼              ▼
    ┌─────────────┐     ┌─────────────┐  ┌─────────────┐
    │ Gemini CLI  │     │ Codex CLI   │  │ Copilot CLI │
    │ (gemini)    │     │ (codex)     │  │ (copilot)   │
    └─────────────┘     └─────────────┘  └─────────────┘
```

## Lisans

MIT
