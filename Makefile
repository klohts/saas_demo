.PHONY: run admin

run: ## Run API locally
	uvicorn app.main:app --reload

admin: ## Run Streamlit dashboard
	streamlit run admin_dashboard/streamlit_app.py
