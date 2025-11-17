#!/bin/bash
# Package Lambda function for deployment
# Usage: ./package.sh
# All Lambda-related files are now in this folder, so packaging is simple!

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
ZIP_FILE="$BACKEND_DIR/lambda.zip"

echo "Packaging Lambda function from $SCRIPT_DIR..."

# Create zip file directly from lambda folder
# Exclude packaging scripts and README from the zip
# Note: We need __init__.py files inside finance_analyzer_lib/, so we only exclude the root __init__.py
cd "$SCRIPT_DIR"
zip -r "$ZIP_FILE" \
    lambda_ses_scheduler.py \
    finance_analyzer_lib/ \
    -x "*.sh" "*.ps1" "README.md" "./__init__.py" > /dev/null
cd - > /dev/null

echo "✓ Lambda package created: $ZIP_FILE"
echo "  Size: $(du -h "$ZIP_FILE" | cut -f1)"
echo ""
echo "Package contents:"
unzip -l "$ZIP_FILE" | grep -E "(lambda_ses_scheduler|finance_analyzer_lib)" | head -10

