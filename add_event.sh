#!/bin/bash

# Script to add a new event to the scraping system
# Usage: ./add_event.sh <event_id> <event_name>
# Example: ./add_event.sh 39474 "2025 State Cup"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <gotsport_event_id> <event_name>"
    echo "Example: $0 39474 \"2025 State Cup\""
    exit 1
fi

EVENT_ID=$1
EVENT_NAME=$2
API_URL="${API_URL:-https://soccerschedules-backend.fly.dev}"

echo "Creating event: $EVENT_NAME (ID: $EVENT_ID)"

# Create the event
RESPONSE=$(curl -s -X POST "$API_URL/api/v1/events/" \
  -H "Content-Type: application/json" \
  -d "{
    \"gotsport_event_id\": \"$EVENT_ID\",
    \"name\": \"$EVENT_NAME\",
    \"url\": \"https://system.gotsport.com/org_event/events/$EVENT_ID\",
    \"status\": \"active\"
  }")

echo "Response: $RESPONSE"

# Extract the database ID from response
DB_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', 'unknown'))" 2>/dev/null)

if [ "$DB_ID" != "unknown" ] && [ -n "$DB_ID" ]; then
    echo ""
    echo "✓ Event created successfully with database ID: $DB_ID"
    echo ""
    echo "To trigger scraping, run:"
    echo "curl -X POST $API_URL/api/v1/scraping/trigger -H 'Content-Type: application/json' -d '{\"event_id\": $DB_ID}'"
    echo ""
    echo "Or trigger it now? (y/n)"
    read -r TRIGGER
    
    if [ "$TRIGGER" = "y" ]; then
        echo "Triggering scrape..."
        curl -X POST "$API_URL/api/v1/scraping/trigger" \
          -H "Content-Type: application/json" \
          -d "{\"event_id\": $DB_ID}"
        echo ""
        echo "✓ Scrape triggered! Check logs with: fly logs --app soccerschedules-backend"
    fi
else
    echo "✗ Failed to create event or extract ID"
fi
