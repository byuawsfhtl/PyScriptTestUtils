import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.pyscripttestutils.PyScriptTestRunner import PyScriptTestRunner
from tests.utils.python.CustomClass import CustomClass
from tests.utils.python.random_funcs import (
    add_three_ints,
    add_two_ints,
    create_custom_class,
    multiply_by_ten,
)

BRIDGE = (
    Path(__file__).resolve().parent.parent.parent
    / "dist" / "tests" / "utils" / "bridge.js"
)
SUBPROCESS_PATH = "src.pyscripttestutils.PyScriptTestRunner.subprocess.run"

# Module-level lambda: __qualname__ is exactly "<lambda>", which the runner rejects.
_MODULE_LAMBDA = lambda x: x  # noqa: E731


def _make_runner(**kwargs) -> PyScriptTestRunner:
    return PyScriptTestRunner(BRIDGE, **kwargs)


class TestAddMethod:
    @pytest.mark.parametrize("bad_name", ["", "   ", "\t"])
    def test_add_method_rejects_empty_ts_name(self, bad_name):
        runner = _make_runner()
        with pytest.raises(ValueError, match="ts_method_name must be non-empty"):
            runner.add_method(multiply_by_ten, bad_name)


    def test_add_method_rejects_lambda(self):
        runner = _make_runner()
        with pytest.raises(ValueError, match="named function"):
            runner.add_method(_MODULE_LAMBDA, "someMethod")


    def test_add_method_rejects_duplicate_python_key(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        with pytest.raises(ValueError, match="Duplicate Python"):
            runner.add_method(multiply_by_ten, "multiplyByTen2")


    def test_add_method_rejects_duplicate_ts_name(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        with pytest.raises(ValueError, match="Duplicate TypeScript"):
            runner.add_method(add_two_ints, "multiplyByTen")


    def test_add_method_stores_executor_and_ts_pack_input(self):
        runner = _make_runner()
        executor = lambda args: add_two_ints(args[0], args[1])
        runner.add_method(add_two_ints, "addTwoInts", executor=executor, ts_pack_input=True)
        rec = runner._by_ts["addTwoInts"]
        assert rec.executor is executor
        assert rec.ts_pack_input is True


class TestRunValidation:
    def test_run_rejects_unknown_python_function(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        with pytest.raises(ValueError, match="Unknown Python function"):
            runner.run("no_such_fn", "multiplyByTen", {"input": 5})


    def test_run_rejects_ts_name_mismatch(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        with pytest.raises(ValueError, match="TypeScript name mismatch"):
            runner.run("multiply_by_ten", "wrongName", {"input": 5})


class TestCallPythonFunction:
    def test_call_python_unknown_fn_raises_value_error(self):
        runner = _make_runner()
        with pytest.raises(ValueError, match="Unknown Python function"):
            runner._call_python_function("no_such_fn", 1, {})


    def test_call_python_expected_error_returns_error_dict(self):
        def failing_fn(x):
            raise ValueError("intentional failure")

        runner = _make_runner()
        runner.add_method(failing_fn, "someTs")
        result = runner._call_python_function(
            failing_fn.__qualname__, 1, {}, expected_error=True
        )
        assert result["error"] is True
        assert result["error_type"] == "ValueError"
        assert "intentional failure" in result["error_message"]


    def test_call_python_raises_runtime_when_error_not_expected(self):
        def raising_fn(x):
            raise ValueError("boom")

        runner = _make_runner()
        runner.add_method(raising_fn, "someTs2")
        with pytest.raises(RuntimeError, match="failed"):
            runner._call_python_function(
                raising_fn.__qualname__, 1, {}, expected_error=False
            )


    def test_call_python_serializer_failure_returns_raw_result(self):
        def bad_serializer(x):
            raise RuntimeError("serializer exploded")

        runner = _make_runner(serializer=bad_serializer)
        runner.add_method(multiply_by_ten, "multiplyByTen")
        result = runner._call_python_function("multiply_by_ten", 3, {})
        assert result == 30


    def test_call_python_executor_invoked_instead_of_py_fn(self):
        side_effect = []

        def recording_executor(args):
            side_effect.append(args)
            return add_two_ints(args[0], args[1])

        runner = _make_runner()
        runner.add_method(add_two_ints, "addTwoInts", executor=recording_executor)
        result = runner._call_python_function("add_two_ints", [3, 4], {})
        assert result == 7
        assert side_effect, "executor was never called"


    def test_call_python_mock_patches_named_target(self):
        runner = _make_runner()
        runner.add_method(
            add_three_ints,
            "addThreeInts",
            executor=lambda args: add_three_ints(args[0], args[1], args[2]),
        )
        mocks = {"tests.utils.python.random_funcs.add_two_ints": 42}
        result = runner._call_python_function("add_three_ints", [1, 2, 3], mocks)
        assert result == 42


class TestInitListDeserializerWrapping:
    def test_init_list_deserializer_applies_per_element(self):
        received = []

        def capture(arg):
            received.append(arg)
            return arg

        runner = PyScriptTestRunner(
            BRIDGE,
            deserializer=lambda x: CustomClass(x["value"], x["myName"]),
        )
        runner.add_method(capture, "captureTs")

        runner._call_python_function(
            capture.__qualname__,
            [{"value": 1, "myName": "a"}, {"value": 2, "myName": "b"}],
            {},
        )
        assert received[0] == [CustomClass(1, "a"), CustomClass(2, "b")]


    def test_init_list_deserializer_falls_back_to_identity_on_non_deserializable_list(self):
        received = []

        def capture(arg):
            received.append(arg)
            return arg

        runner = PyScriptTestRunner(
            BRIDGE,
            deserializer=lambda x: CustomClass(x["value"], x["myName"]),
        )
        runner.add_method(capture, "captureTs2")

        runner._call_python_function(capture.__qualname__, [1, 2, 3], {})
        assert received[0] == [1, 2, 3]


class TestCallTypescriptFunction:
    def test_call_typescript_unknown_fn_raises_value_error(self):
        runner = _make_runner()
        with pytest.raises(ValueError, match="Unknown TypeScript function"):
            runner._call_typescript_function("no_such_ts_fn", 1, {})


    def test_call_typescript_unknown_bridge_method_with_expected_error(self):
        runner = _make_runner()
        runner.add_method(
            add_three_ints,
            "addThreeInts",
            executor=lambda args: add_three_ints(args[0], args[1], args[2]),
        )
        result = runner._call_typescript_function(
            "addThreeInts", [1, 2, 3], {}, expected_error=True
        )
        assert result["error"] is True
        assert "addThreeInts" in result["error_message"]


    def test_call_typescript_unknown_bridge_method_raises_without_expected_error(self):
        runner = _make_runner()
        runner.add_method(
            add_three_ints,
            "addThreeInts",
            executor=lambda args: add_three_ints(args[0], args[1], args[2]),
        )
        with pytest.raises(RuntimeError, match="TypeScript function failed"):
            runner._call_typescript_function("addThreeInts", [1, 2, 3], {})


    def test_call_typescript_nonzero_returncode_raises(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        mock_proc = Mock(returncode=1, stderr="node crashed", stdout="")
        with patch(SUBPROCESS_PATH, return_value=mock_proc):
            with pytest.raises(RuntimeError, match="TypeScript bridge failed"):
                runner._call_typescript_function("multiplyByTen", 5, {})


    def test_call_typescript_invalid_json_swallowed_when_expected_error(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        mock_proc = Mock(returncode=0, stderr="", stdout="not valid json {{")
        with patch(SUBPROCESS_PATH, return_value=mock_proc):
            result = runner._call_typescript_function(
                "multiplyByTen", 5, {}, expected_error=True
            )
        assert result["error"] is True


    def test_call_typescript_invalid_json_raises_when_not_expected(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        mock_proc = Mock(returncode=0, stderr="", stdout="not valid json {{")
        with patch(SUBPROCESS_PATH, return_value=mock_proc):
            with pytest.raises(RuntimeError, match="Failed to parse TypeScript response"):
                runner._call_typescript_function("multiplyByTen", 5, {})


    def test_call_typescript_subprocess_raises_exception_with_expected_error(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        with patch(SUBPROCESS_PATH, side_effect=OSError("node not found")):
            result = runner._call_typescript_function(
                "multiplyByTen", 5, {}, expected_error=True
            )
        assert result["error"] is True
        assert "node not found" in result["error_message"]


    def test_call_typescript_subprocess_raises_exception_without_expected_error(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        with patch(SUBPROCESS_PATH, side_effect=OSError("node not found")):
            with pytest.raises(RuntimeError, match="multiplyByTen failed"):
                runner._call_typescript_function("multiplyByTen", 5, {})


    def test_call_typescript_stderr_triggers_debug_banner(self, capsys):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        mock_proc = Mock(
            returncode=0,
            stderr="console.log debug info",
            stdout=json.dumps({"success": True, "result": 50}),
        )
        with patch(SUBPROCESS_PATH, return_value=mock_proc):
            result = runner._call_typescript_function("multiplyByTen", 5, {})
        assert result == 50
        out = capsys.readouterr().out
        assert "TypeScript Debug Output" in out
        assert "console.log debug info" in out


    def test_call_typescript_success_applies_serializer_and_deserializer(self):
        runner = PyScriptTestRunner(
            BRIDGE,
            deserializer=lambda x: CustomClass(x["value"], x["myName"]),
            serializer=lambda c: {"value": c.value, "myName": c.my_name},
        )
        runner.add_method(
            create_custom_class,
            "createCustomClass",
            executor=lambda args: create_custom_class(args[0], args[1]),
        )
        mock_proc = Mock(
            returncode=0,
            stderr="",
            stdout=json.dumps({"success": True, "result": {"value": 1, "myName": "a"}}),
        )
        with patch(SUBPROCESS_PATH, return_value=mock_proc):
            result = runner._call_typescript_function("createCustomClass", [1, "a"], {})
        assert result == {"value": 1, "myName": "a"}


    def test_call_typescript_scalar_input_wrapped_in_list(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen")
        captured = {}

        def fake_run(cmd, **_kwargs):
            captured["args"] = json.loads(cmd[2])["args"]
            return Mock(returncode=0, stderr="", stdout=json.dumps({"success": True, "result": 50}))

        with patch(SUBPROCESS_PATH, side_effect=fake_run):
            runner._call_typescript_function("multiplyByTen", 5, {})

        assert captured["args"] == [5]


    def test_call_typescript_list_input_spread_as_args(self):
        runner = _make_runner()
        runner.add_method(
            add_two_ints,
            "addTwoInts",
            executor=lambda args: add_two_ints(args[0], args[1]),
        )
        captured = {}

        def fake_run(cmd, **_kwargs):
            captured["args"] = json.loads(cmd[2])["args"]
            return Mock(returncode=0, stderr="", stdout=json.dumps({"success": True, "result": 3}))

        with patch(SUBPROCESS_PATH, side_effect=fake_run):
            runner._call_typescript_function("addTwoInts", [1, 2], {})

        assert captured["args"] == [1, 2]


    def test_call_typescript_ts_pack_input_wraps_list_into_single_arg(self):
        runner = _make_runner()
        runner.add_method(multiply_by_ten, "multiplyByTen", ts_pack_input=True)
        captured = {}

        def fake_run(cmd, **_kwargs):
            captured["args"] = json.loads(cmd[2])["args"]
            return Mock(returncode=0, stderr="", stdout=json.dumps({"success": True, "result": 30}))

        with patch(SUBPROCESS_PATH, side_effect=fake_run):
            runner._call_typescript_function("multiplyByTen", [3], {})

        assert captured["args"] == [[3]]


class TestCompareResults:
    @pytest.fixture()
    def runner(self):
        return _make_runner()


    def test_compare_results_both_error_dicts_short_circuits_to_true(self):
        runner = _make_runner()
        assert runner.compare_results(
            {"error": True, "message": "x"},
            {"error": True, "message": "y"},
        ) is True


    def test_compare_results_unequal_primitives(self, runner):
        runner = _make_runner()
        assert runner.compare_results(1, 2) is False


    def test_compare_results_same_value_different_type(self, runner):
        runner = _make_runner()
        assert runner.compare_results(1, True) is False


    def test_compare_results_dicts_key_set_mismatch(self, runner):
        runner = _make_runner()
        assert runner.compare_results({"a": 1}, {"b": 1}) is False


    def test_compare_results_dicts_nested_type_mismatch(self, runner):
        runner = _make_runner()
        assert runner.compare_results({"a": 1}, {"a": "1"}) is False


    def test_compare_results_nested_dicts_value_mismatch(self, runner):
        runner = _make_runner()
        assert runner.compare_results({"a": {"b": 1}}, {"a": {"b": 2}}) is False


    def test_compare_results_lists_length_mismatch(self, runner):
        runner = _make_runner()
        assert runner.compare_results([1], [1, 2]) is False


    def test_compare_results_lists_element_mismatch(self, runner):
        runner = _make_runner()
        assert runner.compare_results([1], [2]) is False


    def test_compare_results_equal_primitives(self, runner):
        runner = _make_runner()
        assert runner.compare_results(42, 42) is True


    def test_compare_results_equal_dicts(self, runner):
        runner = _make_runner()
        assert runner.compare_results({"a": 1, "b": 2}, {"a": 1, "b": 2}) is True


    def test_compare_results_equal_lists(self, runner):
        runner = _make_runner()
        assert runner.compare_results([1, 2, 3], [1, 2, 3]) is True


    def test_compare_results_equal_nested_dicts(self, runner):
        runner = _make_runner()
        assert runner.compare_results({"a": {"b": 1}}, {"a": {"b": 1}}) is True


    def test_compare_results_dict_values_python_equal_but_different_type(self, runner):
        # {"a": 1} == {"a": True} in Python, so the top-level != check passes,
        # but the per-key type check (line 308) must catch the int/bool mismatch.
        runner = _make_runner()
        assert runner.compare_results({"a": 1}, {"a": True}) is False


    def test_compare_results_nested_dict_recursive_type_mismatch(self, runner):
        # Outer dicts compare equal in Python (1 == True), but recursive check
        # on the nested dict surfaces the type mismatch (line 311).
        runner = _make_runner()
        assert runner.compare_results({"a": {"b": 1}}, {"a": {"b": True}}) is False


    def test_compare_results_list_elements_recursive_type_mismatch(self, runner):
        # [{"a": 1}] == [{"a": True}] in Python, but recursive per-element
        # compare_results catches the nested type mismatch (line 319).
        runner = _make_runner()
        assert runner.compare_results([{"a": 1}], [{"a": True}]) is False


class TestAssertStrictParity:
    @pytest.fixture()
    def runner(self):
        return _make_runner()


    def test_assert_strict_parity_raises_on_value_mismatch(self, runner):
        runner = _make_runner()
        with pytest.raises(AssertionError, match="Value mismatch"):
            runner.assert_strict_parity(1, 2)


    def test_assert_strict_parity_type_mismatch_populates_details(self, runner):
        # 1 == True in Python, so value check passes, but type detail is added.
        runner = _make_runner()
        with pytest.raises(AssertionError, match="Type mismatch"):
            runner.assert_strict_parity(1, True)


    def test_assert_strict_parity_dict_missing_keys_populates_details(self, runner):
        runner = _make_runner()
        with pytest.raises(AssertionError, match="Fields missing"):
            runner.assert_strict_parity({"a": 1, "b": 2}, {"a": 1})


    def test_assert_strict_parity_dict_field_type_mismatch_populates_details(self, runner):
        # {"a": 1} == {"a": True} in Python so value mismatch uses compare_results,
        # and the dict-field type detail (line 361) is also added.
        runner = _make_runner()
        with pytest.raises(AssertionError, match="type mismatch"):
            runner.assert_strict_parity({"a": 1}, {"a": True})


    def test_assert_strict_parity_equal_values_do_not_raise(self, runner):
        runner = _make_runner()
        runner.assert_strict_parity(42, 42)


    def test_assert_strict_parity_raises_on_mismatched_error_dicts_with_context(self, runner):
        """
        Both-error dicts short-circuit compare_results to True, so assert_strict_parity
        proceeds into its own checks, finds a value mismatch, and raises AssertionError.
        """
        runner = _make_runner()
        with pytest.raises(AssertionError, match="my_ctx"):
            runner.assert_strict_parity(
                {"error": True, "msg": "x"},
                {"error": True, "msg": "y"},
                context="my_ctx",
            )


class TestRunWithExpectedError:
    def test_run_with_expected_error_py_succeeds_ts_fails(self):
        runner = _make_runner()
        runner.add_method(
            add_three_ints,
            "addThreeInts",
            executor=lambda args: add_three_ints(args[0], args[1], args[2]),
        )
        py_result, ts_result = runner.run(
            "add_three_ints",
            "addThreeInts",
            {"input": [1, 2, 3], "expected_error": True},
        )
        assert py_result == 6
        assert ts_result["error"] is True
        assert "addThreeInts" in ts_result["error_message"]
