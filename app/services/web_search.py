from langchain_tavily import TavilySearch
from app.core.config import TAVILY_API_KEY

web_search = TavilySearch(
    tavily_api_key=TAVILY_API_KEY,
    max_results=5,
    topic="general",
    include_answer=True,
    include_raw_content=False
)

def search_web(query):
    result = web_search.invoke({"query": query})
    return result