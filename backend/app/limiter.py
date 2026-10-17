"""Shared rate limiter (slowapi) — abuse / brute-force protection.

Kahan lagta hai:
  - auth (register/login): per-IP brute-force / spam rokne ke liye
  - chat message: LLM cost abuse rokne ke liye

Endpoint pe use:  @limiter.limit("10/minute")  + function signature mein `request: Request`.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# headers_enabled: X-RateLimit-* headers response mein bhejta hai (clients ko pata chale).
limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
