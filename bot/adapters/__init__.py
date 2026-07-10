from . import arxiv, github, instagram, web, youtube

# source type → fetch(url) -> (title, content)
FETCHERS = {
    "github": github.fetch,
    "arxiv": arxiv.fetch,
    "instagram": instagram.fetch,
    "youtube": youtube.fetch,
    "web": web.fetch,
}
