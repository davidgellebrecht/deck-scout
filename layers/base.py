#!/usr/bin/env python3
"""
layers/base.py — BaseLayer

Every signal layer inherits from this class and must implement `run()`.

Result structure every layer must return:
    {
        "layer":   str,          # machine-readable layer name, e.g. "new_owner"
        "label":   str,          # human-readable label shown in the UI
        "signal":  bool,         # True = the layer fired (opportunity detected)
        "score":   float | None, # 0.0 – 1.0 confidence / strength (None if N/A)
        "detail":  str,          # one-line human-readable explanation
        "data":    dict,         # layer-specific raw values for CSV / JSON
        "paid":    bool,         # True = layer requires a paid API subscription
    }
"""

from abc import ABC, abstractmethod


class BaseLayer(ABC):
    """Abstract base class for all Deck Scout signal layers."""

    name: str  = "base"
    label: str = "Base Layer"
    paid: bool = False

    @abstractmethod
    def run(self, prop: dict) -> dict:
        """
        Analyse a property dict and return a standardised result dict.

        Parameters
        ----------
        prop : dict
            A property dict as produced by scout.py.
            Expected keys: lat, lon, address, year_built, lot_sqft,
            assessed_value, sale_date, property_type.

        Returns
        -------
        dict — see module docstring for the required schema.
        """

    def _empty_result(self, detail: str = "", signal: bool = False) -> dict:
        """Return a valid empty result."""
        return {
            "layer":  self.name,
            "label":  self.label,
            "signal": signal,
            "score":  None,
            "detail": detail,
            "data":   {},
            "paid":   self.paid,
        }

    def _paid_stub(self) -> dict:
        """Return a stub when the paid API key is missing."""
        return self._empty_result(
            detail="PAID FEATURE — configure credentials in config.py to activate"
        )

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        """Clamp a float to [lo, hi]."""
        return max(lo, min(hi, value))
