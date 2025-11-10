/* api.js — small helper for backend calls and websocket */
export async function fetchIntel(){
  const r = await fetch('/admin/intel')
  return r.json()
}

export function connectWS(onMessage){
  try{
    const wsProto = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${wsProto}://${location.host}/intel/stream`)
    ws.onmessage = (ev)=>{
      try{ onMessage(JSON.parse(ev.data)) }catch(e){/* ignore */}
    }
    return ws
  }catch(e){
    return null
  }
}
