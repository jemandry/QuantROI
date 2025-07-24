#!/bin/bash

LOG_DIR="/tmp/quantroi-lint-logs"
LOG_FILE="$LOG_DIR/daily-lint-$(date +%Y%m%d).log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

mkdir -p "$LOG_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

cd "$PROJECT_ROOT" || exit 1

log "🚀 Starting daily linting checks for QuantROI platform"
log "Project root: $PROJECT_ROOT"
log "Log file: $LOG_FILE"

chmod +x "$SCRIPT_DIR/lint-all.sh"
chmod +x "$SCRIPT_DIR/reminder-bot.py"

log "Running comprehensive linting suite..."
if "$SCRIPT_DIR/lint-all.sh" >> "$LOG_FILE" 2>&1; then
    success "All linting checks passed!"
    LINT_STATUS="success"
else
    error "Linting checks failed - see log for details"
    LINT_STATUS="failed"
fi

if grep -q "failed\|error" "$LOG_FILE"; then
    warning "Linting failures detected, triggering Reminder Bot..."
    
    if python3 "$SCRIPT_DIR/reminder-bot.py" --alert-failures >> "$LOG_FILE" 2>&1; then
        success "Reminder Bot alerts sent successfully"
    else
        error "Failed to send Reminder Bot alerts"
    fi
else
    log "No linting failures detected"
fi

log "📊 Generating daily summary report..."

RUST_ERRORS=$(grep -c "Rust.*failed" "$LOG_FILE" || echo "0")
PYTHON_ERRORS=$(grep -c "Python.*failed" "$LOG_FILE" || echo "0")
TS_ERRORS=$(grep -c "TypeScript.*failed" "$LOG_FILE" || echo "0")
TOTAL_ERRORS=$((RUST_ERRORS + PYTHON_ERRORS + TS_ERRORS))

cat >> "$LOG_FILE" << EOF

📊 DAILY LINTING SUMMARY - $(date +%Y-%m-%d)
================================================
Overall Status: $LINT_STATUS
Rust Errors: $RUST_ERRORS
Python Errors: $PYTHON_ERRORS
TypeScript Errors: $TS_ERRORS
Total Errors: $TOTAL_ERRORS

Log Location: $LOG_FILE
Next Check: $(date -d '+1 day' +%Y-%m-%d)
================================================
EOF

find "$LOG_DIR" -name "daily-lint-*.log" -mtime +30 -delete 2>/dev/null || true

if [ "$LINT_STATUS" = "success" ]; then
    success "✅ Daily linting check completed successfully"
    exit 0
else
    error "❌ Daily linting check completed with errors"
    exit 1
fi
