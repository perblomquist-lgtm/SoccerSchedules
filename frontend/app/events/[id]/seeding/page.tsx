'use client';

import { useQuery } from '@tanstack/react-query';
import { schedulesApi } from '@/lib/api';
import { useState, use } from 'react';
import axios from 'axios';

interface SeedingTeam {
  rank: number;
  team_name: string;
  bracket: string;
  points: number;
  goal_difference: number;
  goals_for: number;
  goals_against: number;
  wins: number;
  draws: number;
  losses: number;
  played: number;
  is_bracket_winner: boolean;
}

interface SeedingData {
  division_id: number;
  division_name: string;
  bracket_winners: SeedingTeam[];
  top_remaining: SeedingTeam[];
}

export default function SeedingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const eventId = parseInt(id);
  const [selectedDivision, setSelectedDivision] = useState<number | undefined>();

  // Fetch schedule to get divisions list
  const { data: schedule } = useQuery({
    queryKey: ['schedule', eventId],
    queryFn: async () => {
      const response = await schedulesApi.getEventSchedule(eventId, {});
      return response.data;
    },
  });

  // Fetch seeding data for selected division
  const { data: seedingData, isLoading: seedingLoading, error: seedingError } = useQuery<SeedingData>({
    queryKey: ['seeding', eventId, selectedDivision],
    queryFn: async () => {
      if (!selectedDivision) return null;
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await axios.get(`${API_URL}/api/v1/events/${eventId}/divisions/${selectedDivision}/seeding`);
      return response.data;
    },
    enabled: !!selectedDivision,
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <button
                onClick={() => window.location.href = `/events/${eventId}`}
                className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                ← Back to Schedule
              </button>
              <h1 className="text-xl font-bold text-gray-900">Seeding</h1>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tournament Info */}
        {schedule && (
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900">{schedule.event.name}</h2>
            {schedule.event.last_scraped_at && (
              <p className="text-sm text-gray-500 mt-1">
                Last updated: {new Date(schedule.event.last_scraped_at).toLocaleString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                  hour12: true
                })}
              </p>
            )}
          </div>
        )}

        {/* Division Selector */}
        <div className="mb-8 bg-white rounded-lg shadow p-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Division
          </label>
          <select
            className="w-full px-4 py-2 border border-gray-300 rounded-md text-sm bg-white"
            value={selectedDivision || ''}
            onChange={(e) => setSelectedDivision(e.target.value ? parseInt(e.target.value) : undefined)}
          >
            <option value="">Choose a division...</option>
            {schedule?.divisions.map(division => (
              <option key={division.id} value={division.id}>
                {division.name}
              </option>
            ))}
          </select>
        </div>

        {/* Loading State */}
        {seedingLoading && (
          <div className="text-center py-12">
            <div className="text-lg text-gray-600">Loading seeding data...</div>
          </div>
        )}

        {/* Error State */}
        {seedingError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-800 font-medium">Error loading seeding data</p>
            <p className="text-red-600 text-sm mt-2">
              {axios.isAxiosError(seedingError) && seedingError.response?.status === 404
                ? 'No bracket standings found for this division. Make sure brackets have been scraped.'
                : 'Please try again later.'}
            </p>
          </div>
        )}

        {/* Seeding Tables */}
        {seedingData && !seedingLoading && (
          <div className="space-y-8">
            {/* Bracket Winners */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="bg-green-600 px-6 py-4">
                <h3 className="text-xl font-bold text-white">Bracket Winners</h3>
                <p className="text-green-100 text-sm mt-1">
                  {seedingData.bracket_winners.length} team{seedingData.bracket_winners.length !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Seed</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Team</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bracket</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">PTS</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">GD</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">GF</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">GA</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">W</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">D</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">L</th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">P</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {seedingData.bracket_winners.map((team) => (
                      <tr key={team.rank} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-green-100 text-green-800 font-bold text-sm">
                              {team.rank}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900">{team.team_name}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                            {team.bracket_name}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium text-gray-900">{team.points}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">{team.goal_difference > 0 ? '+' : ''}{team.goal_difference}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">{team.goals_for}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">{team.goals_against}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">{team.wins}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">{team.draws}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">{team.losses}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">{team.played}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Top Remaining Teams */}
            {seedingData.top_remaining.length > 0 && (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="bg-gray-700 px-6 py-4">
                  <h3 className="text-xl font-bold text-white">Top Remaining Teams</h3>
                  <p className="text-gray-300 text-sm mt-1">
                    Next {seedingData.top_remaining.length} best team{seedingData.top_remaining.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Seed</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Team</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Bracket</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">PTS</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">GD</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">GF</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">GA</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">W</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">D</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">L</th>
                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">P</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {seedingData.top_remaining.map((team) => (
                        <tr key={team.rank} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-800 font-bold text-sm">
                                {team.rank}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm font-medium text-gray-900">{team.team_name}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                              {team.bracket_name}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium text-gray-900">{team.points}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">{team.goal_difference > 0 ? '+' : ''}{team.goal_difference}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">{team.goals_for}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">{team.goals_against}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">{team.wins}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">{team.draws}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">{team.losses}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500">{team.played}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* No Division Selected */}
        {!selectedDivision && !seedingLoading && (
          <div className="bg-gray-100 border border-gray-300 rounded-lg p-12 text-center">
            <p className="text-gray-600 text-lg">Please select a division to view seeding</p>
          </div>
        )}
      </main>
    </div>
  );
}
