"""
AEGIS — Tavily Search Tool
Uses Tavily API for real-time web search in General Mode.
"""

import os

# Tavily is optional — if no API key is set, tool gracefully degrades
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "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")


def search_tavily(query: str, max_results: int = 3) -> str:
    """Run a web search via Tavily and return formatted results."""
    if not TAVILY_API_KEY:
        return (
            "⚠️ Tavily API key not configured.\n"
            "Set the `TAVILY_API_KEY` environment variable to enable web search."
        )

    try:
        from tavily import TavilyClient  # lazy import

        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.search(query=query, max_results=max_results)

        results = response.get("results", [])
        if not results:
            return f"⚠️ No web results found for **{query}**."

        parts = ["🌐 **Web Search Results:**\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("url", "")
            snippet = r.get("content", "")[:300]
            parts.append(f"**{i}. {title}**\n{snippet}\n🔗 {url}\n")

        return "\n".join(parts)

    except ImportError:
        return "❌ `tavily-python` package not installed."
    except Exception as e:
        return f"❌ Tavily error: {e}"
