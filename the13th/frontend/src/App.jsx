import TenantProfile from "./components/TenantProfile";
import AdminTenantPanel from "./components/AdminTenantPanel";

export default function App(){
  const [selectedTenant,setSelectedTenant]=React.useState(null);
  return (<div className='p-8'>
  {!selectedTenant && <AdminTenantPanel onSelect={setSelectedTenant}/>}
  {selectedTenant && <TenantProfile tenantId={selectedTenant.id} onClose={()=>setSelectedTenant(null)}/>}
  </div>);}