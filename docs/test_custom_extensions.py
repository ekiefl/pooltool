from custom_extensions import extract_qualified_name


class TestClass:
    @staticmethod
    def a_static_method():
        pass

    @classmethod
    def a_class_method(cls):
        pass

    def an_instance_method(self):
        pass


def just_a_func():
    pass


lambda_func = lambda x: x  # noqa: E731


def test_a_class_method():
    assert (
        extract_qualified_name(TestClass.a_class_method) == "TestClass.a_class_method"
    )


def test_a_static_method():
    assert (
        extract_qualified_name(TestClass.a_static_method) == "TestClass.a_static_method"
    )


def test_an_instance_method():
    instance = TestClass()
    assert (
        extract_qualified_name(instance.an_instance_method)
        == "TestClass.an_instance_method"
    )


def test_just_a_func():
    assert extract_qualified_name(just_a_func) == "just_a_func"


def test_lambda_func():
    assert extract_qualified_name(lambda_func) == "UNKNOWN"


def test_unknown():
    assert extract_qualified_name(123) == "UNKNOWN"
