"""Optional third-party dependencies.

Keeping imports here makes both desktop and future API usage easier:
- the desktop UI can fail gracefully with friendly messages
- a future API can validate availability at startup
"""

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from newspaper import Article
except ImportError:
    Article = None

__all__ = ["anthropic", "Article"]
