import React, {useState, useEffect} from 'react'
import api from '../api'

export default function RulesEditor({rules, onSave}){
  const [local, setLocal] = useState(rules)
  useEffect(()=> setLocal(rules), [rules])
  const save = ()=>{
    onSave(local)
  }
  return (
    <div className="rules">
      <h3>Rules</h3>
      <div>
        <label>Score threshold: {local?.score_threshold}</label>
        <input type="range" min="0" max="1" step="0.01" value={local?.score_threshold||0.8}
          onChange={e=> setLocal({...local, score_threshold: parseFloat(e.target.value)})} />
        <button onClick={save}>Save Rules</button>
      </div>
      <pre>{JSON.stringify(local, null, 2)}</pre>
    </div>
  )
}
