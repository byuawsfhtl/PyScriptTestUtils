import json
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from unittest.mock import patch


def _default_package_root() -> Path:
    """Return the directory containing ``package.json``, or this file's directory.
    
    Args:
        None

    Returns:
        The directory containing ``package.json``, or this file's directory.
    """
    here = Path(__file__).resolve().parent
    for ancestor in (here, *here.parents):
        if (ancestor / "package.json").is_file():
            return ancestor
    return here


@dataclass(frozen=True)
class RegisteredMethod:
    """A registered method to be run by the test runner."""
    py_fn: Callable[..., Any]
    ts_name: str
    executor: Optional[Callable[..., Any]] = None
    ts_pack_input: bool = False


class PyScriptTestRunner:
    """Dual-language test runner: register Python callables and matching TS RPC names."""

    _environment_initialized = False
    _setup_lock = threading.Lock()

    def __init__(
        
        self,
        ts_bridge_path: Path,
        package_root: Optional[Path] = None,
        serializer: Callable[[Any], Any] = lambda d: d,
        deserializer: Callable[[Any], Any] = lambda d: d
    ) -> None:
        """
        Initialize the test runner.
        
        Args:
            ts_bridge_path: The path to the TypeScript bridge.
            package_root: The root of the package.
            serializer: A function to serialize objects into consistent Json-like structures.
            deserializer: A function to deserialize objects into an expected custom class.
        """

        self.package_root = (
            package_root if package_root is not None else _default_package_root()
        )
        self.ts_bridge_path = ts_bridge_path

        self.serializer = serializer

        def list_deserializer(d: Any) -> Any:
            """
            Deserialize a list or a single item.

            Args:
                d: The list or single item to deserialize.

            Returns:
                The deserialized list or single item.
            """
            if isinstance(d, list):
                try: d = [deserializer(d) for d in d]
                except: pass
            try: return deserializer(d)
            except: return d
        self.deserializer = list_deserializer

        self._by_py: Dict[str, RegisteredMethod] = {}
        self._by_ts: Dict[str, RegisteredMethod] = {}

    def add_method(
        self,
        py_callable: Callable[..., Any],
        ts_method_name: str,
        executor: Optional[Callable[..., Any]] = None,
        ts_pack_input: bool = False,
    ) -> None:
        """
        Add a method to the test runner.

        Args:
            py_callable: The Python callable to add.
            ts_method_name: The name of the TypeScript method to add.
            executor: An optional executor function to process the test data.
            ts_pack_input: Whether to pack the input data into a single array.
        """
        if not ts_method_name or not str(ts_method_name).strip():
            raise ValueError("ts_method_name must be non-empty")
        py_key = getattr(py_callable, "__qualname__", None) or getattr(py_callable, "__name__", None)
        if not py_key or py_key == "<lambda>":
            raise ValueError("py_callable must be a named function (not lambda or <lambda>)")

        if py_key in self._by_py:
            raise ValueError(f"Duplicate Python registration: {py_key!r}")
        if ts_method_name in self._by_ts:
            raise ValueError(f"Duplicate TypeScript registration: {ts_method_name!r}")

        rec = RegisteredMethod(
            py_fn=py_callable,
            ts_name=ts_method_name,
            executor=executor,
            ts_pack_input=ts_pack_input,
        )
        self._by_py[py_key] = rec
        self._by_ts[ts_method_name] = rec

    def run(
        self,
        python_function: str,
        ts_function: str,
        test_data: Dict[str, Any],
    ) -> tuple[Any, Any]:
        """
        Run the test.

        Args:
            python_function: The name of the Python function to run.
            ts_function: The name of the TypeScript function to run.
            test_data: The test data to run.

        Returns:
            A tuple containing the Python and TypeScript results.
        """
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

        py_result_holder["result"] = self._call_python_function(
            python_function, input_data, mocks.get("python", {}), expected_error
        )

        ts_result_holder["result"] = self._call_typescript_function(
            ts_function, input_data, mocks.get("typescript", {}), expected_error
        )

        py_result = py_result_holder.get("result")
        ts_result = ts_result_holder.get("result")

        return py_result, ts_result

    def _call_python_function(
        self,
        function_name: str,
        input_data: Any,
        mocks: Dict[str, Any],
        expected_error: bool = False,
    ) -> Any:
        """
        Call the Python function.

        Args:
            function_name: The name of the Python function to call.
            input_data: The input data to pass to the Python function.
            mocks: The mocks to use for the Python function.
            expected_error: Whether to expect an error from the Python function.

        Returns:
            The result of the Python function.

        Raises:
            ValueError: If the Python function is not found.
            RuntimeError: If the Python function fails.
        """
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
                if rec.executor is not None:
                    result = rec.executor(self.deserializer(input_data))
                else:
                    result = rec.py_fn(self.deserializer(input_data))
                try: return self.serializer(result)
                except: return result
            finally:
                for mock_context in reversed(mock_contexts):
                    mock_context.__exit__(None, None, None)

        except Exception as e:
            if expected_error:
                return {"error": True, "error_type": type(e).__name__, "error_message": str(e)}
            raise RuntimeError(f"Python function {function_name} failed: {str(e)}") from e

    def _call_typescript_function(
        self,
        function_name: str,
        input_data: Any,
        mocks: Dict[str, Any],
        expected_error: bool = False,
    ) -> Any:
        """
        Call the TypeScript function.
        
        Args:
            function_name: The name of the TypeScript function to call.
            input_data: The input data to pass to the TypeScript function.
            mocks: The mocks to use for the TypeScript function.
            expected_error: Whether to expect an error from the TypeScript function.

        Returns:
            The result of the TypeScript function.

        Raises:
            ValueError: If the TypeScript function is not found.
            RuntimeError: If the TypeScript function fails.
            json.JSONDecodeError: If the TypeScript response is not valid JSON.
            Exception: If the TypeScript function fails for any other reason.
        """
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
                ["node", str(self.ts_bridge_path), json.dumps(request, ensure_ascii=False).encode('utf-8')],
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
                    return {"error": True, "error_type": "Error", "error_message": response.get("error", "Unknown error")}
                raise RuntimeError(
                    f"TypeScript function failed: {response.get('error', 'Unknown error')}"
                )

            return self.serializer(self.deserializer(response["result"]))

        except json.JSONDecodeError as e:
            if expected_error:
                return {"error": True, "error_type": "JSONDecodeError", "error_message": str(e)}
            raise RuntimeError(f"Failed to parse TypeScript response: {str(e)}") from e
        except Exception as e:
            if expected_error:
                return {"error": True, "error_type": type(e).__name__, "error_message": str(e)}
            raise RuntimeError(f"TypeScript function {function_name} failed: {str(e)}") from e

    def compare_results(self, py_result: Any, ts_result: Any) -> bool:
        """
        Compare the Python and TypeScript results.

        Args:
            py_result: The Python result to compare.
            ts_result: The TypeScript result to compare.

        Returns:
            True if the results are equal, False otherwise.
        """
        if isinstance(py_result, dict) and isinstance(ts_result, dict):
            if py_result.get("error") is True and ts_result.get("error") is True:
                return True

        if py_result != ts_result:
            return False

        if type(py_result) is not type(ts_result):
            return False

        if isinstance(py_result, dict) and isinstance(ts_result, dict):
            return self._compare_dicts(py_result, ts_result)

        elif isinstance(py_result, list) and isinstance(ts_result, list):
            return self._compare_lists(py_result, ts_result)

        return True

    def _compare_dicts(self, py_result: Dict[str, Any], ts_result: Dict[str, Any]) -> bool:
        """
        Compare two dictionaries.

        Args:
            py_result: The Python dictionary to compare.
            ts_result: The TypeScript dictionary to compare.

        Returns:
            True if the dictionaries are equal, False otherwise.
        """
        if set(py_result.keys()) != set(ts_result.keys()):
            return False

        for key in py_result.keys():
            py_value = py_result[key]
            ts_value = ts_result[key]

            if type(py_value) is not type(ts_value):
                return False

            if isinstance(py_value, dict) and isinstance(ts_value, dict) and not self.compare_results(py_value, ts_value):
                return False
        
        return True

    def _compare_lists(self, py_result: list[Any], ts_result: list[Any]) -> bool:
        """
        Compare two lists.

        Args:
            py_result: The Python list to compare.
            ts_result: The TypeScript list to compare.

        Returns:
            True if the lists are equal, False otherwise.
        """
        if len(py_result) != len(ts_result):
            return False

        for py_item, ts_item in zip(py_result, ts_result):
            if not self.compare_results(py_item, ts_item):
                return False

        return True

    def assert_strict_parity(self, py_result: Any, ts_result: Any, context: str = "") -> None:
        """
        Assert that the Python and TypeScript results are strictly equal.

        Args:
            py_result: The Python result to compare.
            ts_result: The TypeScript result to compare.
            context: The context of the comparison.

        Raises:
            AssertionError: If the Python and TypeScript results are not strictly equal.
        """
        error_details = []

        if py_result != ts_result or not self.compare_results(py_result, ts_result):
            error_details.append(f"Value mismatch: Python={py_result}, TypeScript={ts_result}")

        if type(py_result) is not type(ts_result):
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
                if type(py_result[key]) is not type(ts_result[key]):
                    error_details.append(f"Field '{key}' type mismatch: Python={type(py_result[key]).__name__}, TypeScript={type(ts_result[key]).__name__}")

        if len(error_details) == 0:
            return

        context_str = f" ({context})" if context else ""
        raise AssertionError(
            f"Implementation parity check failed{context_str}:\n"
            + "\n".join(f"  - {detail}" for detail in error_details)
        )
