#!/bin/bash
set -e

echo "🚀 Deploying Soccer Schedules to Fly.io..."

# Set PATH to include fly
export PATH="$HOME/.fly/bin:$PATH"

# Login to Fly.io (if not already logged in)
echo "📝 Please login to Fly.io..."
fly auth login

# Create Fly.io apps if they don't exist
echo "📦 Setting up Fly.io apps..."

# Create PostgreSQL database
echo "🗄️  Creating PostgreSQL database..."
fly postgres create --name soccerschedules-db --region ewr --initial-cluster-size 1 --vm-size shared-cpu-1x --volume-size 1 || echo "Database already exists"

# Create Redis instance  
echo "🔴 Creating Redis instance..."
fly redis create --name soccerschedules-redis --region ewr --plan free || echo "Redis already exists"

# Create backend app
echo "🔧 Creating backend app..."
fly apps create soccerschedules-backend --org personal || echo "Backend app already exists"

# Attach database to backend
echo "🔗 Attaching database to backend..."
fly postgres attach soccerschedules-db --app soccerschedules-backend || echo "Database already attached"

# Deploy backend
echo "🚢 Deploying backend..."
cd /Users/Per/code/Soccerschedules
fly deploy --config fly.toml --app soccerschedules-backend

# Get backend URL
BACKEND_URL=$(fly status --app soccerschedules-backend --json | grep -o '"Hostname":"[^"]*"' | cut -d'"' -f4)
echo "✅ Backend deployed at: https://$BACKEND_URL"

# Deploy frontend to Vercel (recommended for Next.js)
echo ""
echo "📱 For the frontend, I recommend deploying to Vercel:"
echo "1. Push your code to GitHub"
echo "2. Go to vercel.com and import your repository"
echo "3. Set environment variable: NEXT_PUBLIC_API_URL=https://$BACKEND_URL"
echo "4. Deploy!"

echo ""
echo "🎉 Backend deployment complete!"
echo "Backend URL: https://$BACKEND_URL"
