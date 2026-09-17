"""Documentation and architecture analyzers package."""

from cci.analyzers.documentation.architecture import (
    analyze_adr,
    analyze_layer_boundaries,
    analyze_openapi_spec,
    analyze_readme,
)

__all__ = [
    "analyze_adr",
    "analyze_layer_boundaries",
    "analyze_openapi_spec",
    "analyze_readme",
]
