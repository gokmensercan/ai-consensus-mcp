#!/bin/bash
# AI Consensus Skills Installer
# Bu script Claude Code slash komutlarını yükler

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$HOME/.claude/skills"

echo "Claude Code skills yükleniyor..."

# Skills dizinini oluştur
mkdir -p "$SKILLS_DIR"

# Skill'leri kopyala
cp -r "$SCRIPT_DIR/skills/consensus" "$SKILLS_DIR/"
cp -r "$SCRIPT_DIR/skills/consensus-synthesize" "$SKILLS_DIR/"

echo "Yüklenen komutlar:"
echo "  /consensus - Gemini ve Codex'ten paralel yanıt al"
echo "  /consensus-synthesize - Paralel yanıt + sentez"
echo ""
echo "Kurulum tamamlandı! Claude Code'u yeniden başlatın."
