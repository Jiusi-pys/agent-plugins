#!/bin/bash
# create_task.sh - 创建移植任务记录
# 用法: ./create_task.sh <library_name> <version> [source_url]

LIBRARY="${1:?Error: library name required}"
VERSION="${2:?Error: version required}"
SOURCE_URL="${3:-}"

RECORDS_DIR="${HOME}/.claude/working-records"
mkdir -p "$RECORDS_DIR"

# 生成任务 ID
DATE=$(date +%Y%m%d)
SEQ=$(ls -1 "$RECORDS_DIR" 2>/dev/null | grep "^PORTING-${DATE}" | wc -l)
SEQ=$((SEQ + 1))
TASK_ID="PORTING-${DATE}-$(printf '%03d' $SEQ)"

TASK_FILE="$RECORDS_DIR/${TASK_ID}.yaml"

cat > "$TASK_FILE" << EOF
task_id: ${TASK_ID}
library: ${LIBRARY}
version: ${VERSION}
source_url: ${SOURCE_URL}
target_platform: OpenHarmony
target_device: 

created_at: $(date -Iseconds)
updated_at: $(date -Iseconds)

status: pending

phases:
  - name: clarification
    status: pending
  - name: exploration
    status: pending
  - name: diagnostics
    status: pending
  - name: architecture
    status: pending
  - name: implementation
    status: pending
  - name: build
    status: pending
  - name: deploy
    status: pending
  - name: finalization
    status: pending

blockers: []

artifacts: []

next_steps:
  - "开始需求澄清阶段"

context:
  key_files: []
  key_decisions: []
EOF

echo "Task created: $TASK_ID"
echo "File: $TASK_FILE"
