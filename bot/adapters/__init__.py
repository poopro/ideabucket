from . import arxiv, github, instagram, web

# source type → fetch(url) -> (title, content)
FETCHERS = {
    "github": github.fetch,
    "arxiv": arxiv.fetch,
    "instagram": instagram.fetch,
    "web": web.fetch,
}
