import pickle
import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Optional
from ..llmfactory import LLMFactory


class LLMCache:
    """
    High-performance LLM client cache that persists clients to disk
    and maintains in-memory cache for near-zero startup time.
    """
    
    _memory_cache: Dict[str, Any] = {}
    
    def __init__(self):
        """Initialize the LLM cache with disk storage."""
        self.cache_dir = Path.home() / ".cache" / "codedjinn" / "llm_clients"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.factory = None  # Lazy initialize
    
    def _get_cache_key(self, provider: str, model: str) -> str:
        """Generate a cache key for the provider/model combination."""
        key_string = f"{provider}:{model}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cached client."""
        return self.cache_dir / f"{cache_key}.pkl"
    
    def get_llm(self, provider: str, model: str, api_key: str) -> Any:
        """
        Get an LLM client, using cache when possible.
        
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
        
        # Check disk cache (fast)
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    llm = pickle.load(f)
                    # Update API key and store in memory cache
                    self._update_api_key(llm, provider, api_key)
                    self._memory_cache[cache_key] = llm
                    return llm
            except Exception:
                # Cache file corrupted, remove it
                cache_path.unlink(missing_ok=True)
        
        # Create new client (slow - only happens first time)
        if self.factory is None:
            self.factory = LLMFactory()
            
        llm = self.factory.create_llm(provider, model, api_key)
        
        # Cache both in memory and disk
        self._memory_cache[cache_key] = llm
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(llm, f)
        except Exception:
            # Disk caching failed, but memory cache still works
            pass
            
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
        """Clear both memory and disk caches."""
        self._memory_cache.clear()
        
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink(missing_ok=True)
    
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