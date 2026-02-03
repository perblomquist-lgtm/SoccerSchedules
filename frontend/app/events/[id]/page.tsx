'use client';

import { useQuery } from '@tanstack/react-query';
import { schedulesApi, Game } from '@/lib/api';
import { useState, use, useEffect } from 'react';
import AdminModal from '@/components/AdminModal';

type FilterType = 'all' | 'division' | 'team' | 'location' | 'favorites' | 'current';

export default function EventPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const eventId = parseInt(id);
  const [selectedDivision, setSelectedDivision] = useState<number | undefined>();
  const [teamFilter, setTeamFilter] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const [filterType, setFilterType] = useState<FilterType>('division');
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [favoriteTeams, setFavoriteTeams] = useState<string[]>([]);
  const [showFavoritesModal, setShowFavoritesModal] = useState(false);
  const [showAdminModal, setShowAdminModal] = useState(false);

  // Load favorite teams from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem('favoriteTeams');
    if (stored) {
      setFavoriteTeams(JSON.parse(stored));
    }
  }, []);

  // Save favorite teams to localStorage whenever it changes
  useEffect(() => {
    if (favoriteTeams.length > 0) {
      localStorage.setItem('favoriteTeams', JSON.stringify(favoriteTeams));
    }
  }, [favoriteTeams]);

  const toggleFavoriteTeam = (teamName: string) => {
    setFavoriteTeams(prev => {
      if (prev.includes(teamName)) {
        const updated = prev.filter(t => t !== teamName);
        localStorage.setItem('favoriteTeams', JSON.stringify(updated));
        return updated;
      } else {
        const updated = [...prev, teamName];
        localStorage.setItem('favoriteTeams', JSON.stringify(updated));
        return updated;
      }
    });
  };

  const removeFavoriteTeam = (teamName: string) => {
    const updated = favoriteTeams.filter(t => t !== teamName);
    setFavoriteTeams(updated);
    localStorage.setItem('favoriteTeams', JSON.stringify(updated));
  };

  const clearAllFavorites = () => {
    setFavoriteTeams([]);
    localStorage.removeItem('favoriteTeams');
  };

  const { data: schedule, isLoading, error } = useQuery({
    queryKey: ['schedule', eventId, selectedDivision],
    queryFn: async () => {
      const response = await schedulesApi.getEventSchedule(eventId, {
        division_id: selectedDivision,
      });
      return response.data;
    },
  });

  // Extract unique teams from all games
  const allTeams = schedule ? Array.from(new Set([
    ...schedule.games.map(g => g.home_team_name).filter((name): name is string => Boolean(name)),
    ...schedule.games.map(g => g.away_team_name).filter((name): name is string => Boolean(name))
  ])).sort() : [];

  // Extract unique locations from all games
  const allLocations = schedule ? Array.from(new Set(
    schedule.games.map(g => g.field_name).filter((name): name is string => Boolean(name))
  )).sort() : [];

  // Filter games by location when location filter is active and sort by date/time
  const filteredGames = (schedule?.games.filter(game => {
    if (filterType === 'location' && locationFilter) {
      return game.field_name === locationFilter;
    }
    if (filterType === 'team' && teamFilter) {
      return (game.home_team_name === teamFilter) || (game.away_team_name === teamFilter);
    }
    if (filterType === 'favorites') {
      return (game.home_team_name && favoriteTeams.includes(game.home_team_name)) ||
             (game.away_team_name && favoriteTeams.includes(game.away_team_name));
    }
    return true;
  }) || []).sort((a, b) => {
    // First sort by date
    const dateA = a.game_date ? new Date(a.game_date).getTime() : 0;
    const dateB = b.game_date ? new Date(b.game_date).getTime() : 0;
    
    if (dateA !== dateB) {
      return dateA - dateB;
    }
    
    // If dates are equal, sort by time
    // Convert time strings like "8:00 AM" to comparable numbers
    const parseTime = (timeStr: string | null) => {
      if (!timeStr) return 0;
      const match = timeStr.match(/(\d+):(\d+)\s*(AM|PM)/i);
      if (!match) return 0;
      let hours = parseInt(match[1]);
      const minutes = parseInt(match[2]);
      const period = match[3].toUpperCase();
      
      // Convert to 24-hour format
      if (period === 'PM' && hours !== 12) hours += 12;
      if (period === 'AM' && hours === 12) hours = 0;
      
      return hours * 60 + minutes; // Return total minutes for comparison
    };
    
    const timeA = parseTime(a.game_time);
    const timeB = parseTime(b.game_time);
    return timeA - timeB;
  });

  // Handle filter type change - reset all filters
  const handleFilterTypeChange = (newFilterType: FilterType) => {
    setFilterType(newFilterType);
    setSelectedDivision(undefined);
    setTeamFilter('');
    setLocationFilter('');
    setShowFilterMenu(false);
  };

  // Handle clicking on a team name in the table
  const handleTeamClick = (teamName: string) => {
    setFilterType('team');
    setTeamFilter(teamName);
    setSelectedDivision(undefined);
    setLocationFilter('');
  };

  // Handle clicking on a location in the table
  const handleLocationClick = (location: string) => {
    setFilterType('location');
    setLocationFilter(location);
    setSelectedDivision(undefined);
    setTeamFilter('');
  };

  // Handle clicking on a division in the table
  const handleDivisionClick = (divisionId: number) => {
    setFilterType('division');
    setSelectedDivision(divisionId);
    setTeamFilter('');
    setLocationFilter('');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-lg text-gray-600">Loading schedule...</div>
      </div>
    );
  }

  if (error || !schedule) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-lg text-red-600">Error loading schedule</div>
      </div>
    );
  }

  const getFilterLabel = () => {
    switch (filterType) {
      case 'all': return 'All Games';
      case 'division': return 'Filter by Division';
      case 'team': return 'Filter by Team';
      case 'location': return 'Filter by Location';
      case 'favorites': return 'Show Favorites';
      case 'current': return 'Current Matches';
      default: return 'Filter by Division';
    }
  };

  const getViewingText = () => {
    if (filterType === 'location' && locationFilter) {
      return locationFilter;
    }
    if (filterType === 'division' && selectedDivision) {
      const division = schedule?.divisions.find(d => d.id === selectedDivision);
      return division?.name || 'All';
    }
    if (filterType === 'team' && teamFilter) {
      return teamFilter;
    }
    return 'All';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Admin Modal */}
      <AdminModal isOpen={showAdminModal} onClose={() => setShowAdminModal(false)} />
      
      {/* Top Navigation Bar */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Left side - Tournament selector and viewing mode */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-700">Tournament:</span>
                <select 
                  className="px-3 py-1.5 border border-gray-300 rounded-md text-sm bg-white min-w-[200px]"
                  value={eventId}
                  onChange={(e) => window.location.href = `/events/${e.target.value}`}
                >
                  <option value={eventId}>{schedule.event.name}</option>
                </select>
              </div>
              {schedule.event.last_scraped_at && (
                <div className="text-xs text-gray-500">
                  Last Scraped: {new Date(schedule.event.last_scraped_at).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true
                  })}
                </div>
              )}
            </div>
            
            {/* Right side - Admin button */}
            <button
              onClick={() => setShowAdminModal(true)}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
            >
              Admin
            </button>
          </div>
        </div>
      </header>

      {/* Viewing Info */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-2 text-base text-gray-700">
            <span>Viewing: <span className="font-bold">{getViewingText()}</span></span>
            {filterType === 'team' && teamFilter && (
              <button
                onClick={() => toggleFavoriteTeam(teamFilter)}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title={favoriteTeams.includes(teamFilter) ? 'Remove from favorites' : 'Add to favorites'}
              >
                <svg 
                  className="w-5 h-5" 
                  fill={favoriteTeams.includes(teamFilter) ? 'currentColor' : 'none'}
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" 
                  />
                </svg>
              </button>
            )}
            {filterType === 'favorites' && favoriteTeams.length > 0 && (
              <button
                onClick={() => setShowFavoritesModal(true)}
                className="flex items-center gap-2 px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors"
              >
                <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
                <span>{favoriteTeams.length} favorite team{favoriteTeams.length !== 1 ? 's' : ''}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {/* Filter Bar */}
        <div className="bg-white rounded-lg shadow mb-6 p-4">
          <div className="flex items-center gap-4">
            {/* Filter Type Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowFilterMenu(!showFilterMenu)}
                className="flex items-center justify-between gap-2 px-4 py-2 border border-gray-300 rounded-md text-sm bg-white min-w-[200px] hover:bg-gray-50"
              >
                <span>{getFilterLabel()}</span>
                <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {showFilterMenu && (
                <div className="absolute top-full left-0 mt-1 w-full bg-white border border-gray-200 rounded-md shadow-lg z-10">
                  <button
                    onClick={() => handleFilterTypeChange('all')}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center justify-between"
                  >
                    All Games
                  </button>
                  <button
                    onClick={() => handleFilterTypeChange('division')}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center justify-between"
                  >
                    Filter by Division
                    {filterType === 'division' && <span>✓</span>}
                  </button>
                  <button
                    onClick={() => handleFilterTypeChange('team')}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                  >
                    Filter by Team
                  </button>
                  <button
                    onClick={() => handleFilterTypeChange('location')}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                  >
                    Filter by Location
                  </button>
                  <button
                    onClick={() => handleFilterTypeChange('favorites')}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                  >
                    Show Favorites
                  </button>
                  <button
                    onClick={() => handleFilterTypeChange('current')}
                    className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50"
                  >
                    Current Matches
                  </button>
                </div>
              )}
            </div>

            {/* Division Selector (when filter type is division) */}
            {filterType === 'division' && (
              <select
                className="px-4 py-2 border border-gray-300 rounded-md text-sm bg-white min-w-[200px]"
                value={selectedDivision || ''}
                onChange={(e) => setSelectedDivision(e.target.value ? parseInt(e.target.value) : undefined)}
              >
                <option value="">Select division...</option>
                {schedule.divisions.map((div) => (
                  <option key={div.id} value={div.id}>
                    {div.name}
                  </option>
                ))}
              </select>
            )}

            {/* Team Filter (when filter type is team) */}
            {filterType === 'team' && (
              <select
                className="px-4 py-2 border border-gray-300 rounded-md text-sm bg-white min-w-[200px]"
                value={teamFilter}
                onChange={(e) => setTeamFilter(e.target.value)}
              >
                <option value="">All Teams</option>
                {allTeams.map((team) => (
                  <option key={team} value={team}>
                    {team}
                  </option>
                ))}
              </select>
            )}

            {/* Location Filter (when filter type is location) */}
            {filterType === 'location' && (
              <select
                className="px-4 py-2 border border-gray-300 rounded-md text-sm bg-white min-w-[200px]"
                value={locationFilter}
                onChange={(e) => setLocationFilter(e.target.value)}
              >
                <option value="">All Locations</option>
                {allLocations.map((location) => (
                  <option key={location} value={location}>
                    {location}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {/* Games Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Home Team
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Results
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Away Team
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Location
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Division
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredGames.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                    No matches found. Contact an admin to upload schedules.
                  </td>
                </tr>
              ) : (
                filteredGames.map((game) => (
                  <tr key={game.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div>{game.game_date ? new Date(game.game_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : ''}</div>
                      <div className="text-gray-600">{game.game_time || 'TBD'}</div>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        onClick={() => game.home_team_name && handleTeamClick(game.home_team_name)}
                        className="text-blue-600 hover:text-blue-800 hover:underline text-left"
                        disabled={!game.home_team_name}
                      >
                        {game.home_team_name || 'TBD'}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                      {game.home_score !== null && game.away_score !== null ? (
                        <span className="font-semibold">{game.home_score} - {game.away_score}</span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        onClick={() => game.away_team_name && handleTeamClick(game.away_team_name)}
                        className="text-blue-600 hover:text-blue-800 hover:underline text-left"
                        disabled={!game.away_team_name}
                      >
                        {game.away_team_name || 'TBD'}
                      </button>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        onClick={() => game.field_name && handleLocationClick(game.field_name)}
                        className="text-blue-600 hover:text-blue-800 hover:underline text-left"
                        disabled={!game.field_name}
                      >
                        {game.field_name || 'TBD'}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      <button
                        onClick={() => game.division_id && handleDivisionClick(game.division_id)}
                        className="text-blue-600 hover:text-blue-800 hover:underline text-left"
                        disabled={!game.division_id}
                      >
                        {game.division_name}
                      </button>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        game.status === 'completed' 
                          ? 'bg-green-100 text-green-800' 
                          : game.status === 'in_progress'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {game.status || 'scheduled'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>

      {/* Favorites Modal */}
      {showFavoritesModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowFavoritesModal(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold">My Favorite Teams - {schedule?.event.name}</h2>
                <button
                  onClick={() => setShowFavoritesModal(false)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="space-y-3">
                {favoriteTeams.map((team) => (
                  <div key={team} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <span className="text-lg">{team}</span>
                    <button
                      onClick={() => removeFavoriteTeam(team)}
                      className="text-gray-400 hover:text-red-600 transition-colors"
                      title="Remove from favorites"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
