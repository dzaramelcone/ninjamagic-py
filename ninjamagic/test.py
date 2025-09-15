from typing import TypeVar, cast


class MyBase:
    my_base_str: str
    pass


class MyClass(MyBase):
    my_str: str
    pass


class MySecondClass(MyBase):
    my_second_str: str


test: list[MyClass] = [MyClass()]
d = {MyClass: test, MySecondClass: list[MySecondClass]()}

T = TypeVar("T")


def get_queue(cls: type[T]) -> list[T]:
    return cast(list[T], d.setdefault(cls, []))


q_cls = get_queue(MyClass)


def my_base_test(b: MyBase):
    print(type(b))
    print(get_queue(type(b)).pop().my_base_str)
    print(get_queue(MyClass).pop().my_str)
    print(get_queue(MySecondClass).pop().my_second_str)


my_base_test(test[0])
