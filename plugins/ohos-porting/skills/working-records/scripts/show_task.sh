#!/bin/bash
# show_task.sh - 显示任务详情
# 用法: ./show_task.sh <task_id>

TASK_ID="${1:?Error: task_id required}"
RECORDS_DIR="${HOME}/.claude/working-records"
TASK_FILE="$RECORDS_DIR/${TASK_ID}.yaml"

if [ ! -f "$TASK_FILE" ]; then
    echo "Error: Task not found: $TASK_ID"
    exit 1
fi

echo "╔════════════════════════════════════════════════════════╗"
echo "║         移植任务详情                                    ║"
echo "╚════════════════════════════════════════════════════════╝"

# 使用 grep/sed 解析 YAML (简单方式)
LIBRARY=$(grep "^library:" "$TASK_FILE" | cut -d: -f2 | xargs)
VERSION=$(grep "^version:" "$TASK_FILE" | cut -d: -f2 | xargs)
STATUS=$(grep "^status:" "$TASK_FILE" | cut -d: -f2 | xargs)
CREATED=$(grep "^created_at:" "$TASK_FILE" | cut -d: -f2- | xargs)

echo "任务ID: $TASK_ID"
echo "目标库: $LIBRARY $VERSION"
echo "状态: $STATUS"
echo "创建时间: $CREATED"
echo ""

echo "【阶段进度】"
IN_PHASES=false
while IFS= read -r line; do
    if [[ "$line" == "phases:" ]]; then
        IN_PHASES=true
        continue
    fi
    if [[ "$IN_PHASES" == true ]]; then
        if [[ "$line" =~ ^[a-z] ]] && [[ ! "$line" =~ ^\ *- ]]; then
            break
        fi
        if [[ "$line" =~ name:\ (.+) ]]; then
            PHASE_NAME="${BASH_REMATCH[1]}"
        fi
        if [[ "$line" =~ status:\ (.+) ]]; then
            PHASE_STATUS="${BASH_REMATCH[1]}"
            case "$PHASE_STATUS" in
                completed) ICON="✓" ;;
                in_progress) ICON="▶" ;;
                blocked) ICON="✗" ;;
                *) ICON="○" ;;
            esac
            echo "  $ICON $PHASE_NAME: $PHASE_STATUS"
        fi
    fi
done < "$TASK_FILE"

echo ""
echo "【下一步】"
IN_NEXT=false
while IFS= read -r line; do
    if [[ "$line" == "next_steps:" ]]; then
        IN_NEXT=true
        continue
    fi
    if [[ "$IN_NEXT" == true ]]; then
        if [[ "$line" =~ ^[a-z] ]] && [[ ! "$line" =~ ^\ *- ]]; then
            break
        fi
        if [[ "$line" =~ ^\ *-\ (.+) ]]; then
            echo "  → ${BASH_REMATCH[1]}"
        fi
    fi
done < "$TASK_FILE"
