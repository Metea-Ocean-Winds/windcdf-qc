"""Tests for QC engine."""

import pytest


class TestQCEngine:
    """Test suite for QCEngine."""

    def test_engine_initialization(self):
        """Test engine can be initialized."""
        from windcdf.qc.engine import QCEngine

        engine = QCEngine()
        assert engine is not None
        assert len(engine.registry) > 0

    def test_run_all_checks(self, sample_dataset):
        """Test running all checks."""
        from windcdf.qc.engine import QCEngine

        engine = QCEngine()
        report = engine.run(sample_dataset)

        assert report is not None
        assert "wind_speed" in report.variables_checked
        assert "wind_direction" in report.variables_checked

    def test_run_specific_checks(self, sample_dataset):
        """Test running specific checks."""
        from windcdf.qc.engine import QCEngine

        engine = QCEngine()
        report = engine.run(
            sample_dataset,
            checks=["range_check"],
        )

        assert report is not None
        assert "range_check" in report.checks_run
        assert len(report.checks_run) == 1
