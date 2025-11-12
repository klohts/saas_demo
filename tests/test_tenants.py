from backend.core.tenants import get_tenant_manager
def test_list(): tm=get_tenant_manager(); assert 'default' in tm.list_tenants()
