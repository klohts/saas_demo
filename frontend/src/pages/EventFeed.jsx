/* pages/EventFeed.jsx */
import React from 'react'
import EventFeed from '../components/EventFeed'
export default function EventFeedPage(){
  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Event Feed</h2>
      <EventFeed events={[]} />
    </div>
  )
}
