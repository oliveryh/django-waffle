from django.test import TestCase
from waffle import switch_is_active
from waffle.testutils import override_switch
from assertpy import assert_that
from waffle.models import Switch

from parameterized.parameterized import default_class_name_func

import sys
# Python 3 doesn't have an InstanceType, so just use a dummy type.
class InstanceType():
    pass
lzip = lambda *a: list(zip(*a))
text_type = str
string_types = str,
bytes_type = bytes
def make_method(func, instance, type):
    if instance is None:
        return func

def parameterized_class_decorators(attrs, input_values=None, class_name_func=None, classname_func=None):
    """ Parameterizes a test class by setting attributes on the class.

        Can be used in two ways:

        1) With a list of dictionaries containing attributes to override::

            @parameterized_class([
                { "username": "foo" },
                { "username": "bar", "access_level": 2 },
            ])
            class TestUserAccessLevel(TestCase):
                ...

        2) With a tuple of attributes, then a list of tuples of values:

            @parameterized_class(("username", "access_level"), [
                ("foo", 1),
                ("bar", 2)
            ])
            class TestUserAccessLevel(TestCase):
                ...

    """

    if isinstance(attrs, string_types):
        attrs = [attrs]

    input_dicts = (
        attrs if input_values is None else
        [dict(zip(attrs, vals)) for vals in input_values]
    )

    class_name_func = class_name_func or default_class_name_func

    if classname_func:
        class_name_func = lambda cls, idx, input: classname_func(cls, idx, input_dicts)

    def decorator(base_class):
        test_class_module = sys.modules[base_class.__module__].__dict__
        for idx, input_dict in enumerate(input_dicts):
            test_class_dict = dict(base_class.__dict__)
            name = class_name_func(base_class, idx, input_dict)

            return_class = type(name, (base_class, ), test_class_dict)

            for switch_name, switch_state in input_dict.items():
                dec_func = override_switch(switch_name, active=switch_state)
                return_class = dec_func(return_class)

            test_class_module[name] = return_class

        # We need to leave the base class in place (see issue #73), but if we
        # leave the test_ methods in place, the test runner will try to pick
        # them up and run them... which doesn't make sense, since no parameters
        # will have been applied.
        # Address this by iterating over the base class and remove all test
        # methods.
        for method_name in list(base_class.__dict__):
            if method_name.startswith("test"):
                delattr(base_class, method_name)
        return base_class

    return decorator

@parameterized_class_decorators([
    { 'a': False },
    { 'a': True },
])
class ParameterizedSwitchOverrideBasicTest(TestCase):

    expected_states = {
        'ParameterizedSwitchOverrideBasicTest_0': {
            'a': False,
        },
        'ParameterizedSwitchOverrideBasicTest_1': {
            'a': True,
        }
    }

    def test_switch_state(self):
        expected_state = self.expected_states[self.__class__.__name__]
        for switch_name, switch_state in expected_state.items():
            assert_that(switch_is_active(switch_name)).is_equal_to(switch_state)

@parameterized_class_decorators([
    { 'a': False, 'b': True },
    { 'a': True, 'b': False },
])
class ParameterizedSwitchOverrideMultipleTest(TestCase):

    expected_states = {
        'ParameterizedSwitchOverrideMultipleTest_0': {
            'a': False,
            'b': True,
        },
        'ParameterizedSwitchOverrideMultipleTest_1': {
            'a': True,
            'b': False,
        }
    }

    def test_switch_state(self):
        expected_state = self.expected_states[self.__class__.__name__]
        for switch_name, switch_state in expected_state.items():
            assert_that(switch_is_active(switch_name)).is_equal_to(switch_state)


@parameterized_class_decorators([
    { 'a': False, 'b': True },
    { 'a': True, 'b': False },
])
@override_switch('c', active=True)
class ParameterizedSwitchOverrideAdditionalTest(TestCase):

    expected_states = {
        'ParameterizedSwitchOverrideAdditionalTest_0': {
            'a': False,
            'b': True,
            'c': True,
        },
        'ParameterizedSwitchOverrideAdditionalTest_1': {
            'a': True,
            'b': False,
            'c': True,
        }
    }

    def test_switch_state(self):
        expected_state = self.expected_states[self.__class__.__name__]
        for switch_name, switch_state in expected_state.items():
            assert_that(switch_is_active(switch_name)).is_equal_to(switch_state)

from django.test.utils import override_settings
from django.conf import settings

@override_settings(TEST='override-parent')
class ParentDecoratedTestCase(TestCase):
    pass

@override_settings(TEST='override-child')
class ChildDecoratedTestCase(ParentDecoratedTestCase):
    def test_override_settings_inheritance(self):
        self.assertEqual(settings.TEST, 'override-child')


# class override_settings(TestContextDecorator):
#     """
#     Act as either a decorator or a context manager. If it's a decorator, take a
#     function and return a wrapped function. If it's a contextmanager, use it
#     with the ``with`` statement. In either event, entering/exiting are called
#     before and after, respectively, the function/block is executed.
#     """
#     enable_exception = None

#     def __init__(self, **kwargs):
#         self.options = kwargs
#         super().__init__()

#     def enable(self):
#         # Keep this code at the beginning to leave the settings unchanged
#         # in case it raises an exception because INSTALLED_APPS is invalid.
#         if 'INSTALLED_APPS' in self.options:
#             try:
#                 apps.set_installed_apps(self.options['INSTALLED_APPS'])
#             except Exception:
#                 apps.unset_installed_apps()
#                 raise
#         override = UserSettingsHolder(settings._wrapped)
#         for key, new_value in self.options.items():
#             setattr(override, key, new_value)
#         self.wrapped = settings._wrapped
#         settings._wrapped = override
#         for key, new_value in self.options.items():
#             try:
#                 setting_changed.send(
#                     sender=settings._wrapped.__class__,
#                     setting=key, value=new_value, enter=True,
#                 )
#             except Exception as exc:
#                 self.enable_exception = exc
#                 self.disable()

#     def disable(self):
#         if 'INSTALLED_APPS' in self.options:
#             apps.unset_installed_apps()
#         settings._wrapped = self.wrapped
#         del self.wrapped
#         responses = []
#         for key in self.options:
#             new_value = getattr(settings, key, None)
#             responses_for_setting = setting_changed.send_robust(
#                 sender=settings._wrapped.__class__,
#                 setting=key, value=new_value, enter=False,
#             )
#             responses.extend(responses_for_setting)
#         if self.enable_exception is not None:
#             exc = self.enable_exception
#             self.enable_exception = None
#             raise exc
#         for _, response in responses:
#             if isinstance(response, Exception):
#                 raise response

#     def save_options(self, test_func):
#         if test_func._overridden_settings is None:
#             test_func._overridden_settings = self.options
#         else:
#             # Duplicate dict to prevent subclasses from altering their parent.
#             test_func._overridden_settings = {
#                 **test_func._overridden_settings,
#                 **self.options,
#             }

#     def decorate_class(self, cls):
#         from django.test import SimpleTestCase
#         if not issubclass(cls, SimpleTestCase):
#             raise ValueError(
#                 "Only subclasses of Django SimpleTestCase can be decorated "
#                 "with override_settings")
#         self.save_options(cls)
#         return cls

from django.test.utils import TestContextDecorator

class _overrider(TestContextDecorator):
    def __init__(self, name, active):
        super(_overrider, self).__init__()
        self.name = name
        self.active = active
        self.set = False

    def get(self):
        self.obj, self.created = self.cls.objects.get_or_create(name=self.name)

    def update(self, active):
        raise NotImplementedError

    def get_value(self):
        raise NotImplementedError

    def enable(self):
        self.get()
        self.old_value = self.get_value()
        print(f"enable | old_value={self.old_value} | active={self.active}")
        if self.old_value != self.active:
            print(f"ENABLE: {self.active}")
            self.update(self.active)

    def disable(self):
        if self.created:
            self.obj.delete()
            self.obj.flush()
        else:
            print(f"DISABLE: {self.old_value}")
            self.update(self.old_value)





class override_switch_new(_overrider):
    """
    override_switch is a contextmanager for easier testing of switches.

    It accepts two parameters, name of the switch and it's state. Example
    usage::

        with override_switch('happy_mode', active=True):
            ...

    If `Switch` already existed, it's value would be changed inside the context
    block, then restored to the original value. If `Switch` did not exist
    before entering the context, it is created, then removed at the end of the
    block.

    It can also act as a decorator::

        @override_switch('happy_mode', active=True)
        def test_happy_mode_enabled():
            ...

    """
    cls = Switch

    def update(self, active):
        obj = self.cls.objects.get(pk=self.obj.pk)
        obj.active = active
        obj.save()
        obj.flush()
        self.set = True

    def get_value(self):
        return self.obj.active

    def save_options(self, test_func):

        if not hasattr(test_func, '_overridden_switches'):
            test_func._overridden_switches = None

        if test_func._overridden_switches is None:
            test_func._overridden_switches = {
                self.name: self.active,
            }
        else:
            # Duplicate dict to prevent subclasses from altering their parent.
            test_func._overridden_switches = {
                **test_func._overridden_switches,
                self.name: self.active,
            }

    def decorate_class(self, cls):
        from django.test import SimpleTestCase
        if not issubclass(cls, SimpleTestCase):
            raise ValueError(
                "Only subclasses of Django SimpleTestCase can be decorated "
                "with override_settings")
        self.save_options(cls)

        def setUp(inner_self):
            for switch_name, switch_state in inner_self._overridden_switches.items():
                obj, _ = self.cls.objects.get_or_create(name=switch_name)
                obj.active = switch_state
                obj.save()
                obj.flush()
        cls.setUp = setUp
        return cls


# @override_switch_new('a', active=False)
# class XParentDecoratedTestCase(TestCase):
#     pass

# @override_switch_new('a', active=True)
# class XChildDecoratedTestCase(XParentDecoratedTestCase):
#     def test_override_settings_inheritance(self):
#         self.assertEqual(switch_is_active('a'), True)

@override_switch_new('a', active=True)
@override_switch_new('c', active=True)
class XParentDecoratedTestCaseOpposite(TestCase):
    def test_override_settings_inheritance(self):
        self.assertEqual(switch_is_active('a'), True)
        self.assertEqual(switch_is_active('c'), True)

@override_switch_new('a', active=False)
@override_switch_new('b', active=True)
class XChildDecoratedTestCaseOpposite(XParentDecoratedTestCaseOpposite):
    def test_override_settings_inheritance(self):
        self.assertEqual(switch_is_active('a'), False)
        self.assertEqual(switch_is_active('b'), True)
        self.assertEqual(switch_is_active('c'), True)

@override_settings(SOME_SETTING='a')
class ParentClassTest(TestCase):
    def test_setting(self):
        self.assertEqual(settings.SOME_SETTING, 'a')

class ChildClassTest(ParentClassTest):
    def test_setting(self):
        self.assertEqual(settings.SOME_SETTING, 'a')

