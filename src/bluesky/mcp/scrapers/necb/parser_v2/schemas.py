"""Pydantic schemas for NECB table types

These schemas define the target structure for parsed NECB tables.
Used by the LLM repair layer to validate and normalize extracted data.
"""

from pydantic import BaseModel, Field, field_validator


class AssemblyRequirement(BaseModel):
    """Single row of building envelope requirements (Table 3.2.2.2)"""

    assembly_type: str = Field(
        ...,
        description="Type of building assembly",
        pattern="^(Walls|Roofs|Floors|Windows|Doors|Skylights)$",
    )
    zone_4_max_u: float = Field(..., ge=0.05, le=2.0, description="Zone 4 max U-value (W/m²·K)")
    zone_5_max_u: float = Field(..., ge=0.05, le=2.0, description="Zone 5 max U-value (W/m²·K)")
    zone_6_max_u: float = Field(..., ge=0.05, le=2.0, description="Zone 6 max U-value (W/m²·K)")
    zone_7a_max_u: float = Field(..., ge=0.05, le=2.0, description="Zone 7A max U-value (W/m²·K)")
    zone_7b_max_u: float = Field(..., ge=0.05, le=2.0, description="Zone 7B max U-value (W/m²·K)")
    zone_8_max_u: float = Field(..., ge=0.05, le=2.0, description="Zone 8 max U-value (W/m²·K)")

    @field_validator("zone_4_max_u", "zone_5_max_u", "zone_6_max_u",
                     "zone_7a_max_u", "zone_7b_max_u", "zone_8_max_u")
    @classmethod
    def validate_uvalue_order(cls, v):
        """U-values should be reasonable for building envelopes"""
        if v < 0.05 or v > 2.0:
            raise ValueError(f"U-value {v} out of reasonable range (0.05-2.0 W/m²·K)")
        return v


class EnvelopeTable(BaseModel):
    """Table 3.2.2.2 - Overall Thermal Transmittance of Above-ground Opaque Building Assemblies"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^(3\\.2\\.2\\.[23])$")  # 3.2.2.2 or 3.2.2.3
    assemblies: list[AssemblyRequirement] = Field(..., min_length=3, max_length=6)

    @field_validator("assemblies")
    @classmethod
    def validate_assembly_types(cls, v):
        """Ensure all required assembly types are present"""
        types = {a.assembly_type for a in v}
        required_opaque = {"Walls", "Roofs", "Floors"}
        required_fenestration = {"Windows", "Doors", "Skylights"}

        # Must have either opaque OR fenestration types
        has_opaque = required_opaque.issubset(types)
        has_fenestration = any(t in types for t in required_fenestration)

        if not (has_opaque or has_fenestration):
            raise ValueError("Must have at least Walls/Roofs/Floors or Windows/Doors/Skylights")

        return v


class FDWRRequirement(BaseModel):
    """Single row of FDWR requirements (Table 3.2.1.4)"""

    hdd_min: int = Field(..., ge=0, le=10000, description="Minimum HDD")
    hdd_max: int | None = Field(None, ge=0, le=10000, description="Maximum HDD (None for open-ended)")
    max_fdwr: float = Field(..., ge=0.0, le=1.0, description="Maximum FDWR ratio (0-1)")


class FDWRTable(BaseModel):
    """Table 3.2.1.4 - Maximum Allowable FDWR"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="3.2.1.4")
    requirements: list[FDWRRequirement] = Field(..., min_length=1)


class HVACEquipmentPerformance(BaseModel):
    """Single row of HVAC equipment performance (Table 8.4.4.8.A/B)"""

    equipment_type: str = Field(..., description="Type of HVAC equipment")
    capacity_min: float | None = Field(None, description="Minimum capacity (kW or other unit)")
    capacity_max: float | None = Field(None, description="Maximum capacity (kW or other unit)")
    performance_metric: str = Field(..., description="Performance metric (COP, EER, IEER, etc.)")
    minimum_value: float = Field(..., ge=0.0, description="Minimum required performance")


class HVACTable(BaseModel):
    """Table 8.4.4.8.A/B - HVAC Equipment Performance"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^8\\.4\\.4\\.8\\.[AB]$")
    equipment: list[HVACEquipmentPerformance] = Field(..., min_length=1)


class LightingPowerDensity(BaseModel):
    """Single row of lighting power density requirements (Table 4.2.1.3)"""

    building_type: str = Field(..., description="Building or space type")
    space_type: str | None = Field(None, description="Specific space type within building")
    max_lpd: float = Field(..., ge=0.0, le=50.0, description="Maximum LPD (W/m²)")


class LightingTable(BaseModel):
    """Table 4.2.1.3 - Building Area and Space-by-Space Methods for Determining Lighting Power Density"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="4.2.1.3")
    requirements: list[LightingPowerDensity] = Field(..., min_length=1)


class PipingInsulation(BaseModel):
    """Single row of piping insulation requirements (Table 5.2.5.3)"""

    system_type: str = Field(..., description="Heating or cooling system")
    temp_range_min: float = Field(..., description="Min operating temperature (°C)")
    temp_range_max: float = Field(..., description="Max operating temperature (°C)")
    pipe_diameter_mm: str = Field(..., description="Pipe diameter range (mm)")
    min_insulation_thickness_mm: float = Field(..., ge=0.0, description="Minimum insulation thickness (mm)")


class PipingInsulationTable(BaseModel):
    """Table 5.2.5.3 - Minimum Thickness of Piping Insulation"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="5.2.5.3")
    requirements: list[PipingInsulation] = Field(..., min_length=1)


# Schema registry for easy lookup
SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    "3.2.2.2": EnvelopeTable,
    "3.2.2.3": EnvelopeTable,  # Fenestration uses same schema
    "3.2.1.4": FDWRTable,
    "4.2.1.3": LightingTable,
    "5.2.5.3": PipingInsulationTable,
    "8.4.4.8.A": HVACTable,
    "8.4.4.8.B": HVACTable,
}


def get_schema_for_table(table_number: str) -> type[BaseModel] | None:
    """
    Get the appropriate Pydantic schema for a table number

    Args:
        table_number: NECB table number (e.g., "3.2.2.2", "8.4.4.8.A")

    Returns:
        Pydantic BaseModel class or None if not found

    Example:
        >>> schema = get_schema_for_table("3.2.2.2")
        >>> print(schema.__name__)
        'EnvelopeTable'
    """
    # Normalize table number (handle variations)
    normalized = table_number.replace("Table ", "").replace("A-", "").strip()
    return SCHEMA_REGISTRY.get(normalized)
