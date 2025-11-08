from utils.admin_audit import record_audit

def patch_operator_audit(app):
    @app.post("/admin/reset-logs")
    async def reset_logs_audited(request):
        record_audit("Reset Logs executed")
        return await app.router.routes_by_name["reset_logs"].endpoint(request)

    @app.post("/admin/filter-emails")
    async def filter_emails_audited(request):
        record_audit("Filter Failed Emails executed")
        return await app.router.routes_by_name["filter_failed_emails"].endpoint(request)

    @app.post("/admin/toggle-demo")
    async def toggle_demo_audited(request):
        record_audit("Toggle Demo Mode executed")
        return await app.router.routes_by_name["toggle_demo"].endpoint(request)
