# Photography ML - Deployment & Sharing Guide

## 🚀 How to Launch the App Locally

### Prerequisites
- Docker Desktop running (for PostgreSQL database)
- Python 3.14 with virtual environment at `backend/env-photography-ml/`
- Node.js and npm installed

### Step-by-Step Launch

#### 1. Start the Database
```bash
cd /Users/espoma/Desktop/espoma-ml/photography-ml
docker compose up -d db
```

Verify it's running:
```bash
docker ps --filter "name=photography_db"
```

#### 2. Start the Backend (in Terminal 1)
```bash
cd /Users/espoma/Desktop/espoma-ml/photography-ml/backend
./env-photography-ml/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

#### 3. Start the Frontend (in Terminal 2)
```bash
cd /Users/espoma/Desktop/espoma-ml/photography-ml/frontend
npm run dev
```

You should see:
```
▲ Next.js 16.1.4
- Local:         http://localhost:3000
✓ Ready in 1336ms
```

#### 4. Access the App
- Open browser: `http://localhost:3000`
- Upload page: `http://localhost:3000/upload`
- Gallery page: `http://localhost:3000/gallery`

#### 5. Stop Everything
```bash
# Stop backend (Ctrl+C in Terminal 1)
# Stop frontend (Ctrl+C in Terminal 2)
# Stop database
docker compose down
```

---

## 💻 Sharing the App with Others

### Current Situation
**Your app is NOT accessible to others right now because:**
- Backend runs only on `127.0.0.1:8000` (localhost, your machine only)
- Frontend runs only on `localhost:3000` (your machine only)
- Anyone on your network cannot access it

---

### Option 1: Share on Same Local Network (Easiest)

#### Step 1: Change Backend Host
Edit `backend/main.py` or run with `0.0.0.0`:
```bash
./env-photography-ml/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Step 2: Change Frontend API URL
Edit `frontend/app/upload/page.tsx` and `frontend/app/gallery/page.tsx`:
- Replace `http://localhost:8000` with your machine's IP
- Find your IP: `ipconfig getifaddr en0` (macOS)
- Example: `http://192.168.1.41:8000`

#### Step 3: Change Frontend Host
```bash
npm run dev -- --hostname 0.0.0.0 --port 3000
```

#### Step 4: Share the Link
- Get your machine's IP: `ipconfig getifaddr en0`
- Share: `http://192.168.1.41:3000` with others on WiFi

**Limitations:**
- Only works if others are on the same WiFi network
- Stops working if your computer goes to sleep
- Not secure (no authentication)

---

### Option 2: Deploy to the Internet (Recommended)

This makes your app accessible to anyone with a link, from anywhere.

#### Best Option: Fly.io (Free Tier, $3/mo credit)

**Step 1: Install Fly CLI**
```bash
# macOS
brew install flyctl
```

**Step 2: Create Fly Account**
```bash
flyctl auth login
```

**Step 3: Initialize Fly Project**
```bash
cd /Users/espoma/Desktop/espoma-ml/photography-ml
flyctl launch
```

When prompted:
- App name: `photography-ml`
- Region: Pick closest to you
- PostgreSQL: Say "Yes" to create managed database

**Step 4: Set Environment Variables**
```bash
flyctl secrets set GEMINI_API_KEY="AIzaSyD2WFrqq4TcrRBv2DYMm90bflhN9Atwsq4"
```

**Step 5: Deploy**
```bash
flyctl deploy
```

**Step 6: Access Your App**
```bash
flyctl open
```

Your app gets a unique URL like: `https://photography-ml-1234.fly.dev`

**Cost:** Free tier covers ~$3/mo. If you go over, pay as you go.

---

### Option 3: Other Cloud Providers

#### Railway.app
```bash
# Connect GitHub repo
# Railway auto-deploys on push
# Includes free PostgreSQL
```
- Cost: $5/mo free tier
- Setup: ~5 minutes
- Link: `https://photography-ml.railway.app`

#### Render
```bash
# Connect GitHub
# Deploy via UI
```
- Cost: Free tier (sleeps after 15 min inactivity)
- Setup: ~10 minutes
- Link: `https://photography-ml.onrender.com`

#### AWS / Google Cloud
- More complex setup
- Better for large-scale projects
- Costs can add up quickly

---

## 🔧 Before Sharing: Checklist

### Security
- [ ] Change hardcoded credentials in `.env`
- [ ] Use environment variables for GEMINI_API_KEY
- [ ] Add input validation (file size, format)
- [ ] Enable HTTPS (Fly.io handles this automatically)
- [ ] Add rate limiting (prevent abuse)

### Performance
- [ ] Test with multiple users
- [ ] Check image upload speed
- [ ] Monitor database performance

### User Experience
- [ ] Add error messages for failed uploads
- [ ] Test on mobile devices
- [ ] Test drag-and-drop on different browsers

---

## 🌐 Making the App Production-Ready for Sharing

To share safely with multiple users, you MUST add:

1. **User Authentication**
   - Users need accounts
   - Each user sees only their own images
   - Prevents one user from deleting another's data

2. **Rate Limiting**
   - Prevent abuse (max 10 uploads/hour per user)
   - Protects your Gemini API quota

3. **Input Validation**
   - Reject files >50MB
   - Only allow image formats
   - Prevent malicious uploads

4. **Error Handling**
   - Show user-friendly error messages
   - Log errors for debugging
   - Don't expose sensitive info

5. **Monitoring**
   - Track uptime
   - Alert on crashes
   - Monitor API costs

---

## 📊 Quick Comparison: Deployment Options

| Option | Cost | Setup Time | Uptime | Best For |
|--------|------|-----------|--------|----------|
| Local Network | Free | 5 min | ~100% (if laptop on) | Testing with friends |
| Fly.io | Free→$3/mo | 15 min | 99.9% | Small projects, hobby |
| Railway.app | $5/mo | 10 min | 99% | Simple apps, learning |
| Render | Free/paid | 10 min | 95% (free tier sleeps) | Learning only |
| AWS/GCP | $$$$ | 1+ hour | 99.99% | Production, many users |

---

## 🚨 Important Notes

### About the Free Tier
- **Fly.io free tier includes:**
  - 3 shared CPU VMs
  - 3 GB storage
  - Reasonable bandwidth
- **What costs extra:**
  - Database storage (PostgreSQL is ~$10/mo if large)
  - Egress (data out) after limit
  - Additional VMs

### About Your Gemini API Key
- **Current setup:** Key is in `.env` file (visible in code)
- **For production:** Use environment secrets (Fly.io handles this)
- **Cost:** First 15 image generations/min free, then charged

### About Updates
- **Local:** Changes take effect on save (hot reload)
- **Fly.io:** Push to GitHub, `flyctl deploy`, or auto-deploy on merge

