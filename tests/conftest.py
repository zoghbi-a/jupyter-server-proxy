"""Reusable test fixtures for ``jupyter_server_proxy``."""
import socket
import sys
import os
from pytest import fixture
from subprocess import Popen
from typing import Generator, Any, Tuple
from pathlib import Path
from uuid import uuid4
from urllib.error import URLError
import time
from urllib.request import urlopen
import shutil

HERE = Path(__file__).parent
RESOURCES = HERE / "resources"

@fixture
def a_token() -> str:
    """Get a random UUID to use for a token."""
    return str(uuid4())


@fixture
def an_unused_port() -> int:
    """Get a random unused port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


@fixture(params=["notebook", "lab"])
def a_server_cmd(request: Any) -> str:
    """Get a viable name for a command."""
    return request.param


@fixture
def a_server(
    a_server_cmd: str,
    tmp_path: Path,
    an_unused_port: int,
    a_token: str,
) -> Generator[str, None, None]:
    """Get a running server."""
    # get a copy of the resources
    tests = tmp_path / "tests"
    tests.mkdir()
    shutil.copytree(RESOURCES, tests / "resources")
    args = [
        sys.executable,
        "-m",
        "jupyter",
        a_server_cmd,
        f"--port={an_unused_port}",
        "--no-browser",
        "--config=./tests/resources/jupyter_server_config.py",
        "--debug",
    ]

    # prepare an env
    env = dict(os.environ)
    env.update(JUPYTER_TOKEN=a_token)

    # start the process
    server_proc = Popen(args, cwd=str(tmp_path), env=env)

    # prepare some URLss
    url = f"http://127.0.0.1:{an_unused_port}/"
    canary_url = f"{url}favicon.ico"
    shutdown_url = f"{url}api/shutdown?token={a_token}"

    retries = 10

    while retries:
        try:
            urlopen(canary_url)
            break
        except URLError as err:
            if "Connection refused" in str(err):
                print(
                    f"{a_server_cmd} not ready, will try again in 0.5s [{retries} retries]",
                    flush=True,
                )
                time.sleep(0.5)
                retries -= 1
                continue
            raise err

    print(f"{a_server_cmd} is ready...", flush=True)

    yield url

    # clean up after server is no longer needed
    print(f"{a_server_cmd} shutting down...", flush=True)
    urlopen(shutdown_url, data=[])
    server_proc.wait()
    print(f"{a_server_cmd} is stopped", flush=True)


@fixture
def a_server_port_and_token(
    a_server: str,  # noqa
    an_unused_port: int,
    a_token: str,
) -> Tuple[int, str]:
    """Get the port and token for a running server."""
    return an_unused_port, a_token
