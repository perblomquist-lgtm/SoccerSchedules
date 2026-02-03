# Soccer Schedule Scraper

A full-stack web application that scrapes soccer tournament schedules from Gotsport and displays them in a responsive web interface.

## Features

- 🔄 Automated schedule scraping from Gotsport tournament sites
- 📅 Smart scraping frequency: Daily by default, hourly starting the day before tournaments
- 🏆 Multi-event support with age/gender divisions
- 📱 Responsive mobile-first web interface
- 🔍 Advanced filtering by division, date, field, and team
- 📊 Real-time schedule updates

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM with async support
- **PostgreSQL** - Relational database
- **Playwright** - Headless browser for scraping
- **APScheduler** - Background job scheduling
- **Redis** - Caching and job queue

### Frontend
- **Next.js** - React framework with SSR
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **React Query** - Data fetching and caching

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Quick Start with Docker

1. Clone the repository:
```bash
git clone <repository-url>
cd Soccerschedules
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start all services:
```bash
docker-compose up -d
```

4. Run database migrations:
```bash
docker-compose exec backend alembic upgrade head
```

5. Install Playwright browsers:
```bash
docker-compose exec backend playwright install chromium
```

6. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Local Development

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
Soccerschedules/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── scraper/       # Playwright scraper
│   │   ├── database.py    # Database configuration
│   │   ├── scheduler.py   # APScheduler configuration
│   │   └── main.py        # FastAPI application
│   ├── alembic/           # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js app directory
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities and API client
│   │   └── types/         # TypeScript types
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

## Usage

### Adding a New Event

1. Navigate to the web interface
2. Click "Add Event"
3. Enter the Gotsport event URL (e.g., https://system.gotsport.com/org_event/events/39474)
4. The system will automatically scrape and display the schedule

### Viewing Schedules

- Browse all events on the home page
- Click an event to view its full schedule
- Filter by division, date, field, or team
- Schedules update automatically based on smart frequency rules

## API Endpoints

- `GET /api/events` - List all events
- `POST /api/events` - Add new event
- `GET /api/events/{id}` - Get event details
- `GET /api/events/{id}/schedules` - Get schedules with filters
- `POST /api/events/{id}/scrape` - Trigger manual scrape
- `GET /api/health` - Health check

## License

MIT
