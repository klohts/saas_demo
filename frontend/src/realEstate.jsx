import React, { useEffect, useState } from 'react';
import { fetchRESummary, postREEvent } from './api';

export default function RealEstatePanel(){
  const [summary, setSummary] = useState({ top_listings: {}, leads_by_agent: {}, weekly_leads: {}, raw_count: 0 });

  useEffect(()=>{
    load();
    const id = setInterval(load, 15000); // refresh every 15s
    return ()=> clearInterval(id);
  }, []);

  async function load(){
    const s = await fetchRESummary();
    if (s) setSummary(s);
  }

  async function sendTest(){
    const r = await postREEvent({ user: 'demo_agent', action: 'property_viewed', property_id: 'listing_123' });
    console.log('posted', r);
    load();
  }

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-semibold text-primary">Real Estate Summary</h3>
          <p className="text-sm text-dark/70">Top listings / leads</p>
        </div>
        <button onClick={sendTest} className="btn">Post demo view</button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="font-medium text-primary mb-2">Top Listings</h4>
          <pre className="bg-dark text-light rounded-lg p-3 text-sm overflow-auto">
            {JSON.stringify(summary.top_listings, null, 2)}
          </pre>
        </div>
        <div>
          <h4 className="font-medium text-primary mb-2">Leads by Agent</h4>
          <pre className="bg-dark text-light rounded-lg p-3 text-sm overflow-auto">
            {JSON.stringify(summary.leads_by_agent, null, 2)}
          </pre>
        </div>

        <div>
          <h4 className="font-medium text-primary mb-2">Weekly Leads</h4>
          <pre className="bg-dark text-light rounded-lg p-3 text-sm overflow-auto">
            {JSON.stringify(summary.weekly_leads, null, 2)}
          </pre>
        </div>

        <div>
          <h4 className="font-medium text-primary mb-2">Raw Events</h4>
          <pre className="bg-dark text-light rounded-lg p-3 text-sm overflow-auto">
            {summary.raw_count}
          </pre>
        </div>
      </div>
    </div>
  );
}
