import React from 'react'

export default function TenantHeader({tenant, onToggleDemo}){
  return (
    <div className="row" style={{justifyContent:"space-between"}}>
      <div>
        <h2 style={{margin:0}}>{tenant?.name || "Tenant"}</h2>
        <small>Plan: {tenant?.plan || "Starter"}</small>
      </div>
      <div>
        <button onClick={onToggleDemo}>Toggle Demo</button>
      </div>
    </div>
  )
}
