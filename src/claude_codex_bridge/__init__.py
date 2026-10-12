"""Local discovery and explicit messaging between existing agent sessions."""

from .bridge import Bridge
from .models import Address, DeliveryError, Discovery, Peer, ProviderError, Receipt

__all__ = ["Address", "Bridge", "DeliveryError", "Discovery", "Peer", "ProviderError", "Receipt"]
__version__ = "0.1.0a1"
