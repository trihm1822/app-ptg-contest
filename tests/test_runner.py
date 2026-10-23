"""Integration tests for the Isolated C++ Runner."""

import shutil
import tempfile
from pathlib import Path
import pytest

from ptg.core.runner import IsolatedRunner
from ptg.models.runner import SandboxLimits, Verdict


@pytest.fixture(scope="module")
def runner():
    """Shared runner instance using the built Docker image."""
    return IsolatedRunner(image_name="ptg-cpp-runner:latest")


@pytest.fixture
def temp_workspace():
    """Per-test temporary directory within ./temp/ for Docker mounting."""
    workspace = Path(tempfile.mkdtemp(prefix="ptg_test_", dir="temp"))
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


def test_compile_and_run_success(runner, temp_workspace):
    """Test compiling and executing a normal C++17 program."""
    cpp_code = """
    #include <iostream>
    int main() {
        int a, b;
        if (std::cin >> a >> b) {
            std::cout << (a + b) << std::endl;
        }
        return 0;
    }
    """
    compile_res = runner.compile(cpp_code, binary_name="adder", workspace_dir=temp_workspace)
    assert compile_res.success is True
    assert compile_res.exit_code == 0

    exec_res = runner.execute("adder", workspace_dir=temp_workspace, stdin_data="15 27\n")
    assert exec_res.verdict == Verdict.OK
    assert exec_res.exit_code == 0
    assert exec_res.stdout.strip() == "42"


def test_compile_error(runner, temp_workspace):
    """Test that C++ syntax error is correctly captured."""
    invalid_cpp = """
    #include <iostream>
    int main() {
        this_is_an_invalid_syntax;;;
        return 0;
    }
    """
    compile_res = runner.compile(invalid_cpp, binary_name="bad_syntax", workspace_dir=temp_workspace)
    assert compile_res.success is False
    assert compile_res.exit_code != 0
    assert "error:" in compile_res.stderr


def test_runtime_error(runner, temp_workspace):
    """Test that runtime crash (non-zero exit) is reported as RUNTIME_ERROR."""
    crash_cpp = """
    #include <iostream>
    int main() {
        return 42; // non-zero exit
    }
    """
    compile_res = runner.compile(crash_cpp, binary_name="crasher", workspace_dir=temp_workspace)
    assert compile_res.success is True

    exec_res = runner.execute("crasher", workspace_dir=temp_workspace)
    assert exec_res.verdict == Verdict.RUNTIME_ERROR
    assert exec_res.exit_code == 42


def test_time_limit_exceeded(runner, temp_workspace):
    """Test that infinite loop is killed and marked TIME_LIMIT_EXCEEDED."""
    loop_cpp = """
    #include <iostream>
    int main() {
        volatile long long sum = 0;
        while (true) {
            sum++;
        }
        return 0;
    }
    """
    compile_res = runner.compile(loop_cpp, binary_name="infinite_loop", workspace_dir=temp_workspace)
    assert compile_res.success is True

    # Run with a short 2-second timeout
    exec_res = runner.execute("infinite_loop", workspace_dir=temp_workspace, custom_timeout_sec=2)
    assert exec_res.verdict == Verdict.TIME_LIMIT_EXCEEDED
    assert exec_res.exit_code == 137


def test_security_network_isolated(runner, temp_workspace):
    """Test that container cannot open external network connections (--network=none)."""
    network_cpp = """
    #include <iostream>
    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <unistd.h>

    int main() {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) {
            std::cout << "SOCKET_FAILED" << std::endl;
            return 1;
        }
        sockaddr_in serv_addr;
        serv_addr.sin_family = AF_INET;
        serv_addr.sin_port = htons(80);
        inet_pton(AF_INET, "8.8.8.8", &serv_addr.sin_addr);

        if (connect(sock, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
            std::cout << "CONNECT_REJECTED" << std::endl;
            close(sock);
            return 0; // expected: connection blocked
        }
        std::cout << "CONNECT_SUCCESS" << std::endl;
        close(sock);
        return 2;
    }
    """
    compile_res = runner.compile(network_cpp, binary_name="net_test", workspace_dir=temp_workspace)
    assert compile_res.success is True

    exec_res = runner.execute("net_test", workspace_dir=temp_workspace, custom_timeout_sec=3)
    assert exec_res.verdict == Verdict.OK
    assert "CONNECT_REJECTED" in exec_res.stdout


def test_security_readonly_filesystem(runner, temp_workspace):
    """Test that container cannot write to system directories (--read-only)."""
    write_cpp = """
    #include <iostream>
    #include <fstream>

    int main() {
        std::ofstream file("/etc/malicious_file.txt");
        if (!file.is_open()) {
            std::cout << "WRITE_BLOCKED" << std::endl;
            return 0; // expected: read-only rootfs prevents writing
        }
        file << "pwned";
        file.close();
        std::cout << "WRITE_SUCCESS" << std::endl;
        return 1;
    }
    """
    compile_res = runner.compile(write_cpp, binary_name="fs_test", workspace_dir=temp_workspace)
    assert compile_res.success is True

    exec_res = runner.execute("fs_test", workspace_dir=temp_workspace, custom_timeout_sec=3)
    assert exec_res.verdict == Verdict.OK
    assert "WRITE_BLOCKED" in exec_res.stdout
