"""
Data Providers for importing match data from various sources.
"""

from .base import DataProvider
from .factory import ProviderFactory
from .openligadb import OpenLigaDBProvider
from .manual import ManualProvider

__all__ = ['DataProvider', 'ProviderFactory', 'OpenLigaDBProvider', 'ManualProvider']
