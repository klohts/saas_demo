import React, {useEffect, useState, useRef} from 'react'

export default function EventFeed({wsUrl}){
  const [events, setEvents] = useState([]);
  const wsRef = useRef(null);

  useEffect(()=>{
    let mounted=true;
    const connect = ()=> {
      try{
        const proto = location.protocol === "https:" ? "wss" : "ws";
        const url = wsUrl || `${proto}://${location.hostname}:8000/analytics/ws`;
        const ws = new WebSocket(url);
        ws.onmessage = (ev)=>{
          try{
            const msg = JSON.parse(ev.data);
            if(msg?.type === "event"){
              setEvents(prev => [msg.data, ...prev].slice(0,50));
            }
          }catch(e){}
        }
        ws.onopen = ()=> console.log("ws open", url);
        ws.onclose = ()=> setTimeout(connect, 2000);
        wsRef.current = ws;
      }catch(e){
        console.warn("ws err", e);
        setTimeout(connect, 2000);
      }
    }
    connect();
    return ()=> { mounted=false; if(wsRef.current) wsRef.current.close(); }
  }, [wsUrl]);

  return (
    <div>
      <h3>Live Events</h3>
      <ul>
        {events.map((e, i)=> <li key={i}><strong>{e.user}</strong> — {e.action} <small>({e.ts})</small></li>)}
      </ul>
    </div>
  )
}
