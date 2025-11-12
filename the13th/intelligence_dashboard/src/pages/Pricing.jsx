import React, {useEffect, useState} from 'react'
import PricingCard from '../components/PricingCard'

export default function Pricing(){
  const [pricing, setPricing] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(()=>{
    fetch('/api/pricing')
      .then(r=>{ if(!r.ok) throw new Error('Pricing fetch failed'); return r.json() })
      .then(setPricing)
      .catch(e=>setErr(e.message))
  },[])

  if(err) return <div className="card"><h3>Error</h3><p>{err}</p></div>
  if(!pricing) return <div className="card">Loading...</div>

  return (
    <div className="page container">
      <h1 className="header">Pricing</h1>
      <div className="pricing-grid">
        {pricing.tiers.map(t => <PricingCard key={t.id} tier={t} />)}
      </div>
    </div>
  )
}
