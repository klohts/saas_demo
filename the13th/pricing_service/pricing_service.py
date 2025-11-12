#!/usr/bin/env python3
from __future__ import annotations
import os
import json
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pricing_service")

PRICING_CONFIG = Path(os.getenv('PRICING_CONFIG', '/home/hp/AIAutomationProjects/saas_demo/the13th/config/pricing.json'))
API_KEY = os.getenv('PRICING_API_KEY', '')
PORT = int(os.getenv('PORT', '8003'))

app = FastAPI(title="THE13TH — Pricing Service", version="1.0.0")

class Tier(BaseModel):
    id: str
    name: str
    price_monthly: float
    limits: dict
    description: Optional[str]

class PricingResponse(BaseModel):
    version: str
    currency: str
    tiers: list[Tier]


def load_pricing() -> dict:
    if not PRICING_CONFIG.exists():
        log.error('Pricing config not found at %s', PRICING_CONFIG)
        raise FileNotFoundError('pricing config not found')
    with PRICING_CONFIG.open() as f:
        return json.load(f)


@app.get('/api/pricing', response_model=PricingResponse)
def get_pricing(x_api_key: Optional[str] = Header(None)):
    """
    Return pricing config. If PRICING_API_KEY is set, require it in X-API-KEY header.
    """
    if API_KEY:
        if not x_api_key or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail='Invalid API Key')
    try:
        data = load_pricing()
        return JSONResponse(content=data)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail='Pricing config missing')


if __name__ == '__main__':
    import uvicorn
    log.info('Starting Pricing Service on port %s — serving %s', PORT, PRICING_CONFIG)
    uvicorn.run('pricing_service:app', host='0.0.0.0', port=PORT, reload=False)
