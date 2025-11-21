# Quick Deployment Script
# Run this after pushing to GitHub

Write-Host "🚀 Agama Shastra Guru - Deployment Helper" -ForegroundColor Cyan
Write-Host ""

# Check if git is clean
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "⚠️  You have uncommitted changes. Please commit first:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  git add ." -ForegroundColor White
    Write-Host "  git commit -m 'your message'" -ForegroundColor White
    Write-Host "  git push" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "✅ Git is clean" -ForegroundColor Green
Write-Host ""

Write-Host "📋 Deployment Checklist:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Backend (Render):" -ForegroundColor Yellow
Write-Host "   - Go to: https://dashboard.render.com/" -ForegroundColor White
Write-Host "   - Click 'New +' → 'Blueprint'" -ForegroundColor White
Write-Host "   - Connect your GitHub repo" -ForegroundColor White
Write-Host "   - Add GEMINI_API_KEY environment variable" -ForegroundColor White
Write-Host "   - Wait for deployment (~5-10 min)" -ForegroundColor White
Write-Host ""

Write-Host "2. Update Frontend:" -ForegroundColor Yellow
Write-Host "   - Copy your Render URL (e.g., https://agama-shastra-api.onrender.com)" -ForegroundColor White
Write-Host "   - Open web/script.js" -ForegroundColor White
Write-Host "   - Update line 4 with your backend URL" -ForegroundColor White
Write-Host ""

$backendUrl = Read-Host "Enter your Render backend URL (or press Enter to skip)"

if ($backendUrl) {
    Write-Host ""
    Write-Host "Updating web/script.js..." -ForegroundColor Cyan
    
    $scriptPath = "web\script.js"
    $content = Get-Content $scriptPath -Raw
    $content = $content -replace "https://your-backend-url\.onrender\.com", $backendUrl
    Set-Content $scriptPath $content
    
    Write-Host "✅ Updated!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Committing changes..." -ForegroundColor Cyan
    git add web/script.js
    git commit -m "chore: update API URL for production"
    git push
    Write-Host "✅ Pushed to GitHub" -ForegroundColor Green
}

Write-Host ""
Write-Host "3. Frontend (Vercel):" -ForegroundColor Yellow
Write-Host "   - Go to: https://vercel.com/new" -ForegroundColor White
Write-Host "   - Import your GitHub repo" -ForegroundColor White
Write-Host "   - Set Root Directory to: web" -ForegroundColor White
Write-Host "   - Click Deploy" -ForegroundColor White
Write-Host ""

Write-Host "📖 Full guide: See DEPLOYMENT.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 Good luck with deployment!" -ForegroundColor Green
