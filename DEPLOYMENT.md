# Deployment Guide - Soccer Schedules App

## ✅ Backend Deployed to Fly.io

Your backend is deployed at: **https://soccerschedules-backend.fly.dev**

### Backend URLs:
- **API Root**: https://soccerschedules-backend.fly.dev/api/v1/
- **API Docs**: https://soccerschedules-backend.fly.dev/docs
- **Health Check**: https://soccerschedules-backend.fly.dev/health

### Current Status:
✅ Backend API is running and healthy  
✅ Database migrations completed  
✅ Database connected successfully  
⚠️ Web scraping with Playwright needs debugging (Internal Server Error)  
⏳ Frontend deployment pending  

### Database:
- PostgreSQL database: `soccerschedules-db`
- Connection via `DATABASE_URL` secret (automatically configured)

---

## 📱 Deploy Frontend (Next.js)

### Option 1: Vercel (Recommended - FREE)

1. **Push to GitHub** (if not already done):
   ```bash
   cd /Users/Per/code/Soccerschedules
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/soccerschedules.git
   git push -u origin main
   ```

2. **Deploy to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Click "Add New" → "Project"
   - Import your GitHub repository
   - Set Root Directory: `frontend`
   - Add Environment Variable:
     - `NEXT_PUBLIC_API_URL` = `https://soccerschedules-backend.fly.dev`
   - Click "Deploy"

### Option 2: Deploy Frontend to Fly.io

1. Create `frontend/Dockerfile.prod`:
   ```dockerfile
   FROM node:20-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci
   COPY . .
   ENV NEXT_PUBLIC_API_URL=https://soccerschedules-backend.fly.dev
   RUN npm run build
   EXPOSE 3000
   CMD ["npm", "start"]
   ```

2. Create `frontend/fly.toml`:
   ```toml
   app = "soccerschedules-frontend"
   primary_region = "ewr"
   
   [build]
     dockerfile = "Dockerfile.prod"
   
   [http_service]
     internal_port = 3000
     force_https = true
   
   [[vm]]
     memory = "512mb"
   ```

3. Deploy:
   ```bash
   cd frontend
   fly launch --dockerfile Dockerfile.prod
   fly deploy
   ```

---

## 🔧 Managing Your Deployment

### View Backend Logs:
```bash
fly logs --app soccerschedules-backend
```

### SSH into Backend:
```bash
fly ssh console --app soccerschedules-backend
```

### Scale Backend:
```bash
fly scale memory 2048 --app soccerschedules-backend
```

### Database Management:
```bash
# Connect to database
fly postgres connect --app soccerschedules-db

# View database info
fly postgres db list --app soccerschedules-db
```

### Set Environment Variables:
```bash
fly secrets set VARIABLE_NAME=value --app soccerschedules-backend
```

---

## 💰 Estimated Costs

- **Fly.io Backend**: ~$5-10/month (1GB RAM, shared CPU)
- **Fly.io PostgreSQL**: ~$5/month (1GB volume)
- **Vercel Frontend**: FREE
- **Total**: ~$10-15/month

---

## 🚀 Quick Commands

```bash
# Deploy backend updates
cd /Users/Per/code/Soccerschedules
fly deploy

# View app status
fly status --app soccerschedules-backend

# Open app in browser
fly open --app soccerschedules-backend

# Monitor app
fly dashboard soccerschedules-backend
```

---

## 📝 Next Steps

1. ✅ Backend is deployed
2. 🔄 Deploy frontend to Vercel or Fly.io
3. 🎨 Update CORS settings if needed (backend/app/core/config.py)
4. 🔐 Set up custom domain (optional)
5. 📊 Set up monitoring and alerts

---

## 🆘 Troubleshooting

### If backend won't start:
```bash
fly logs --app soccerschedules-backend
```

### If database connection fails:
```bash
fly secrets list --app soccerschedules-backend
# Should see DATABASE_URL
```

### Force rebuild:
```bash
fly deploy --build-only
```
