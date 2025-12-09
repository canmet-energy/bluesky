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
    zone_4_max_u: float = Field(..., ge=0.05, le=3.0, description="Zone 4 max U-value (W/m²·K)")
    zone_5_max_u: float = Field(..., ge=0.05, le=3.0, description="Zone 5 max U-value (W/m²·K)")
    zone_6_max_u: float = Field(..., ge=0.05, le=3.0, description="Zone 6 max U-value (W/m²·K)")
    zone_7a_max_u: float = Field(..., ge=0.05, le=3.0, description="Zone 7A max U-value (W/m²·K)")
    zone_7b_max_u: float = Field(..., ge=0.05, le=3.0, description="Zone 7B max U-value (W/m²·K)")
    zone_8_max_u: float = Field(..., ge=0.05, le=3.0, description="Zone 8 max U-value (W/m²·K)")

    @field_validator("zone_4_max_u", "zone_5_max_u", "zone_6_max_u",
                     "zone_7a_max_u", "zone_7b_max_u", "zone_8_max_u")
    @classmethod
    def validate_uvalue_order(cls, v):
        """U-values should be reasonable for building envelopes (includes skylights up to 3.0)"""
        if v < 0.05 or v > 3.0:
            raise ValueError(f"U-value {v} out of reasonable range (0.05-3.0 W/m²·K)")
        return v


class EnvelopeTable(BaseModel):
    """Table 3.2.2.* / 3.2.3.* - Overall Thermal Transmittance of Building Assemblies"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^(3\\.2\\.2\\.[234]|3\\.2\\.3\\.1)$")  # 3.2.2.2-4, 3.2.3.1
    assemblies: list[AssemblyRequirement] = Field(..., min_length=1, max_length=6)

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

    # NECB2011+ formula-based FDWR calculation
    formula: str | None = Field(
        None,
        description="HDD-based FDWR formula - e.g., '(hdd < 4000) ? 0.4 : ...'"
    )
    skylight_to_roof_max: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Maximum skylight to roof ratio (Table 3.2.1.4(2))"
    )


class HVACEquipmentPerformance(BaseModel):
    """Single row of HVAC equipment performance (Table 8.4.4.8.A/B)"""

    equipment_type: str = Field(..., description="Type of HVAC equipment")
    capacity_min: float | None = Field(None, description="Minimum capacity (kW or other unit)")
    capacity_max: float | None = Field(None, description="Maximum capacity (kW or other unit)")
    performance_metric: str = Field(..., description="Performance metric (COP, EER, IEER, etc.)")
    minimum_value: float = Field(..., ge=0.0, description="Minimum required performance")


class HVACTable(BaseModel):
    """Table 8.4.4.8/8.4.4.8.A/B/8.4.4.13/8.4.4.14 - HVAC Equipment Performance"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^8\\.4\\.4\\.(8(\\.[AB])?|13|14)$")
    equipment: list[HVACEquipmentPerformance] = Field(..., min_length=1)


class LightingPowerDensity(BaseModel):
    """Single row of lighting power density requirements (Table 4.2.1.3)"""

    building_type: str = Field(..., description="Building or space type")
    space_type: str | None = Field(None, description="Specific space type within building")
    max_lpd: float = Field(..., ge=0.0, le=50.0, description="Maximum LPD (W/m²)")


class LightingTable(BaseModel):
    """Table 4.2.1.3/4.2.1.5 - Building Area and Space-by-Space Methods for Determining Lighting Power Density"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^4\\.2\\.1\\.(3|5)$")
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


class EquipmentEfficiency(BaseModel):
    """Single row of equipment efficiency requirements (Table 5.2.6.2)"""

    equipment_category: str = Field(..., description="Equipment category (e.g., Chillers, Boilers)")
    equipment_type: str = Field(..., description="Specific equipment type")
    size_category: str | None = Field(None, description="Size or capacity category")
    efficiency_metric: str = Field(..., description="Efficiency metric (COP, AFUE, kW/ton, etc.)")
    minimum_efficiency: float = Field(..., ge=0.0, description="Minimum required efficiency")


class EquipmentEfficiencyTable(BaseModel):
    """Table 5.2.6/5.2.6.2 - Energy Efficiency of HVAC Equipment"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^5\\.2\\.6(\\.2)?$")
    equipment: list[EquipmentEfficiency] = Field(..., min_length=1)


class DuctSealingRequirement(BaseModel):
    """Single row of duct sealing requirements (Table A-5.2.2.3.(1))"""

    static_pressure_class: str = Field(..., description="Static pressure class range")
    seal_class: str = Field(..., pattern="^[ABC]$", description="Seal class (A, B, or C)")
    description: str = Field(..., description="Sealing requirements description")


class DuctSealingTable(BaseModel):
    """Table 5.2.2.3/A-5.2.2.3.(1) - SMACNA Duct Sealing Classification"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^(5\\.2\\.2\\.3|A-5\\.2\\.2\\.3\\.\\(1\\))$")
    requirements: list[DuctSealingRequirement] = Field(..., min_length=1, max_length=5)


class ServiceWaterPipingInsulation(BaseModel):
    """Single row of service water piping insulation requirements (Table 6.2.3.1)"""

    location: str = Field(..., description="Location of piping (e.g., conditioned space, unconditioned space)")
    pipe_diameter: str = Field(..., description="Nominal pipe diameter")
    min_thickness_mm: float = Field(..., ge=0.0, description="Minimum insulation thickness (mm)")


class ServiceWaterPipingInsulationTable(BaseModel):
    """Table 6.2.3.1 - Minimum Thickness of Piping Insulation for Service Water Heating Systems"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="6.2.3.1")
    requirements: list[ServiceWaterPipingInsulation] = Field(..., min_length=1)


class PackagedHVACEquipment(BaseModel):
    """Single row of packaged HVAC equipment requirements (Table 5.2.12.1)

    Phase 6B: Relaxed schema to handle merged cells and formula-based requirements.
    Accepts equipment category groupings and preserves performance formulas as strings.
    """

    equipment_category: str | None = Field(
        None,
        description="Equipment category from merged header (e.g., 'Air Conditioners', 'Heat Pumps')"
    )
    equipment_type: str = Field(..., description="Component or equipment type")
    capacity_range: str | None = Field(None, description="Cooling or heating capacity range")
    standard: str | None = Field(None, description="Applicable standard (e.g., CAN/CSA-C656)")
    minimum_performance: str = Field(
        ...,
        description="Minimum performance requirement - may be formula (e.g., 'SEER = 15', 'EER ≥ 11.0')"
    )
    notes: str | None = Field(None, description="Footnotes or additional requirements")


class PackagedHVACTable(BaseModel):
    """Table 5.2.12.1.* - Unitary and Packaged HVAC Equipment Performance Requirements"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^5\\.2\\.12\\.1(\\.-[A-P])?$")  # 5.2.12.1 or 5.2.12.1.-A through -P
    equipment: list[PackagedHVACEquipment] = Field(..., min_length=1)


class PumpPowerRequirement(BaseModel):
    """Single row of pump power requirements (Table 5.2.6.3)"""

    hydronic_system_type: str = Field(
        ...,
        description="Type of hydronic system",
        pattern="^(Heating|Heat_rejection|Cooling|WSHP)$"
    )
    max_total_pump_power: float = Field(
        ...,
        ge=0.0,
        le=50.0,
        description="Maximum total pump power (W per kW of capacity)"
    )


class PumpPowerTable(BaseModel):
    """Table 5.2.6.3 - Maximum Total Pump Power (NECB2015+)"""

    vintage: str = Field(..., pattern="^(2015|2017|2020)$")  # Not in 2011
    table_number: str = Field(default="5.2.6.3")
    requirements: list[PumpPowerRequirement] = Field(..., min_length=4, max_length=4)

    @field_validator("requirements")
    @classmethod
    def validate_system_types(cls, v):
        """Ensure all 4 system types are present"""
        types = {req.hydronic_system_type for req in v}
        required = {"Heating", "Heat_rejection", "Cooling", "WSHP"}
        if types != required:
            raise ValueError(f"Must include all system types: {required}")
        return v


class OccupancySensorRequirement(BaseModel):
    """Single row of occupancy sensor requirements (Table 8.4.4.6(3))"""

    space_type: str = Field(
        ...,
        description="Space type category",
        pattern="^(Storage|Enclosed_Office|Other)$"
    )
    area_threshold_m2: float | None = Field(
        None,
        ge=0.0,
        le=1000.0,
        description="Maximum floor area requiring sensors (m²), None if not area-based"
    )
    sensor_required: bool = Field(
        ...,
        description="Whether occupancy sensors are required"
    )
    notes: str | None = Field(
        None,
        description="Additional requirements or conditions"
    )


class OccupancySensorTable(BaseModel):
    """Table 8.4.4.6(3) - Occupancy Sensor Requirements"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="8.4.4.6(3)")
    requirements: list[OccupancySensorRequirement] = Field(..., min_length=1)


class SWHEquipmentEfficiency(BaseModel):
    """Single row of SWH equipment efficiency requirements (Table 6.2.2.1)

    Phase 6B: Relaxed schema to handle formula-based requirements and merged cells.
    Available in all NECB vintages (2011-2020), not just 2020.
    """

    equipment_type: str = Field(
        ...,
        description="Equipment type (relaxed - accepts compound types like 'Gas-fired storage')"
    )
    fuel_type: str | None = Field(
        None,
        description="Fuel type (Gas, Oil, Electric, etc.) if specified separately"
    )
    storage_type: str | None = Field(
        None,
        description="Storage category (Storage, Instantaneous, Non-storage) if applicable"
    )
    capacity_range: str | None = Field(
        None,
        description="Heating capacity or volume range with units (e.g., '> 117 kW', '76-208 L')"
    )
    efficiency_metric: str | None = Field(
        None,
        description="Efficiency metric name (UEF, Et, EF, COP, SCOP, etc.)"
    )
    efficiency_requirement: str = Field(
        ...,
        description="Efficiency requirement - may be formula (e.g., 'Et ≥ 0.81', 'SL ≤35 + 0.20V')"
    )
    standby_loss: str | None = Field(
        None,
        description="Standby loss requirement - may be formula (e.g., 'SL ≤35 + 0.20V (top inlet)')"
    )
    test_standard: str | None = Field(
        None,
        description="Test procedure reference (e.g., 'CSA P.7', 'CAN/CSA-C191')"
    )
    notes: str | None = Field(
        None,
        description="Footnotes and additional requirements"
    )


class SWHEquipmentTable(BaseModel):
    """Table 6.2.2.1 - Service Water Heating Equipment Efficiency

    Phase 6B: Available in all NECB vintages (2011, 2015, 2017, 2020).
    Handles merged cells, formula-based efficiency requirements, and footnotes.
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="6.2.2.1")
    equipment: list[SWHEquipmentEfficiency] = Field(..., min_length=1)


class HeatPumpSystemDescription(BaseModel):
    """Single row of heat pump system descriptions (Table 8.4.4.13)"""

    system_number: str = Field(..., description="System number or range (e.g., 'Systems 1 and 3 to 6', 'System 2')")
    type_of_system: str = Field(..., description="Type of HVAC system")
    fan_control: str | None = Field(None, description="Fan control type (e.g., 'Constant volume')")
    terminal_heating_type: str | None = Field(None, description="Type of terminal or auxiliary heating")


class HeatPumpSystemTable(BaseModel):
    """Table 8.4.4.13/8.4.4.14 - Heat Pump System Description

    Note: Both 8.4.4.13 and 8.4.4.14 contain heat pump system descriptions.
    8.4.4.13: General heat pump system descriptions
    8.4.4.14: Heat pump system descriptions for reference building
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^8\\.4\\.4\\.(13|14)$")
    systems: list[HeatPumpSystemDescription] = Field(..., min_length=1)


class PumpPowerCoefficient(BaseModel):
    """Single coefficient for pump power calculations (Tables 8.4.4.14, 8.4.4.18)

    Note: NECB 2017 table 8.4.4.14 has 6 coefficients (A-F), while some
    vintages may have 5 coefficients (A-E). Pattern supports both.
    """

    coefficient_name: str = Field(..., pattern="^[A-F]$", description="Coefficient name (uppercase A through F)")
    riding_curve_value: float = Field(..., description="Value for pump riding its curve")
    variable_speed_value: float = Field(..., description="Value for pump with variable speed drive")


class PumpPowerCoefficientTable(BaseModel):
    """Tables 8.4.4.14, 8.4.4.18 - Coefficients Used in Calculating Pump Power versus Flow Rate

    Note: NECB 2017 uses table 8.4.4.14 with 6 coefficients (A-F).
    Other vintages may use different table numbers or have 5 coefficients (A-E).
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="8.4.4.14")
    coefficients: list[PumpPowerCoefficient] = Field(..., min_length=5, max_length=6)

    @field_validator("coefficients")
    @classmethod
    def validate_all_coefficients(cls, v):
        """Ensure all coefficients A-E or A-F are present (depending on vintage)"""
        names = {c.coefficient_name for c in v}
        # Accept either 5 coefficients (A-E) or 6 coefficients (A-F)
        valid_5 = {"A", "B", "C", "D", "E"}
        valid_6 = {"A", "B", "C", "D", "E", "F"}
        if names != valid_5 and names != valid_6:
            raise ValueError(f"Must include all coefficients A-E or A-F, got: {names}")
        return v


class ExteriorLightingRow(BaseModel):
    """Single row for exterior lighting tables (4.2.3.1.*)"""

    category: str = Field(..., description="Category or zone identifier")
    value: str | float = Field(..., description="Allowance, description, or numeric value")


class ExteriorLightingTable(BaseModel):
    """Table 4.2.3.1.* - Exterior Lighting Requirements"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^4\\.2\\.3\\.1(\\.\\-[A-E])?$")  # 4.2.3.1 or subtables
    rows: list[ExteriorLightingRow] = Field(..., min_length=1)


class LightingControlRequirement(BaseModel):
    """Single row of lighting control requirements (Table 4.2.1.6)"""

    control_type: str = Field(
        ...,
        description="Type of lighting control (e.g., Manual, Bi-Level, Daylight Responsive)"
    )
    space_requirements: dict[str, str] = Field(
        ...,
        description="Requirements per space type - values are X (required), B (base), A (allowed), or - (not applicable)"
    )
    reference: str | None = Field(
        None,
        description="Reference to related NECB section (e.g., '4.2.2.1.(9)')"
    )
    notes: str | None = Field(
        None,
        description="Additional requirements or conditions"
    )


class LightingControlTable(BaseModel):
    """Table 4.2.1.6 - Lighting Control Requirements Matrix"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="4.2.1.6")
    requirements: list[LightingControlRequirement] = Field(..., min_length=1)


class TradeOffComponentFactorRow(BaseModel):
    """Single row of trade-off component factors (Table 5.3.2.2)"""

    trade_off_value: str = Field(
        ...,
        description="Trade-off value identifier (e.g., ToV1, ToV2, ...)"
    )
    hvac_system_factors: dict[str, float] = Field(
        ...,
        description="γi factors per HVAC System ID - keys are system IDs (1-27), values are factors (0 or 1)"
    )


class TradeOffComponentFactorTable(BaseModel):
    """Table 5.3.2.2 - Component Factors, γi, for Trade-off Calculations"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="5.3.2.2")
    factors: list[TradeOffComponentFactorRow] = Field(..., min_length=1)


class TradeOffValueRow(BaseModel):
    """Single row of trade-off values (Table 5.3.2.7)

    Note: Table 5.3.2.7 spans multiple pages and may be extracted as separate sections.
    Each row represents one (ToV, description) pair with values for all 27 HVAC systems.

    Example: ToV5 | Supply OA Reset | 0.7211 | 0.7315 | ... | 0.9344
    """

    tov_id: str = Field(
        ...,
        description="Trade-off value identifier (ToV5, ToV6, etc.)"
    )
    description: str = Field(
        ...,
        description="Row description (e.g., 'Supply OA Reset', 'Forward curve with vanes')"
    )
    # Values for each HVAC System (1-27)
    system_1: float | str | None = None
    system_2: float | str | None = None
    system_3: float | str | None = None
    system_4: float | str | None = None
    system_5: float | str | None = None
    system_6: float | str | None = None
    system_7: float | str | None = None
    system_8: float | str | None = None
    system_9: float | str | None = None
    system_10: float | str | None = None
    system_11: float | str | None = None
    system_12: float | str | None = None
    system_13: float | str | None = None
    system_14: float | str | None = None
    system_15: float | str | None = None
    system_16: float | str | None = None
    system_17: float | str | None = None
    system_18: float | str | None = None
    system_19: float | str | None = None
    system_20: float | str | None = None
    system_21: float | str | None = None
    system_22: float | str | None = None
    system_23: float | str | None = None
    system_24: float | str | None = None
    system_25: float | str | None = None
    system_26: float | str | None = None
    system_27: float | str | None = None


class TradeOffValueTable(BaseModel):
    """Table 5.3.2.7 - Trade-off Values by HVAC System

    Note: This table spans 2 pages (173-174) and may be extracted as separate sections.
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="5.3.2.7")
    values: list[TradeOffValueRow] = Field(..., min_length=1)
    page_section: int | None = Field(
        None,
        description="Page section number for multi-page tables (1, 2, etc.)"
    )


class HeatRecoveryThreshold(BaseModel):
    """Single threshold value for heat recovery (5.2.10.1.*)"""

    climate_zone: str = Field(..., description="Climate zone identifier")
    outdoor_air_percentage: str = Field(..., description="Percentage range of outdoor air")
    threshold_value: str = Field(..., description="Threshold airflow rate or 'NR'/'R'")


class HeatRecoveryTable(BaseModel):
    """Table 5.2.10.1.* - Energy Recovery Requirements"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^5\\.2\\.10\\.1(\\.\\-[AB])?$")  # 5.2.10.1 or subtables
    thresholds: list[HeatRecoveryThreshold] = Field(..., min_length=1)


# ============================================================================
# Section 5: Additional HVAC Equipment Tables
# ============================================================================


class HeatRejectionEquipmentRow(BaseModel):
    """Single row of heat rejection equipment requirements (Table 5.2.12.2)"""

    equipment_type: str = Field(..., description="Type of heat rejection equipment")
    capacity_range: str | None = Field(None, description="Capacity range")
    performance_metric: str = Field(..., description="Performance metric (e.g., Fan power, Efficiency)")
    minimum_requirement: str | float = Field(..., description="Minimum required value or condition")


class HeatRejectionEquipmentTable(BaseModel):
    """Table 5.2.12.2 - Heat Rejection Equipment Performance Requirements"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="5.2.12.2")
    equipment: list[HeatRejectionEquipmentRow] = Field(..., min_length=1)


class HeatRecoveryVentilatorRow(BaseModel):
    """Single row of HRV/ERV performance requirements (Table 5.2.10.4)"""

    equipment_type: str = Field(..., description="HRV or ERV type")
    efficiency_metric: str = Field(..., description="Efficiency metric")
    minimum_efficiency: float = Field(..., ge=0.0, le=1.0, description="Minimum efficiency (ratio)")


class HeatRecoveryVentilatorTable(BaseModel):
    """Table 5.2.10.4 - Performance of Heat-recovery Ventilators"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="5.2.10.4")
    equipment: list[HeatRecoveryVentilatorRow] = Field(..., min_length=1)


class DuctLeakageClass(BaseModel):
    """Single duct leakage class definition (Table 5.2.2.4)

    Phase 6B: Simplified schema for matrix structure.
    Phase 12: Extended to support both seal class-based and pressure-based formats.

    Two formats supported:
    1. Seal class format: duct_shape + seal_class + leakage_class (older vintages)
    2. Pressure format: duct_shape + pressure_range + leakage_rate (NECB 2020)
    """

    duct_shape: str = Field(
        ...,
        pattern="^(Rectangular|Round)$",
        description="Duct shape"
    )

    # Seal class format fields (optional for pressure-based format)
    seal_class: str | None = Field(
        None,
        pattern="^(A|B|C)$",
        description="Sealing class per SMACNA (seal class format only)"
    )
    leakage_class: int | None = Field(
        None,
        ge=3,
        le=48,
        description="Leakage class (CL) - integer value (seal class format only)"
    )

    # Pressure-based format fields (optional for seal class format)
    pressure_range: str | None = Field(
        None,
        description="Operating static pressure range (e.g., '< 500', '500-1000', '> 1000' Pa)"
    )
    leakage_rate: float | None = Field(
        None,
        ge=0.0,
        description="Leakage rate in L/s per m² (pressure format only)"
    )

    # Legacy field (optional for both formats)
    pressure_category: str | None = Field(
        None,
        description="Pressure category if specified (e.g., 'Positive', 'Negative', 'Both')"
    )


class DuctLeakageTable(BaseModel):
    """Table 5.2.2.4 - Leakage Classes, CL / Duct Leakage

    Phase 6B: Matrix structure with shape × seal class combinations.
    Phase 12: Extended to support pressure-based format (NECB 2020).

    Two formats supported:
    - Seal class format: 6 rows (2 shapes × 3 seal classes)
    - Pressure format: 6 rows (2 shapes × 3 pressure ranges)
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="5.2.2.4")
    classes: list[DuctLeakageClass] = Field(..., min_length=1)


class DuctInsulationRequirement(BaseModel):
    """Single duct insulation requirement (Table 5.2.2.5)"""

    duct_location: str = Field(..., description="Location of duct (e.g., unconditioned space)")
    duct_type: str = Field(..., description="Supply or return")
    min_insulation_rsi: float = Field(..., ge=0.0, description="Minimum insulation R-value (m²·K/W)")


class DuctInsulationTable(BaseModel):
    """Table 5.2.2.5 - Insulation of Ducts"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="5.2.2.5")
    requirements: list[DuctInsulationRequirement] = Field(..., min_length=1)


class KitchenVentilationThreshold(BaseModel):
    """Single threshold for kitchen ventilation control (Table 5.2.3.4)"""

    hood_type: str = Field(..., description="Type of kitchen hood")
    exhaust_rate_threshold: float = Field(..., ge=0.0, description="Threshold exhaust rate (L/s)")


class KitchenVentilationTable(BaseModel):
    """Table 5.2.3.4 - Demand Control Ventilation Threshold for Commercial Kitchen Ventilation Systems"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="5.2.3.4")
    thresholds: list[KitchenVentilationThreshold] = Field(..., min_length=1)


class EconomizerControl(BaseModel):
    """Single economizer HLSO control setting (Table A-5.2.2.8.(2))"""

    climate_zone: str = Field(..., description="Climate zone")
    control_type: str = Field(..., description="Control method (e.g., dry-bulb, enthalpy)")
    setpoint: str | float = Field(..., description="HLSO setpoint value")


class EconomizerControlTable(BaseModel):
    """Table A-5.2.2.8.(2) - High-Limit Shut-off (HLSO) Control Settings for Air Economizers"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="A-5.2.2.8.(2)")
    controls: list[EconomizerControl] = Field(..., min_length=1)


# ============================================================================
# Section 8: HVAC System Selection and Performance Compliance Tables
# ============================================================================


class HVACSystemSelectionRow(BaseModel):
    """Single row for HVAC system selection (Table 8.4.4.7.-A)"""

    building_type: str = Field(..., description="Building type or category")
    system_number: str = Field(..., description="Reference system number (e.g., 'System 1', 'System 3')")
    conditions: str | None = Field(None, description="Additional selection conditions")


class HVACSystemSelectionTable(BaseModel):
    """Table 8.4.4.7.-A, 8.4.4.8.A, 8.4.4.8.B - HVAC System Selection

    Tables that define HVAC system selection based on building type:
    - 8.4.4.7.-A: HVAC System Selection for Reference Building
    - 8.4.4.8.A: System Selection by Building Type (alternate format)
    - 8.4.4.8.B: System Selection by Building Type (alternate format)
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^8\\.4\\.4\\.(7\\.-A|8\\.[AB])$")
    selections: list[HVACSystemSelectionRow] = Field(..., min_length=1)


class HVACSystemDescriptionRow(BaseModel):
    """Single system description (Table 8.4.4.7.-B)"""

    system_number: str = Field(..., description="System number (1-6)")
    heating_type: str = Field(..., description="Type of heating")
    cooling_type: str = Field(..., description="Type of cooling")
    fan_control: str | None = Field(None, description="Fan control method")
    notes: str | None = Field(None, description="Additional system notes")


class HVACSystemDescriptionTable(BaseModel):
    """Table 8.4.4.7.-B - Descriptions of HVAC Systems 1 to 6"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="8.4.4.7.-B")
    systems: list[HVACSystemDescriptionRow] = Field(..., min_length=1)


class EconomizerRequirementRow(BaseModel):
    """Single economizer requirement (Table 8.4.4.12)"""

    system_type: str = Field(..., description="Type of HVAC system")
    economizer_required: bool | str = Field(..., description="Whether economizer is required")
    conditions: str | None = Field(None, description="Conditions or exceptions")


class EconomizerRequirementTable(BaseModel):
    """Table 8.4.4.12 - Applicable Requirements for Cooling with Outside Air According to Type of HVAC System"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="8.4.4.12")
    requirements: list[EconomizerRequirementRow] = Field(..., min_length=1)


class FanPowerCoefficient(BaseModel):
    """Single coefficient for fan power calculations (Table 8.4.4.17)"""

    coefficient_name: str = Field(..., pattern="^[A-F]$", description="Coefficient name (A-F)")
    constant_volume_value: float = Field(..., description="Value for constant volume systems")
    variable_volume_value: float = Field(..., description="Value for variable volume systems")


class FanPowerCoefficientTable(BaseModel):
    """Table 8.4.4.17 - Coefficients Used in Calculating Fan Power versus Flow Rate"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="8.4.4.17")
    coefficients: list[FanPowerCoefficient] = Field(..., min_length=1)


class ChillerPerformanceLevel(BaseModel):
    """Single chiller performance level (Table 8.4.3.5)"""

    chiller_type: str = Field(..., description="Type of chiller")
    capacity_range: str | None = Field(None, description="Capacity range")
    performance_metric: str = Field(..., description="Performance metric (COP, kW/ton, etc.)")
    minimum_value: float = Field(..., ge=0.0, description="Minimum required value")


class ChillerPerformanceTable(BaseModel):
    """Table 8.4.3.5 - Type and Performance Levels of Chiller Providing Purchased Energy"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="8.4.3.5")
    chillers: list[ChillerPerformanceLevel] = Field(..., min_length=1)


class PerformanceCoefficient(BaseModel):
    """Generic performance coefficient for Section 8.4.5 tables"""

    coefficient_name: str = Field(..., description="Coefficient identifier")
    value: float | str = Field(..., description="Coefficient value or formula")
    description: str | None = Field(None, description="Coefficient description")


class PerformanceCoefficientTable(BaseModel):
    """Generic table for performance coefficients (Tables 8.4.5.*)"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^8\\.4\\.5\\.[0-9]+(\\.\\-[A-C])?$")
    coefficients: list[PerformanceCoefficient] = Field(..., min_length=1)


# ============================================================================
# Section 4: Daylight and Occupancy Control Tables
# ============================================================================


class DaylightControlFactor(BaseModel):
    """Single daylight control factor (Tables 4.3.2.7.*, 4.3.2.8, 4.3.2.9.*, 4.3.2.10.*)"""

    category: str = Field(..., description="Category, control type, or space type")
    subcategory: str | None = Field(None, description="Subcategory if applicable")
    factor_value: float | str = Field(..., description="Factor value or range")
    conditions: str | None = Field(None, description="Conditions or notes")


class DaylightControlTable(BaseModel):
    """Generic table for daylight control factors (Tables 4.3.2.*)"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., pattern="^4\\.3\\.2\\.[0-9]+(\\.\\-[A-B])?$")
    factors: list[DaylightControlFactor] = Field(..., min_length=1)


# ============================================================================
# Generic Flexible Schema for Simple Reference Tables
# ============================================================================


class GenericTableRow(BaseModel):
    """Generic row for simple reference tables"""

    key: str = Field(..., description="Primary identifier or category")
    value: str | float | int = Field(..., description="Associated value")
    notes: str | None = Field(None, description="Additional notes or conditions")


class GenericReferenceTable(BaseModel):
    """Generic schema for simple reference tables, appendices, and design data"""

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(..., description="Table number")
    description: str | None = Field(None, description="Table description")
    rows: list[GenericTableRow] = Field(..., min_length=1)


# ============================================================================
# Phase 1: HVAC Coefficient Tables (5.3.2.8.-A through -AA)
# ============================================================================


class HVACCoefficientRow(BaseModel):
    """Single row of HVAC system coefficient values (Tables 5.3.2.8.-A to -AA)

    These tables contain polynomial coefficients for modeling HVAC system
    performance curves. Each row represents a specific performance curve
    or operating condition.
    """

    curve_name: str = Field(
        ...,
        description="Name of the performance curve (e.g., 'CAP_FT', 'EIR_FT', 'PLF')"
    )
    description: str | None = Field(
        None,
        description="Description of what this curve models"
    )
    coefficient_a: float | None = Field(None, description="Coefficient A (constant term)")
    coefficient_b: float | None = Field(None, description="Coefficient B")
    coefficient_c: float | None = Field(None, description="Coefficient C")
    coefficient_d: float | None = Field(None, description="Coefficient D")
    coefficient_e: float | None = Field(None, description="Coefficient E")
    coefficient_f: float | None = Field(None, description="Coefficient F")
    minimum_value: float | None = Field(None, description="Minimum output value for this curve")
    maximum_value: float | None = Field(None, description="Maximum output value for this curve")


class HVACCoefficientTable(BaseModel):
    """Tables 5.3.2.8.-A through 5.3.2.8.-AA - HVAC System Performance Coefficients

    Each table provides polynomial coefficients for a specific HVAC system type
    (HVAC-1 through HVAC-27). These coefficients are used in energy modeling
    software to calculate system performance curves.

    Available in NECB 2011, 2015, and 2017 (not in 2020 which uses different methodology).
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017)$")
    table_number: str = Field(
        ...,
        description="Table identifier (e.g., '5.3.2.8.-A', '5.3.2.8.-AA')",
        pattern=r"^5\.3\.2\.8\.-[A-Z]{1,2}$"
    )
    hvac_system_type: str = Field(
        ...,
        description="HVAC system type number (e.g., 'HVAC-1', 'HVAC-27')"
    )
    system_description: str = Field(
        ...,
        description="Description of the HVAC system (e.g., 'Built-up Variable-Volume')"
    )
    coefficients: list[HVACCoefficientRow] = Field(
        ...,
        min_length=1,
        description="List of performance curve coefficients"
    )


# ============================================================================
# Phase 1: Objectives Tables (x.5.1.1)
# ============================================================================


class ObjectiveRow(BaseModel):
    """Single row of objectives table data (Tables x.5.1.1)

    These tables map NECB sections to their associated objectives and
    functional statements from the National Building Code.
    """

    section_reference: str = Field(
        ...,
        description="NECB section reference (e.g., '3.2.1.1.(1)', '4.2.3.1.(2)')"
    )
    objectives: str | None = Field(
        None,
        description="Objective codes (e.g., 'OE', 'OE1.1', 'OE1.2')"
    )
    functional_statements: str | None = Field(
        None,
        description="Functional statement codes (e.g., 'F81', 'F82')"
    )


class ObjectivesTable(BaseModel):
    """Tables x.5.1.1 - Objectives and Functional Statements

    These informational tables list the objectives and functional statements
    from the National Building Code that are attributed to the acceptable
    solutions in each major NECB section.

    Available tables:
    - 3.5.1.1: Building Envelope objectives
    - 4.5.1.1: Lighting objectives
    - 5.5.1.1: HVAC objectives
    - 6.5.1.1: Service Water Heating objectives
    - 7.5.1.1: Electrical Power objectives
    - 8.5.1.1: Building Energy Performance Compliance objectives
    - 10.2.1.1: Alternative Compliance Path objectives
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(
        ...,
        description="Table identifier (e.g., '3.5.1.1', '10.2.1.1')",
        pattern=r"^(\d+\.5\.1\.1|10\.2\.1\.1)$"
    )
    section_name: str = Field(
        ...,
        description="Name of the NECB section (e.g., 'Building Envelope', 'Lighting')"
    )
    objectives: list[ObjectiveRow] = Field(
        ...,
        min_length=1,
        description="List of section-to-objective mappings"
    )


# ============================================================================
# Phase 2: Schedule Tables (A-8.4.3.2.(1) and A-8.4.3.3.(1))
# ============================================================================


class ScheduleEntry(BaseModel):
    """Single hourly value in an operating schedule.

    Operating schedules define hourly values (0-23) for different day types
    (weekday, weekend, holiday) and system types (occupancy, lighting, etc.).
    """

    hour: int = Field(
        ...,
        ge=0,
        le=23,
        description="Hour of day (0-23)"
    )
    value: float | str = Field(
        ...,
        description="Schedule value (float 0.0-1.0 for fractions/percentages, or string 'On'/'Off' for fans/HVAC)"
    )


class DayTypeSchedule(BaseModel):
    """Schedule for a single day type (weekday, weekend, or holiday)."""

    day_type: str = Field(
        ...,
        description="Day type (e.g., 'Weekday', 'Weekend', 'Holiday')"
    )
    hours: list[ScheduleEntry] = Field(
        ...,
        min_length=1,
        max_length=24,
        description="Hourly schedule values (up to 24 entries)"
    )


class ScheduleType(BaseModel):
    """Schedule for a specific type (occupancy, lighting, equipment, fans, HVAC, etc.)."""

    schedule_type: str = Field(
        ...,
        description="Schedule type (e.g., 'Occupants, fraction occupied', 'Lighting, fraction \"ON\"', 'Fans', 'Cooling System, °C')"
    )
    day_types: list[DayTypeSchedule] = Field(
        ...,
        min_length=1,
        description="Schedules for each day type (Mon-Fri, Sat, Sun, etc.)"
    )


class OperatingScheduleTable(BaseModel):
    """Tables A-8.4.3.2.(1)A through K - Building Operating Schedules

    These tables define hourly operating schedules for different building types:
    - Schedule A: Office/Professional
    - Schedule B: Retail
    - Schedule C: School/University
    - Schedule D: Hotel/Motel
    - Schedule E: Healthcare (24-hr)
    - Schedule F: Restaurant
    - Schedule G: Warehouse
    - Schedule H: Religious
    - Schedule I: Sports/Recreation
    - Schedule J: Manufacturing
    - Schedule K: Multifamily Residential

    Each schedule provides hourly values (0-23) for:
    - Occupancy (fraction of design occupancy)
    - Lighting (fraction of installed lighting power)
    - Equipment (fraction of installed equipment power)
    - HVAC schedules (may include heating/cooling setpoints)

    Day types: Weekday, Weekend, Holiday

    Available in all NECB vintages (2011, 2015, 2017, 2020).
    Note: NECB 2011 uses format "A-8.4.3.2.(1)A", later versions use "A-8.4.3.2.(1)-A"
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(
        ...,
        description="Table identifier (e.g., 'A-8.4.3.2.(1)-A', 'A-8.4.3.2.(1)A')",
    )
    schedule_name: str = Field(
        ...,
        description="Schedule name (e.g., 'Operating Schedule A', 'Office/Professional')"
    )
    schedule_types: list[ScheduleType] = Field(
        ...,
        min_length=1,
        description="Schedule types (occupants, lighting, receptacle equipment, fans, cooling system, heating system, service water heating)"
    )


class DefaultLoadEntry(BaseModel):
    """Single entry in the default loads table (A-8.4.3.2.(2) or A-8.4.3.3.(1))."""

    building_or_space_type: str = Field(
        ...,
        description="Building type or space type"
    )
    occupancy_density: float | None = Field(
        None,
        description="Design occupancy density (m²/person or persons/100m²)"
    )
    lighting_power_density: float | None = Field(
        None,
        description="Lighting power density (W/m²)"
    )
    equipment_power_density: float | None = Field(
        None,
        description="Equipment/plug load power density (W/m²)"
    )
    ventilation_rate: float | None = Field(
        None,
        description="Outdoor air ventilation rate (L/s·person or L/s·m²)"
    )
    hot_water_usage: str | None = Field(
        None,
        description="Service hot water usage (L/day·person or L/day·m²) or footnote reference letter (A-K, *)"
    )
    schedule_reference: str | None = Field(
        None,
        description="Reference to operating schedule (e.g., 'Schedule A', 'A-8.4.3.2.(1)-A')"
    )


class ModelingGuidanceTable(BaseModel):
    """Tables A-8.4.3.2.(2)-A/B and A-8.4.3.3.(1)A/B - Modeling Guidance

    These tables provide default loads and operating schedules by building type
    or space type for energy modeling purposes.

    A-8.4.3.2.(2)-A: Default values by building type
    A-8.4.3.2.(2)-B: Default values by space type
    A-8.4.3.3.(1)A: Default loads by building type (NECB 2011 format)
    A-8.4.3.3.(1)B: Default loads by space type (NECB 2011 format)

    Available in all NECB vintages.
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(
        ...,
        description="Table identifier (e.g., 'A-8.4.3.2.(2)-A', 'A-8.4.3.3.(1)A')",
    )
    guidance_type: str = Field(
        ...,
        description="Type of guidance ('by_building_type' or 'by_space_type')"
    )
    entries: list[DefaultLoadEntry] = Field(
        ...,
        min_length=1,
        description="List of default load entries"
    )


# ============================================================================
# Phase 3: Performance & System Selection Tables
# ============================================================================


class PartLoadPerformanceRow(BaseModel):
    """Single row of part-load performance data (Tables 8.4.4.21.-A through -G)."""

    equipment_type: str = Field(
        ...,
        description="Equipment type (e.g., 'Furnace', 'Boiler', 'DX Cooling', 'Chiller')"
    )
    performance_curve: str = Field(
        ...,
        description="Name of performance curve (e.g., 'HIR_FPLR', 'CAP_FT', 'EIR_FT')"
    )
    coefficient_a: float | None = Field(None, description="Coefficient A (constant term)")
    coefficient_b: float | None = Field(None, description="Coefficient B")
    coefficient_c: float | None = Field(None, description="Coefficient C")
    coefficient_d: float | None = Field(None, description="Coefficient D")
    coefficient_e: float | None = Field(None, description="Coefficient E")
    coefficient_f: float | None = Field(None, description="Coefficient F")
    minimum_output: float | None = Field(None, description="Minimum output value")
    maximum_output: float | None = Field(None, description="Maximum output value")
    formula_text: str | None = Field(
        None,
        description="LaTeX-formatted formula or table content (for formula-based tables like 8.4.4.21.-G)"
    )


class PartLoadPerformanceTable(BaseModel):
    """Tables 8.4.4.21.-A through -G (2015+) / 8.4.4.22.A-G (2011) - Part-Load Performance Characteristics

    These tables provide polynomial coefficients for equipment performance
    curves at various load conditions. Used for energy modeling calculations.

    Available tables:
    NECB 2015, 2017:
    - 8.4.4.21.-A: Heating Equipment (furnaces, boilers)
    - 8.4.4.21.-B: Direct-Expansion Cooling Equipment
    - 8.4.4.21.-C: Electric Chiller Cooling Equipment
    - 8.4.4.21.-E: Electric Air-Source Heat Pump Equipment
    - 8.4.4.21.-F: Absorption Chiller Cooling Equipment
    - 8.4.4.21.-G: Fuel-Fired Service Water Heater

    NECB 2011 (different numbering, same content):
    - 8.4.4.22.A through 8.4.4.22.G

    Note: Available in NECB 2011, 2015, 2017 (not in 2020).
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017)$")
    table_number: str = Field(
        ...,
        description="Table identifier (e.g., '8.4.4.21.-A' for 2015+ or '8.4.4.22.A' for 2011)",
        pattern=r"^8\.4\.4\.(21\.-|22\.)[A-G]$"
    )
    equipment_category: str = Field(
        ...,
        description="Equipment category (e.g., 'Heating', 'Cooling', 'Heat Pump', 'SWH')"
    )
    performance_curves: list[PartLoadPerformanceRow] = Field(
        ...,
        min_length=1,
        description="List of performance curve coefficients"
    )


class HVACSystemTypeRow(BaseModel):
    """Single row in HVAC system types table (5.3.1.1.-A)."""

    system_number: str = Field(
        ...,
        description="System identifier (e.g., 'HVAC-1', 'System-1')"
    )
    system_name: str = Field(
        ...,
        description="System name (e.g., 'Built-up Variable Volume')"
    )
    heating_type: str | None = Field(
        None,
        description="Heating system type (e.g., 'Boiler', 'Furnace', 'Heat Pump')"
    )
    cooling_type: str | None = Field(
        None,
        description="Cooling system type (e.g., 'Chiller', 'DX', 'None')"
    )
    distribution_type: str | None = Field(
        None,
        description="Distribution system (e.g., 'VAV', 'CAV', 'Radiant')"
    )
    terminal_type: str | None = Field(
        None,
        description="Terminal units (e.g., 'Reheat', 'Fan Coil', 'None')"
    )
    description: str | None = Field(
        None,
        description="Full system description"
    )


class HVACSystemTypesTable(BaseModel):
    """Table 5.3.1.1.-A - Types of HVAC Systems

    Lists standard HVAC system configurations used in NECB trade-off
    calculations and reference building modeling.

    Available in NECB 2011, 2015, 2017 (not in 2020).
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017)$")
    table_number: str = Field(
        ...,
        description="Table identifier",
        pattern=r"^5\.3\.1\.1\.-A$"
    )
    systems: list[HVACSystemTypeRow] = Field(
        ...,
        min_length=1,
        description="List of HVAC system types"
    )


class ComponentFactorRow(BaseModel):
    """Single row in component factor or trade-off table."""

    component_type: str = Field(
        ...,
        description="Component type (e.g., 'Chiller', 'Boiler', 'Fan', 'Pump')"
    )
    parameter_name: str | None = Field(
        None,
        description="Parameter name (e.g., 'γi', 'ToVi')"
    )
    factor_value: float | None = Field(
        None,
        description="Factor or coefficient value"
    )
    base_value: float | None = Field(
        None,
        description="Base value for calculations"
    )
    units: str | None = Field(
        None,
        description="Units for the value"
    )
    applicability: str | None = Field(
        None,
        description="When this factor applies"
    )
    notes: str | None = None


class ComponentFactorTable(BaseModel):
    """Tables 5.3.2.2, 5.3.2.3, 5.3.2.7, 6.3.2.5 - Component Factors for Trade-offs

    These tables provide component factors (γi) and trade-off values (ToVi)
    used in NECB trade-off compliance calculations.

    - 5.3.2.2: Component Factors γi for HVAC Trade-off
    - 5.3.2.3: Component Trade-off Values ToVi (Proposed Building)
    - 5.3.2.7: Additional trade-off parameters
    - 6.3.2.5: SWH Component Trade-off Values

    Available in NECB 2011, 2015, 2017 (not in 2020).
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017)$")
    table_number: str = Field(
        ...,
        description="Table identifier",
        pattern=r"^(5\.3\.2\.[237]|6\.3\.2\.5)$"
    )
    table_type: str = Field(
        ...,
        description="Type of factors ('component_factor', 'trade_off_value', 'swh_trade_off')"
    )
    factors: list[ComponentFactorRow] = Field(
        ...,
        min_length=1,
        description="List of component factors"
    )


class SWHSystemTypeRow(BaseModel):
    """Single row in SWH system types table (6.3.1.1)."""

    system_number: str = Field(
        ...,
        description="System identifier (e.g., 'SWH-1', 'System-1')"
    )
    system_name: str = Field(
        ...,
        description="System name"
    )
    heater_type: str | None = Field(
        None,
        description="Water heater type (e.g., 'Storage', 'Tankless', 'Heat Pump')"
    )
    fuel_type: str | None = Field(
        None,
        description="Fuel type (e.g., 'Gas', 'Electric', 'Oil')"
    )
    distribution_type: str | None = Field(
        None,
        description="Distribution type (e.g., 'Recirculating', 'Point-of-use')"
    )
    description: str | None = Field(
        None,
        description="Full system description"
    )


class SWHSystemTypesTable(BaseModel):
    """Table 6.3.1.1 - Types of SWH System

    Lists standard service water heating system configurations used in
    NECB trade-off calculations and reference building modeling.

    Available in NECB 2011, 2015, 2017 (not in 2020).
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017)$")
    table_number: str = Field(
        ...,
        description="Table identifier",
        pattern=r"^6\.3\.1\.1$"
    )
    systems: list[SWHSystemTypeRow] = Field(
        ...,
        min_length=1,
        description="List of SWH system types"
    )


# ============================================================================
# Phase 4: Reference and Administrative Tables
# ============================================================================


class ReferenceTableRow(BaseModel):
    """Single row in a reference/administrative table."""

    key: str = Field(
        ...,
        description="Reference key or section (e.g., 'Part 3', 'Div B')"
    )
    description: str = Field(
        ...,
        description="Description or content"
    )
    reference: str | None = Field(
        None,
        description="Cross-reference to other sections or tables"
    )
    notes: str | None = None


class ReferenceTable(BaseModel):
    """Reference and Administrative Tables (1-1, 2-1, 1.3.1.2, etc.)

    These tables contain organizational, scope, compliance, and reference information.
    Content varies by vintage:

    **NECB 2011/2015/2017:**
    - 1-1: Scope of Division B
    - 2-1: Objective and Functional Statement Index

    **NECB 2020:**
    - 1-1: Nominal R-Values of Wall Components in Figure 1-1 (material properties)
    - 2-1: Nominal R-Values of Wall Components in Figure 2-1 (material properties)

    **All vintages:**
    - 1.3.1.2: Referenced documents or compliance forms
    - A-1.3.1.2.(1): Appendix compliance information
    - 10.1.2.1: Alternative compliance path scope
    - A-5.2.2.8.(1): Appendix economizer information
    - C-1: Compliance path summary

    **IMPORTANT**: This schema covers both administrative/organizational tables AND
    material property reference tables (thermal resistance values, R-values, etc.).
    If a table provides reference data for figures or diagrams, it belongs here.

    Available in all NECB vintages.
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(
        ...,
        description="Table identifier (e.g., '1-1', '2-1', 'C-1')"
    )
    title: str = Field(
        ...,
        description="Table title or description"
    )
    content_type: str = Field(
        ...,
        description="Type of content (e.g., 'Scope', 'Index', 'Compliance', 'Reference')"
    )
    rows: list[ReferenceTableRow] = Field(
        ...,
        min_length=1,
        description="Table content rows"
    )


# ============================================================================
# Phase 5: Generic Fallback Schema
# ============================================================================


class GenericTableRow(BaseModel):
    """Single row in a generic NECB table."""

    parameter: str = Field(
        ...,
        description="Parameter, requirement, or item name"
    )
    value: str | float | None = Field(
        None,
        description="Value (flexible type)"
    )
    units: str | None = Field(
        None,
        description="Units if applicable"
    )
    condition: str | None = Field(
        None,
        description="Applicability condition or category"
    )
    notes: str | None = None


class GenericNECBTable(BaseModel):
    """Generic schema for simple NECB tables

    Use for tables that don't fit existing specialized schemas.
    Provides flexible key-value structure for various table formats.

    Available in all NECB vintages.
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(
        ...,
        description="Table identifier"
    )
    title: str | None = Field(
        None,
        description="Table title or description"
    )
    rows: list[GenericTableRow] = Field(
        ...,
        min_length=1,
        description="Table data rows"
    )


# ============================================================================
# Phase 5: Additional Table Schemas
# ============================================================================


class HVACSystemTypeTable(BaseModel):
    """Table 5.3.1.1 - Types of HVAC Systems (NECB 2011 format, no dash)

    NECB 2011 uses table number 5.3.1.1 (no dash) while 2015/2017 use 5.3.1.1.-A.
    Both have the same structure, so this table reuses HVACSystemTypeRow.
    Only in NECB 2011 (not in 2020).
    """

    vintage: str = Field(..., pattern="^2011$")
    table_number: str = Field(
        default="5.3.1.1",
        description="Table identifier"
    )
    # Use the Phase 3 HVACSystemTypeRow class (defined earlier in this file)
    systems: list[HVACSystemTypeRow] = Field(
        ...,
        min_length=1,
        description="List of HVAC system types"
    )


class DaylightFactorRow(BaseModel):
    """Single row for daylight factor tables (4.3.2.x)"""

    category: str = Field(
        ...,
        description="Category or condition"
    )
    factor_value: float | str = Field(
        ...,
        description="Factor value"
    )
    description: str | None = Field(
        None,
        description="Additional description"
    )
    notes: str | None = None


class DaylightFactorTable(BaseModel):
    """Daylight Factor Tables (4.3.2.7.x, 4.3.2.9.x, 4.3.2.10.x)

    NECB 2011 format tables for daylight control factors.
    """

    vintage: str = Field(..., pattern="^2011$")
    table_number: str = Field(
        ...,
        pattern=r"^4\.3\.2\.(7|9|10)\.[A-B]$",
        description="Table identifier"
    )
    factor_type: str = Field(
        ...,
        description="Type of factor (e.g., 'daylight_control', 'daylight_supply')"
    )
    rows: list[DaylightFactorRow] = Field(
        ...,
        min_length=1,
        description="Factor values"
    )


class PumpPowerCoefficientTable2011(BaseModel):
    """Table 8.4.4.15 - Pump Power Coefficients (NECB 2011)

    Note: In NECB 2011, pump power coefficients are in table 8.4.4.15.
    In later vintages, this moved to a different table number.
    """

    vintage: str = Field(..., pattern="^2011$")
    table_number: str = Field(default="8.4.4.15")
    coefficients: list = Field(
        ...,
        min_length=1,
        description="Pump power coefficients"
    )


# Phase 12: Climate Design Data Table (Table C-1)
class ClimateDesignDataRow(BaseModel):
    """Row schema for climate design data tables"""

    location: str = Field(
        ...,
        description="Province and location name"
    )
    elevation_m: float | None = Field(
        None,
        description="Elevation in meters"
    )
    design_temp_jan_2_5_pct: float | None = Field(
        None,
        description="January 2.5% design temperature (°C)"
    )
    design_temp_jan_1_pct: float | None = Field(
        None,
        description="January 1% design temperature (°C)"
    )
    design_temp_july_dry: float | None = Field(
        None,
        description="July 2.5% dry bulb design temperature (°C)"
    )
    design_temp_july_wet: float | None = Field(
        None,
        description="July 2.5% wet bulb design temperature (°C)"
    )
    degree_days_below_18c: float | None = Field(
        None,
        description="Degree-days below 18°C"
    )
    degree_days_below_15c: float | None = Field(
        None,
        description="Degree-days below 15°C"
    )
    wind_pressure_1_10: float | None = Field(
        None,
        description="Hourly wind pressure 1/10 (kPa)"
    )
    wind_pressure_1_50: float | None = Field(
        None,
        description="Hourly wind pressure 1/50 (kPa)"
    )


class ClimateDesignDataTable(BaseModel):
    """Table C-1 - Climate Design Data for Canadian Locations

    Contains climate and weather parameters for design purposes:
    elevation, design temperatures, degree-days, wind pressures
    """

    vintage: str = Field(..., pattern="^(2011|2015|2017|2020)$")
    table_number: str = Field(default="C-1")
    title: str = Field(
        default="Climate Design Data for Locations in Canada",
        description="Table title"
    )
    rows: list[ClimateDesignDataRow] = Field(
        ...,
        min_length=1,
        description="Climate design data by location"
    )


# Schema registry for easy lookup
SCHEMA_REGISTRY: dict[str, type[BaseModel]] = {
    # Section 3: Building Envelope
    "3.2.2.2": EnvelopeTable,
    "3.2.2.3": EnvelopeTable,  # Fenestration uses same schema
    "3.2.2.4": EnvelopeTable,  # Doors uses same schema
    "3.2.3.1": EnvelopeTable,  # Below-grade assemblies uses same schema
    "3.2.1.4": FDWRTable,
    "A-3.2.1.4.(1)": FDWRTable,  # Appendix FDWR uses same schema as main table

    # Section 4: Lighting
    "4.2.1.3": LightingTable,
    "4.2.1.5": LightingTable,  # Building area method - same schema as 4.2.1.3
    "4.2.3.1.-A": ExteriorLightingTable,  # Lighting zones
    "4.2.3.1.-B": ExteriorLightingTable,  # Basic site allowances
    "4.2.3.1.-C": ExteriorLightingTable,  # Specific building exterior applications
    "4.2.3.1.-D": ExteriorLightingTable,  # General building exterior applications
    "4.2.3.1.-E": ExteriorLightingTable,  # Building exterior applications

    # Section 4: Daylight Control Factors
    "4.3.2.7.-A": DaylightControlTable,  # Daylight System Control Factor
    "4.3.2.7.-B": DaylightControlTable,  # Daylight-Dependent Control Factor
    "4.3.2.8": DaylightControlTable,  # Raw Daylight Supply Factors
    "4.3.2.9.-A": DaylightControlTable,  # Daylight Supply Factors for Toplighting
    "4.3.2.9.-B": DaylightControlTable,  # Utilization Factor
    "4.3.2.10.-A": DaylightControlTable,  # Factors for Relative Absence of Occupants
    "4.3.2.10.-B": DaylightControlTable,  # Factor to Account for Occupancy-Sensing

    # Section 5: HVAC Equipment - Ducts
    "5.2.2.3": DuctSealingTable,  # Duct sealing requirements
    "5.2.2.4": DuctLeakageTable,  # Leakage classes
    "5.2.2.5": DuctInsulationTable,  # Duct insulation
    "A-5.2.2.3.(1)": DuctSealingTable,
    "A-5.2.2.8.(2)": EconomizerControlTable,  # HLSO control settings

    # Section 5: HVAC Equipment - Ventilation
    "5.2.3.4": KitchenVentilationTable,  # Kitchen ventilation DCV threshold

    # Section 5: HVAC Equipment - Piping & Pumps
    "5.2.5.3": PipingInsulationTable,
    "5.2.6": EquipmentEfficiencyTable,  # Parent table alias → 5.2.6.2
    "5.2.6.2": EquipmentEfficiencyTable,
    "5.2.6.3": PumpPowerTable,  # Maximum pump power (NECB2015+)

    # Section 5: HVAC Equipment - Heat Recovery
    "5.2.10.1.-A": HeatRecoveryTable,  # Energy recovery thresholds (exhaust air)
    "5.2.10.1.-B": HeatRecoveryTable,  # Energy recovery thresholds (relief air)
    "5.2.10.4": HeatRecoveryVentilatorTable,  # HRV/ERV performance

    # Section 5: HVAC Equipment - Packaged Equipment
    "5.2.12.1": PackagedHVACTable,
    "5.2.12.1.-A": PackagedHVACTable,  # Air-cooled unitary air conditioners
    "5.2.12.1.-B": PackagedHVACTable,  # Single-package vertical units
    "5.2.12.1.-C": PackagedHVACTable,  # Water-cooled/evaporatively-cooled units
    "5.2.12.1.-D": PackagedHVACTable,  # Condensing units
    "5.2.12.1.-E": PackagedHVACTable,  # Water-source unitary heat pumps
    "5.2.12.1.-F": PackagedHVACTable,  # Direct-expansion ground-source heat pumps
    "5.2.12.1.-G": PackagedHVACTable,  # Packaged terminal air conditioners/heat pumps
    "5.2.12.1.-H": PackagedHVACTable,  # Computer room air conditioners
    "5.2.12.1.-I": PackagedHVACTable,  # Variable refrigerant flow systems
    "5.2.12.1.-J": PackagedHVACTable,  # Direct-expansion dedicated outdoor air systems
    "5.2.12.1.-K": PackagedHVACTable,  # Packaged water chillers
    "5.2.12.1.-L": PackagedHVACTable,  # Heat pumps and heat recovery chillers (air/water cooled)
    "5.2.12.1.-M": PackagedHVACTable,  # Heat pumps and heat-recovery chillers (water/ground source)
    "5.2.12.1.-N": PackagedHVACTable,  # Boilers
    "5.2.12.1.-O": PackagedHVACTable,  # Warm-air furnaces
    "5.2.12.1.-P": PackagedHVACTable,  # Other fuel-burning equipment
    "5.2.12.2": HeatRejectionEquipmentTable,  # Heat rejection equipment

    # Section 5: HVAC System Performance Coefficients (Phase 1)
    # Tables 5.3.2.8.-A through -AA (NECB 2011, 2015, 2017 only)
    "5.3.2.8.-A": HVACCoefficientTable,   # HVAC-1: Built-up Variable-Volume
    "5.3.2.8.-B": HVACCoefficientTable,   # HVAC-2: Constant-Volume Reheat
    "5.3.2.8.-C": HVACCoefficientTable,   # HVAC-3: Packaged Single Duct - Single Zone
    "5.3.2.8.-D": HVACCoefficientTable,   # HVAC-4: Built-up Single Duct - Single Zone
    "5.3.2.8.-E": HVACCoefficientTable,   # HVAC-5: Packaged Variable-Volume
    "5.3.2.8.-F": HVACCoefficientTable,   # HVAC-6: Packaged Constant-Volume with Reheat
    "5.3.2.8.-G": HVACCoefficientTable,   # HVAC-7: Built-up Ceiling Bypass VAV
    "5.3.2.8.-H": HVACCoefficientTable,   # HVAC-8: Packaged Ceiling Bypass VAV
    "5.3.2.8.-I": HVACCoefficientTable,   # HVAC-9: Powered Induction Unit
    "5.3.2.8.-J": HVACCoefficientTable,   # HVAC-10: Built-up Multi-zone System
    "5.3.2.8.-K": HVACCoefficientTable,   # HVAC-11: Packaged Multi-zone System
    "5.3.2.8.-L": HVACCoefficientTable,   # HVAC-12: Constant-Volume Dual-Duct System
    "5.3.2.8.-M": HVACCoefficientTable,   # HVAC-13: Variable-Volume Dual-Duct System
    "5.3.2.8.-N": HVACCoefficientTable,   # HVAC-14: Two-Pipe Fan Coil
    "5.3.2.8.-O": HVACCoefficientTable,   # HVAC-15: Four-Pipe Fan Coil
    "5.3.2.8.-P": HVACCoefficientTable,   # HVAC-16: Three-Pipe Fan Coil
    "5.3.2.8.-Q": HVACCoefficientTable,   # HVAC-17: Water-Loop Heat Pump
    "5.3.2.8.-R": HVACCoefficientTable,   # HVAC-18: Ground-Source Heat Pump
    "5.3.2.8.-S": HVACCoefficientTable,   # HVAC-19: Induction Unit - Two-Pipe
    "5.3.2.8.-T": HVACCoefficientTable,   # HVAC-20: Induction Unit - Four-Pipe
    "5.3.2.8.-U": HVACCoefficientTable,   # HVAC-21: Induction Unit - Three-Pipe
    "5.3.2.8.-V": HVACCoefficientTable,   # HVAC-22: Packaged Terminal AC - Split
    "5.3.2.8.-W": HVACCoefficientTable,   # HVAC-23: Radiant (In-floor, Ceiling)
    "5.3.2.8.-X": HVACCoefficientTable,   # HVAC-24: Active Chilled Beams
    "5.3.2.8.-Y": HVACCoefficientTable,   # HVAC-25: Unit Heater
    "5.3.2.8.-Z": HVACCoefficientTable,   # HVAC-26: Unit Ventilator
    "5.3.2.8.-AA": HVACCoefficientTable,  # HVAC-27: Radiation with Optional Make-up Air Unit

    # Section 5: HVAC System Types and Trade-off Tables (Phase 3)
    # NECB 2011, 2015, 2017 only (not in 2020)
    "5.3.1.1.-A": HVACSystemTypesTable,   # Types of HVAC Systems
    "5.3.2.2": TradeOffComponentFactorTable,  # Component Factors γi for Trade-off
    "5.3.2.3": ComponentFactorTable,       # Component Trade-off Values ToVi
    "5.3.2.7": TradeOffValueTable,         # Trade-off Values by HVAC System

    # Section 6: Service Water Heating
    "6.2.2.1": SWHEquipmentTable,  # SWH equipment efficiency (NECB2020)
    "6.2.3.1": ServiceWaterPipingInsulationTable,

    # Section 6: SWH System Types and Trade-off Tables (Phase 3)
    # NECB 2011, 2015, 2017 only (not in 2020)
    "6.3.1.1": SWHSystemTypesTable,        # Types of SWH System
    "6.3.2.5": ComponentFactorTable,       # SWH Component Trade-off Values

    # Section 8: Part-Load Performance Tables (Phase 3)
    # NECB 2015, 2017 (dash format)
    "8.4.4.21.-A": PartLoadPerformanceTable,  # Heating Equipment
    "8.4.4.21.-B": PartLoadPerformanceTable,  # Direct-Expansion Cooling
    "8.4.4.21.-C": PartLoadPerformanceTable,  # Electric Chiller Cooling
    "8.4.4.21.-E": PartLoadPerformanceTable,  # Electric Air-Source Heat Pump
    "8.4.4.21.-F": PartLoadPerformanceTable,  # Absorption Chiller Cooling
    "8.4.4.21.-G": PartLoadPerformanceTable,  # Fuel-Fired Service Water Heater

    # NECB 2011 (different numbering, same schemas) - Phase 6A
    "8.4.4.22.A": PartLoadPerformanceTable,  # Heating Equipment
    "8.4.4.22.B": PartLoadPerformanceTable,  # Direct-Expansion Cooling
    "8.4.4.22.C": PartLoadPerformanceTable,  # Electric Chiller Cooling
    "8.4.4.22.E": PartLoadPerformanceTable,  # Electric Air-Source Heat Pump
    "8.4.4.22.F": PartLoadPerformanceTable,  # Absorption Chiller Cooling
    "8.4.4.22.G": PartLoadPerformanceTable,  # Fuel-Fired Service Water Heater

    # Section 8: Performance Compliance - Purchased Energy
    "8.4.3.5": ChillerPerformanceTable,  # Chiller performance levels

    # Section 8: Performance Compliance - HVAC Systems
    "8.4.4.6(3)": OccupancySensorTable,  # Occupancy sensor requirements
    "8.4.4.7.-A": HVACSystemSelectionTable,  # HVAC system selection
    "8.4.4.7.-B": HVACSystemDescriptionTable,  # HVAC system descriptions
    "8.4.4.8": HVACSystemSelectionTable,  # Parent table alias → 8.4.4.8.A/B (Phase 4 fix)
    "8.4.4.8.A": HVACSystemSelectionTable,  # System selection table (Phase 4 fix)
    "8.4.4.8.B": HVACSystemSelectionTable,  # System selection table (Phase 4 fix)
    "8.4.4.12": EconomizerRequirementTable,  # Economizer requirements by system type
    "8.4.4.13": HeatPumpSystemTable,  # Heat pump system descriptions
    "8.4.4.14": PumpPowerCoefficientTable,  # Pump power coefficients (Phase 11 fix)
    "8.4.4.17": FanPowerCoefficientTable,  # Fan power calculation coefficients
    "8.4.4.18": PumpPowerCoefficientTable,  # Pump power calculation coefficients (moved from 8.4.4.14)

    # Section 8: Performance Compliance - Performance Curves
    "8.4.5.2.-A": PerformanceCoefficientTable,  # Boiler coefficients (condensing/non-condensing)
    "8.4.5.2.-B": PerformanceCoefficientTable,  # Boiler coefficients (modulating)
    "8.4.5.3": PerformanceCoefficientTable,  # Furnace coefficients
    "8.4.5.5.-A": PerformanceCoefficientTable,  # Capacity coefficients (CAP_FTEC)
    "8.4.5.5.-B": PerformanceCoefficientTable,  # Efficiency coefficients (EIR_FPLR)
    "8.4.5.5.-C": PerformanceCoefficientTable,  # Efficiency coefficients (EIR_FT)
    "8.4.5.8.-A": PerformanceCoefficientTable,  # Capacity coefficients (CAP_FTAC)
    "8.4.5.8.-B": PerformanceCoefficientTable,  # Efficiency coefficients (FIR_FPLR)
    "8.4.5.8.-C": PerformanceCoefficientTable,  # Efficiency coefficients (FIR_FT)

    # Objectives Tables (Phase 1)
    # These tables map NECB sections to National Building Code objectives
    "3.5.1.1": ObjectivesTable,   # Building Envelope objectives
    "4.5.1.1": ObjectivesTable,   # Lighting objectives
    "5.5.1.1": ObjectivesTable,   # HVAC objectives
    "6.5.1.1": ObjectivesTable,   # Service Water Heating objectives
    "7.5.1.1": ObjectivesTable,   # Electrical Power objectives
    "8.5.1.1": ObjectivesTable,   # Building Energy Performance Compliance objectives
    "10.2.1.1": ObjectivesTable,  # Alternative Compliance Path objectives

    # Schedule Tables (Phase 2)
    # Operating Schedules A-K (NECB 2015, 2017, 2020 format with dash)
    "A-8.4.3.2.(1)-A": OperatingScheduleTable,  # Schedule A: Office/Professional
    "A-8.4.3.2.(1)-B": OperatingScheduleTable,  # Schedule B: Retail
    "A-8.4.3.2.(1)-C": OperatingScheduleTable,  # Schedule C: School/University
    "A-8.4.3.2.(1)-D": OperatingScheduleTable,  # Schedule D: Hotel/Motel
    "A-8.4.3.2.(1)-E": OperatingScheduleTable,  # Schedule E: Healthcare (24-hr)
    "A-8.4.3.2.(1)-F": OperatingScheduleTable,  # Schedule F: Restaurant
    "A-8.4.3.2.(1)-G": OperatingScheduleTable,  # Schedule G: Warehouse
    "A-8.4.3.2.(1)-H": OperatingScheduleTable,  # Schedule H: Religious
    "A-8.4.3.2.(1)-I": OperatingScheduleTable,  # Schedule I: Sports/Recreation
    "A-8.4.3.2.(1)-J": OperatingScheduleTable,  # Schedule J: Manufacturing
    "A-8.4.3.2.(1)-K": OperatingScheduleTable,  # Schedule K: Multifamily Residential

    # Operating Schedules A-I (NECB 2011 format without dash)
    "A-8.4.3.2.(1)A": OperatingScheduleTable,  # Schedule A: Office/Professional
    "A-8.4.3.2.(1)B": OperatingScheduleTable,  # Schedule B: Retail
    "A-8.4.3.2.(1)C": OperatingScheduleTable,  # Schedule C: School/University
    "A-8.4.3.2.(1)D": OperatingScheduleTable,  # Schedule D: Hotel/Motel
    "A-8.4.3.2.(1)E": OperatingScheduleTable,  # Schedule E: Healthcare (24-hr)
    "A-8.4.3.2.(1)F": OperatingScheduleTable,  # Schedule F: Restaurant
    "A-8.4.3.2.(1)G": OperatingScheduleTable,  # Schedule G: Warehouse
    "A-8.4.3.2.(1)H": OperatingScheduleTable,  # Schedule H: Religious
    "A-8.4.3.2.(1)I": OperatingScheduleTable,  # Schedule I: Sports/Recreation

    # Modeling Guidance Tables (all vintages)
    "A-8.4.3.2.(2)-A": ModelingGuidanceTable,  # Default loads by building type (2015+)
    "A-8.4.3.2.(2)-B": ModelingGuidanceTable,  # Default loads by space type (2015+)
    "A-8.4.3.3.(1)A": ModelingGuidanceTable,   # Default loads by building type (2011)
    "A-8.4.3.3.(1)B": ModelingGuidanceTable,   # Default loads by space type (2011)

    # Reference and Administrative Tables (Phase 4)
    "1-1": ReferenceTable,               # Scope of Division B
    "2-1": ReferenceTable,               # Objective and Functional Statement Index
    "1.3.1.2": ReferenceTable,           # Compliance requirements
    "A-1.3.1.2.(1)": ReferenceTable,     # Appendix compliance information
    "10.1.2.1": ReferenceTable,          # Alternative compliance path scope
    "A-5.2.2.8.(1)": ReferenceTable,     # Appendix economizer information
    "C-1": ClimateDesignDataTable,       # Climate design data for Canadian locations (Phase 12)

    # =========================================================================
    # Phase 5: NECB 2011 Format Tables (no-dash variants)
    # =========================================================================

    # Section 4: Lighting - NECB 2011 format (no dash)
    "4.2.1.6": LightingControlTable,     # Lighting control requirements matrix (all vintages)
    "4.2.3.1.A": ExteriorLightingTable,  # 2011 format of 4.2.3.1.-A
    "4.2.3.1.B": ExteriorLightingTable,  # 2011 format of 4.2.3.1.-B
    "4.2.3.1.C": ExteriorLightingTable,  # 2011 format of 4.2.3.1.-C
    "4.2.3.1.D": ExteriorLightingTable,  # 2011 format of 4.2.3.1.-D

    # Section 4: Daylight Control - NECB 2011 format
    "4.3.2.7.A": DaylightFactorTable,    # Daylight system control factor
    "4.3.2.7.B": DaylightFactorTable,    # Daylight-dependent control factor
    "4.3.2.9.A": DaylightFactorTable,    # Daylight supply factors for toplighting
    "4.3.2.9.B": DaylightFactorTable,    # Utilization factor
    "4.3.2.10.A": DaylightFactorTable,   # Occupancy absence factors
    "4.3.2.10.B": DaylightFactorTable,   # Occupancy-sensing mechanism factor

    # Section 5: HVAC - NECB 2011 format
    "5.3.1.1": HVACSystemTypeTable,      # Types of HVAC Systems (2011 only)

    # Section 5: HVAC Coefficients - NECB 2011 format (no dash)
    "5.3.2.8.A": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-A
    "5.3.2.8.B": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-B
    "5.3.2.8.C": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-C
    "5.3.2.8.D": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-D
    "5.3.2.8.E": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-E
    "5.3.2.8.F": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-F
    "5.3.2.8.G": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-G
    "5.3.2.8.H": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-H
    "5.3.2.8.I": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-I
    "5.3.2.8.J": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-J
    "5.3.2.8.K": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-K
    "5.3.2.8.L": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-L
    "5.3.2.8.M": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-M
    "5.3.2.8.N": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-N
    "5.3.2.8.O": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-O
    "5.3.2.8.P": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-P
    "5.3.2.8.Q": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-Q
    "5.3.2.8.R": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-R
    "5.3.2.8.S": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-S
    "5.3.2.8.T": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-T
    "5.3.2.8.U": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-U
    "5.3.2.8.V": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-V
    "5.3.2.8.W": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-W
    "5.3.2.8.X": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-X
    "5.3.2.8.Y": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-Y
    "5.3.2.8.Z": HVACCoefficientTable,   # 2011 format of 5.3.2.8.-Z
    "5.3.2.8.AA": HVACCoefficientTable,  # 2011 format of 5.3.2.8.-AA

    # Section 8: Performance - NECB 2011 format
    "8.4.4.15": PumpPowerCoefficientTable2011,  # Pump power coefficients (2011)
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
    import re

    # Normalize table number (handle variations)
    normalized = table_number.replace("Table ", "").strip()

    # Try direct lookup first
    if normalized in SCHEMA_REGISTRY:
        return SCHEMA_REGISTRY[normalized]

    # Try without "A-" prefix for appendix tables
    if normalized.startswith("A-"):
        without_prefix = normalized.replace("A-", "")
        if without_prefix in SCHEMA_REGISTRY:
            return SCHEMA_REGISTRY[without_prefix]

    # Phase 5: Try format normalization (NECB 2011 no-dash → 2015+ dash format)
    # Convert "5.3.2.8.A" to "5.3.2.8.-A" or "4.2.3.1.B" to "4.2.3.1.-B"
    # Pattern: ends with .[letter(s)] but not already .-[letter(s)]
    dash_normalized = re.sub(r'\.([A-Z]+)$', r'.-\1', normalized)
    if dash_normalized != normalized and dash_normalized in SCHEMA_REGISTRY:
        return SCHEMA_REGISTRY[dash_normalized]

    # Try the reverse: convert "5.3.2.8.-A" to "5.3.2.8.A" (dash → no-dash)
    no_dash_normalized = re.sub(r'\.-([A-Z]+)$', r'.\1', normalized)
    if no_dash_normalized != normalized and no_dash_normalized in SCHEMA_REGISTRY:
        return SCHEMA_REGISTRY[no_dash_normalized]

    return None
