import React from 'react'

export default function PricingCard({tier}){
  return (
    <div className="card pricing-card">
      <h3 className="header">{tier.name}</h3>
      <p className="muted">{tier.description}</p>
      <div className="price">${tier.price_monthly}/mo</div>
      <ul>
        {Object.entries(tier.limits || {}).map(([k,v])=>(<li key={k}>{k}: {v}</li>))}
      </ul>
      <button className="btn">Select</button>
    </div>
  )
}
