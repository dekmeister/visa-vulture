"""Test results CSV writer."""

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result from a single test step."""

    step_number: int
    timestamp: datetime
    target_voltage: float
    target_current: float
    measured_voltage: float
    measured_current: float
    status: str = "OK"
    message: str = ""


@dataclass
class TestResults:
    """Collection of test results."""

    test_name: str
    start_time: datetime
    results: list[TestResult] = field(default_factory=list)
    end_time: datetime | None = None
    success: bool = True
    error_message: str = ""

    def add_result(self, result: TestResult) -> None:
        """Add a step result."""
        self.results.append(result)

    def complete(self, success: bool = True, error_message: str = "") -> None:
        """Mark test as complete."""
        self.end_time = datetime.now()
        self.success = success
        self.error_message = error_message


def write_results(
    results: TestResults,
    output_dir: str | Path = ".",
) -> tuple[Path | None, list[str]]:
    """
    Write test results to a CSV file.

    Creates a file named: {test_name}_{timestamp}.csv

    Args:
        results: TestResults to write
        output_dir: Directory for output file

    Returns:
        Tuple of (output file path or None, list of error messages)
    """
    errors: list[str] = []
    output_dir = Path(output_dir)

    # Ensure output directory exists
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        errors.append(f"Cannot create output directory: {e}")
        return None, errors

    # Generate filename
    timestamp_str = results.start_time.strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "_" for c in results.test_name
    )
    filename = f"{safe_name}_{timestamp_str}.csv"
    output_path = output_dir / filename

    # Write CSV
    try:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)

            # Write header comment
            writer.writerow([f"# Test: {results.test_name}"])
            writer.writerow([f"# Started: {results.start_time.isoformat()}"])
            if results.end_time:
                writer.writerow([f"# Ended: {results.end_time.isoformat()}"])
            writer.writerow([f"# Success: {results.success}"])
            if results.error_message:
                writer.writerow([f"# Error: {results.error_message}"])
            writer.writerow([])

            # Write data header
            writer.writerow(
                [
                    "step",
                    "timestamp",
                    "target_voltage",
                    "target_current",
                    "measured_voltage",
                    "measured_current",
                    "status",
                    "message",
                ]
            )

            # Write data rows
            for result in results.results:
                writer.writerow(
                    [
                        result.step_number,
                        result.timestamp.isoformat(),
                        f"{result.target_voltage:.6f}",
                        f"{result.target_current:.6f}",
                        f"{result.measured_voltage:.6f}",
                        f"{result.measured_current:.6f}",
                        result.status,
                        result.message,
                    ]
                )

    except OSError as e:
        errors.append(f"Error writing results file: {e}")
        return None, errors

    logger.info("Results written to %s", output_path)
    return output_path, []
