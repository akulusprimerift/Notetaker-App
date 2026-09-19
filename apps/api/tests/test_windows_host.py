import socket
import sys

import pytest

from notetaker.config import Settings
from notetaker.windows_host import require_free_ports


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows exclusive socket semantics')
def test_native_host_refuses_an_occupied_port_without_touching_listener():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(RuntimeError, match='in use'):
            require_free_ports([port])
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            assert listener.fileno() != -1


def test_native_brokerless_profile_retains_postgres_and_private_object_store():
    settings = Settings(_env_file=None, broker_enabled=False, database_url='postgresql+psycopg://test:test@127.0.0.1:55432/postgres')
    assert not settings.broker_enabled
    assert not settings.preview and not settings.standalone
    assert Settings(_env_file=None).broker_enabled
