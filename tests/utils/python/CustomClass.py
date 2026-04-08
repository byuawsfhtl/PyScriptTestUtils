class CustomClass:
    def __init__(self, value: int, my_name: str):
        self.value = value
        self.my_name = my_name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CustomClass):
            return False
        return self.value == other.value and self.my_name == other.my_name

    def __str__(self) -> str:
        return f"{self.my_name}: {self.value}"

    def __repr__(self) -> str:
        return f"CustomClass(value={self.value}, my_name={self.my_name})"

    def set_value(self, value: int):
        self.value = value

    def set_my_name(self, my_name: str):
        self.my_name = my_name

    def add_to_val(self, increment: int) -> int:
        self.value += increment
        return self.value

    def get_name_and_value(self) -> str:
        return f"My name is {self.my_name} and my value is {self.value}"