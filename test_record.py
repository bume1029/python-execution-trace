import unittest
import mock

from record import record, RECORD_FN_NAME, find_indent_level, strip_indent


class TestRecord(unittest.TestCase):

    # Patch path refers to current module because the decorator injects the
    # record fn in here.
    record_state_fn_path = 'test_record.%s' % RECORD_FN_NAME
    dump_state_fn_path = 'record.dump_recorded_state'

    def setUp(self):
        self.dump_patcher = mock.patch(self.dump_state_fn_path)
        self.dump_mock = self.dump_patcher.start()

    def tearDown(self):
        if self.dump_patcher:
            self.dump_patcher.stop()

    def test_simple(self):
        """Simple function, no loop, no return, no conditional."""

        @record
        def foo():
            x = 5
            y = 6

        with mock.patch(self.record_state_fn_path) as record_mock:
            foo()

        self._check_record_calls(record_mock, [3, 4])
        self.assertEqual(self.dump_mock.call_count, 1, "Too many calls to dump fn.")

    def test_conditional(self):
        """Fn with a simple conditional."""

        @record
        def foo():
            x = 3
            y = 2
            if x == 3:
                y = 5

        with mock.patch(self.record_state_fn_path) as record_mock:
            foo()

        self._check_record_calls(record_mock, [3, 4, 5, 6])
        self.assertEqual(self.dump_mock.call_count, 1, "Too many calls to dump fn.")

    def test_conditional_else(self):
        """Fn with conditional having else."""

        @record
        def foo():
            x = 3
            y = 2
            if x != 3:
                y = 5
            else:
                y = 6

        with mock.patch(self.record_state_fn_path) as record_mock:
            foo()

        # Note: `else` does not have a lineno, using `if`'s lineno.
        self._check_record_calls(record_mock, [3, 4, 5, 8])
        self.assertEqual(self.dump_mock.call_count, 1, "Too many calls to dump fn.")

    def test_while(self):
        """Fn with a while."""

        @record
        def foo():
            x = 3
            y = 6

            while x < y:
                x += 1

        with mock.patch(self.record_state_fn_path) as record_mock:
            foo()

        self._check_record_calls(record_mock, [3, 4, 6, 7, 6, 7, 6, 7, 6])
        self.assertEqual(self.dump_mock.call_count, 1, "Too many calls to dump fn.")

    def test_for(self):
        """Fn with a for."""

        @record
        def foo():
            x = 3
            s = 0
            for i in range(x):
                s = s + i

        with mock.patch(self.record_state_fn_path) as record_mock:
            foo()

        self._check_record_calls(record_mock, [3, 4, 5, 6, 5, 6, 5, 6, 5])
        self.assertEqual(self.dump_mock.call_count, 1, "Too many calls to dump fn.")

    def test_nested_if_in_for(self):
        """Fn with a for containing an if."""

        @record
        def foo():
            x = 3
            s = 0
            for i in range(x):
                if s > -1:
                    s += i

        with mock.patch(self.record_state_fn_path) as record_mock:
            foo()

        self._check_record_calls(record_mock, [3, 4, 5, 6, 7, 5, 6, 7, 5, 6, 7, 5])
        self.assertEqual(self.dump_mock.call_count, 1, "Too many calls to dump fn.")

    def test_return_wrapping(self):
        """Fn with return has return value captured."""

        @record
        def foo():
            x = 3
            return x

        with mock.patch(self.record_state_fn_path) as record_mock:
            foo()

        self._check_record_calls(record_mock, [3, 4])
        self.assertEqual(self.dump_mock.call_count, 1, "Too many calls to dump fn.")

    def test_find_indent_level(self):
        source = '    def foo()'
        self.assertEqual(find_indent_level(source), 4)

        source = '    '
        self.assertEqual(find_indent_level(source), 4)

        source = ''
        self.assertEqual(find_indent_level(source), 0)

    @mock.patch('record.find_indent_level')
    def test_strip_indent(self, find_indent_mock):
        find_indent_mock.return_value = 4

        indented_source = """
    def foo():
        x = 3

        y = 4
        # Comment here
        if x == 3:
            y = 5
        return x + y
"""
        stripped_source = """
def foo():
    x = 3

    y = 4
    # Comment here
    if x == 3:
        y = 5
    return x + y
"""

        self.assertEqual(strip_indent(indented_source), stripped_source,
                         "Incorrectly stripped indentation.")

    def _check_record_calls(self, record_mock, expected_linenos):
        self.assertEqual(record_mock.call_count, len(expected_linenos))
        for i, lineno in enumerate(expected_linenos):
            self.assertEqual(record_mock.call_args_list[i][0][0], lineno)
