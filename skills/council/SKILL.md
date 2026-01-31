---
name: council
description: 3 asamali LLM Council pipeline - gorusler, peer review, baskan sentezi
---

# LLM Council Pipeline

Kullanicinin sorusunu 3 asamali bir konsey pipeline'indan gecir.

## Soru
$ARGUMENTS

## Gorev
`mcp__ai-consensus__council` aracini kullanarak soruyu 3 asamali konsey pipeline'indan gecir:

1. **Stage 1 - Ilk Gorusler:** Gemini, Codex ve Copilot'a paralel sorgu
2. **Stage 2 - Peer Review:** Her model, diger modellerin yanitlarini degerlendirir
3. **Stage 3 - Baskan Sentezi:** Baskan model tum yanitlari ve degerlendirmeleri sentezler
