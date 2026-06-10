"""Minimal TCP loopback SCPI responder for real-transport tests.

Serves a canned command -> response byte table over a genuine OS socket.
Deliberately holds no instrument state and implements no SCPI logic beyond
splitting the incoming byte stream on a terminator, so tests verify the
transport layer (framing, terminators, timeouts) rather than a re-implemented
instrument spec.
"""

import socket
import threading


class ScpiLoopbackServer:
    """A single-client TCP server answering from a fixed byte table.

    Commands not present in the table receive no response, which lets tests
    exercise client-side timeout behaviour.
    """

    def __init__(
        self,
        responses: dict[bytes, bytes],
        command_termination: bytes = b"\n",
        response_termination: bytes = b"\n",
    ):
        """
        Initialize the server (does not start listening).

        Args:
            responses: Map of command (without terminator) to response
                payload (without terminator)
            command_termination: Delimiter used to split incoming bytes
            response_termination: Bytes appended to every outgoing response
        """
        self._responses = responses
        self._command_termination = command_termination
        self._response_termination = response_termination
        self._listen_socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._received = bytearray()
        self._commands: list[bytes] = []

    @property
    def port(self) -> int:
        """Port the server is listening on."""
        if self._listen_socket is None:
            raise RuntimeError("Server not started")
        port: int = self._listen_socket.getsockname()[1]
        return port

    @property
    def resource_address(self) -> str:
        """VISA resource address for connecting to this server."""
        return f"TCPIP0::127.0.0.1::{self.port}::SOCKET"

    def received_bytes(self) -> bytes:
        """All raw bytes received so far, in order."""
        with self._lock:
            return bytes(self._received)

    def received_commands(self) -> list[bytes]:
        """Parsed commands (terminators stripped) in arrival order."""
        with self._lock:
            return list(self._commands)

    def start(self) -> None:
        """Bind to an ephemeral loopback port and start serving."""
        if self._listen_socket is not None:
            raise RuntimeError("Server already started")
        self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_socket.bind(("127.0.0.1", 0))
        self._listen_socket.listen(1)
        self._listen_socket.settimeout(0.2)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop serving and release the socket."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._listen_socket is not None:
            self._listen_socket.close()
            self._listen_socket = None

    def __enter__(self) -> "ScpiLoopbackServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def _serve(self) -> None:
        assert self._listen_socket is not None
        while not self._stop_event.is_set():
            try:
                client, _ = self._listen_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with client:
                self._handle_client(client)

    def _handle_client(self, client: socket.socket) -> None:
        client.settimeout(0.2)
        buffer = bytearray()
        while not self._stop_event.is_set():
            try:
                chunk = client.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                return
            if not chunk:
                return
            with self._lock:
                self._received.extend(chunk)
            buffer.extend(chunk)
            while self._command_termination in buffer:
                command, _, rest = bytes(buffer).partition(self._command_termination)
                buffer = bytearray(rest)
                with self._lock:
                    self._commands.append(command)
                response = self._responses.get(command)
                if response is not None:
                    try:
                        client.sendall(response + self._response_termination)
                    except OSError:
                        return
