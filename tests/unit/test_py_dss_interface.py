"""Smoke tests for py-dss-interface (OpenDSS)."""

import pytest
from py_dss_interface import DSS


@pytest.fixture(scope="module")
def dss():
    """Single DSS instance shared across all tests (OpenDSS allows only one circuit per process)."""
    return DSS()


@pytest.fixture(autouse=True)
def _clear_dss(dss):
    """Clear the DSS engine before each test."""
    dss.text("clear")


@pytest.mark.unit
class TestDSSInterface:
    def test_engine_starts(self, dss):
        assert dss.started is True

    def test_version_string(self, dss):
        version = dss.dssinterface.version
        assert "Version" in version

    def test_create_circuit(self, dss):
        dss.text("New Circuit.SmokeCkt bus1=src basekv=12.47 pu=1.0")
        assert dss.circuit.name == "smokeckt"

    def test_add_line_and_load(self, dss):
        dss.text("New Circuit.LineCkt bus1=src basekv=12.47 pu=1.0")
        dss.text("New Line.Line1 bus1=src bus2=load1 length=1 units=km")
        dss.text("New Load.Load1 bus1=load1 kW=100 kvar=50")
        dss.solution.solve()
        assert dss.solution.converged == 1

    def test_bus_voltages_after_solve(self, dss):
        dss.text("New Circuit.VoltCkt bus1=src basekv=12.47 pu=1.0")
        dss.text("New Line.L1 bus1=src bus2=b2 length=0.5 units=km")
        dss.text("New Load.Ld1 bus1=b2 kW=50 kvar=20")
        dss.solution.solve()
        voltages = dss.circuit.buses_vmag_pu
        assert len(voltages) > 0
        assert all(v > 0 for v in voltages)
