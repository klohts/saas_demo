import React from 'react';
export default function Stats({data}){
  if(!data) return <div className='card'>Loading summary...</div>;
  return (<div className='grid grid-cols-3 gap-4'>
    <div className='card'><div className='text-sm'>Total Events</div><div className='text-2xl header'>{data.total_events}</div></div>
    <div className='card'><div className='text-sm'>Unique Clients</div><div className='text-2xl header'>{data.unique_clients}</div></div>
    <div className='card'><div className='text-sm'>Top Action</div><div className='text-2xl header'>{data.top_actions?.[0]?.action || '-'}</div></div>
  </div>);
}
