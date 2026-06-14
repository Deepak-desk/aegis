"""
AEGIS — Arxiv Tool
Searches academic papers on arXiv for research-related queries.
"""

import arxiv


def search_arxiv(query: str, max_results: int = 3) -> str:
    """Search arXiv for papers matching the query."""
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        results = list(client.results(search))

        if not results:
            return f"⚠️ No arXiv papers found for **{query}**."

        parts = ["📑 **arXiv Papers:**\n"]
        for i, paper in enumerate(results, 1):
            title = paper.title
            authors = ", ".join(a.name for a in paper.authors[:3])
            if len(paper.authors) > 3:
                authors += " et al."
            summary = paper.summary[:250].replace("\n", " ") + "..."
            url = paper.entry_id
            published = paper.published.strftime("%Y-%m-%d")

            parts.append(
                f"**{i}. {title}**\n"
                f"   Authors: {authors}\n"
                f"   Published: {published}\n"
                f"   {summary}\n"
                f"   🔗 {url}\n"
            )

        return "\n".join(parts)

    except Exception as e:
        return f"❌ arXiv error: {e}"
