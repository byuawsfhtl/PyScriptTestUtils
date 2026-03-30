import json
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from unittest.mock import patch


@dataclass(frozen=True)
class RegisteredMethod:
    py_fn: Callable[[Any], Any]
    ts_name: str
    ts_pack_input: bool = False


class PyScriptTestRunner:
    """Dual-language test runner: register Python callables and matching TS RPC names."""

    _environment_initialized = False
    _setup_lock = threading.Lock()

    def __init__(
        self,
        ts_bridge_path: Optional[Path] = None,
        package_root: Optional[Path] = None,
    ) -> None:
        assert ts_bridge_path is None or isinstance(ts_bridge_path, Path)
        assert package_root is None or isinstance(package_root, Path)

        self.package_root = (
            package_root if package_root is not None else Path(__file__).resolve().parent
        )
        self.ts_bridge_path = (
            ts_bridge_path
            if ts_bridge_path is not None
            else self.package_root / "dist" / "test_bridge_entry.js"
        )
        self._by_py: Dict[str, RegisteredMethod] = {}
        self._by_ts: Dict[str, RegisteredMethod] = {}

        with PyScriptTestRunner._setup_lock:
            if not PyScriptTestRunner._environment_initialized:
                self._setup_environment()
                PyScriptTestRunner._environment_initialized = True

    def add_method(
        self,
        py_callable: Callable[[Any], Any],
        ts_method_name: str,
        *,
        ts_pack_input: bool = False,
    ) -> None:
        assert callable(py_callable)
        if not ts_method_name or not str(ts_method_name).strip():
            raise ValueError("ts_method_name must be non-empty")
        py_key = getattr(py_callable, "__name__", None)
        if not py_key or py_key == "<lambda>":
            raise ValueError("py_callable must be a named function (not lambda or <lambda>)")

        if py_key in self._by_py:
            raise ValueError(f"Duplicate Python registration: {py_key!r}")
        if ts_method_name in self._by_ts:
            raise ValueError(f"Duplicate TypeScript registration: {ts_method_name!r}")

        rec = RegisteredMethod(
            py_fn=py_callable, ts_name=ts_method_name, ts_pack_input=ts_pack_input
        )
        self._by_py[py_key] = rec
        self._by_ts[ts_method_name] = rec

    def run(
        self,
        python_function_name: str,
        ts_function_name: str,
        test_data: Dict[str, Any],
    ) -> tuple[Any, Any]:
        return self.run_dual_test(python_function_name, ts_function_name, test_data)

    def run_dual_test(
        self, python_function: str, ts_function: str, test_data: Dict[str, Any]
    ) -> tuple[Any, Any]:
        rec = self._by_py.get(python_function)
        if rec is None:
            raise ValueError(f"Unknown Python function: {python_function!r}")
        if rec.ts_name != ts_function:
            raise ValueError(
                f"TypeScript name mismatch for {python_function!r}: "
                f"expected {rec.ts_name!r}, got {ts_function!r}"
            )

        input_data = test_data["input"]
        mocks = test_data.get("mocks", {})
        expected_error = test_data.get("expected_error", False)

        py_result_holder: Dict[str, Any] = {}
        ts_result_holder: Dict[str, Any] = {}

        def run_python() -> None:
            py_result_holder["result"] = self._call_python_function_with_mocks(
                python_function, input_data, mocks.get("python", {}), expected_error
            )

        def run_typescript() -> None:
            ts_result_holder["result"] = self._call_typescript_function_with_mocks(
                ts_function, input_data, mocks.get("typescript", {}), expected_error
            )

        t_py = threading.Thread(target=run_python)
        t_ts = threading.Thread(target=run_typescript)
        t_py.start()
        t_ts.start()
        t_py.join()
        t_ts.join()

        py_result = py_result_holder.get("result")
        ts_result = ts_result_holder.get("result")

        return py_result, ts_result

    def _setup_environment(self) -> None:
        print("Setting up dual-language testing environment...")

        if not self.ts_bridge_path.exists():
            if not self._check_nodejs():
                raise EnvironmentError(
                    "Node.js not found and TypeScript bridge not compiled. "
                    "Install Node.js to run dual-language tests.\n"
                    "Download from: https://nodejs.org/"
                )
            self._compile_typescript()
        else:
            print("TypeScript bridge found, skipping compilation.")

        print("Environment setup complete.")

    def _check_nodejs(self) -> bool:
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _compile_typescript(self) -> None:
        ts_dir = self.package_root
        try:
            print("Installing TypeScript dependencies...")
            result = subprocess.run(
                ["npm", "ci"], cwd=str(ts_dir), capture_output=True, text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to install npm dependencies: {result.stderr}")

            print("Compiling TypeScript...")
            result = subprocess.run(
                ["npm", "run", "build"], cwd=str(ts_dir), capture_output=True, text=True
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to compile TypeScript: {result.stderr}")

        except FileNotFoundError as exc:
            raise EnvironmentError(
                "npm command not found. Ensure Node.js and npm are installed and on PATH.\n"
                "Download from: https://nodejs.org/\n"
                "After installation, restart your terminal/IDE and try again."
            ) from exc

    def _call_python_function_with_mocks(
        self,
        function_name: str,
        input_data: Any,
        mocks: Dict[str, Any],
        expected_error: bool = False,
    ) -> Any:
        rec = self._by_py.get(function_name)
        if rec is None:
            raise ValueError(f"Unknown Python function: {function_name!r}")

        try:
            mock_contexts = []
            for mock_target, mock_value in mocks.items():
                mock_contexts.append(patch(mock_target, return_value=mock_value))

            for mock_context in mock_contexts:
                mock_context.__enter__()

            try:
                return rec.py_fn(input_data)
            finally:
                for mock_context in reversed(mock_contexts):
                    mock_context.__exit__(None, None, None)

        except Exception as e:
            if expected_error:
                return {"error": True, "error_type": type(e).__name__, "error_message": str(e)}
            raise RuntimeError(f"Python function {function_name} failed: {str(e)}") from e

    def _call_typescript_function_with_mocks(
        self,
        function_name: str,
        input_data: Any,
        mocks: Dict[str, Any],
        expected_error: bool = False,
    ) -> Any:
        rec = self._by_ts.get(function_name)
        if rec is None:
            raise ValueError(f"Unknown TypeScript function: {function_name!r}")

        try:
            if rec.ts_pack_input:
                args = [input_data]
            else:
                args = [input_data] if not isinstance(input_data, list) else input_data

            request = {"method": function_name, "args": args, "mocks": mocks}

            result = subprocess.run(
                ["node", str(self.ts_bridge_path), json.dumps(request)],
                capture_output=True,
                text=True,
                cwd=str(self.package_root),
            )

            if result.stderr:
                print("=== TypeScript Debug Output ===")
                print(result.stderr)
                print("================================")

            if result.returncode != 0:
                raise RuntimeError(f"TypeScript bridge failed: {result.stderr}")

            response = json.loads(result.stdout)

            if not response.get("success", False):
                if expected_error:
                    return {
                        "error": True,
                        "error_type": "Error",
                        "error_message": response.get("error", "Unknown error"),
                    }
                raise RuntimeError(
                    f"TypeScript function failed: {response.get('error', 'Unknown error')}"
                )

            return response["result"]

        except json.JSONDecodeError as e:
            if expected_error:
                return {"error": True, "error_type": "JSONDecodeError", "error_message": str(e)}
            raise RuntimeError(f"Failed to parse TypeScript response: {str(e)}") from e
        except Exception as e:
            if expected_error:
                return {"error": True, "error_type": type(e).__name__, "error_message": str(e)}
            raise RuntimeError(f"TypeScript function {function_name} failed: {str(e)}") from e

    def compare_results(self, py_result: Any, ts_result: Any) -> bool:
        if isinstance(py_result, dict) and isinstance(ts_result, dict):
            if py_result.get("error") is True and ts_result.get("error") is True:
                return True

        if py_result != ts_result:
            return False

        if type(py_result) != type(ts_result):
            return False

        if isinstance(py_result, dict) and isinstance(ts_result, dict):
            if set(py_result.keys()) != set(ts_result.keys()):
                return False

            for key in py_result.keys():
                py_value = py_result[key]
                ts_value = ts_result[key]

                if type(py_value) != type(ts_value):
                    return False

                if isinstance(py_value, dict) and isinstance(ts_value, dict):
                    if not self.compare_results(py_value, ts_value):
                        return False

        elif isinstance(py_result, list) and isinstance(ts_result, list):
            if len(py_result) != len(ts_result):
                return False

            for py_item, ts_item in zip(py_result, ts_result):
                if not self.compare_results(py_item, ts_item):
                    return False

        return True

    def assert_strict_parity(self, py_result: Any, ts_result: Any, context: str = "") -> None:
        if not self.compare_results(py_result, ts_result):
            error_details = []

            if py_result != ts_result:
                error_details.append(f"Value mismatch: Python={py_result}, TypeScript={ts_result}")

            if type(py_result) != type(ts_result):
                error_details.append(
                    f"Type mismatch: Python={type(py_result).__name__}, "
                    f"TypeScript={type(ts_result).__name__}"
                )
                error_details.append(f"Python value: {py_result}, TypeScript value: {ts_result}")

            if isinstance(py_result, dict) and isinstance(ts_result, dict):
                py_keys = set(py_result.keys())
                ts_keys = set(ts_result.keys())

                if py_keys != ts_keys:
                    missing_in_ts = py_keys - ts_keys
                    missing_in_py = ts_keys - py_keys
                    if missing_in_ts:
                        error_details.append(f"Fields missing in TypeScript: {missing_in_ts}")
                    if missing_in_py:
                        error_details.append(f"Fields missing in Python: {missing_in_py}")

                for key in py_keys & ts_keys:
                    if type(py_result[key]) != type(ts_result[key]):
                        error_details.append(
                            f"Field '{key}' type mismatch: "
                            f"Python={type(py_result[key]).__name__}, "
                            f"TypeScript={type(ts_result[key]).__name__}"
                        )

            context_str = f" ({context})" if context else ""
            raise AssertionError(
                f"Implementation parity check failed{context_str}:\n"
                + "\n".join(f"  - {detail}" for detail in error_details)
            )
