"""VISA connection management."""

import logging
from pathlib import Path

import pyvisa

logger = logging.getLogger(__name__)


class VISAConnection:
    """
    Manages VISA resource manager and resource discovery.

    Supports both real VISA backends and PyVISA-sim for simulation.
    """

    def __init__(
        self, simulation_mode: bool = False, simulation_file: str | Path | None = None
    ):
        """
        Initialize VISA connection manager.

        Args:
            simulation_mode: If True, use PyVISA-sim backend
            simulation_file: Path to simulation YAML file (required if simulation_mode is True)
        """
        self._simulation_mode = simulation_mode
        self._simulation_file = simulation_file
        self._resource_manager: pyvisa.ResourceManager | None = None

    @property
    def is_open(self) -> bool:
        """Check if resource manager is open."""
        return self._resource_manager is not None

    def open(self) -> None:
        """
        Open the VISA resource manager.

        Uses the simulation backend if simulation_mode is True.
        """
        if self._resource_manager is not None:
            logger.warning("Resource manager already open")
            return

        if self._simulation_mode:
            if self._simulation_file is None:
                raise ValueError(
                    "simulation_file required when simulation_mode is True"
                )

            sim_path = Path(self._simulation_file)
            if not sim_path.is_absolute():
                # Make relative to package root
                sim_path = Path(__file__).parent.parent / sim_path

            if not sim_path.exists():
                raise FileNotFoundError(f"Simulation file not found: {sim_path}")

            backend = f"{sim_path}@sim"
            logger.info(
                "Opening VISA resource manager with simulation backend: %s", sim_path
            )
        else:
            backend = ""
            logger.info("Opening VISA resource manager with default backend")

        self._resource_manager = pyvisa.ResourceManager(backend)
        logger.info("VISA resource manager opened successfully")

    def close(self) -> None:
        """Close the VISA resource manager."""
        if self._resource_manager is not None:
            self._resource_manager.close()
            self._resource_manager = None
            logger.info("VISA resource manager closed")

    def list_resources(self, query: str = "?*::INSTR") -> tuple[str, ...]:
        """
        List available VISA resources.

        Args:
            query: VISA resource query string

        Returns:
            Tuple of resource address strings
        """
        if self._resource_manager is None:
            raise RuntimeError("Resource manager not open. Call open() first.")

        resources = self._resource_manager.list_resources(query)
        logger.debug(
            "Found %d resources matching '%s': %s", len(resources), query, resources
        )
        return resources

    def open_resource(
        self,
        resource_address: str,
        timeout_ms: int = 5000,
        read_termination: str | None = "\n",
        write_termination: str | None = "\n",
    ) -> pyvisa.resources.MessageBasedResource:
        """
        Open a VISA resource.

        Args:
            resource_address: VISA resource address string
            timeout_ms: Communication timeout in milliseconds
            read_termination: Character(s) appended to reads, or None for no termination
            write_termination: Character(s) appended to writes, or None for no termination

        Returns:
            Opened VISA resource
        """
        if self._resource_manager is None:
            raise RuntimeError("Resource manager not open. Call open() first.")

        logger.info("Opening resource: %s (timeout=%dms)", resource_address, timeout_ms)
        resource = self._resource_manager.open_resource(resource_address)
        # Type assertion: INSTR resources are always MessageBasedResource
        if not isinstance(resource, pyvisa.resources.MessageBasedResource):
            resource.close()
            raise TypeError(f"Expected MessageBasedResource, got {type(resource)}")
        resource.timeout = timeout_ms
        if read_termination is not None:
            resource.read_termination = read_termination
        if write_termination is not None:
            resource.write_termination = write_termination
        return resource

    def __enter__(self) -> "VISAConnection":
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
