import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['FLIGHT_PROVIDER'] = 'demo'
os.environ['GROQ_API_KEY'] = ''

from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app import database as db
from app.main import app
from app.providers import duffel
from app.config import settings


@pytest.fixture
def client():
    previous = db.engine
    db.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    with TestClient(app) as client:
        yield client
    db.engine.dispose()
    db.engine = previous


def trip():
    return {'origin': 'CMB', 'destination': 'SIN', 'departure_date': (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(), 'budget_usd': 400}


def test_search_quote_confirmation_and_duplicate_protection(client):
    result = client.post('/api/search', json=trip())
    assert result.status_code == 200
    offers = result.json()['offers']
    assert len(offers) == 2
    assert all(float(o['amount']) <= 400 and o['mode'] == 'demo' for o in offers)
    quote = client.post('/api/quotes', json={'offer_id': offers[0]['id']}).json()
    request = {'quote_id': quote['id'], 'confirmed': False, 'idempotency_key': str(uuid4())}
    original_key = request['idempotency_key']
    assert client.post('/api/bookings', json=request).status_code == 400
    request['confirmed'] = True
    booking = client.post('/api/bookings', json=request)
    assert booking.status_code == 200
    assert booking.json()['status'] == 'simulated'
    assert 'no airline ticket issued' in booking.json()['message']
    assert client.post('/api/bookings', json=request).json()['id'] == booking.json()['id']
    request['idempotency_key'] = str(uuid4())
    assert client.post('/api/bookings', json=request).json()['id'] == booking.json()['id']
    quote2 = client.post('/api/quotes', json={'offer_id': offers[1]['id']}).json()
    request['quote_id'] = quote2['id']
    request['idempotency_key'] = original_key
    assert client.post('/api/bookings', json=request).status_code == 409


def test_expired_quote_cannot_book(client):
    offers = client.post('/api/search', json=trip()).json()['offers']
    quote = client.post('/api/quotes', json={'offer_id': offers[0]['id']}).json()
    quote['expires_at'] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    db.save('quotes', quote['id'], quote)
    response = client.post('/api/bookings', json={'quote_id': quote['id'], 'confirmed': True, 'idempotency_key': str(uuid4())})
    assert response.status_code == 409


def test_agent_search_and_clarification(client):
    day = trip()['departure_date']
    response = client.post('/api/chat', json={'message': f'From Colombo to Singapore on {day} under $400'})
    assert response.status_code == 200
    assert len(response.json()['offers']) == 2
    for message in ['Book a flight', f'From Colombo to Singapore on {day} return', f'From Colombo to Singapore on {day} for 2 adults']:
        response = client.post('/api/chat', json={'message': message})
        assert response.status_code == 200
        assert response.json()['trip'] is None
        assert response.json()['offers'] == []


def test_invalid_trip_rejected(client):
    data = trip()
    data['departure_date'] = '2000-01-01'
    assert client.post('/api/search', json=data).status_code == 422
    data = trip()
    data['destination'] = 'CMB'
    assert client.post('/api/search', json=data).status_code == 422
    assert client.post('/api/quotes', json={'offer_id': 'missing'}).status_code == 404


def test_live_provider_token_rejected_before_network(monkeypatch):
    import asyncio
    monkeypatch.setattr(settings, 'duffel_access_token', 'duffel_live_example')
    with pytest.raises(ValueError, match='Live tokens are disabled'):
        asyncio.run(duffel('POST', '/air/offer_requests'))


@pytest.fixture
def groq_mock(monkeypatch):
    import httpx
    from pydantic import SecretStr
    from app import llm
    monkeypatch.setattr(settings, 'groq_api_key', SecretStr('unit-test-placeholder'))
    original_client = httpx.AsyncClient

    def install(handler):
        monkeypatch.setattr(llm.httpx, 'AsyncClient', lambda **kwargs: original_client(
            transport=httpx.MockTransport(handler), **kwargs))
    return install


def groq_response(**overrides):
    data = {**trip(), 'cabin': 'economy', 'needs_clarification': False}
    data.update(overrides)
    return data


def completion(data):
    import json
    return {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(data)}}]}


def test_groq_extraction_search_and_simulation(client, groq_mock):
    import httpx
    import json

    def handler(request):
        assert str(request.url) == 'https://api.groq.com/openai/v1/chat/completions'
        assert request.headers['Authorization'] == 'Bearer unit-test-placeholder'
        payload = json.loads(request.content)
        assert payload['model'] == 'openai/gpt-oss-120b'
        assert payload['messages'][1]['content'] == 'A flight request'
        schema = payload['response_format']['json_schema']
        assert schema['strict'] is True
        assert schema['schema']['additionalProperties'] is False
        assert set(schema['schema']['required']) == set(schema['schema']['properties'])
        return httpx.Response(200, json=completion(groq_response()))

    groq_mock(handler)
    response = client.post('/api/chat', json={'message': 'A flight request'})
    assert response.status_code == 200
    assert len(response.json()['offers']) == 2
    assert response.json()['agent_mode'] == 'Groq openai/gpt-oss-120b + LangGraph'
    quote = client.post('/api/quotes', json={'offer_id': response.json()['offers'][0]['id']}).json()
    booking = client.post('/api/bookings', json={
        'quote_id': quote['id'], 'confirmed': True, 'idempotency_key': str(uuid4()),
    })
    assert booking.status_code == 200
    assert booking.json()['status'] == 'simulated'
    health = client.get('/api/health').json()
    assert health['ai'] == 'groq'
    assert health['ai_model'] == 'openai/gpt-oss-120b'
    assert 'unit-test-placeholder' not in str(health)
    assert health['real_booking_enabled'] is False


def test_groq_clarification_does_not_search(client, groq_mock, monkeypatch):
    import httpx
    from app import agent

    async def unexpected_search(*args):
        pytest.fail('An incomplete request must not search flights')

    monkeypatch.setattr(agent, 'search', unexpected_search)
    groq_mock(lambda request: httpx.Response(200, json=completion(groq_response(
        origin=None, destination=None, departure_date=None, budget_usd=None,
        needs_clarification=True,
    ))))
    response = client.post('/api/chat', json={'message': 'I want a flight'})
    assert response.status_code == 200
    assert response.json()['trip'] is None
    assert response.json()['offers'] == []


@pytest.mark.parametrize('provider_status,expected_status,text', [
    (401, 502, 'access was rejected'), (403, 502, 'access was rejected'),
    (429, 429, 'rate limit'), (500, 502, 'request failed'),
])
def test_groq_provider_errors_are_sanitized(client, groq_mock, provider_status, expected_status, text):
    import httpx
    groq_mock(lambda request: httpx.Response(provider_status, text='private-provider-debug-content'))
    response = client.post('/api/chat', json={'message': 'A flight request'})
    assert response.status_code == expected_status
    assert text in response.json()['detail']
    assert 'private-provider-debug-content' not in response.text
    assert 'unit-test-placeholder' not in response.text


@pytest.mark.parametrize('body', [
    {}, {'choices': []},
    {'choices': [{'finish_reason': 'stop', 'message': {'content': '{bad-json'}}]},
    {'choices': [{'finish_reason': 'length', 'message': {'content': '{}'}}]},
    {'choices': [{'finish_reason': 'stop', 'message': {'content': None, 'refusal': 'Refused'}}]},
    completion(groq_response(origin='invalid')),
    completion(groq_response(departure_date='2000-01-01')),
    completion(groq_response(budget_usd=-10)),
    completion(groq_response(origin=None)),
    completion(groq_response(needs_clarification='false')),
])
def test_groq_invalid_output_never_becomes_flight_inventory(client, groq_mock, body):
    import httpx
    groq_mock(lambda request: httpx.Response(200, json=body))
    response = client.post('/api/chat', json={'message': 'A flight request'})
    assert response.status_code == 502
    assert 'valid trip' in response.json()['detail']


@pytest.mark.parametrize('failure,expected_status', [('timeout', 504), ('connection', 502)])
def test_groq_network_failures(client, groq_mock, failure, expected_status):
    import httpx

    def handler(request):
        error = httpx.ReadTimeout if failure == 'timeout' else httpx.ConnectError
        raise error('private network detail', request=request)

    groq_mock(handler)
    response = client.post('/api/chat', json={'message': 'A flight request'})
    assert response.status_code == expected_status
    assert 'private network detail' not in response.text


def test_health_offline_mode(client):
    response = client.get('/api/health').json()
    assert response['ai'] == 'demo'
    assert response['ai_model'] is None
