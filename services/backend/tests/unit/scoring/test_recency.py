import pytest
import math
from datetime import datetime, timezone, timedelta
from cci.scoring.recency import compute_recency_factor, calculate_elapsed_years
from cci.domain.enums import CapabilityKey
from cci.domain.contracts import ScoringConfig

def test_compute_recency_factor():
    # delta_t_years < 0 -> 0.0
    factor = compute_recency_factor(-5.0, CapabilityKey.BACKEND_ENGINEERING)
    assert factor == 1.0 # math.exp(0)
    
    # normal usage
    factor2 = compute_recency_factor(2.0, CapabilityKey.BACKEND_ENGINEERING)
    # default lambda for BACKEND_ENGINEERING is probably not specified, defaults to 0.25
    expected = math.exp(-0.25 * 2.0)
    assert math.isclose(factor2, expected)
    
    # with config
    config = ScoringConfig(lambda_decay={CapabilityKey.BACKEND_ENGINEERING: 0.5})
    factor3 = compute_recency_factor(2.0, CapabilityKey.BACKEND_ENGINEERING, config=config)
    assert math.isclose(factor3, math.exp(-0.5 * 2.0))

def test_calculate_elapsed_years():
    now = datetime.now(timezone.utc)
    observed = now - timedelta(days=365.25 * 2)
    
    # Test normal
    years = calculate_elapsed_years(observed, now)
    assert math.isclose(years, 2.0)
    
    # Test reference_time None
    years2 = calculate_elapsed_years(observed)
    assert math.isclose(years2, 2.0, abs_tol=0.1)
    
    # Test naive datetimes
    naive_now = datetime.now()
    naive_observed = naive_now - timedelta(days=365.25 * 2)
    years3 = calculate_elapsed_years(naive_observed, naive_now)
    assert math.isclose(years3, 2.0)
    
    # Test future (observed > ref)
    years4 = calculate_elapsed_years(now, observed)
    assert years4 == 0.0
