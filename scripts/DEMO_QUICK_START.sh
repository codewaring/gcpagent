#!/usr/bin/env bash

# ============================================
# Cloud Shell Demo - Quick Start Guide
# 现场演示用快速启动脚本
# ============================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     Cloud Shell Local Demo - 快速启动指南                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "📋 演示前检查清单："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ 第1步：打开 Cloud Shell Terminal"
echo "   • 访问 https://shell.cloud.google.com"
echo "   • 或在 GCP Console 右上角点击 >_ 图标"
echo ""

echo "✅ 第2步：一键启动所有服务"
echo "   $ bash ~/demo0908/jd-agent-gcp/scripts/cloudshell_run_all.sh ~/demo0908"
echo ""
echo "   输出应该显示："
echo "   [done] Started local demo services in tmux session: demo0908"
echo ""

echo "✅ 第3步：查看访问地址（可选）"
echo "   $ bash ~/demo0908/jd-agent-gcp/scripts/cloudshell_demo_urls.sh"
echo ""

echo "✅ 第4步：打开 Web Preview 访问服务"
echo "   • 在 Cloud Shell UI 右上角找 'Web Preview' 按钮"
echo "   • 点击它，在弹出框中输入 8080（JD Agent）或 8090（Recruiter Agent）"
echo "   • 或直接修改浏览器 URL 中的端口号"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 服务地址："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣  JD Agent（岗位描述生成系统）- 端口 8080"
echo "   • 功能："
echo "     - 生成职位描述（JD）"
echo "     - 与 GCS 关联参考文档"
echo "     - 管理职位应用"
echo ""

echo "2️⃣  Recruiter Agent（候选人筛选系统）- 端口 8090"
echo "   • 功能："
echo "     - 列出所有候选人"
echo "     - 根据管理偏好重新排名候选人"
echo "     - AI 驱动的候选人评估"
echo ""

echo "🎯 演示流程建议："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "第1分钟：启动服务"
echo "  \$ bash ~/demo0908/jd-agent-gcp/scripts/cloudshell_run_all.sh ~/demo0908"
echo ""

echo "第2分钟：打开 JD Agent (8080)"
echo "  • 展示职位列表和详情"
echo "  • 演示 JD 生成功能"
echo ""

echo "第3分钟：打开 Recruiter Agent (8090)"
echo "  • 展示候选人列表"
echo "  • 演示重新排名功能"
echo "  • 展示 AI 评估结果"
echo ""

echo "🛠️  维护命令："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "查看 JD Agent 日志："
echo "  \$ tmux send-keys -t demo0908:0 up Enter"
echo ""

echo "查看 Recruiter 日志："
echo "  \$ tmux send-keys -t demo0908:1 up Enter"
echo ""

echo "停止所有服务："
echo "  \$ tmux kill-session -t demo0908"
echo ""

echo "检查服务健康状态："
echo "  \$ curl -sS http://127.0.0.1:8080/health"
echo "  \$ curl -sS http://127.0.0.1:8090/health"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ 准备好了吗？现在就开始吧！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
