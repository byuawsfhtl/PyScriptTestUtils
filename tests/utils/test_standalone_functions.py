from tests.utils.python.random_funcs import *
from src.pyscripttestutils.PyScriptTestRunner import PyScriptTestRunner
from pathlib import Path
import pytest

runner = PyScriptTestRunner(Path(__file__).resolve().parent.parent.parent / "dist" / "tests" / "utils" / "bridge.js")
runner.add_method(multiply_by_ten, "multiplyByTen")
runner.add_method(add_two_ints, "addTwoInts", executor=lambda args: add_two_ints(args[0], args[1]))

@pytest.mark.parametrize("a, expected", [
    (1, 10),
    (2, 20),
    (3, 30),
], ids=["1*10=10", "2*10=20", "3*10=30"])
def test_multiply_by_ten(a, expected):
    test_data = {
        "input": a
    }
    py_result, ts_result = runner.run("multiply_by_ten", "multiplyByTen", test_data)
    assert py_result == expected
    assert ts_result == expected
    runner.assert_strict_parity(py_result, ts_result)

@pytest.mark.parametrize("a, b, expected", [
    (1, 2, 3),
    (2, 3, 5),
    (3, 4, 7),
], ids=["1+2=3", "2+3=5", "3+4=7"])
def test_add_two_ints(a, b, expected):
    test_data = {
        "input": [a, b]
    }
    py_result, ts_result = runner.run("add_two_ints", "addTwoInts", test_data)
    assert py_result == expected
    assert ts_result == expected
    runner.assert_strict_parity(py_result, ts_result)