import hashlib
from typing import Dict, Any
from ..llmfactory import LLMFactory


class LLMCache:
    """
    High-performance memory-only LLM client cache for fast access within the same session.
    On process restart, clients are re-instantiated via LLMFactory for security and stability.
    """
    
    _memory_cache: Dict[str, Any] = {}
    
    def __init__(self):
        """Initialize the memory-only LLM cache."""
        self.factory = None  # Lazy initialize
    
    def _get_cache_key(self, provider: str, model: str) -> str:
        """Generate a cache key for the provider/model combination."""
        key_string = f"{provider}:{model}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get_llm(self, provider: str, model: str, api_key: str) -> Any:
        """
        Get an LLM client, using memory cache when possible.
        
        Args:
            provider: LLM provider name
            model: Model name  
            api_key: API key
            
        Returns:
            LLM client instance
        """
        cache_key = self._get_cache_key(provider, model)
        
        # Check memory cache first (fastest)
        if cache_key in self._memory_cache:
            llm = self._memory_cache[cache_key]
            # Update API key in case it changed
            self._update_api_key(llm, provider, api_key)
            return llm
        
        # Create new client (only happens first time per session)
        if self.factory is None:
            self.factory = LLMFactory()
            
        llm = self.factory.create_llm(provider, model, api_key)
        
        # Cache in memory only
        self._memory_cache[cache_key] = llm
            
        return llm
    
    def _update_api_key(self, llm_instance: Any, provider: str, api_key: str) -> None:
        """Update the API key in an existing LLM instance."""
        provider = provider.lower()
        
        try:
            if provider == "deepinfra":
                llm_instance.deepinfra_api_token = api_key
            elif provider == "mistralai":
                llm_instance.mistral_api_key = api_key  
            elif provider == "gemini":
                llm_instance.google_api_key = api_key
        except AttributeError:
            # If API key update fails, the cached client will still work
            # assuming the API key hasn't changed
            pass
    
    def clear_cache(self) -> None:
        """Clear the memory cache."""
        self._memory_cache.clear()
    
    @classmethod
    def get_memory_cache_size(cls) -> int:
        """Get the number of cached clients in memory."""
        return len(cls._memory_cache)


# Global cache instance
_llm_cache = LLMCache()


def get_cached_llm(provider: str, model: str, api_key: str) -> Any:
    """
    Global function to get a cached LLM client.
    
    Args:
        provider: LLM provider name
        model: Model name
        api_key: API key
        
    Returns:
        LLM client instance
    """
    return _llm_cache.get_llm(provider, model, api_key)


def clear_llm_cache() -> None:
    """Clear the global LLM cache."""
    _llm_cache.clear_cache()