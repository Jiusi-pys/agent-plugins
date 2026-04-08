#!/bin/bash
# OpenHarmony Device Environment Survey Script
# Run this ON THE TARGET DEVICE before any deployment
#
# Usage (via HDC from host):
#   hdc shell < device_survey.sh
#   hdc file recv /data/device_survey_*.tar.gz ./
#
# Usage (direct on device):
#   sh device_survey.sh

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="/data/device_survey_${TIMESTAMP}"
ARCHIVE_NAME="device_survey_${TIMESTAMP}.tar.gz"

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

echo "========================================"
echo "OpenHarmony Device Environment Survey"
echo "Time: $(date)"
echo "Output: $OUTPUT_DIR"
echo "========================================"
echo ""

# 1. System Information
echo "[1/7] Collecting system info..."
{
    echo "=== uname ==="
    uname -a
    echo ""
    echo "=== CPU Info ==="
    cat /proc/cpuinfo | head -30
    echo ""
    echo "=== Memory ==="
    cat /proc/meminfo | head -10
    echo ""
    echo "=== Mount Points ==="
    mount | grep -E "^/dev"
} > system_info.txt 2>&1

# 2. OpenHarmony Version
echo "[2/7] Collecting OHOS version..."
{
    echo "=== Build Properties ==="
    for prop in ro.build.version.sdk ro.build.ohos.version ro.product.model ro.product.brand; do
        val=$(getprop "$prop" 2>/dev/null || echo "N/A")
        echo "$prop = $val"
    done
    echo ""
    echo "=== Version File ==="
    cat /system/etc/version.txt 2>/dev/null || echo "Not found"
    echo ""
    echo "=== Build Info ==="
    cat /system/build.prop 2>/dev/null | head -20 || echo "Not found"
} > ohos_version.txt 2>&1

# 3. System Libraries (/system/lib64)
echo "[3/7] Scanning /system/lib64..."
{
    echo "=== Library List ==="
    ls -lh /system/lib64/*.so 2>/dev/null | awk '{print $5, $9}'
    echo ""
    echo "=== Library Count ==="
    ls /system/lib64/*.so 2>/dev/null | wc -l
    echo ""
    echo "=== Subdirectories ==="
    ls -d /system/lib64/*/ 2>/dev/null || echo "No subdirectories"
} > system_lib64.txt 2>&1

# Extract just library names for conflict checking
ls /system/lib64/*.so 2>/dev/null | xargs -n1 basename > system_lib64_names.txt 2>&1

# 4. Critical OHOS Components
echo "[4/7] Checking OHOS components..."
{
    echo "=== HiLog ==="
    ls -lh /system/lib64/*hilog* 2>/dev/null || echo "Not found"
    echo ""
    echo "=== SoftBus ==="
    ls -lh /system/lib64/*softbus* 2>/dev/null || echo "Not found"
    echo ""
    echo "=== SAMGR ==="
    ls -lh /system/lib64/*samgr* 2>/dev/null || echo "Not found"
    echo ""
    echo "=== Utils ==="
    ls -lh /system/lib64/*utils* 2>/dev/null || echo "Not found"
    echo ""
    echo "=== IPC ==="
    ls -lh /system/lib64/*ipc* 2>/dev/null || echo "Not found"
    echo ""
    echo "=== C/C++ Runtime ==="
    ls -lh /system/lib64/libc.so /system/lib64/libc++* 2>/dev/null || echo "Check failed"
} > ohos_components.txt 2>&1

# 5. Running Processes
echo "[5/7] Collecting process info..."
{
    echo "=== Process List ==="
    ps -ef 2>/dev/null || ps aux 2>/dev/null || ps
    echo ""
    echo "=== OHOS Services ==="
    ps -ef 2>/dev/null | grep -E "(samgr|softbus|hilog|foundation)" || echo "None found"
} > processes.txt 2>&1

# 6. /data directory inspection
echo "[6/7] Inspecting /data..."
{
    echo "=== /data contents ==="
    ls -la /data/ 2>/dev/null | head -50
    echo ""
    echo "=== Existing .so in /data ==="
    find /data -name "*.so" -type f 2>/dev/null | head -100
    echo ""
    echo "=== Disk Usage ==="
    df -h /data 2>/dev/null || df /data
} > data_inspection.txt 2>&1

# 7. Environment Variables
echo "[7/7] Collecting environment..."
{
    echo "=== Environment ==="
    env | sort
    echo ""
    echo "=== LD_LIBRARY_PATH ==="
    echo "$LD_LIBRARY_PATH"
    echo ""
    echo "=== PATH ==="
    echo "$PATH"
} > environment.txt 2>&1

# Generate Summary
echo ""
echo "Generating summary..."
{
    echo "========================================"
    echo "DEVICE SURVEY SUMMARY"
    echo "========================================"
    echo ""
    echo "System: $(uname -m) / $(uname -r)"
    echo "OHOS SDK: $(getprop ro.build.version.sdk 2>/dev/null || echo 'Unknown')"
    echo ""
    echo "--- Critical Libraries Found ---"
    for lib in libc.so libm.so libdl.so libc++.so libhilog.so libsoftbus_client.so libutils.so; do
        if [ -f "/system/lib64/$lib" ]; then
            echo "  [EXISTS] $lib"
        else
            echo "  [ABSENT] $lib"
        fi
    done
    echo ""
    echo "--- Library Counts ---"
    echo "  /system/lib64/*.so: $(ls /system/lib64/*.so 2>/dev/null | wc -l)"
    echo "  /data/**/*.so: $(find /data -name '*.so' 2>/dev/null | wc -l)"
    echo ""
    echo "--- Disk Space ---"
    df -h /data 2>/dev/null | tail -1 || df /data | tail -1
    echo ""
    echo "========================================"
} | tee summary.txt

# Create archive
echo ""
echo "Creating archive..."
cd /data
tar czf "$ARCHIVE_NAME" "device_survey_${TIMESTAMP}/"

echo ""
echo "========================================"
echo "Survey complete!"
echo ""
echo "Files saved to: $OUTPUT_DIR/"
echo "Archive: /data/$ARCHIVE_NAME"
echo ""
echo "To retrieve from host:"
echo "  hdc file recv /data/$ARCHIVE_NAME ./"
echo "========================================"
