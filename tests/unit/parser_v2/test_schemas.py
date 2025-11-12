"""Tests for NECB Pydantic schemas"""

import pytest
from pydantic import ValidationError

from bluesky.mcp.scrapers.necb.parser_v2.schemas import (
    AssemblyRequirement,
    EnvelopeTable,
    FDWRRequirement,
    FDWRTable,
    HVACEquipmentPerformance,
    HVACTable,
    LightingPowerDensity,
    LightingTable,
    get_schema_for_table,
)


def test_assembly_requirement_valid():
    """Test valid assembly requirement"""
    assembly = AssemblyRequirement(
        assembly_type="Walls",
        zone_4_max_u=0.315,
        zone_5_max_u=0.278,
        zone_6_max_u=0.247,
        zone_7a_max_u=0.210,
        zone_7b_max_u=0.210,
        zone_8_max_u=0.183,
    )

    assert assembly.assembly_type == "Walls"
    assert assembly.zone_4_max_u == 0.315
    assert assembly.zone_8_max_u == 0.183


def test_assembly_requirement_invalid_type():
    """Test invalid assembly type"""
    with pytest.raises(ValidationError) as exc_info:
        AssemblyRequirement(
            assembly_type="InvalidType",
            zone_4_max_u=0.315,
            zone_5_max_u=0.278,
            zone_6_max_u=0.247,
            zone_7a_max_u=0.210,
            zone_7b_max_u=0.210,
            zone_8_max_u=0.183,
        )

    assert "assembly_type" in str(exc_info.value)


def test_assembly_requirement_invalid_uvalue():
    """Test U-value out of range"""
    with pytest.raises(ValidationError) as exc_info:
        AssemblyRequirement(
            assembly_type="Walls",
            zone_4_max_u=5.0,  # Too high
            zone_5_max_u=0.278,
            zone_6_max_u=0.247,
            zone_7a_max_u=0.210,
            zone_7b_max_u=0.210,
            zone_8_max_u=0.183,
        )

    assert "zone_4_max_u" in str(exc_info.value)


def test_envelope_table_valid():
    """Test valid envelope table (Table 3.2.2.2)"""
    table = EnvelopeTable(
        vintage="2020",
        table_number="3.2.2.2",
        assemblies=[
            AssemblyRequirement(
                assembly_type="Walls",
                zone_4_max_u=0.315,
                zone_5_max_u=0.278,
                zone_6_max_u=0.247,
                zone_7a_max_u=0.210,
                zone_7b_max_u=0.210,
                zone_8_max_u=0.183,
            ),
            AssemblyRequirement(
                assembly_type="Roofs",
                zone_4_max_u=0.193,
                zone_5_max_u=0.156,
                zone_6_max_u=0.156,
                zone_7a_max_u=0.138,
                zone_7b_max_u=0.138,
                zone_8_max_u=0.121,
            ),
            AssemblyRequirement(
                assembly_type="Floors",
                zone_4_max_u=0.227,
                zone_5_max_u=0.183,
                zone_6_max_u=0.183,
                zone_7a_max_u=0.162,
                zone_7b_max_u=0.162,
                zone_8_max_u=0.142,
            ),
        ],
    )

    assert table.vintage == "2020"
    assert table.table_number == "3.2.2.2"
    assert len(table.assemblies) == 3
    assert table.assemblies[0].assembly_type == "Walls"


def test_envelope_table_missing_assemblies():
    """Test envelope table with insufficient assemblies"""
    with pytest.raises(ValidationError) as exc_info:
        EnvelopeTable(
            vintage="2020",
            table_number="3.2.2.2",
            assemblies=[
                AssemblyRequirement(
                    assembly_type="Walls",
                    zone_4_max_u=0.315,
                    zone_5_max_u=0.278,
                    zone_6_max_u=0.247,
                    zone_7a_max_u=0.210,
                    zone_7b_max_u=0.210,
                    zone_8_max_u=0.183,
                )
            ],  # Only 1 assembly, need at least 3
        )

    assert "assemblies" in str(exc_info.value)


def test_fdwr_requirement_valid():
    """Test valid FDWR requirement"""
    req = FDWRRequirement(hdd_min=0, hdd_max=4000, max_fdwr=0.40)

    assert req.hdd_min == 0
    assert req.hdd_max == 4000
    assert req.max_fdwr == 0.40


def test_fdwr_table_valid():
    """Test valid FDWR table"""
    table = FDWRTable(
        vintage="2020",
        requirements=[
            FDWRRequirement(hdd_min=0, hdd_max=4000, max_fdwr=0.40),
            FDWRRequirement(hdd_min=4000, hdd_max=5000, max_fdwr=0.33),
            FDWRRequirement(hdd_min=5000, hdd_max=None, max_fdwr=0.27),  # Open-ended
        ],
    )

    assert table.vintage == "2020"
    assert len(table.requirements) == 3
    assert table.requirements[2].hdd_max is None  # Open-ended range


def test_hvac_equipment_valid():
    """Test valid HVAC equipment performance"""
    equipment = HVACEquipmentPerformance(
        equipment_type="Heat Pump",
        capacity_min=0.0,
        capacity_max=10.0,
        performance_metric="COP",
        minimum_value=3.5,
    )

    assert equipment.equipment_type == "Heat Pump"
    assert equipment.performance_metric == "COP"
    assert equipment.minimum_value == 3.5


def test_lighting_power_density_valid():
    """Test valid lighting power density"""
    lpd = LightingPowerDensity(
        building_type="Office", space_type="Open Office", max_lpd=10.5
    )

    assert lpd.building_type == "Office"
    assert lpd.space_type == "Open Office"
    assert lpd.max_lpd == 10.5


def test_schema_registry():
    """Test schema registry lookup"""
    schema = get_schema_for_table("3.2.2.2")
    assert schema == EnvelopeTable

    schema = get_schema_for_table("8.4.4.8.A")
    assert schema == HVACTable

    schema = get_schema_for_table("4.2.1.3")
    assert schema == LightingTable

    # Non-existent table
    schema = get_schema_for_table("99.99.99")
    assert schema is None


def test_schema_registry_normalization():
    """Test schema registry handles variations in table numbers"""
    # With "Table " prefix
    schema = get_schema_for_table("Table 3.2.2.2")
    assert schema == EnvelopeTable

    # Appendix A table (should strip A- prefix)
    schema = get_schema_for_table("A-3.2.1.4")
    assert schema == FDWRTable


def test_envelope_table_json_serialization():
    """Test that envelope table can be serialized to JSON"""
    table = EnvelopeTable(
        vintage="2011",
        table_number="3.2.2.2",
        assemblies=[
            AssemblyRequirement(
                assembly_type="Walls",
                zone_4_max_u=0.315,
                zone_5_max_u=0.278,
                zone_6_max_u=0.247,
                zone_7a_max_u=0.210,
                zone_7b_max_u=0.210,
                zone_8_max_u=0.183,
            ),
            AssemblyRequirement(
                assembly_type="Roofs",
                zone_4_max_u=0.227,
                zone_5_max_u=0.183,
                zone_6_max_u=0.183,
                zone_7a_max_u=0.162,
                zone_7b_max_u=0.162,
                zone_8_max_u=0.142,
            ),
            AssemblyRequirement(
                assembly_type="Floors",
                zone_4_max_u=0.227,
                zone_5_max_u=0.183,
                zone_6_max_u=0.183,
                zone_7a_max_u=0.162,
                zone_7b_max_u=0.162,
                zone_8_max_u=0.142,
            ),
        ],
    )

    # Test JSON serialization
    json_str = table.model_dump_json()
    assert '"vintage":"2011"' in json_str
    assert '"table_number":"3.2.2.2"' in json_str
    assert '"assembly_type":"Walls"' in json_str

    # Test deserialization
    table2 = EnvelopeTable.model_validate_json(json_str)
    assert table2.vintage == table.vintage
    assert len(table2.assemblies) == len(table.assemblies)
