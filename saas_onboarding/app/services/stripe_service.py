import logging
import stripe
from fastapi import HTTPException
from typing import Dict
from ..config import settings
from ..services.event_hooks import post_event
import asyncio

logger = logging.getLogger("stripe_service")

stripe.api_key = settings.STRIPE_API_KEY


async def create_checkout_session(
    customer_email: str,
    plan: str,
    success_url: str,
    cancel_url: str
) -> Dict:
    """
    Create a Stripe Checkout Session for a given plan.
    Falls back gracefully in dev/test mode when price IDs are dummy or missing.
    """

    # Determine price ID from plan
    price_id = getattr(settings, f"PRICE_{plan.upper()}_ID", None)

    # Detect missing or dummy price IDs
    if not price_id or "dummy" in price_id or "test" in price_id:
        logger.warning(f"Stripe price id missing or dummy for plan={plan}, bypassing live session.")
        asyncio.create_task(post_event("stripe_bypass", user=customer_email, plan=plan))
        # Return a pseudo-session for local/test mode
        return {
            "id": f"test_session_{plan}",
            "url": f"{success_url}?session_id=test_{plan}",
            "mode": "test",
            "status": "bypassed",
        }

    try:
        # Create real Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            customer_email=customer_email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=cancel_url,
        )

        logger.info(f"Created Stripe checkout session for {customer_email} plan={plan}")
        return session

    except stripe.error.StripeError as e:
        logger.error(f"Stripe API error for plan={plan}: {e}")
        asyncio.create_task(post_event("stripe_error", user=customer_email, plan=plan))
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    except Exception as e:
        logger.exception(f"Unexpected error during Stripe session creation for plan={plan}")
        asyncio.create_task(post_event("stripe_exception", user=customer_email, plan=plan))
        raise HTTPException(status_code=500, detail="Payment service unavailable.")


def construct_event(payload: bytes, sig_header: str):
    """
    Validate and construct a Stripe webhook event.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("Stripe webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        return event
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
