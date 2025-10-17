#!/bin/bash
set -e

echo "🧹 Cleaning up ai-troubleshooter-v8 for git..."

# Remove backup files
echo "Removing backup ConfigMaps..."
rm -f backup-configmap-*.yaml

# Remove Python cache
echo "Removing __pycache__..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete

# Remove OS files
echo "Removing .DS_Store files..."
find . -name ".DS_Store" -delete

# Remove environment files
echo "Removing .env files..."
rm -f .env .env.local .env.v7 .env.*

# Remove temporary files
echo "Removing temporary files..."
rm -f *.log *.tmp

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📊 Repository Status:"
echo "===================="
ls -lh *.py 2>/dev/null | wc -l | xargs echo "Python files:"
ls -lh *.yaml 2>/dev/null | wc -l | xargs echo "YAML files:"
ls -lh *.md 2>/dev/null | wc -l | xargs echo "Documentation files:"
echo ""
echo "Next steps:"
echo "1. Review files with: git status"
echo "2. Add files with: git add ."
echo "3. Commit with: git commit -m 'Initial commit: AI Troubleshooter v8'"
echo "4. Add remote with: git remote add origin <your-repo-url>"
echo "5. Push with: git push -u origin main"
