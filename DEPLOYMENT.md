# Deployment Guide - Agama Shastra Guru

This guide will help you deploy the application with:
- **Frontend** on Vercel (free)
- **Backend** on Render (free tier)

---

## Prerequisites

1. GitHub account
2. Vercel account (sign up at vercel.com)
3. Render account (sign up at render.com)
4. Your Gemini API key

---

## Step 1: Push to GitHub

```bash
git add .
git commit -m "feat: replace Streamlit with custom HTML/JS UI and FastAPI backend"
git push origin main
```

---

## Step 2: Deploy Backend (Render)

### Option A: Using render.yaml (Recommended)

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will auto-detect `render.yaml`
5. Add environment variable:
   - Key: `GEMINI_API_KEY`
   - Value: `your-actual-gemini-api-key`
6. Click **"Apply"**
7. Wait 5-10 minutes for deployment
8. Copy your backend URL (e.g., `https://agama-shastra-api.onrender.com`)

### Option B: Manual Setup

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `agama-shastra-api`
   - **Region**: Oregon (US West)
   - **Branch**: `main`
   - **Root Directory**: Leave empty
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.api:app --host 0.0.0.0 --port $PORT`
5. Add environment variable:
   - Key: `GEMINI_API_KEY`
   - Value: `your-actual-gemini-api-key`
6. Click **"Create Web Service"**
7. Wait for deployment (5-10 minutes)
8. Copy your backend URL

---

## Step 3: Update Frontend Configuration

1. Open `web/script.js`
2. Find this line (around line 4):
   ```javascript
   : 'https://your-backend-url.onrender.com';
   ```
3. Replace with your actual Render URL:
   ```javascript
   : 'https://agama-shastra-api.onrender.com';
   ```
4. Save and commit:
   ```bash
   git add web/script.js
   git commit -m "chore: update API URL for production"
   git push
   ```

---

## Step 4: Deploy Frontend (Vercel)

### Option A: Using Vercel CLI (Fastest)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd web
vercel --prod
```

### Option B: Using Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **"Add New..."** → **"Project"**
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Other
   - **Root Directory**: `web`
   - **Build Command**: Leave empty
   - **Output Directory**: Leave empty
5. Click **"Deploy"**
6. Wait 1-2 minutes
7. Your app is live! 🎉

---

## Step 5: Update CORS (Important!)

After deploying the frontend, update the backend CORS settings:

1. Open `src/api.py`
2. Find this line (around line 25):
   ```python
   allow_origins=["*"],
   ```
3. Replace with your Vercel domain:
   ```python
   allow_origins=["https://your-app.vercel.app"],
   ```
4. Commit and push:
   ```bash
   git add src/api.py
   git commit -m "chore: update CORS for production"
   git push
   ```
5. Render will auto-deploy the update

---

## Troubleshooting

### Backend Issues

**Problem**: "Application failed to start"
- Check Render logs for errors
- Verify `GEMINI_API_KEY` is set correctly
- Ensure `chroma_db` folder is committed to Git

**Problem**: "Module not found"
- Check `requirements.txt` has all dependencies
- Rebuild the service in Render dashboard

### Frontend Issues

**Problem**: "Failed to fetch" or CORS errors
- Verify backend URL in `web/script.js` is correct
- Check CORS settings in `src/api.py`
- Ensure backend is running (check Render dashboard)

**Problem**: Icons not loading
- Verify `assets/` folder is in the repository
- Check file paths in HTML (should be `../assets/`)

---

## Free Tier Limitations

### Render Free Tier:
- ⚠️ **Spins down after 15 minutes of inactivity**
- First request after inactivity takes 30-60 seconds
- 750 hours/month (enough for demo)

### Vercel Free Tier:
- ✅ Always on
- 100 GB bandwidth/month
- Perfect for frontend

---

## Production Checklist

- [ ] Backend deployed on Render
- [ ] Environment variable `GEMINI_API_KEY` set
- [ ] Backend URL updated in `web/script.js`
- [ ] Frontend deployed on Vercel
- [ ] CORS updated with Vercel domain
- [ ] Test the live app
- [ ] Monitor Render logs for errors

---

## Useful Commands

```bash
# Check backend health
curl https://your-backend-url.onrender.com/health

# View Render logs
# Go to Render Dashboard → Your Service → Logs

# Redeploy Vercel
vercel --prod

# Redeploy Render
# Push to GitHub (auto-deploys)
```

---

## Next Steps After Deployment

1. **Custom Domain** (Optional):
   - Add custom domain in Vercel settings
   - Update CORS in backend

2. **Monitoring**:
   - Set up Render alerts for downtime
   - Monitor API usage in Gemini console

3. **Improvements**:
   - Add loading state for cold starts
   - Implement caching for common queries
   - Add analytics (Google Analytics, Plausible)

---

Need help? Check the logs in Render/Vercel dashboards or contact support.
