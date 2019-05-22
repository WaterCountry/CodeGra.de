import os  # typing: ignore
import abc
import pwd
import sys
import copy
import json
import time
import uuid
import errno
import signal
import typing as t
import datetime
import tempfile
import threading
import contextlib
import subprocess
from multiprocessing import Queue, context
from multiprocessing.dummy import Pool

import lxc  # typing: ignore
import requests
import structlog
import transip.service
from suds import WebFault
from mypy_extensions import TypedDict

import psef

from .. import app, models
from .steps import TestStep, StopRunningStepsException, auto_test_handlers
from ..helpers import (
    JSONType, defer, register, timed_code, bound_to_logger,
    ensure_on_test_server
)

logger = structlog.get_logger()

auto_test_runners: register.Register[str, t.Type['AutoTestRunner']
                                     ] = register.Register()

OutputCallback = t.Callable[[bytes], None]
URL = t.NewType('URL', str)

STOP_CONTAINERS = threading.Event()

T = t.TypeVar('T')


class StopContainerException(Exception):
    pass


class CommandTimeoutException(Exception):
    pass


def maybe_stop_container() -> None:
    if STOP_CONTAINERS.is_set():
        raise StopContainerException


def get_new_container_name() -> str:
    return str(uuid.uuid1())


def get_amount_cpus() -> int:
    return os.cpu_count() or 1


def _start_container(cont: lxc.Container) -> None:
    maybe_stop_container()

    with timed_code('start_container'):
        assert cont.start()
        assert cont.wait('RUNNING', 3)
        for _ in range(30):
            if cont.get_ips():
                return
            time.sleep(1)
        else:
            raise Exception(f"Couldn't get ip for container {cont}")


class StepInstructions(TypedDict, total=True):
    id: int
    weight: float
    test_type_name: str
    data: 'psef.helpers.JSONType'


class SuiteInstructions(TypedDict, total=True):
    id: int
    steps: t.List[StepInstructions]


class SetInstructions(TypedDict, total=True):
    id: int
    suites: t.List[SuiteInstructions]
    stop_points: float


class RunnerInstructions(TypedDict, total=True):
    runner_id: str
    run_id: int
    auto_test_id: int
    result_ids: t.List[int]
    sets: t.List[SetInstructions]
    base_systems: t.List[t.Dict[str, str]]
    fixtures: t.List[t.Tuple[str, int]]
    setup_script: str


def init_app(app: 'psef.PsefFlask') -> None:
    res = {}
    for ip, conf in app.config['__S_AUTO_TEST_CREDENTIALS'].items():
        assert isinstance(conf['password'], str)
        assert isinstance(conf['type'], str)
        typ = auto_test_runners[conf['type']]
        res[ip] = {
            'password': conf['password'],
            'type': typ,
            'disable_origin_check': conf.get('disable_origin_check', False),
        }
    app.config['AUTO_TEST_CREDENTIALS'] = res  # type: ignore


def _push_logging(post_log: t.Callable[[JSONType], object]
                  ) -> t.Callable[[], None]:
    logs: t.List[t.Dict[str, object]] = []
    logs_lock = threading.RLock()

    @psef.logger_callback
    def log_line(logger: object, method_name: str, event_dict: str) -> None:
        json_event = json.loads(event_dict)
        with logs_lock:
            logs.append(json_event)

    stop_event = threading.Event()

    def log_thread() -> None:
        while True:
            stop_event.wait(timeout=15)

            with logs_lock:
                logs_copy = list(logs)
                logs.clear()
            if logs_copy:
                post_log(logs_copy)
            del logs_copy

            if stop_event.is_set():
                return

    thread = threading.Thread(target=log_thread)
    thread.start()

    def stop() -> None:
        stop_event.set()
        thread.join()

    return stop


def start_polling(config: 'psef.FlaskConfig') -> None:
    while True:
        for url, url_config in config['__S_AUTO_TEST_CREDENTIALS'].items():
            logger.try_unbind('server')
            logger.bind(server=url)
            logger.info('Checking next server')

            try:
                response = requests.get(
                    f'{url}/api/v-internal/auto_tests/',
                    params={
                        'get': 'tests_to_run',
                    },
                    headers={
                        'CG-Internal-Api-Password':
                            f'NOT_PRESENT@:@{url_config["password"]}',
                    }
                )
            except requests.exceptions.RequestException:
                logger.error('Failed to get server', exc_info=True)
                continue

            if response.status_code == 200:
                data = response.json()
                logger.info('Got test', response=response, json=data)
                typ = auto_test_runners[url_config['type']]

                typ(
                    t.cast(URL,
                           url_config.get('container_url') or url), data,
                    url_config['password'], config
                ).run_test()
                break
            else:
                logger.info('No tests found', response=response)
                continue
        else:
            sleep_time = config['AUTO_TEST_POLL_TIME']
            logger.info('Tried all servers, sleeping', sleep_time=sleep_time)
            time.sleep(sleep_time)

        logger.try_unbind('server')


class StartedContainer:
    def __init__(
        self, container: lxc.Container, name: str, config: 'psef.FlaskConfig'
    ) -> None:
        self._snapshots: t.List[str] = []
        self._dirty = False
        self._container = container
        self._config = config
        self._name = name

    def destroy_snapshots(self) -> None:
        self.stop_container()
        with timed_code(
            'destroy_snapshots', snapshot_amount=len(self._snapshots)
        ):
            while self._snapshots:
                self._container.snapshot_destroy(self._snapshots.pop())

    def set_cgroup_item(self, key: str, value: str) -> None:
        success = self._container.set_cgroup_item(key, value)
        if not success:
            raise ValueError(f'Could not set "{key}" to "{value}"')

    def stop_container(self) -> None:
        with timed_code('stop_container', container=self._name):
            assert self._container.stop()
            assert self._container.wait('STOPPED', 3)

    def _create_snapshot(self) -> None:
        snap = self._container.snapshot()
        assert isinstance(snap, str)
        self._snapshots.append(snap)
        self._dirty = False

    @contextlib.contextmanager
    def as_snapshot(self) -> t.Generator['StartedContainer', None, None]:
        maybe_stop_container()

        # NOTE: This code never destroys snapshots, as this logic makes the
        # function way harder to follow. As we keep a dirty flag, only one
        # snapsnot will probably be created.

        try:
            if self._dirty or not self._snapshots:
                with timed_code(
                    'create_snapshot',
                    container=self._name,
                    amount_of_snapshots=len(self._snapshots)
                ):
                    self.stop_container()
                    self._create_snapshot()
                    _start_container(self._container)
            else:
                logger.info(
                    'Snapshot creation not needed',
                    snapshots=self._snapshots,
                    dirty=self._dirty
                )
            yield self
        finally:
            self.stop_container()
            # Creating the snapshot, so we might not have a snapshot
            if self._snapshots:
                with timed_code('restore_snapshots'):
                    self._container.snapshot_restore(self._snapshots[-1])
                self._dirty = False
            _start_container(self._container)

    def _read_fifo(
        self, callback: t.Optional[OutputCallback], fname: str
    ) -> None:
        with open(fname, 'rb') as f:
            while True:
                maybe_stop_container()
                line = f.readline()
                if not line:
                    return
                if callback is not None:
                    callback(line)

    def _change_user(self, username: str) -> None:
        pw_record = pwd.getpwnam(username)
        user_uid = pw_record.pw_uid
        user_gid = pw_record.pw_gid

        path = os.environ['PATH']
        # Converting to a list is important here as we mutate the object in the
        # body of the loop.
        for key in list(os.environ):
            del os.environ[key]

        os.environ['PATH'] = path
        os.environ['USER'] = username
        os.environ['HOME'] = pw_record.pw_dir
        os.environ['LOGUSER'] = username

        os.setgid(user_gid)
        os.setuid(user_uid)

    def _run_command(
        self, cmd_user: t.Tuple[t.List[str], t.Optional[str]]
    ) -> int:
        cmd, user = cmd_user
        env = os.environ.copy()
        env['PATH'] += ':/usr/sbin/:/sbin/'

        def preexec() -> None:
            if user:
                self._change_user(user)

        return subprocess.call(cmd, preexec_fn=preexec, env=env)

    def _run_shell(self, cmd_cwd_user: t.Tuple[str, str, str]) -> int:
        cmd, cwd, user = cmd_cwd_user
        env = os.environ.copy()
        env['PATH'] += ':/home/codegrade/student/:/home/codegrade/fixtures/'

        def preexec() -> None:
            self._change_user(user)

        return subprocess.call(
            cmd, shell=True, cwd=cwd, preexec_fn=preexec, env=env
        )

    def run_student_command(
        self,
        cmd: str,
        stdin: t.Union[None, bytes, t.BinaryIO] = None,
    ) -> t.Tuple[int, str, str]:
        stdout: t.List[bytes] = []
        stderr: t.List[bytes] = []

        user = 'codegrade'
        cwd = '/home/codegrade/student/'
        timeout = self._config['AUTO_TEST_MAX_TIME_SINGLE_RUN']
        assert timeout > 0
        max_size = self._config['AUTO_TEST_OUTPUT_LIMIT']
        assert max_size > 0

        size_lock = threading.RLock()
        total_size = 0

        def make_add_function(lst: t.List[bytes]) -> t.Callable[[bytes], None]:
            if max_size is None:
                return lst.append
            else:

                def fun(data: bytes) -> None:
                    nonlocal total_size
                    assert max_size is not None
                    with size_lock:
                        if total_size >= max_size:
                            return
                        size_left = max_size - total_size
                        if len(data) > size_left:
                            lst.append(data[:size_left])
                            lst.append(b' <OUTPUT TRUNCATED>\n')
                        else:
                            lst.append(data)
                        total_size += len(data)

                return fun

        code = self._run(
            cmd=(cmd, cwd, user),
            callback=self._run_shell,
            stdout=make_add_function(stdout),
            stderr=make_add_function(stderr),
            stdin=stdin,
            check=False,
            timeout=timeout,
        )

        stdout_str, stderr_str = [
            b''.join(v).decode('utf-8', 'backslashreplace')
            for v in [stdout, stderr]
        ]
        return code, stdout_str, stderr_str

    def run_command(
        self,
        cmd: t.List[str],
        stdout: t.Optional[OutputCallback] = None,
        stderr: t.Optional[OutputCallback] = None,
        stdin: t.Union[None, bytes, t.BinaryIO] = None,
        user: t.Optional[str] = None,
        check: bool = True,
    ) -> int:
        return self._run(
            (cmd, user),
            self._run_command,
            stdout,
            stderr,
            stdin,
            check,
            timeout=None
        )

    def _run(
        self,
        cmd: T,
        callback: t.Callable[[T], int],
        stdout: t.Optional[OutputCallback],
        stderr: t.Optional[OutputCallback],
        stdin: t.Union[None, bytes, t.BinaryIO],
        check: bool,
        timeout: t.Optional[int],
    ) -> int:
        self._dirty = True

        with bound_to_logger(
            cmd=cmd, timeout=timeout
        ), tempfile.TemporaryDirectory(
        ) as output_dir, tempfile.NamedTemporaryFile() as stdin_file, open(
            '/dev/null', 'r'
        ) as dev_null:
            logger.info('Running command')
            local_logger = structlog.threadlocal.as_immutable(logger)

            if isinstance(stdin, bytes):
                os.chmod(stdin_file.name, 0o777)
                stdin_file.write(stdin)
                stdin_file.flush()
            elif stdin is not None:
                stdin_file = dev_null

            stdout_fifo = os.path.join(output_dir, 'stdout')
            os.mkfifo(stdout_fifo)
            stderr_fifo = os.path.join(output_dir, 'stderr')
            os.mkfifo(stderr_fifo)

            def _make_log_function(log_location: str
                                   ) -> t.Callable[[bytes], None]:
                def inner(log_line: bytes) -> None:
                    local_logger.info(
                        'Got output from command',
                        location=log_location,
                        output=log_line
                    )

                return inner

            stdout_thread = threading.Thread(
                target=self._read_fifo,
                args=(stdout or _make_log_function('stdout'), stdout_fifo)
            )
            stderr_thread = threading.Thread(
                target=self._read_fifo,
                args=(stderr or _make_log_function('stderr'), stderr_fifo)
            )
            stdout_thread.start()
            stderr_thread.start()

            # The order is really important here! We first need to close the
            # two fifo files before we join our threads. As otherwise the
            # threads will hang because they are still reading from these
            # files.
            with defer(stdout_thread.join), defer(stderr_thread.join), open(
                stdout_fifo,
                'wb',
            ) as out, open(
                stderr_fifo,
                'wb',
            ) as err:
                assert timeout is None or timeout > 0
                start = datetime.datetime.utcnow()
                maybe_stop_container()

                pid = self._container.attach(
                    callback,
                    cmd,
                    stdout=out,
                    stderr=err,
                    stdin=stdin_file,
                )
                while not STOP_CONTAINERS.is_set() and (
                    timeout is None or
                    (datetime.datetime.utcnow() - start).total_seconds() <
                    timeout
                ):
                    try:
                        new_pid, status = os.waitpid(pid, os.WNOHANG)
                        if new_pid == status == 0 or not os.WIFEXITED(status):
                            time.sleep(0.5)
                            continue
                        res = os.WEXITSTATUS(status)
                        break
                    except OSError as e:
                        if e.errno == errno.EINTR:
                            continue
                        raise
                else:
                    logger.warning('Process took too long, killing', pid=pid)
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    logger.warning('Killing done', pid=pid)
                    maybe_stop_container()
                    raise CommandTimeoutException

            maybe_stop_container()

            if check and res != 0:
                raise RuntimeError(f'Command "{cmd}" crashed: {res}')

            return res


class AutoTestContainer:
    def __init__(
        self,
        name: str,
        config: 'psef.FlaskConfig',
        cont: t.Optional[lxc.Container] = None
    ) -> None:
        self._name = name
        self._lock = threading.RLock()
        self._config = config
        if cont is None:
            self._cont = lxc.Container(name)
        else:
            self._cont = cont

    @contextlib.contextmanager
    def started_container(self) -> t.Generator[StartedContainer, None, None]:
        started = None

        try:
            _start_container(self._cont)
            started = StartedContainer(self._cont, self._name, self._config)
            yield started
        finally:
            self._stop_container(started)

    def _stop_container(self, cont: t.Optional[StartedContainer]) -> None:
        with bound_to_logger(cont=self):
            logger.info('Stopping container', cont=self)
            try:
                if self._cont.running:
                    self._cont.stop()
                    self._cont.wait('STOPPED', 3)
                if cont is not None:
                    logger.info('Destroying snapshots')
                    cont.destroy_snapshots()
            finally:
                with timed_code('destroy_container'):
                    self._cont.destroy()

    def create(self) -> None:
        assert self._cont.create(
            'download',
            0, {
                'dist': 'ubuntu',
                'release': 'bionic',
                'arch': 'amd64',
            },
            bdevtype=self._config['AUTO_TEST_BDEVTYPE']
        )

    def clone(self, new_name: str = '') -> 'AutoTestContainer':
        maybe_stop_container()

        new_name = new_name or get_new_container_name()

        with self._lock:
            cont = self._cont.clone(new_name)
            assert isinstance(cont, lxc.Container)
            return type(self)(new_name, self._config, cont)


class AutoTestRunner(abc.ABC):
    def __init__(
        self, base_url: URL, instructions: RunnerInstructions,
        global_password: str, config: 'psef.FlaskConfig'
    ) -> None:
        self.base_url = base_url
        self._global_password = global_password
        self.instructions = instructions
        self.auto_test_id = instructions['auto_test_id']
        self.config = config
        self.setup_script = self.instructions['setup_script']

        with open(
            os.path.join(
                os.path.dirname(__file__), '..', '..', 'seed_data',
                'auto_test_base_systems.json'
            ), 'r'
        ) as f:
            self.base_systems = [
                val for val in json.load(f)
                if val['id'] in self.instructions['base_systems']
            ]
        self.fixtures = self.instructions['fixtures']

        self.req = requests.Session()
        self.req.headers.update({'CG-Internal-Api-Password': self.password})

    @property
    def password(self) -> str:
        return f'{self.instructions["runner_id"]}@:@{self._global_password}'

    @abc.abstractmethod
    def run_test(self) -> None:
        ...

    @classmethod
    def after_run(cls, runner: 'models.AutoTestRunner') -> None:
        logger.info('Call after run!')

    def make_container(self) -> AutoTestContainer:
        return AutoTestContainer(get_new_container_name(), self.config)


@auto_test_runners.register('simple_runner')
class _SimpleAutoTestRunner(AutoTestRunner):
    def _install_base_systems(self, cont: StartedContainer) -> None:
        for system in self.base_systems:
            for cmd in system['setup_commands']:
                cont.run_command(cmd)

    def _finalize_base_systems(self, cont: StartedContainer) -> None:
        for system in self.base_systems:
            for cmd in system.get('pre_start_commands', []):
                cont.run_command(cmd)

    def copy_file(
        self, container: StartedContainer, src: str, dst: str
    ) -> None:
        with open(src, 'rb') as f:
            container.run_command(['dd', 'status=none', f'of={dst}'], stdin=f)
        container.run_command(['chmod', '+x', dst])

    def download_fixtures(self, cont: StartedContainer) -> None:
        cont.run_command(
            ['mkdir', '/home/codegrade/fixtures/'], user='codegrade'
        )

        for name, fixture_id in self.fixtures:
            url = (
                f'{self.base_url}/api/v-internal/auto_tests/'
                f'{self.auto_test_id}/fixtures/{fixture_id}'
            )
            path = f'/home/codegrade/fixtures/{name}'
            cont.run_command(
                [
                    'wget',
                    '--header',
                    f'CG-Internal-Api-Password: {self.password}',
                    url,
                    '-O',
                    path,
                ],
                user='codegrade'
            )
            logger.info('Downloaded fixtures', name=name, url=url)

        cont.run_command(
            ['chmod', '-R', '+x', '/home/codegrade/fixtures/'],
            user='codegrade'
        )
        cont.run_command(
            ['ls', '-hl', '/home/codegrade/fixtures/'],
            user='codegrade',
        )

    def download_student_code(
        self, cont: StartedContainer, result_id: int
    ) -> None:
        url = (
            f'{self.base_url}/api/v-internal/auto_tests/'
            f'{self.auto_test_id}/results/{result_id}?type=submission_files'
        )

        logger.info('Downloading student code', url=url)
        cont.run_command(
            [
                'wget',
                f'--header=CG-Internal-Api-Password: {self.password}',
                url,
                '-O',
                '/home/codegrade/student.zip',
            ],
            user='codegrade'
        )
        logger.info('Downloaded student code', url=url)

        cont.run_command(
            ['mkdir', '-p', '/home/codegrade/student/'], user='codegrade'
        )
        cont.run_command(
            [
                'unzip', '/home/codegrade/student.zip', '-d',
                '/home/codegrade/student/'
            ],
            user='codegrade',
        )
        logger.info('Extracted student code')

        cont.run_command(
            ['chmod', '-R', '+x', '/home/codegrade/student/'],
            user='codegrade'
        )
        cont.run_command(['rm', '-f', '/home/codegrade/student.zip'])

    def _run_test_suite(
        self, student_container: StartedContainer, result_id: int,
        test_suite: SuiteInstructions
    ) -> float:
        total_points = 0.0

        with student_container.as_snapshot() as snap:
            url = (
                f'{self.base_url}/api/v-internal/auto_tests/'
                f'{self.auto_test_id}/results/{result_id}/'
                f'step_results/'
            )

            for test_step in test_suite['steps']:
                logger.info('Running step', step=test_step)
                step_result_id: t.Optional[int] = None

                def update_test_result(
                    state: models.AutoTestStepResultState,
                    log: t.Dict[str, object]
                ) -> None:
                    nonlocal step_result_id
                    data = {
                        'log': log,
                        'state': state.name,
                        'auto_test_step_id': test_step['id'],
                    }
                    if step_result_id is not None:
                        data['id'] = step_result_id

                    logger.info('Posting result data', json=data, url=url)
                    response = self.req.put(
                        url,
                        json=data,
                    )
                    logger.info('Posted result data', response=response)
                    assert response.status_code == 200
                    step_result_id = response.json()['id']

                typ = auto_test_handlers[test_step['test_type_name']]

                try:
                    logger.bind(step=test_step)
                    total_points += typ(test_step['data']).execute_step(
                        snap, update_test_result, test_step, total_points
                    )
                except StopRunningStepsException:
                    logger.info('Stopping steps', exc_info=True)
                    break
                except CommandTimeoutException:
                    logger.warning('Command timed out', exc_info=True)
                    update_test_result(
                        models.AutoTestStepResultState.timed_out, {}
                    )
                else:
                    logger.info('Ran step')
                finally:
                    logger.try_unbind('step')

        return total_points

    def run_student(
        self,
        base_container: AutoTestContainer,
        cpu_queue: 'Queue[int]',
        result_id: int,
    ) -> None:
        student_container = base_container.clone()
        cpu_number = cpu_queue.get()

        result_url = (
            f'{self.base_url}/api/v-internal/auto_tests/'
            f'{self.auto_test_id}/results/{result_id}'
        )
        result_state = models.AutoTestStepResultState.running

        try:
            logger.bind(result_id=result_id)

            self.req.patch(
                result_url,
                json={'state': result_state.name},
            )

            with student_container.started_container() as cont:

                cont.set_cgroup_item(
                    'memory.limit_in_bytes',
                    self.config['AUTO_TEST_MEMORY_LIMIT']
                )
                cont.set_cgroup_item('cpuset.cpus', str(cpu_number))
                cont.set_cgroup_item(
                    'memory.memsw.limit_in_bytes',
                    self.config['AUTO_TEST_MEMORY_LIMIT']
                )

                self.download_student_code(cont, result_id)

                if self.setup_script:
                    logger.info('Running setup script')
                    _, stdout, stderr = cont.run_student_command(
                        self.setup_script
                    )

                    self.req.patch(
                        result_url,
                        json={
                            'setup_stdout': stdout,
                            'setup_stderr': stderr
                        },
                    )

                logger.info('Dropping sudo rights')
                cont.run_command(['deluser', 'codegrade', 'sudo'])

                total_points = 0.0

                for test_set in self.instructions['sets']:
                    for test_suite in test_set['suites']:
                        total_points += self._run_test_suite(
                            cont, result_id, test_suite
                        )
                    if total_points < test_set['stop_points']:
                        break
        except CommandTimeoutException:
            logger.error('Command timed out', exc_info=True)
            result_state = models.AutoTestStepResultState.timed_out
        except:
            logger.error('Something went wrong', exc_info=True)
            result_state = models.AutoTestStepResultState.failed
            raise
        else:
            result_state = models.AutoTestStepResultState.passed
        finally:
            cpu_queue.put(cpu_number)
            logger.try_unbind('result_id')
            self.req.patch(
                result_url,
                json={'state': result_state.name},
            )

    def run_test(self) -> None:
        stop_logger = _push_logging(
            lambda logs: self.req.post(
                (
                    f'{self.base_url}/api/v-internal/auto_tests/'
                    f'{self.auto_test_id}/runs/{self.instructions["run_id"]}/'
                    'logs/'
                ),
                json={'logs': logs},
            )
        )
        run_result_url = (
            f'{self.base_url}/api/v-internal/auto_tests/'
            f'{self.auto_test_id}/runs/{self.instructions["run_id"]}'
        )

        self.req.patch(
            run_result_url,
            json={'state': models.AutoTestRunState.running.name},
        )
        try:
            with timed_code('run_complete_auto_test'):
                self._run_test()
        except:
            logger.warning('Something went wrong running tests', exc_info=True)
            end_state = models.AutoTestRunState.crashed.name
        else:
            logger.info('Finished running tests')
            end_state = models.AutoTestRunState.done.name
        finally:
            try:
                self.req.patch(
                    run_result_url,
                    json={'state': end_state},
                )
            finally:
                stop_logger()

    def _run_test(self) -> None:
        ensure_on_test_server()

        STOP_CONTAINERS.clear()

        # We use uuid1 as this is always unique for a single machine
        base_container = self.make_container()
        base_container.create()

        with base_container.started_container() as cont:
            cont.run_command(['apt', 'update'])
            cont.run_command(['apt', 'upgrade', '-y'])

            # Install useful commands
            cont.run_command(['apt', 'install', '-y', 'wget', 'curl', 'unzip'])

            self.copy_file(
                cont,
                (
                    f'{os.path.dirname(__file__)}/'
                    '../../seed_data/install_pyenv.sh'
                ),
                '/usr/bin/install_pyenv.sh',
            )

            self._install_base_systems(cont)

            cont.run_command(
                ['adduser', '--disabled-password', '--gecos', '', 'codegrade'],
            )

            cont.run_command(['usermod', '-aG', 'sudo', 'codegrade'])

            self.download_fixtures(cont)
            self._finalize_base_systems(cont)

            cont.stop_container()
            del cont

            with Pool(get_amount_cpus()) as pool:
                q: 'Queue[int]' = Queue(maxsize=get_amount_cpus())
                for i in range(get_amount_cpus()):
                    q.put(i)

                try:
                    res = pool.starmap_async(
                        self.run_student, [
                            (base_container, q, res_id)
                            for res_id in self.instructions['result_ids']
                        ]
                    )
                    while True:
                        try:
                            res.get(60)
                        except context.TimeoutError:
                            continue
                        else:
                            break
                finally:
                    logger.info('Done with containers, cleaning up')
                    STOP_CONTAINERS.set()
                    pool.terminate()
                    pool.join()


@auto_test_runners.register('transip_runner')
class _TransipAutoTestRunner(_SimpleAutoTestRunner):
    @staticmethod
    def _retry_vps_action(
        action_name: str, func: t.Callable[[], object], max_tries: int = 50
    ) -> None:
        with bound_to_logger(
            action=action_name,
        ), timed_code('_retry_vps_action'):
            for _ in range(max_tries):
                try:
                    func()
                except WebFault:
                    logger.info('Could not perform action yet', exc_info=True)
                    time.sleep(1)
                else:
                    break
            else:
                logger.error("Couldn't perform action")
                raise TimeoutError

    @classmethod
    def after_run(self, runner: 'models.AutoTestRunner') -> None:
        username = psef.current_app.config['_TRANSIP_USERNAME']
        key_file = psef.current_app.config['_TRANSIP_PRIVATE_KEY_FILE']
        vs = transip.service.VpsService(username, private_key_file=key_file)
        vps, = [
            vps for vps in vs.get_vpses() if vps['ipAddress'] == runner.ipaddr
        ]
        with bound_to_logger(vps=vps):
            vps_name = vps['name']
            snapshots = vs.get_snapshots_by_vps(vps_name)
            snapshot = min(snapshots, key=lambda s: s['dateTimeCreate'])
            self._retry_vps_action('stopping vps', lambda: vs.stop(vps_name))
            self._retry_vps_action(
                'reverting snapshot',
                lambda: vs.revert_snapshot(vps_name, snapshot['name']),
            )
