"""Shipping carrier factory."""

from app.services.shipping.base import ShippingCarrier
from app.services.shipping.aramex import AramexCarrier


def get_carrier(carrier: str, **kwargs) -> ShippingCarrier:
    """Factory to get a carrier implementation."""
    carriers = {
        "aramex": AramexCarrier,
        "dhl": AramexCarrier,
        "fetchr": AramexCarrier,
        "shipa": AramexCarrier,
    }
    cls = carriers.get(carrier, AramexCarrier)
    return cls(**kwargs)
