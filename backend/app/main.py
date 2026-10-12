from contextlib import asynccontextmanager
from datetime import timedelta
import json
from uuid import uuid4
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from . import database as db
from .agent import graph
from .config import settings
from .llm import AIError
from .models import Search, Offer, Quote, ChatRequest, QuoteRequest, BookingRequest
from .providers import search, refresh, now


@asynccontextmanager
async def lifespan(app):
    db.initialize()
    yield


app = FastAPI(title='Flight Agent — Demo & Sandbox', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.cors_origin], allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])


def remember(offers):
    for offer in offers:
        data = offer if isinstance(offer, dict) else offer.model_dump(mode='json')
        db.save('offers', data['id'], data)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'provider': settings.flight_provider, 'ai': 'groq' if settings.groq_api_key.get_secret_value() else 'demo', 'ai_model': settings.groq_model if settings.groq_api_key.get_secret_value() else None, 'real_booking_enabled': False}


@app.post('/api/search')
async def flight_search(trip: Search):
    try:
        offers = await search(trip)
        remember(offers)
        return {'offers': offers}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, 'Flight provider unavailable. Try again later.') from exc


@app.post('/api/chat')
async def chat(request: ChatRequest):
    try:
        result = await graph.ainvoke({'message': request.message, 'offers': []})
        remember(result.get('offers', []))
        return result
    except AIError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, 'The agent or provider is unavailable. Try the search form or try again later.') from exc


@app.post('/api/quotes', response_model=Quote)
async def create_quote(request: QuoteRequest):
    data = db.get('offers', request.offer_id)
    if not data:
        raise HTTPException(404, 'Offer not found. Search again.')
    offer = Offer.model_validate(data)
    if offer.expires_at <= now():
        raise HTTPException(409, 'Offer expired. Search again.')
    try:
        offer = await refresh(offer)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, 'Flight provider unavailable. Try again later.') from exc
    quote = Quote(id=uuid4().hex, offer=offer, expires_at=min(offer.expires_at, now() + timedelta(minutes=5)))
    db.save('quotes', quote.id, quote.model_dump(mode='json'))
    return quote


@app.post('/api/bookings')
def simulate_booking(request: BookingRequest):
    if not request.confirmed:
        raise HTTPException(400, 'Confirm the itinerary and amount first.')
    data = db.get('quotes', request.quote_id)
    if not data:
        raise HTTPException(404, 'Quote not found.')
    quote = Quote.model_validate(data)
    # Database uniqueness protects duplicate clicks and simultaneous requests.
    with db.engine.begin() as connection:
        row = connection.execute(text('SELECT quote_id, booking_id FROM booking_keys WHERE id=:key'), {'key': request.idempotency_key}).first()
        if row:
            if row[0] != quote.id:
                raise HTTPException(409, 'This request key belongs to a different quote.')
            return db.get('bookings', row[1])
    if quote.expires_at <= now():
        raise HTTPException(409, 'Quote expired. Review the flight again.')
    booking = {'id': 'SIM-' + uuid4().hex[:10].upper(), 'status': 'simulated', 'message': 'Simulation complete. No payment taken and no airline ticket issued.', 'offer': quote.offer.model_dump(mode='json'), 'created_at': now().isoformat()}
    try:
        with db.engine.begin() as connection:
            connection.execute(text('INSERT INTO bookings (id,payload) VALUES (:id,:payload)'), {'id': booking['id'], 'payload': json.dumps(booking)})
            connection.execute(text('INSERT INTO booking_keys (id,quote_id,booking_id) VALUES (:key,:quote,:booking)'), {'key': request.idempotency_key, 'quote': quote.id, 'booking': booking['id']})
    except IntegrityError:
        with db.engine.connect() as connection:
            row = connection.execute(text('SELECT id, quote_id, booking_id FROM booking_keys WHERE id=:key OR quote_id=:quote'), {'key': request.idempotency_key, 'quote': quote.id}).first()
        if row and row[1] == quote.id:
            return db.get('bookings', row[2])
        raise HTTPException(409, 'Booking request conflict. Review the quote again.')
    return booking
