import re
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from .config import settings
from .models import Search
from .llm import extract_trip
from .providers import search

AIRPORTS = {'colombo': 'CMB', 'singapore': 'SIN', 'dubai': 'DXB', 'london': 'LHR', 'paris': 'CDG', 'bangkok': 'BKK', 'tokyo': 'HND', 'sydney': 'SYD', 'amsterdam': 'AMS', 'frankfurt': 'FRA'}


class State(TypedDict, total=False):
    message: str
    trip: dict | None
    reply: str
    offers: list
    agent_mode: str


def offline_parse(message):
    pattern = r'\bfrom\s+([a-z]{3}|colombo|singapore|dubai|london|paris|bangkok|tokyo|sydney|amsterdam|frankfurt)\s+to\s+([a-z]{3}|colombo|singapore|dubai|london|paris|bangkok|tokyo|sydney|amsterdam|frankfurt)\b'
    route = re.search(pattern, message.lower())
    day = re.search(r'\b\d{4}-\d{2}-\d{2}\b', message)
    budget = re.search(r'(?:under|below|budget(?: of)?)\s*(?:USD\s*|\$)?(\d+(?:\.\d{1,2})?)', message, re.I)
    if not route or not day:
        return None
    return {'origin': AIRPORTS.get(route[1], route[1].upper()), 'destination': AIRPORTS.get(route[2], route[2].upper()), 'departure_date': day[0], 'budget_usd': budget[1] if budget else None, 'cabin': 'business' if 'business' in message.lower() else 'economy'}


async def parse_node(state):
    message = state['message']
    if settings.groq_api_key.get_secret_value():
        trip = await extract_trip(message)
        mode = f'Groq {settings.groq_model} + LangGraph'
    else:
        data = offline_parse(message)
        unsupported = re.search(r'\b(return|round.?trip|[2-9]\s+(?:adults|passengers)|children|child|infant)\b', message, re.I)
        trip = Search.model_validate(data).model_dump(mode='json') if data and not unsupported else None
        mode = 'Demo parser + LangGraph'
    return {'trip': trip, 'agent_mode': mode, 'reply': 'Please include the origin, destination, and YYYY-MM-DD date. This starter supports one adult and one-way trips. Example: From Colombo to Singapore on 2026-12-10 under $400.' if trip is None else ''}


async def search_node(state):
    offers = await search(Search.model_validate(state['trip']))
    suffix = ' Non-USD offers are not filtered by your USD budget.' if any(o.currency != 'USD' for o in offers) and state['trip'].get('budget_usd') else ''
    return {'offers': [o.model_dump(mode='json') for o in offers], 'reply': f'Found {len(offers)} options. Select one to review its current price. These are demo or sandbox results; no real ticket will be issued.' + suffix}


builder = StateGraph(State)
builder.add_node('extract_trip', parse_node)
builder.add_node('search_flights', search_node)
builder.add_edge(START, 'extract_trip')
builder.add_conditional_edges('extract_trip', lambda s: 'search_flights' if s.get('trip') else END)
builder.add_edge('search_flights', END)
graph = builder.compile()
