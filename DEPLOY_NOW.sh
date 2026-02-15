#!/bin/bash
cd /Users/Per/code/Soccerschedules
git add -A
git commit -m "Add robust error handling and retry logic to bracket standings storage"
git push
fly deploy --app soccerschedules-backend
