import React from 'react';
export default function Events({events}){
  return (<div><h2 className='text-xl mb-2 header'>Recent Events</h2><table className='table'><thead><tr><th>Time</th><th>Client</th><th>Action</th><th>User</th></tr></thead><tbody>{events.map(e=>(<tr key={e.id}><td>{new Date(e.created_at).toLocaleString()}</td><td>{e.client_id}</td><td>{e.action}</td><td>{e.user}</td></tr>))}</tbody></table></div>);
}
