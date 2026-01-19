#!/bin/bash
#
# 小红书博主内容自动沉淀系统 - Cron 定时任务配置脚本
#
# 功能: 配置系统 cron 定时任务，定期自动运行同步脚本
#
# 使用方法:
#   chmod +x scripts/setup_cron.sh
#   ./scripts/setup_cron.sh
#
# 默认配置: 每周一凌晨2点执行同步

set -e

# 项目路径
PROJECT_DIR="/Volumes/ExtSSD2601/ws/xiaohongshu_bozhu"
PYTHON_PATH="${PROJECT_DIR}/.venv/bin/python"
LOG_FILE="${PROJECT_DIR}/logs/cron.log"

# 检查 Python 虚拟环境
if [ ! -f "$PYTHON_PATH" ]; then
    echo "错误: 未找到 Python 虚拟环境"
    echo "请先运行: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 同步命令
SYNC_CMD="${PYTHON_PATH} ${PROJECT_DIR}/main.py --headless"

# Cron 表达式说明:
# ┌─────────────── minute (0-59)
# │ ┌───────────── hour (0-23)
# │ │ ┌─────────── day of month (1-31)
# │ │ │ ┌───────── month (1-12)
# │ │ │ │ ┌─────── day of week (0-6, Sunday=0)
# │ │ │ │ │
# * * * * * command

# 默认: 每周一凌晨2点
CRON_SCHEDULE="0 2 * * 1"

# 其他常用配置 (取消注释使用):
# CRON_SCHEDULE="0 2 * * *"      # 每天凌晨2点
# CRON_SCHEDULE="0 */6 * * *"    # 每6小时
# CRON_SCHEDULE="0 8,20 * * *"   # 每天8点和20点

# Cron 任务完整命令
CRON_JOB="${CRON_SCHEDULE} cd ${PROJECT_DIR} && ${SYNC_CMD} >> ${LOG_FILE} 2>&1"

echo "========================================"
echo "小红书博主内容自动沉淀系统 - Cron 配置"
echo "========================================"
echo ""
echo "项目目录: ${PROJECT_DIR}"
echo "Python路径: ${PYTHON_PATH}"
echo "日志文件: ${LOG_FILE}"
echo ""
echo "计划任务: ${CRON_SCHEDULE}"
echo "  - 每周一凌晨2点执行同步"
echo ""
echo "完整命令:"
echo "  ${CRON_JOB}"
echo ""

# 询问用户
read -p "是否添加到 crontab? (y/N): " confirm

if [[ "$confirm" =~ ^[Yy]$ ]]; then
    # 检查是否已存在
    if crontab -l 2>/dev/null | grep -q "xiaohongshu_bozhu"; then
        echo ""
        echo "警告: 已存在相关 cron 任务:"
        crontab -l | grep "xiaohongshu_bozhu"
        echo ""
        read -p "是否替换现有任务? (y/N): " replace
        if [[ ! "$replace" =~ ^[Yy]$ ]]; then
            echo "已取消"
            exit 0
        fi
        # 移除现有任务
        crontab -l 2>/dev/null | grep -v "xiaohongshu_bozhu" | crontab -
    fi

    # 添加新任务
    (crontab -l 2>/dev/null; echo "${CRON_JOB}") | crontab -

    echo ""
    echo "成功添加 cron 任务!"
    echo ""
    echo "当前 crontab 内容:"
    crontab -l | grep "xiaohongshu_bozhu" || echo "(无)"
    echo ""
    echo "管理命令:"
    echo "  crontab -l          # 查看所有定时任务"
    echo "  crontab -e          # 编辑定时任务"
    echo "  tail -f ${LOG_FILE} # 查看运行日志"
else
    echo ""
    echo "已取消。如需手动配置，请运行: crontab -e"
    echo "然后添加以下行:"
    echo ""
    echo "${CRON_JOB}"
fi

echo ""
echo "========================================"
