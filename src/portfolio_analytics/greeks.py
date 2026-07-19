"""Black-Scholes analytical Greeks without broker or execution dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, pi, sqrt


def _cdf(value: float) -> float:
    return (1.0 + erf(value / sqrt(2.0))) / 2.0


def _pdf(value: float) -> float:
    return exp(-0.5 * value * value) / sqrt(2.0 * pi)


@dataclass(frozen=True)
class Greeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


def calculate_greeks(*, spot: float, strike: float, time_years: float, volatility: float,
                     risk_free_rate: float, option_type: str) -> Greeks:
    """Return annualized Black-Scholes Greeks; theta is per calendar day."""
    if spot <= 0 or strike <= 0 or time_years <= 0 or volatility <= 0:
        raise ValueError("spot, strike, time_years, and volatility must be positive")
    root = sqrt(time_years)
    d1 = (log(spot / strike) + (risk_free_rate + volatility ** 2 / 2) * time_years) / (volatility * root)
    d2 = d1 - volatility * root
    gamma = _pdf(d1) / (spot * volatility * root)
    vega = spot * _pdf(d1) * root / 100.0
    if option_type.upper() == "CALL":
        delta = _cdf(d1)
        theta = (-spot * _pdf(d1) * volatility / (2 * root) - risk_free_rate * strike * exp(-risk_free_rate * time_years) * _cdf(d2)) / 365
        rho = strike * time_years * exp(-risk_free_rate * time_years) * _cdf(d2) / 100
    elif option_type.upper() == "PUT":
        delta = _cdf(d1) - 1
        theta = (-spot * _pdf(d1) * volatility / (2 * root) + risk_free_rate * strike * exp(-risk_free_rate * time_years) * _cdf(-d2)) / 365
        rho = -strike * time_years * exp(-risk_free_rate * time_years) * _cdf(-d2) / 100
    else:
        raise ValueError("option_type must be CALL or PUT")
    return Greeks(delta, gamma, theta, vega, rho)
