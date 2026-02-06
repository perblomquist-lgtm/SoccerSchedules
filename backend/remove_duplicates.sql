-- Remove duplicate games, keeping only the oldest record for each unique game
-- A game is considered duplicate if it has the same:
-- division_id, home_team_name, away_team_name, game_date, game_time

-- First, let's see how many duplicates we have
SELECT 
    COUNT(*) as duplicate_count
FROM (
    SELECT 
        id,
        ROW_NUMBER() OVER (
            PARTITION BY division_id, home_team_name, away_team_name, game_date, game_time 
            ORDER BY created_at ASC
        ) as row_num
    FROM games
) subquery
WHERE row_num > 1;

-- Now delete the duplicates (keeping the oldest record for each group)
DELETE FROM games
WHERE id IN (
    SELECT id
    FROM (
        SELECT 
            id,
            ROW_NUMBER() OVER (
                PARTITION BY division_id, home_team_name, away_team_name, game_date, game_time 
                ORDER BY created_at ASC
            ) as row_num
        FROM games
    ) subquery
    WHERE row_num > 1
);

-- Show the result
SELECT 
    e.name as event_name,
    COUNT(g.id) as game_count
FROM events e
LEFT JOIN divisions d ON d.event_id = e.id
LEFT JOIN games g ON g.division_id = d.id
GROUP BY e.id, e.name
ORDER BY e.name;
