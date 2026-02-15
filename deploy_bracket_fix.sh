#!/bin/bash

echo "Deploying bracket standings storage improvements..."

cd /Users/Per/code/Soccerschedules

git add -A
git commit -m "Add robust error handling and retry logic to bracket standings storage"
git push

echo "Deploying to Fly.io..."
fly deploy --app soccerschedules-backend

echo ""
echo "Deployment complete!"
echo ""
echo "To trigger a new scrape with the improved error handling:"
echo "curl -X POST https://soccerschedules-backend.fly.dev/api/v1/scraping/scrape-event/28"
echo ""
echo "To check if bracket standings are stored:"
echo "curl https://soccerschedules-backend.fly.dev/api/v1/events/28/divisions/468295/seeding"
