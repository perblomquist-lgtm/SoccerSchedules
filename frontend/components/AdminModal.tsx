'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { eventsApi, scrapingApi, Event } from '@/lib/api';
import { format } from 'date-fns';

interface AdminModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AdminModal({ isOpen, onClose }: AdminModalProps) {
  const [newEventId, setNewEventId] = useState('');
  const [newEventName, setNewEventName] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const queryClient = useQueryClient();

  const { data: events, isLoading } = useQuery({
    queryKey: ['events'],
    queryFn: async () => {
      const response = await eventsApi.getAll();
      return response.data;
    },
    enabled: isOpen,
  });

  const deleteEventMutation = useMutation({
    mutationFn: (eventId: number) => eventsApi.delete(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['events'] });
      setSuccess('Event deleted successfully');
      setTimeout(() => setSuccess(''), 3000);
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to delete event');
      setTimeout(() => setError(''), 5000);
    },
  });

  const addEventMutation = useMutation({
    mutationFn: async (data: { gotsport_event_id: string; name: string }) => {
      const url = `https://system.gotsport.com/org_event/events/${data.gotsport_event_id}`;
      const response = await eventsApi.create({
        gotsport_event_id: data.gotsport_event_id,
        name: data.name,
        url,
        status: 'active',
      });
      return response.data;
    },
    onSuccess: async (newEvent) => {
      queryClient.invalidateQueries({ queryKey: ['events'] });
      setSuccess(`Event added successfully! Scraping started for "${newEvent.name}"`);
      setNewEventId('');
      setNewEventName('');
      setShowAddForm(false);
      setTimeout(() => setSuccess(''), 5000);
    },
    onError: (error: any) => {
      setError(error.response?.data?.detail || 'Failed to add event');
      setTimeout(() => setError(''), 5000);
    },
  });

  const handleDeleteEvent = (event: Event) => {
    if (window.confirm(`Are you sure you want to delete "${event.name}"? This will remove all games and divisions for this event.`)) {
      deleteEventMutation.mutate(event.id);
    }
  };

  const handleAddEvent = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!newEventId.trim()) {
      setError('Event ID is required');
      return;
    }
    if (!newEventName.trim()) {
      setError('Event name is required');
      return;
    }

    addEventMutation.mutate({
      gotsport_event_id: newEventId.trim(),
      name: newEventName.trim(),
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Admin Panel</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Status Messages */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg">
              {success}
            </div>
          )}

          {/* Add Event Section */}
          <div className="mb-6">
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="w-full sm:w-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              {showAddForm ? 'Cancel' : '+ Add New Event'}
            </button>

            {showAddForm && (
              <form onSubmit={handleAddEvent} className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="space-y-4">
                  <div>
                    <label htmlFor="eventId" className="block text-sm font-medium text-gray-700 mb-1">
                      Gotsport Event ID *
                    </label>
                    <input
                      type="text"
                      id="eventId"
                      value={newEventId}
                      onChange={(e) => setNewEventId(e.target.value)}
                      placeholder="e.g., 39474"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Find this in the Gotsport URL: https://system.gotsport.com/org_event/events/<strong>39474</strong>
                    </p>
                  </div>
                  <div>
                    <label htmlFor="eventName" className="block text-sm font-medium text-gray-700 mb-1">
                      Event Name *
                    </label>
                    <input
                      type="text"
                      id="eventName"
                      value={newEventName}
                      onChange={(e) => setNewEventName(e.target.value)}
                      placeholder="e.g., 2025 U.S. Futsal Northeast Regional Championship"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      required
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={addEventMutation.isPending}
                    className="w-full sm:w-auto px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
                  >
                    {addEventMutation.isPending ? 'Adding...' : 'Add Event & Start Scraping'}
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* Events List */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Active Events</h3>
            
            {isLoading ? (
              <div className="text-center py-8 text-gray-500">Loading events...</div>
            ) : !events || events.length === 0 ? (
              <div className="text-center py-8 text-gray-500">No events found</div>
            ) : (
              <div className="space-y-3">
                {events.map((event) => (
                  <div
                    key={event.id}
                    className="p-4 bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-gray-900 mb-1 truncate">{event.name}</h4>
                        <div className="text-sm text-gray-500 space-y-1">
                          <p>
                            <span className="font-medium">Event ID:</span> {event.gotsport_event_id}
                          </p>
                          {event.total_games !== undefined && (
                            <p>
                              <span className="font-medium">Stats:</span> {event.total_divisions || 0} divisions, {event.total_games} games
                            </p>
                          )}
                          {event.last_scraped_at && (
                            <p>
                              <span className="font-medium">Last scraped:</span>{' '}
                              {format(new Date(event.last_scraped_at), 'MMM d, yyyy h:mm a')}
                            </p>
                          )}
                          {event.next_scrape_in_hours !== undefined && event.next_scrape_in_hours > 0 && (
                            <p>
                              <span className="font-medium">Next scrape:</span> in {event.next_scrape_in_hours.toFixed(1)} hours
                            </p>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteEvent(event)}
                        disabled={deleteEventMutation.isPending}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium disabled:bg-gray-400 disabled:cursor-not-allowed whitespace-nowrap"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="w-full sm:w-auto px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
