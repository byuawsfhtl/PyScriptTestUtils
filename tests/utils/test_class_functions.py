import pytest
from pathlib import Path

from src.pyscripttestutils.PyScriptTestRunner import PyScriptTestRunner
from tests.utils.python.CustomClass import CustomClass
from tests.utils.python.random_funcs import *

runner = PyScriptTestRunner(
    Path(__file__).resolve().parent.parent.parent / "dist" / "tests" / "utils" / "bridge.js",
    deserializer=lambda x: CustomClass(x["value"], x["myName"])
)
runner.add_method(create_custom_class, "createCustomClass", executor=lambda args: create_custom_class(args[0], args[1]))
runner.add_method(CustomClass.get_name_and_value, "CustomClassTS.getNameAndValue")

@pytest.mark.parametrize("value, name, expected", [
    (1, "test", CustomClass(1, "test")),
    (2, "test2", CustomClass(2, "test2")),
    (3, "test3", CustomClass(3, "test3")),
], ids=["1, test", "2, test2", "3, test3"])
def test_create_custom_class(value, name, expected):
    test_data = {
        "input": [value, name]
    }
    py_result, ts_result = runner.run("create_custom_class", "createCustomClass", test_data)
    assert py_result == expected
    assert ts_result == expected
    runner.assert_strict_parity(py_result, ts_result)

@pytest.mark.parametrize("custom_class, expected", [
    ({"value": 1, "myName": "test"}, "My name is test and my value is 1"),
    ({"value": 2, "myName": "test2"}, "My name is test2 and my value is 2"),
    ({"value": 3, "myName": "test3"}, "My name is test3 and my value is 3"),
], ids=["1, test", "2, test2", "3, test3"])
def test_print_custom_class(custom_class, expected):
    test_data = {
        "input": custom_class
    }
    py_result, ts_result = runner.run("CustomClass.get_name_and_value", "CustomClassTS.getNameAndValue", test_data)
    assert py_result == expected
    assert ts_result == expected
    runner.assert_strict_parity(py_result, ts_result)