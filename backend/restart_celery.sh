#!/bin/bash
# Restart Celery Workers with Playwright Support
# Usage: ./restart_celery.sh [solo|threads] [concurrency]

set -e

POOL_TYPE=${1:-solo}
CONCURRENCY=${2:-4}

echo "=========================================="
echo "Restarting Celery Workers"
echo "Pool Type: $POOL_TYPE"
echo "Concurrency: $CONCURRENCY"
echo "=========================================="

# Step 1: Kill existing Celery processes
echo ""
echo "Step 1: Stopping existing Celery workers..."
pkill -f celery || echo "No existing celery processes found"
sleep 2

# Verify all killed
REMAINING=$(ps aux | grep celery | grep -v grep | wc -l)
if [ $REMAINING -gt 0 ]; then
    echo "⚠️  Warning: $REMAINING celery processes still running"
    echo "Forcing kill..."
    killall -9 celery 2>/dev/null || true
    sleep 2
fi

echo "✓ All Celery workers stopped"

# Step 2: Check PostgreSQL
echo ""
echo "Step 2: Checking PostgreSQL..."
if pg_isready -q; then
    echo "✓ PostgreSQL is running"
else
    echo "⚠️  PostgreSQL is not running. Starting..."
    brew services start postgresql
    sleep 3
fi

# Step 3: Activate virtual environment
echo ""
echo "Step 3: Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
else
    echo "❌ Virtual environment not found at venv/bin/activate"
    exit 1
fi

# Step 4: Check Playwright installation
echo ""
echo "Step 4: Verifying Playwright installation..."
if python -c "import playwright" 2>/dev/null; then
    echo "✓ Playwright installed"

    # Check chromium
    if [ -d "$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1200" ]; then
        echo "✓ Chromium headless shell found"
    else
        echo "⚠️  Chromium not found. Installing..."
        python -m playwright install chromium
    fi
else
    echo "❌ Playwright not installed. Installing..."
    pip install playwright==1.40.0
    python -m playwright install chromium
fi

# Step 5: Start Celery
echo ""
echo "Step 5: Starting Celery workers..."
echo "Command: celery -A carb_backend worker --pool=$POOL_TYPE --concurrency=$CONCURRENCY --loglevel=info"
echo ""

if [ "$POOL_TYPE" = "solo" ]; then
    # Solo pool ignores concurrency
    celery -A carb_backend worker --pool=solo --loglevel=info
else
    celery -A carb_backend worker --pool=$POOL_TYPE --concurrency=$CONCURRENCY --loglevel=info
fi
