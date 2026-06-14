"""
AEGIS — Wikipedia Tool
Fetches summaries from Wikipedia for general-knowledge queries.
"""

import wikipedia


def search_wikipedia(query: str, sentences: int = 4) -> str:
    """Return a Wikipedia summary for the given query."""
    try:
        summary = wikipedia.summary(query, sentences=sentences, auto_suggest=True)
        return f"📖 **Wikipedia:**\n\n{summary}"
    except wikipedia.DisambiguationError as e:
        # Multiple matches — pick the first option
        try:
            first = e.options[0]
            summary = wikipedia.summary(first, sentences=sentences)
            return f"📖 **Wikipedia** (showing result for *{first}*):\n\n{summary}"
        except Exception:
            options = ", ".join(e.options[:5])
            return f"⚠️ Multiple matches found: {options}. Please be more specific."
    except wikipedia.PageError:
        return f"⚠️ No Wikipedia article found for **{query}**."
    except Exception as e:
        return f"❌ Wikipedia error: {e}"
