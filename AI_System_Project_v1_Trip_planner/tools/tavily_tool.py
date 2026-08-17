from tavily import TavilyClient
import os 
from dotenv import load_dotenv

load_dotenv()

TavailyClient=TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def tavily_search(query):
    """
    Search for flights using the Tavily API.

    Args:
        query (str): The search query.  
        
    Returns:
        dict: The search results from the Tavily API.
        
    """
    response = TavailyClient.search(query=query, max_results=5)
    # Example output of response:
    # {
    #     "results": [
    #         {
    #             "title": "Flight to Paris",
    #             "url": "https://example.com/flight-to-paris",
    #             "content": "Here is some information about flights to Paris..."
    #         }
    #     ]
    # }

    results=[]
    
    for i, r in enumerate(response['results'],1): 
        
        title = r.get('title', '')  
        url = r.get('url', '')
        snippet = r.get('content', '').strip()
        
        # EXAMPLE OUTPUT:
        # 1. Flight to Paris
        # URL: https://example.com/flight-to-paris
        # Snippet: Here is some information about flights to Paris...
        
        # ONly keep the first 300 characters of the snippet
        snippet = snippet[:300] + '...' if len(snippet) > 300 else snippet
        results.append(f"{i}. {title}\nURL: {url}\nSnippet: {snippet}\n")
        
  

    return "\n\n".join(results) # Return the results as a single string with double newlines between each result


    # Example output if there are 4 results:
    # 1. Flight to Paris
    # URL: https://example.com/flight-to-paris
    # Snippet: Here is some information about flights to Paris...
    #
    # 2. Flight to London
    # URL: https://example.com/flight-to-london
    # Snippet: Here is some information about flights to London...
    #
    # 3. Flight to Tokyo
    # URL: https://example.com/flight-to-tokyo
    # Snippet: Here is some information about flights to Tokyo...
    #
    # 4. Flight to New York
    # URL: https://example.com/flight-to-new-york
    # Snippet: Here is some information about flights to New York...
    
    
    


