from tests.utils.python.CustomClass import CustomClass

def multiply_by_ten(a: int) -> int:
    return a * 10

def add_two_ints(a: int, b: int) -> int:
    return a + b

def create_custom_class(value: int, my_name: str) -> CustomClass:
    return CustomClass(value, my_name)

def print_custom_class(custom_class: CustomClass):
    custom_class.print_name_and_value()

def add_three_ints(a: int, b: int, c: int) -> int:
    step1 = add_two_ints(a, b)
    step2 = add_two_ints(step1, c)
    return step2
