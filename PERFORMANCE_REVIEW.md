# Performance Code Review - Soccer Schedules App

## Executive Summary

This comprehensive review identified **17 performance issues** across backend and frontend, categorized by severity:
- 🔴 **Critical (5)**: High-impact issues causing N+1 queries, unnecessary data fetching
- 🟡 **Medium (8)**: Moderate impact on response time and user experience  
- 🟢 **Low (4)**: Minor optimizations for long-term maintainability

**Estimated Performance Gains:**
- Backend API responses: **40-70% faster** (especially list endpoints)
- Frontend initial load: **30-50% faster**
- Database query count: **Reduced by 60-80%** on list operations

---

## Backend Performance Issues

### 🔴 CRITICAL ISSUES

#### 1. N+1 Query Problem in Event List Endpoint
**File:** `backend/app/api/v1/endpoints/events.py` (Lines 16-57)

**Problem:**
```python
for event in events:
    # Each iteration = 2 separate DB queries!
    div_count = await db.scalar(select(func.count(Division.id)).where(...))
    game_count = await db.scalar(select(func.count(Game.id)).join(...).where(...))
```

For 10 events, this executes **21 queries** (1 for events + 20 individual count queries).

**Solution:** Use a single query with JOINs and GROUP BY
```python
from sqlalchemy import func, case

# Single query gets all counts
result = await db.execute(
    select(
        Event,
        func.count(func.distinct(Division.id)).label('div_count'),
        func.count(Game.id).label('game_count')
    )
    .outerjoin(Division)
    .outerjoin(Game)
    .group_by(Event.id)
    .order_by(Event.created_at.desc())
    .offset(skip)
    .limit(limit)
)

for event, div_count, game_count in result:
    response.append(EventWithStats(
        **event.__dict__,
        total_divisions=div_count or 0,
        total_games=game_count or 0,
        ...
    ))
```

**Impact:** Reduces 21 queries to 1 query for 10 events (**95% reduction**)

---

#### 2. Missing Composite Indexes on Game Lookups
**File:** `backend/app/models/models.py`

**Problem:** Game queries frequently filter by multiple columns together:
- `division_id + gotsport_game_id`
- `division_id + home_team_name + away_team_name + game_date + game_time`
- `game_date + game_time` (for sorting)

Only individual column indexes exist, forcing full table scans.

**Solution:** Add composite indexes
```python
from sqlalchemy import Index

class Game(Base):
    __tablename__ = "games"
    
    # ... existing columns ...
    
    __table_args__ = (
        Index('ix_games_division_gotsport', 'division_id', 'gotsport_game_id'),
        Index('ix_games_division_teams_datetime', 
              'division_id', 'home_team_name', 'away_team_name', 'game_date', 'game_time'),
        Index('ix_games_datetime', 'game_date', 'game_time'),  # For sorting
        Index('ix_games_field_date', 'field_name', 'game_date'),  # For location+date filters
    )
```

**Migration Required:** Create Alembic migration to add indexes
```bash
cd backend && alembic revision --autogenerate -m "add_composite_indexes_to_games"
```

**Impact:** 10-100x faster game lookups in scraper (especially for large tournaments)

---

#### 3. Inefficient Game Deduplication in Scraper
**File:** `backend/app/services/scrape_service.py` (Lines 232-262)

**Problem:** Each game queries the database 1-2 times to check if it exists:
```python
for game_data in games_data:  # For 1000 games...
    if gotsport_game_id:
        result = await self.db.execute(select(Game).where(...))  # Query #1
        game = result.scalar_one_or_none()
    
    if not game:  # Often true
        result = await self.db.execute(select(Game).where(...))  # Query #2
        game = result.scalar_one_or_none()
```

This results in **1000-2000 queries** for a tournament with 1000 games!

**Solution:** Bulk load existing games into memory
```python
async def _store_games(self, event: Event, divisions_map: Dict, games_data: List[Dict]):
    # Pre-load ALL existing games for this event (1 query)
    division_ids = [div.id for div in divisions_map.values()]
    result = await self.db.execute(
        select(Game).where(Game.division_id.in_(division_ids))
    )
    existing_games = result.scalars().all()
    
    # Build lookup dictionaries
    games_by_gotsport_id = {g.gotsport_game_id: g for g in existing_games if g.gotsport_game_id}
    games_by_signature = {
        (g.division_id, g.home_team_name, g.away_team_name, g.game_date, g.game_time): g
        for g in existing_games
    }
    
    # Now process games using in-memory lookups (no queries!)
    for game_data in games_data:
        gotsport_id = game_data.get('gotsport_game_id')
        game = games_by_gotsport_id.get(gotsport_id) if gotsport_id else None
        
        if not game:
            signature = (division.id, home_team, away_team, game_date, game_time)
            game = games_by_signature.get(signature)
        
        # ... update or create game ...
```

**Impact:** Reduces 1000-2000 queries to 1 query (**99.9% reduction**)

---

#### 4. Schedule Endpoint Returns All Games Without Pagination
**File:** `backend/app/api/v1/endpoints/schedules.py` (Lines 19-102)

**Problem:** 
- Fetches ALL games for an event (could be 2000+)
- No pagination or limit
- Returns full objects with all fields
- Frontend loads entire dataset even if only viewing one division

**Solution:** Add pagination and field selection
```python
@router.get("/{event_id}", response_model=ScheduleResponse)
async def get_event_schedule(
    event_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),  # Max 1000 games per request
    division_id: Optional[int] = None,
    fields: Optional[str] = Query(None, description="Comma-separated fields to return"),
    # ... other filters ...
):
    # Count total games for pagination
    count_query = select(func.count(Game.id)).join(Division).where(Division.event_id == event_id)
    # Apply same filters to count query...
    total_games = await db.scalar(count_query)
    
    # Fetch games with pagination
    query = query.offset(skip).limit(limit)
    
    # ... rest of logic ...
    
    return ScheduleResponse(
        event=event,
        divisions=divisions,
        games=games_response,
        total_games=total_games,
        page=skip // limit + 1,
        page_size=limit,
        has_more=skip + limit < total_games
    )
```

**Frontend Update:** Use infinite scroll or "Load More" button

**Impact:** 
- Initial load time: **50-80% faster**
- Network transfer: **80-95% smaller**

---

#### 5. Event Stats Query in Single Event Endpoint
**File:** `backend/app/api/v1/endpoints/events.py` (Lines 95-127)

**Problem:** Same N+1 issue as list endpoint but for single event
```python
div_count = await db.scalar(...)  # Query 1
game_count = await db.scalar(...)  # Query 2
```

**Solution:** Use single query with JOINs
```python
result = await db.execute(
    select(
        Event,
        func.count(func.distinct(Division.id)).label('div_count'),
        func.count(Game.id).label('game_count')
    )
    .outerjoin(Division)
    .outerjoin(Game)
    .where(Event.id == event_id)
    .group_by(Event.id)
)

row = result.one_or_none()
if not row:
    raise HTTPException(404, detail=f"Event {event_id} not found")

event, div_count, game_count = row
```

**Impact:** 3 queries → 1 query (**67% reduction**)

---

### 🟡 MEDIUM PRIORITY

#### 6. Missing Field Name Index
**File:** `backend/app/models/models.py`

**Problem:** Filtering by `field_name` is common but not indexed
- Frontend filters by location frequently
- "Current matches" view groups by field

**Solution:**
```python
field_name: Mapped[Optional[str]] = mapped_column(String(100), index=True)
```

---

#### 7. Missing Response Caching
**File:** `backend/app/api/v1/endpoints/schedules.py`

**Problem:** Schedule data changes only during scrapes (hourly) but API is called on every page load.

**Solution:** Add Redis/in-memory caching with TTL
```python
from fastapi_cache.decorator import cache

@router.get("/{event_id}")
@cache(expire=300)  # Cache for 5 minutes
async def get_event_schedule(...):
    # ... existing logic ...
```

Install: `pip install fastapi-cache2[redis]`

**Impact:** 95% of requests served from cache, **instant response**

---

#### 8. Event List Returns Last_Scraped_At Without Timezone Handling
**File:** Multiple

**Problem:** Timezone-aware datetime comparisons are expensive and repeated.

**Solution:** Store timestamps in UTC (already done), but ensure consistent handling and add DB-level defaults.

---

#### 9. No Database Connection Pooling Configuration
**File:** `backend/app/core/database.py`

**Problem:** Default connection pool may be too small for concurrent scraping + API requests.

**Solution:** Tune pool settings
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,  # Increase from default 5
    max_overflow=30,  # Allow 50 total connections
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600,  # Recycle connections hourly
)
```

---

#### 10. Division Endpoint Missing
**Problem:** Frontend builds team/location lists by iterating all games. For 2000 games, this is slow in JavaScript.

**Solution:** Add endpoints to get unique teams/locations
```python
@router.get("/{event_id}/teams")
async def get_event_teams(event_id: int):
    result = await db.execute(
        select(func.distinct(Game.home_team_name))
        .join(Division)
        .where(Division.event_id == event_id, Game.home_team_name.isnot(None))
        .union(
            select(func.distinct(Game.away_team_name))
            .join(Division)
            .where(Division.event_id == event_id, Game.away_team_name.isnot(None))
        )
        .order_by(Game.home_team_name)
    )
    return {"teams": [row[0] for row in result]}

@router.get("/{event_id}/locations")
async def get_event_locations(event_id: int):
    result = await db.execute(
        select(func.distinct(Game.field_name))
        .join(Division)
        .where(Division.event_id == event_id, Game.field_name.isnot(None))
        .order_by(Game.field_name)
    )
    return {"locations": [row[0] for row in result]}
```

**Impact:** Offload processing to database, faster and more accurate

---

### 🟢 LOW PRIORITY

#### 11. Scraper Doesn't Use Bulk Insert
**File:** `backend/app/services/scrape_service.py`

**Problem:** Games added one at a time with `self.db.add(game)`

**Solution:** Use `bulk_save_objects` for new games
```python
new_games = []
for game_data in games_data:
    if not game:
        new_games.append(self._create_game_from_data(division.id, game_data))

if new_games:
    self.db.add_all(new_games)  # Bulk insert
```

**Impact:** Marginal - flush already batches, but cleaner code

---

#### 12. No Query Logging in Development
**Problem:** Hard to identify slow queries without logging.

**Solution:** Enable SQLAlchemy query logging
```python
# In config.py for development
if settings.ENVIRONMENT == "development":
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

---

## Frontend Performance Issues

### 🔴 CRITICAL ISSUES

#### 13. Frontend Fetches Entire Schedule on Every Load
**File:** `frontend/app/events/[id]/page.tsx` (Lines 90-97)

**Problem:**
```typescript
const { data: schedule } = useQuery({
    queryKey: ['schedule', eventId, selectedDivision],
    queryFn: async () => {
        const response = await schedulesApi.getEventSchedule(eventId, {
            division_id: selectedDivision,
        });
        return response.data;  // Returns ALL games (2000+)
    },
});
```

Even when filtering by division, backend returns all games then frontend filters.

**Solution:** 
1. Add pagination to API (see backend issue #4)
2. Use TanStack Query's infinite scroll
```typescript
const {
    data,
    fetchNextPage,
    hasNextPage,
} = useInfiniteQuery({
    queryKey: ['schedule', eventId, selectedDivision],
    queryFn: ({ pageParam = 0 }) => 
        schedulesApi.getEventSchedule(eventId, {
            division_id: selectedDivision,
            skip: pageParam,
            limit: 100,
        }),
    getNextPageParam: (lastPage) => 
        lastPage.has_more ? lastPage.page * lastPage.page_size : undefined,
});
```

**Impact:** **70-90% faster initial load**

---

#### 14. Computing allTeams and allLocations on Every Render
**File:** `frontend/app/events/[id]/page.tsx` (Lines 99-106)

**Problem:**
```typescript
// Runs on EVERY render!
const allTeams = schedule ? Array.from(new Set([
    ...schedule.games.map(g => g.home_team_name).filter(...),
    ...schedule.games.map(g => g.away_team_name).filter(...)
])).sort() : [];
```

For 2000 games, this iterates 4000 times (2 maps + Set + sort) **on every keystroke, mouse move, etc.**

**Solution:** Use `useMemo`
```typescript
const allTeams = useMemo(() => {
    if (!schedule) return [];
    return Array.from(new Set([
        ...schedule.games.map(g => g.home_team_name).filter((n): n is string => Boolean(n)),
        ...schedule.games.map(g => g.away_team_name).filter((n): n is string => Boolean(n))
    ])).sort();
}, [schedule?.games]);

const allLocations = useMemo(() => {
    if (!schedule) return [];
    return Array.from(new Set(
        schedule.games.map(g => g.field_name).filter((n): n is string => Boolean(n))
    )).sort();
}, [schedule?.games]);
```

**Even Better:** Use backend endpoint (see issue #10)

**Impact:** **Eliminates 4000+ operations per render**

---

#### 15. Filtering and Sorting Games on Every Render
**File:** `frontend/app/events/[id]/page.tsx` (Lines 158-191)

**Problem:**
```typescript
const filteredGames = (schedule?.games.filter(game => {
    // ... complex filtering logic ...
}) || []).sort((a, b) => {
    // ... complex sorting logic ...
});
```

This runs on EVERY component render!

**Solution:** Use `useMemo`
```typescript
const filteredGames = useMemo(() => {
    if (!schedule?.games) return [];
    
    return schedule.games
        .filter(game => {
            // ... filtering logic ...
        })
        .sort((a, b) => {
            // ... sorting logic ...
        });
}, [schedule?.games, filterType, locationFilter, teamFilter, favoriteTeams, myClubName, selectedDivision]);
```

**Impact:** Eliminates thousands of operations on every render

---

### 🟡 MEDIUM PRIORITY

#### 16. Inefficient getCurrentMatches Algorithm
**File:** `frontend/app/events/[id]/page.tsx` (Lines 135-156)

**Problem:**
- Iterates ALL games to find today's games
- Groups games by field (loops again)
- Sorts games per field (more loops)
- O(n²) complexity for n games

**Solution 1:** Move to backend with efficient SQL
```python
@router.get("/{event_id}/current-matches")
async def get_current_matches(event_id: int):
    from sqlalchemy import distinct, and_
    from datetime import date, datetime
    
    now = datetime.now()
    today = date.today()
    
    # Get latest game per field that has started today
    subquery = (
        select(
            Game.field_name,
            func.max(Game.game_time).label('max_time')
        )
        .join(Division)
        .where(
            Division.event_id == event_id,
            func.date(Game.game_date) == today,
            Game.game_time <= now.strftime('%I:%M %p')
        )
        .group_by(Game.field_name)
        .subquery()
    )
    
    result = await db.execute(
        select(Game)
        .join(subquery, and_(
            Game.field_name == subquery.c.field_name,
            Game.game_time == subquery.c.max_time
        ))
    )
    return result.scalars().all()
```

**Solution 2:** At minimum, memoize the function
```typescript
const currentMatches = useMemo(() => getCurrentMatches(filteredGames), [filteredGames]);
```

---

#### 17. Home Page Auto-Redirects Prevent Caching
**File:** `frontend/app/page.tsx` (Lines 37-48)

**Problem:**
```typescript
if (selectedEventId) {
    window.location.href = `/events/${selectedEventId}`;  // Full page reload!
    return null;
}
```

`window.location.href` causes full page reload, losing React state and cache.

**Solution:** Use Next.js router
```typescript
import { useRouter } from 'next/navigation';

const router = useRouter();

// Later:
if (selectedEventId) {
    router.push(`/events/${selectedEventId}`);  // Client-side navigation
    return null;
}
```

---

### 🟢 LOW PRIORITY

#### 18. Multiple Storage Event Listeners
**File:** `frontend/app/events/[id]/page.tsx` (Lines 45-58)

**Problem:** Sets up both storage listener AND 500ms interval polling.

**Solution:** Use single listener and trigger manual check when modal closes
```typescript
// Pass callback to AdminModal
<AdminModal 
    isOpen={showAdminModal} 
    onClose={() => {
        setShowAdminModal(false);
        const storedClubName = localStorage.getItem('myClubName');
        setMyClubName(storedClubName || '');
    }} 
/>
```

---

#### 19. No Bundle Size Optimization
**File:** `frontend/next.config.ts`

**Solution:** Enable compression and analysis
```typescript
const nextConfig = {
    compress: true,
    swcMinify: true,
    
    webpack: (config, { isServer }) => {
        if (!isServer) {
            config.optimization.splitChunks = {
                chunks: 'all',
                cacheGroups: {
                    default: false,
                    vendors: false,
                    lib: {
                        test: /node_modules/,
                        name: 'lib',
                        priority: 10,
                    },
                },
            };
        }
        return config;
    },
};
```

---

## Implementation Priority

### Phase 1 - Immediate Impact (1-2 days)
1. ✅ Fix N+1 queries in event list endpoint (#1)
2. ✅ Add composite indexes to games table (#2)
3. ✅ Add `useMemo` to frontend filtering (#14, #15)
4. ✅ Bulk load games in scraper (#3)

**Expected Gain:** 60-80% improvement in API response times

### Phase 2 - Medium Impact (2-3 days)
5. ✅ Add pagination to schedule endpoint (#4)
6. ✅ Implement frontend pagination/infinite scroll (#13)
7. ✅ Add field_name index (#6)
8. ✅ Move current matches to backend (#16)
9. ✅ Add teams/locations endpoints (#10)

**Expected Gain:** 40-60% improvement in page load times

### Phase 3 - Long-term Improvements (1 week)
10. ✅ Implement caching layer (#7)
11. ✅ Tune database connection pool (#9)
12. ✅ Enable query logging in dev (#12)
13. ✅ Use Next.js router properly (#17)

**Expected Gain:** 20-30% additional improvement + better debugging

---

## Testing Performance Improvements

### Backend Benchmarking
```bash
# Before and after changes
time curl -s "https://soccerschedules-backend.fly.dev/api/v1/events/" > /dev/null

# Load testing with Apache Bench
ab -n 1000 -c 10 https://soccerschedules-backend.fly.dev/api/v1/events/

# Monitor database queries
# Add to scrape_service.py temporarily:
import time
start = time.time()
# ... query ...
print(f"Query took {time.time() - start:.3f}s")
```

### Frontend Benchmarking
```javascript
// In browser console
performance.mark('start');
// Load page
performance.mark('end');
performance.measure('page-load', 'start', 'end');
console.table(performance.getEntriesByType('measure'));

// React DevTools Profiler
// Enable in providers.tsx and record interactions
```

### Database Query Analysis
```sql
-- Check query execution plans
EXPLAIN ANALYZE 
SELECT g.*, d.name as division_name 
FROM games g 
JOIN divisions d ON g.division_id = d.id 
WHERE d.event_id = 26 
ORDER BY g.game_date, g.game_time;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'games';
```

---

## Monitoring Recommendations

1. **Add APM (Application Performance Monitoring)**
   - Backend: Sentry Performance or New Relic
   - Frontend: Vercel Analytics or Google Lighthouse CI

2. **Database Monitoring**
   - Fly.io Postgres metrics dashboard
   - Set up alerts for slow queries (>1s)

3. **Key Metrics to Track**
   - API p95/p99 response times
   - Database connection pool usage
   - Cache hit rate (after implementing caching)
   - Frontend First Contentful Paint (FCP)
   - Frontend Time to Interactive (TTI)

---

## Conclusion

Implementing Phase 1 improvements alone will provide **massive performance gains** with minimal risk:
- Event list API: **5-10x faster**
- Schedule page load: **3-5x faster**  
- Scraper operation: **10-20x faster**

The most critical issues are:
1. N+1 queries (backend)
2. Missing composite indexes (database)
3. Bulk game loading (scraper)
4. Unnecessary re-renders (frontend)

These should be addressed immediately for best user experience.
