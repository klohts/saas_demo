/* RulesEditor.jsx — simple rules textarea */
import React, {useState} from 'react'

export default function RulesEditor({initial=''}){
  const [val, setVal] = useState(initial)
  return (
    <div className="bg-gray-900 border border-gray-800 p-4 rounded-md">
      <label className="text-sm text-gray-400">Rule Engine</label>
      <textarea value={val} onChange={(e)=>setVal(e.target.value)} className="w-full mt-2 p-2 rounded bg-[#080808] border border-gray-700 text-gray-200 min-h-[120px]" />
      <div className="mt-3 flex gap-2">
        <button className="px-3 py-1 rounded border border-purple-600 text-purple-300 hover:bg-purple-700/10">Save Rules</button>
        <button className="px-3 py-1 rounded border border-gray-700 text-gray-300">Reset</button>
      </div>
    </div>
  )
}
