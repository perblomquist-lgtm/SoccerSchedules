'use client';

import { useQuery } from '@tanstack/react-query';
import { schedulesApi, Game } from '@/lib/api';
import Link from 'next/link';
import { format } from 'date-fns';
import { useState, use } from 'react';

export default function EventPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const eventId = parseInt(id);
  const [selectedDivision, setSelectedDivision] = useState<number | undefined>();
  const [teamFilter, setTeamFilter] = useState('');

  const { data: schedule, isLoading, error } = useQuery({
    queryKey: ['schedule', eventId, selectedDivision, teamFilter],
    queryFn: async () => {
      const response = await schedulesApi.getEventSchedule(eventId, {
        division_id: selectedDivision,
        team_name: teamFilter || undefined,
      });
      return response.data;
    },
  });

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading schedule...</div>
      </div>
    );
  }

  if (error || !schedule) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-red-600">Error loading schedule</div>
      </div>
    );
  }

  const groupedGames = groupGamesByDate(schedule.games);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow sticky top-0 z-10">
        <div className="max-w-7xl mx-auto py-3 px-4 sm:py-6 sm:px-6 lg:px-8">
          <Link href="/" className="text-blue-600 hover:text-blue-800 mb-2 inline-flex items-center gap-1 text-sm sm:text-base">
            <span>←</span> Back to Tournaments
          </Link>
          
          {/* Event ID Badge */}
          <div className="mb-2">
            <span className="inline-block bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">
              Event ID: {schedule.event.gotsport_event_id}
            </span>
          </div>

          <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-900">
            {schedule.event.name}
          </h1>
          
          <div className="mt-2 space-y-1">
            {schedule.event.location && (
              <p className="text-xs sm:text-sm text-gray-600 flex items-center gap-1">
                <span>📍</span> {schedule.event.location}
              </p>
            )}
            {schedule.event.start_date && schedule.event.end_date && (
              <p className="text-xs sm:text-sm text-gray-600 flex items-center gap-1">
                <span>📅</span>
                {format(new Date(schedule.event.start_date), 'MMM d')} -{' '}
                {format(new Date(schedule.event.end_date), 'MMM d, yyyy')}
              </p>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-3 px-4 sm:py-6 sm:px-6 lg:px-8">
        {/* Filters */}
        <div className="bg-white shadow rounded-lg p-3 sm:p-4 mb-4 sm:mb-6">
          <h2 className="text-base sm:text-lg font-semibold text-gray-900 mb-3">Filter Schedule</h2>
          <div className="grid grid-cols-1 gap-3 sm:gap-4">
            <div>
              <label htmlFor="division" className="block text-sm font-medium text-gray-700 mb-1.5">
                Select Division
              </label>
              <select
                id="division"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm sm:text-base"
                value={selectedDivision || ''}
                onChange={(e) => setSelectedDivision(e.target.value ? parseInt(e.target.value) : undefined)}
              >
                <option value="">All Divisions ({schedule.divisions.length})</option>
                {schedule.divisions.map((div) => (
                  <option key={div.id} value={div.id}>
                    {div.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="team" className="block text-sm font-medium text-gray-700 mb-1.5">
                Search by Team
              </label>
              <input
                type="text"
                id="team"
                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm sm:text-base"
                placeholder="Enter team name..."
                value={teamFilter}
                onChange={(e) => setTeamFilter(e.target.value)}
              />
            </div>
          </div>
          {(selectedDivision || teamFilter) && (
            <button
              onClick={() => {
                setSelectedDivision(undefined);
                setTeamFilter('');
              }}
              className="mt-3 text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Clear filters
            </button>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-4 sm:mb-6">
          <div className="bg-white shadow rounded-lg p-3 sm:p-4 text-center">
            <div className="text-xl sm:text-2xl font-bold text-blue-600">{schedule.divisions.length}</div>
            <div className="text-xs sm:text-sm text-gray-600 mt-1">Divisions</div>
          </div>
          <div className="bg-white shadow rounded-lg p-3 sm:p-4 text-center">
            <div className="text-xl sm:text-2xl font-bold text-green-600">{schedule.total_games}</div>
            <div className="text-xs sm:text-sm text-gray-600 mt-1">Games</div>
          </div>
          <div className="bg-white shadow rounded-lg p-3 sm:p-4 text-center">
            <div className="text-xl sm:text-2xl font-bold text-purple-600">
              {Object.keys(groupedGames).length}
            </div>
            <div className="text-xs sm:text-sm text-gray-600 mt-1">Days</div>
          </div>
        </div>

        {/* Schedule */}
        {schedule.games.length === 0 ? (
          <div className="bg-white shadow rounded-lg p-6 sm:p-8 text-center">
            <p className="text-gray-500 text-sm sm:text-base">No games found matching your filters.</p>
          </div>
        ) : (
          <div className="space-y-4 sm:space-y-6">
            {Object.entries(groupedGames).map(([date, games]) => (
              <div key={date} className="bg-white shadow rounded-lg overflow-hidden">
                <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-3 py-2 sm:px-4 sm:py-3">
                  <h3 className="text-base sm:text-lg font-semibold text-white">
                    {formatDateHeader(date)}
                  </h3>
                  <p className="text-xs sm:text-sm text-blue-100 mt-0.5">
                    {games.length} {games.length === 1 ? 'game' : 'games'}
                  </p>
                </div>
                <div className="divide-y divide-gray-200">
                  {games.map((game) => (
                    <GameRow key={game.id} game={game} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function GameRow({ game }: { game: Game }) {
  return (
    <div className="p-3 sm:p-4 hover:bg-gray-50 transition-colors">
      {/* Mobile Layout */}
      <div className="block sm:hidden space-y-3">
        {/* Time and Field */}
        <div className="flex justify-between items-start">
          <div>
            <div className="text-sm font-semibold text-gray-900">{game.game_time || 'TBD'}</div>
            <div className="text-xs text-gray-500 mt-0.5">{game.field_name || 'Field TBD'}</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-500">{game.division_name}</div>
            <div className="text-xs text-gray-400 mt-0.5">Game #{game.game_number}</div>
          </div>
        </div>
        
        {/* Teams and Scores */}
        <div className="space-y-2">
          <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
            <span className="text-sm font-medium text-gray-900 flex-1">{game.home_team_name || 'TBD'}</span>
            {game.home_score !== null && (
              <span className="text-lg font-bold text-gray-900 ml-2">{game.home_score}</span>
            )}
          </div>
          <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
            <span className="text-sm font-medium text-gray-900 flex-1">{game.away_team_name || 'TBD'}</span>
            {game.away_score !== null && (
              <span className="text-lg font-bold text-gray-900 ml-2">{game.away_score}</span>
            )}
          </div>
        </div>
      </div>

      {/* Desktop Layout */}
      <div className="hidden sm:grid sm:grid-cols-12 gap-4 items-center">
        {/* Time and Field */}
        <div className="col-span-3">
          <div className="font-semibold text-gray-900">{game.game_time || 'TBD'}</div>
          <div className="text-sm text-gray-500 mt-0.5">{game.field_name || 'Field TBD'}</div>
        </div>
        
        {/* Teams and Scores */}
        <div className="col-span-6">
          <div className="flex items-center justify-between mb-2 p-2 bg-gray-50 rounded">
            <span className="font-medium text-gray-900">{game.home_team_name || 'TBD'}</span>
            {game.home_score !== null && (
              <span className="text-xl font-bold text-gray-900">{game.home_score}</span>
            )}
          </div>
          <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
            <span className="font-medium text-gray-900">{game.away_team_name || 'TBD'}</span>
            {game.away_score !== null && (
              <span className="text-xl font-bold text-gray-900">{game.away_score}</span>
            )}
          </div>
        </div>
        
        {/* Division and Game Number */}
        <div className="col-span-3 text-right">
          <div className="text-sm text-gray-600">{game.division_name}</div>
          <div className="text-xs text-gray-400 mt-1">Game #{game.game_number}</div>
        </div>
      </div>
    </div>
  );
}

function groupGamesByDate(games: Game[]): Record<string, Game[]> {
  const grouped: Record<string, Game[]> = {};
  
  games.forEach((game) => {
    if (game.game_date) {
      const dateKey = format(new Date(game.game_date), 'yyyy-MM-dd');
      if (!grouped[dateKey]) {
        grouped[dateKey] = [];
      }
      grouped[dateKey].push(game);
    }
  });
  
  return grouped;
}

function formatDateHeader(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return format(date, 'EEEE, MMMM d, yyyy');
  } catch {
    return dateStr;
  }
}
