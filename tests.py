# -*- coding: utf-8 -*-

import re
import sys
import unittest

from flask import Flask
from flask.ext.script._compat import StringIO, text_type
from flask.ext.script import Command, Manager, Option, prompt, prompt_bool

from pytest import raises


class Catcher(object):
    """Helper decorator to test raw_input."""
    ## see: http://stackoverflow.com/questions/13480632/python-stringio-selectively-place-data-into-stdin

    def __init__(self, handler):
        self.handler = handler
        self.inputs = []

    def __enter__(self):
        self.__stdin  = sys.stdin
        self.__stdout = sys.stdout
        sys.stdin = self
        sys.stdout = self

    def __exit__(self, type, value, traceback):
        sys.stdin  = self.__stdin
        sys.stdout = self.__stdout

    def write(self, value):
        self.__stdout.write(value)
        result = self.handler(value)
        if result is not None:
            self.inputs.append(result)

    def readline(self):
        return self.inputs.pop()

    def getvalue(self):
        return self.__stdout.getvalue()

    def truncate(self, pos):
        return self.__stdout.truncate(pos)


def run(command_line, manager_run):
    '''
        Returns tuple of standard output and exit code
    '''
    sys.argv = command_line.split()
    exit_code = None
    try:
        manager_run()
    except SystemExit as e:
        exit_code = e.code

    return exit_code


class SimpleCommand(Command):
    'simple command'

    def run(self):
        print('OK')


class CommandWithArgs(Command):
    'command with args'

    option_list = (
        Option('name'),
    )

    def run(self, name):
        print(name)


class CommandWithOptions(Command):
    'command with options'

    option_list = (
        Option('-n', '--name',
               help='name to pass in',
               dest='name'),
    )

    def run(self, name):
        print(name)


class CommandWithDynamicOptions(Command):
    'command with options'

    def __init__(self, default_name='Joe'):
        self.default_name = default_name

    def get_options(self):

        return (
            Option('-n', '--name',
                   help='name to pass in',
                   dest='name',
                   default=self.default_name),
        )

    def run(self, name):
        print(name)


class CommandWithCatchAll(Command):
    'command with catch all args'

    capture_all_args = True

    def get_options(self):
        return (Option('--foo', dest='foo',
                       action='store_true'),)

    def run(self, remaining_args, foo):
        print(remaining_args)


class TestCommands(unittest.TestCase):

    TESTING = True

    def setup(self):

        self.app = Flask(__name__)
        self.app.config.from_object(self)


class TestManager:

    TESTING = True

    def setup(self):

        self.app = Flask(__name__)
        self.app.config.from_object(self)

    def test_with_default_commands(self):

        manager = Manager(self.app)

        assert 'runserver' in manager._commands
        assert 'shell' in manager._commands

    def test_without_default_commands(self):

        manager = Manager(self.app, with_default_commands=False)

        assert 'runserver' not in manager._commands
        assert 'shell' not in manager._commands

    def test_add_command(self):

        manager = Manager(self.app)
        manager.add_command('simple', SimpleCommand())

        assert isinstance(manager._commands['simple'], SimpleCommand)

    def test_simple_command_decorator(self, capsys):

        manager = Manager(self.app)

        @manager.command
        def hello():
            print('hello')

        assert 'hello' in manager._commands

        code = run('manage.py hello', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'hello' in out

    def test_simple_command_decorator_with_pos_arg(self, capsys):

        manager = Manager(self.app)

        @manager.command
        def hello(name):
            print('hello ' + name)

        assert 'hello' in manager._commands

        code = run('manage.py hello joe', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'hello joe' in out

    def test_command_decorator_with_options(self, capsys):

        manager = Manager(self.app)

        @manager.command
        def hello(name='fred'):
            'Prints your name'
            print('hello ' + name)

        assert 'hello' in manager._commands

        code = run('manage.py hello --name=joe', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'hello joe' in out

        code = run('manage.py hello -n joe', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'hello joe' in out

        code = run('manage.py hello -h', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'Prints your name' in out

        code = run('manage.py hello --help', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'Prints your name' in out

    def test_command_decorator_with_boolean_options(self, capsys):

        manager = Manager(self.app)

        @manager.command
        def verify(verified=False):
            'Checks if verified'
            print('VERIFIED ? ' + 'YES' if verified else 'NO')

        assert 'verify' in manager._commands

        code = run('manage.py verify --verified', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'YES' in out

        code = run('manage.py verify -v', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'YES' in out

        code = run('manage.py verify', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'NO' in out

        code = run('manage.py verify -h', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'Checks if verified' in out

    def test_simple_command_decorator_with_pos_arg_and_options(self, capsys):

        manager = Manager(self.app)

        @manager.command
        def hello(name, url=None):
            if url:
                assert type(url) is text_type
                print('hello ' + name + ' from ' + url)
            else:
                assert type(name) is text_type
                print('hello ' + name)

        assert 'hello' in manager._commands

        code = run('manage.py hello joe', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'hello joe' in out

        code = run('manage.py hello joe --url=reddit.com', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'hello joe from reddit.com' in out

    def test_command_decorator_with_additional_options(self, capsys):

        manager = Manager(self.app)

        @manager.option('-n', '--name', dest='name', help='Your name')
        def hello(name):
            print('hello ' + name)

        assert 'hello' in manager._commands

        code = run('manage.py hello --name=joe', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'hello joe' in out

        code = run('manage.py hello -h', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'Your name' in out

        @manager.option('-n', '--name', dest='name', help='Your name')
        @manager.option('-u', '--url', dest='url', help='Your URL')
        def hello_again(name, url=None):
            if url:
                print('hello ' + name + ' from ' + url)
            else:
                print('hello ' + name)

        assert 'hello_again' in manager._commands

        code = run('manage.py hello_again --name=joe', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'hello joe' in out

        code = run('manage.py hello_again --name=joe --url=reddit.com', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'hello joe from reddit.com' in out

    def test_global_option_provided_before_and_after_command(self, capsys):

        manager = Manager(self.app)
        manager.add_option('-c', '--config', dest='config_name', required=False, default='Development')
        manager.add_command('simple', SimpleCommand())

        assert isinstance(manager._commands['simple'], SimpleCommand)

        code = run('manage.py -c Development simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'OK' in out

        code = run('manage.py simple -c Development', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'OK' in out

    def test_global_option_value(self, capsys):

        def create_app(config_name='Empty'):
            print(config_name)
            return self.app

        manager = Manager(create_app)
        manager.add_option('-c', '--config', dest='config_name', required=False, default='Development')
        manager.add_command('simple', SimpleCommand())

        assert isinstance(manager._commands['simple'], SimpleCommand)

        code = run('manage.py simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'Empty' not in out  # config_name is overwritten by default option value
        assert 'Development' in out
        assert 'OK' in out

        code = run('manage.py -c Before simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'Before' in out
        assert 'OK' in out

        code = run('manage.py simple -c After', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'After' in out
        assert 'OK' in out

        code = run('manage.py -c DoNotShow simple -c NewValue', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'DoNotShow' not in out  # first parameter is ignored
        assert 'NewValue' in out       # second on is printed
        assert 'OK' in out

    def test_get_usage(self):

        manager = Manager(self.app)
        manager.add_command('simple', SimpleCommand())

        usage = manager.create_parser('manage.py').format_help()
        assert 'simple command' in usage

    def test_get_usage_with_specified_usage(self):

        manager = Manager(self.app, usage='hello')
        manager.add_command('simple', SimpleCommand())

        usage = manager.create_parser('manage.py').format_help()
        assert 'simple command' in usage
        assert 'hello' in usage

    def test_run_existing_command(self, capsys):

        manager = Manager(self.app)
        manager.add_command('simple', SimpleCommand())
        code = run('manage.py simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'OK' in out

    def test_run_non_existant_command(self, capsys):

        manager = Manager(self.app)
        run('manage.py simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 'invalid choice' in err

    def test_run_existing(self, capsys):

        manager = Manager(self.app)
        manager.add_command('simple', SimpleCommand())

        code = run('manage.py simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert 0 == code
        assert 'OK' in out

    def test_run_existing_bind_later(self, capsys):

        manager = Manager(self.app)

        code = run('manage.py simple', lambda: manager.run({'simple': SimpleCommand()}))
        out, err = capsys.readouterr()
        assert code == 0
        assert 'OK' in out

    def test_run_not_existing(self, capsys):

        manager = Manager(self.app)

        code = run('manage.py simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 2
        assert 'OK' not in out

    def test_run_no_name(self):

        manager = Manager(self.app)

        code = run('manage.py', lambda: manager.run())
        assert code == 2

    def test_run_good_options(self, capsys):

        manager = Manager(self.app)
        manager.add_command('simple', CommandWithOptions())

        code = run('manage.py simple --name=Joe', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'Joe' in out

    def test_run_dynamic_options(self, capsys):

        manager = Manager(self.app)
        manager.add_command('simple', CommandWithDynamicOptions('Fred'))

        code = run('manage.py simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'Fred' in out

    def test_run_catch_all(self, capsys):
        manager = Manager(self.app)
        manager.add_command('catch', CommandWithCatchAll())

        code = run('manage.py catch pos1 --foo pos2 --bar', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert "['pos1', 'pos2', '--bar']" in out

    def test_run_bad_options(self, capsys):
        manager = Manager(self.app)
        manager.add_command('simple', CommandWithOptions())

        code = run('manage.py simple --foo=bar', lambda: manager.run())
        assert code == 2

    def test_init_with_flask_instance(self):
        manager = Manager(self.app)
        assert callable(manager.app)

    def test_init_with_callable(self):
        manager = Manager(lambda: self.app)
        assert callable(manager.app)

    def test_raise_index_error(self):

        manager = Manager(self.app)

        @manager.command
        def error():
            raise IndexError()

        with raises(IndexError):
            run('manage.py error', lambda: manager.run())

    def test_run_with_default_command(self, capsys):
        manager = Manager(self.app)
        manager.add_command('simple', SimpleCommand())

        code = run('manage.py', lambda: manager.run(default_command='simple'))
        out, err = capsys.readouterr()
        assert code == 0
        assert 'OK' in out

    def test_command_with_prompt(self, capsys):

        manager = Manager(self.app)

        @manager.command
        def hello():
            print(prompt(name='hello'))

        @Catcher
        def hello_john(msg):
            if re.search("hello", msg):
                return 'john'

        with hello_john:
            code = run('manage.py hello', lambda: manager.run())
            out, err = capsys.readouterr()
            assert 'hello: john' in out

    def test_command_with_default_prompt(self, capsys):

        manager = Manager(self.app)

        @manager.command
        def hello():
            print(prompt(name='hello', default='romeo'))

        @Catcher
        def hello(msg):
            if re.search("hello", msg):
                return '\n'  # just hit enter

        with hello:
            code = run('manage.py hello', lambda: manager.run())
            out, err = capsys.readouterr()
            assert 'hello [romeo]: romeo' in out

        @Catcher
        def hello_juliette(msg):
            if re.search("hello", msg):
                return 'juliette'

        with hello_juliette:
            code = run('manage.py hello', lambda: manager.run())
            out, err = capsys.readouterr()
            assert 'hello [romeo]: juliette' in out


    def test_command_with_prompt_bool(self, capsys):

        manager = Manager(self.app)

        @manager.command
        def hello():
            print(prompt_bool(name='correct', default=True, yes_choices=['y'],
                              no_choices=['n']) and 'yes' or 'no')

        @Catcher
        def correct_default(msg):
            if re.search("correct", msg):
                return '\n'  # just hit enter

        @Catcher
        def correct_y(msg):
            if re.search("correct", msg):
                return 'y'

        @Catcher
        def correct_n(msg):
            if re.search("correct", msg):
                return 'n'

        with correct_default:
            code = run('manage.py hello', lambda: manager.run())
            out, err = capsys.readouterr()
            assert 'correct [y]: yes' in out

        with correct_y:
            code = run('manage.py hello', lambda: manager.run())
            out, err = capsys.readouterr()
            assert 'correct [y]: yes' in out

        with correct_n:
            code = run('manage.py hello', lambda: manager.run())
            out, err = capsys.readouterr()
            assert 'correct [y]: no' in out


class TestSubManager:

    TESTING = True

    def setup(self):

        self.app = Flask(__name__)
        self.app.config.from_object(self)

    def test_add_submanager(self):

        sub_manager = Manager()

        manager = Manager(self.app)
        manager.add_command('sub_manager', sub_manager)

        assert isinstance(manager._commands['sub_manager'], Manager)
        assert sub_manager.parent == manager
        assert sub_manager.get_options() == manager.get_options()

    def test_run_submanager_command(self, capsys):

        sub_manager = Manager()
        sub_manager.add_command('simple', SimpleCommand())

        manager = Manager(self.app)
        manager.add_command('sub_manager', sub_manager)

        code = run('manage.py sub_manager simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'OK' in out

    def test_submanager_has_options(self, capsys):

        sub_manager = Manager()
        sub_manager.add_command('simple', SimpleCommand())

        manager = Manager(self.app)
        manager.add_command('sub_manager', sub_manager)
        manager.add_option('-c', '--config', dest='config', required=False)

        code = run('manage.py sub_manager simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'OK' in out

        code = run('manage.py -c Development sub_manager simple', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'OK' in out

    def test_manager_usage_with_submanager(self, capsys):

        sub_manager = Manager(usage='Example sub-manager')

        manager = Manager(self.app)
        manager.add_command('sub_manager', sub_manager)

        code = run('manage.py -h', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'Example sub-manager' in out

    def test_submanager_usage(self, capsys):

        sub_manager = Manager(usage='Example sub-manager')
        sub_manager.add_command('simple', SimpleCommand())

        manager = Manager(self.app)
        manager.add_command('sub_manager', sub_manager)

        code = run('manage.py sub_manager', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 2
        assert 'too few arguments' in err

        code = run('manage.py sub_manager -h', lambda: manager.run())
        out, err = capsys.readouterr()
        assert code == 0
        assert 'simple command' in out

    def test_submanager_has_no_default_commands(self):

        sub_manager = Manager()

        manager = Manager()
        manager.add_command('sub_manager', sub_manager)

        assert 'runserver' not in sub_manager._commands
        assert 'shell' not in sub_manager._commands
