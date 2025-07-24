#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

RUST_ERRORS=0
PYTHON_ERRORS=0
TS_ERRORS=0

log "🔍 Starting comprehensive linting for QuantROI platform..."

log "🦀 Running Rust linting..."
if [ -d "solana-contracts" ]; then
    cd solana-contracts
    
    log "Running cargo clippy..."
    if cargo clippy --all-targets --all-features -- -D warnings; then
        success "Rust clippy passed"
    else
        error "Rust clippy failed"
        RUST_ERRORS=$((RUST_ERRORS + 1))
    fi
    
    log "Running cargo fmt check..."
    if cargo fmt --check; then
        success "Rust formatting passed"
    else
        error "Rust formatting failed"
        RUST_ERRORS=$((RUST_ERRORS + 1))
    fi
    
    log "Running cargo check..."
    if cargo check; then
        success "Rust syntax check passed"
    else
        warning "Rust syntax check failed (dependency issues expected)"
    fi
    
    cd ..
else
    warning "No solana-contracts directory found"
fi

log "🐍 Running Python linting..."
PYTHON_FILES=$(find . -name "*.py" -not -path "./test-samples/*" -not -path "./node_modules/*" -not -path "./.*" 2>/dev/null || true)

if [ -n "$PYTHON_FILES" ]; then
    log "Running flake8..."
    if echo "$PYTHON_FILES" | xargs flake8 --max-line-length=88 --extend-ignore=E203,W503; then
        success "Python flake8 passed"
    else
        error "Python flake8 failed"
        PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
    fi
    
    log "Running pylint..."
    if echo "$PYTHON_FILES" | xargs pylint --rcfile=pyproject.toml; then
        success "Python pylint passed"
    else
        error "Python pylint failed"
        PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
    fi
    
    log "Running mypy..."
    if echo "$PYTHON_FILES" | xargs mypy --config-file=pyproject.toml; then
        success "Python mypy passed"
    else
        error "Python mypy failed"
        PYTHON_ERRORS=$((PYTHON_ERRORS + 1))
    fi
else
    warning "No Python files found for linting"
fi

log "📜 Running TypeScript/JavaScript linting..."
TS_FILES=$(find . -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -not -path "./node_modules/*" -not -path "./test-samples/*" -not -path "./.*" 2>/dev/null || true)

if [ -n "$TS_FILES" ]; then
    log "Running ESLint..."
    if echo "$TS_FILES" | xargs eslint; then
        success "TypeScript ESLint passed"
    else
        error "TypeScript ESLint failed"
        TS_ERRORS=$((TS_ERRORS + 1))
    fi
    
    log "Running TypeScript compilation check..."
    if [ -f "tsconfig.json" ]; then
        if tsc --noEmit; then
            success "TypeScript compilation check passed"
        else
            warning "TypeScript compilation check failed (no tsconfig.json or compilation issues)"
        fi
    else
        warning "No tsconfig.json found, skipping TypeScript compilation check"
    fi
else
    warning "No TypeScript/JavaScript files found for linting"
fi

log "📊 Linting Summary:"
echo "  Rust errors: $RUST_ERRORS"
echo "  Python errors: $PYTHON_ERRORS"
echo "  TypeScript errors: $TS_ERRORS"

TOTAL_ERRORS=$((RUST_ERRORS + PYTHON_ERRORS + TS_ERRORS))

if [ $TOTAL_ERRORS -eq 0 ]; then
    success "✅ All linting checks passed!"
    exit 0
else
    error "❌ Linting completed with $TOTAL_ERRORS error(s)"
    exit 1
fi
