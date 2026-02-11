import logging
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import docling
from docling.document_converter import DocumentConverter
import gc

class Worker(ABC):
    """
    Abstract Base Worker Class.
    Workers execute specific tasks like parsing documents, searching, code execution.
    """
    @abstractmethod
    def execute(self, task: Dict[str, Any]) -> str:
        """Executes the given task and returns a formatted result."""
        pass

    def cleanup(self):
        """Optional cleanup logic for workers."""
        pass

class DoclingWorker(Worker):
    """
    Worker specialized in parsing documents into structured Markdown using Docling.
    Native Intel: No raw text, only structural Markdown.
    """
    def __init__(self):
        self.converter = DocumentConverter()

    def cleanup(self):
        """Release docling resources."""
        if hasattr(self, 'converter'):
            del self.converter
            import gc
            gc.collect()

    def execute(self, task: Dict[str, Any]) -> str:
        """
        Expects task = {"type": "parse_document", "source": "path/to/file_or_url"}
        Returns structured Markdown.
        """
        source = task.get("source")
        if not source:
            return "Error: No source provided for document parsing."

        logging.info(f"DoclingWorker: Parsing {source}...")
        try:
            result = self.converter.convert(source)
            markdown_content = result.document.export_to_markdown()
            # Explicitly clear internal buffers if possible
            return markdown_content
        except Exception as e:
            logging.error(f"DoclingWorker Error: {e}")
            return f"Error parsing document: {e}"
        finally:
            gc.collect()

    def parse_url(self, url: str) -> str:
        """Dedicated method for URL parsing."""
        return self.execute({"source": url})

    def parse_file(self, file_path: str) -> str:
        """Dedicated method for File parsing."""
        return self.execute({"source": file_path})

class DuckDuckGoWorker(Worker):
    """
    Worker specialized in DuckDuckGo Search.
    No API Key required. Privacy focused.
    """
    def __init__(self):
        # We'll initialize DDGS on each execute call for fresh session
        pass

    def execute(self, task: Dict[str, Any]) -> str:
        query = task.get("query")
        num = task.get("num", 5)
        search_type = task.get("search_type", "web")

        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        logging.info(f"DuckDuckGoWorker: Searching {search_type} for '{query}'...")
        
        try:
            results = []
            with DDGS() as ddgs:
                if search_type == "news":
                    res_gen = ddgs.news(query, region="wt-wt", max_results=num)
                else:
                    res_gen = ddgs.text(query, region="wt-wt", max_results=num)

                res_list = list(res_gen)
                for item in res_list:
                    # Robust key mapping
                    title = item.get("title") or item.get("header") or item.get("body", "No Title")[:50]
                    link = item.get("href") or item.get("link") or item.get("url")
                    
                    if link:
                        results.append({"title": title, "link": link})
            
            import json
            if not results:
                logging.warning(f"DuckDuckGoWorker: 0 results for '{query}'")
            return json.dumps(results, indent=2)
        except Exception as e:
            logging.error(f"DuckDuckGoWorker Error: {e}")
            return f"Error performing search: {e}"

    def search(self, query: str, num: int = 5) -> List[Dict[str, str]]:
        """Direct method for web searching."""
        import json
        res = self.execute({"query": query, "num": num, "search_type": "web"})
        try:
            return json.loads(res)
        except:
            return []

    def news(self, query: str, num: int = 5) -> List[Dict[str, str]]:
        """Direct method for news searching."""
        import json
        res = self.execute({"query": query, "num": num, "search_type": "news"})
        try:
            return json.loads(res)
        except:
            return []
