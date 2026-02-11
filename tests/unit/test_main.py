"""Tests for main module helper functions."""

from visa_vulture.main import validate_visa_backend


class TestValidateVisaBackend:
    """Tests for validate_visa_backend function."""

    def test_invalid_backend_returns_error(self) -> None:
        """Invalid backend name returns error message."""
        result = validate_visa_backend("nonexistent_backend")
        assert result is not None
        assert "nonexistent_backend" in result
        assert "Available backends" in result

    def test_valid_sim_backend_returns_none(self) -> None:
        """'sim' backend is valid (pyvisa-sim is installed)."""
        result = validate_visa_backend("sim")
        assert result is None

    def test_valid_ivi_backend_returns_none(self) -> None:
        """'ivi' backend is always valid (built-in)."""
        result = validate_visa_backend("ivi")
        assert result is None
