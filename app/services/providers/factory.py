"""
Factory for creating data providers based on tournament configuration.
"""

from typing import Dict, Type, Any
from .base import DataProvider
from .openligadb import OpenLigaDBProvider
from .manual import ManualProvider


class ProviderFactory:
    """Factory for creating data provider instances."""
    
    _providers: Dict[str, Type[DataProvider]] = {
        'openligadb': OpenLigaDBProvider,
        'manual': ManualProvider,
        # Future providers can be added here:
        # 'api-football': ApiFootballProvider,
        # 'csv': CsvProvider,
    }
    
    @classmethod
    def get(cls, provider_type: str, config: Dict[str, Any] = None) -> DataProvider:
        """
        Get a data provider instance.
        
        Args:
            provider_type: Type of provider ('openligadb', 'manual', etc.)
            config: Provider configuration dict
            
        Returns:
            DataProvider instance
            
        Raises:
            ValueError: If provider type is unknown
        """
        if config is None:
            config = {}
        
        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            available = ', '.join(cls._providers.keys())
            raise ValueError(f"Unknown provider type: '{provider_type}'. Available: {available}")
        
        return provider_class(config)
    
    @classmethod
    def register(cls, name: str, provider_class: Type[DataProvider]) -> None:
        """
        Register a new provider type.
        
        Args:
            name: Provider type name
            provider_class: Provider class (must inherit from DataProvider)
        """
        if not issubclass(provider_class, DataProvider):
            raise ValueError("Provider class must inherit from DataProvider")
        cls._providers[name] = provider_class
    
    @classmethod
    def available_providers(cls) -> Dict[str, str]:
        """
        Get list of available provider types with their names.
        
        Returns:
            Dict mapping provider type to human-readable name
        """
        return {
            key: cls._providers[key]({}).provider_name
            for key in cls._providers.keys()
        }
    
    @classmethod
    def is_valid_provider(cls, provider_type: str) -> bool:
        """Check if a provider type is valid."""
        return provider_type in cls._providers
