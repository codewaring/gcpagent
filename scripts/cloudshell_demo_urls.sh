#!/usr/bin/env bash

# ============================================
# Cloud Shell Demo URLs Generator
# 用于在 Cloud Shell 中生成服务的公开访问 URL
# ============================================

set -e

# 获取项目信息
PROJECT=$(gcloud config get-value project)
ZONE=$(gcloud config get-value compute/zone || echo "unknown")

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          Cloud Shell Local Demo URLs                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "📍 当前项目: $PROJECT"
echo ""

echo "🌐 服务访问地址（Cloud Shell Web Preview）:"
echo ""

# JD Agent - Port 8080
echo "1️⃣  JD Agent（岗位描述生成系统）"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   • 本地地址: http://127.0.0.1:8080"
echo "   • Cloud Shell Preview: https://8080-${PROJECT}.cloudshell.dev"
echo "   • 健康检查: curl -sS http://127.0.0.1:8080/health"
echo ""

# Recruiter Agent - Port 8090
echo "2️⃣  Recruiter Agent（候选人筛选排名系统）"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   • 本地地址: http://127.0.0.1:8090"
echo "   • Cloud Shell Preview: https://8090-${PROJECT}.cloudshell.dev"
echo "   • 健康检查: curl -sS http://127.0.0.1:8090/health"
echo ""

echo "📊 查看服务日志:"
echo "   • JD Agent:       tmux capture-pane -t demo0908:0 -p"
echo "   • Recruiter:      tmux capture-pane -t demo0908:1 -p"
echo ""

echo "🔧 管理服务:"
echo "   • 查看所有 window:  tmux list-windows -t demo0908"
echo "   • 附加日志:        tmux attach -t demo0908"
echo "   • 停止所有:        tmux kill-session -t demo0908"
echo ""

echo "✨ 演示建议:"
echo "   1. 点击 Cloud Shell 右上方的 'Web Preview' 按钮"
echo "   2. 选择端口 8080 查看 JD Agent"
echo "   3. 手动改 URL 中的 8080 为 8090 查看 Recruiter Agent"
echo ""
