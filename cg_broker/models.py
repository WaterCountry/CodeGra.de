"""This file defines all database models and enums used by the broker.

SPDX-License-Identifier: AGPL-3.0-only
"""
import enum
import time
import uuid
import typing as t
import secrets
import dataclasses
from datetime import timedelta

import boto3
import structlog
import sqlalchemy
import transip.service
from suds import WebFault
from sqlalchemy_utils import UUIDType
from botocore.exceptions import ClientError

import cg_broker
import cg_sqlalchemy_helpers as cgs
from cg_logger import bound_to_logger
from cg_timers import timed_code
from cg_dt_utils import DatetimeWithTimezone
from cg_flask_helpers import callback_after_this_request
from cg_sqlalchemy_helpers import JSONB, types, mixins, hybrid_property

from . import BrokerFlask, app, utils

logger = structlog.get_logger()

db: cgs.types.MyDb = cgs.make_db()

T = t.TypeVar('T')


def init_app(flask_app: BrokerFlask) -> None:
    cgs.init_app(db, flask_app)


if t.TYPE_CHECKING:  # pragma: no cover
    from cg_sqlalchemy_helpers.types import Base
else:
    Base: cgs.types.Base = db.Model  # pylint: disable=invalid-name

_T = t.TypeVar('_T', bound='Base')

_Y = t.TypeVar('_Y', bound='Runner')


@enum.unique
class RunnerState(enum.IntEnum):
    """This enum the possible states a runner can be in.

    A runner should never decrease its state.
    """
    not_running = 1
    creating = 2
    started = 3
    running = 4
    cleaning = 5
    cleaned = 6

    @classmethod
    def get_before_started_states(cls) -> t.List['RunnerState']:
        """Get the states in which a is runner before it posted to the alive
            route.
        """
        return [cls.not_running, cls.creating]

    @classmethod
    def get_before_running_states(cls) -> t.List['RunnerState']:
        """Get the states in which a is runner before it has ever done any
            work.

        This states are considered "safe", i.e. we can still make it switch
        jobs.
        """
        return [*cls.get_before_started_states(), cls.started]

    @classmethod
    def get_active_states(cls) -> t.List['RunnerState']:
        """Get the states in which a runner is considered active.
        """
        return [*cls.get_before_running_states(), cls.running]


@enum.unique
class RunnerType(enum.Enum):
    """This enum defines all possible platforms available for runners.

    The platform used is defined in the configuration file.
    """
    aws = enum.auto()
    transip = enum.auto()
    dev_runner = enum.auto()


class Runner(Base, mixins.TimestampMixin, mixins.UUIDMixin):
    """This class represents a abstract runner.

    A runner is used one time to execute a job.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        __mapper__: t.ClassVar[cgs.types.Mapper['Runner']]

    __tablename__ = 'runner'

    ipaddr = db.Column(
        'ipaddr', db.Unicode, nullable=True, default=None, index=True
    )
    _runner_type = db.Column('type', db.Enum(RunnerType), nullable=False)
    state = db.Column(
        'state',
        db.Enum(RunnerState),
        nullable=False,
        # We constantly filter on the state, so it makes to have an index on
        # this column.
        index=True,
        default=RunnerState.not_running
    )
    started_at = db.Column(
        db.TIMESTAMP(timezone=True), default=None, nullable=True
    )

    # The id used by the provider of this execution unit
    instance_id = db.Column('instance_id', db.Unicode, nullable=True)
    last_log_emitted = db.Column(
        'last_log_emitted', db.Boolean, nullable=False, default=False
    )

    job_id = db.Column(
        'job_id',
        db.Integer,
        db.ForeignKey('job.id'),
        nullable=True,
        default=None,
        unique=False
    )

    job = db.relationship(
        lambda: Job,
        foreign_keys=job_id,
        back_populates='runners',
    )

    public_id = db.Column(
        'public_id',
        UUIDType,
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        server_default=sqlalchemy.func.uuid_generate_v4(),
    )

    _pass = db.Column(
        'pass',
        db.Unicode,
        unique=False,
        nullable=False,
        default=utils.make_password,
        server_default=sqlalchemy.func.cast(
            sqlalchemy.func.uuid_generate_v4(),
            db.Unicode,
        )
    )

    def __to_json__(self) -> t.Mapping[str, str]:
        return {'id': str(self.public_id)}

    def cleanup_runner(self, shutdown_only: bool) -> None:
        raise NotImplementedError

    def start_runner(self) -> None:
        raise NotImplementedError

    def is_pass_valid(self, requesting_pass: str) -> bool:
        return secrets.compare_digest(self._pass, requesting_pass)

    def is_ip_valid(self, requesting_ip: str) -> bool:
        """Check if the requesting ip is valid for this Runner.
        """
        if self.ipaddr is None:
            return False
        return secrets.compare_digest(self.ipaddr, requesting_ip)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Runner):
            return self.id == other.id
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        return not self == other

    @property
    def is_before_run(self) -> bool:
        """Is this runner in a state before it started executing any code.
        """
        return self.state in RunnerState.get_before_running_states()

    @property
    def should_clean(self) -> bool:
        """Is this runner in a state where it still needs cleaning.

        This is always true if the runner is not cleaned or currently being
        cleaned.
        """
        return self.state not in {RunnerState.cleaned, RunnerState.cleaning}

    @classmethod
    def get_amount_of_startable_runners(cls) -> int:
        """Get the amount of runners that can still be started.
        """
        active = len(cls.get_all_active_runners().with_for_update().all())
        max_amount = app.config['MAX_AMOUNT_OF_RUNNERS']
        return max(max_amount - active, 0)

    @classmethod
    def can_start_more_runners(cls) -> bool:
        """Is it currently allowed to start more runners.

        This checks the amount of runners currently active and makes sure this
        is less than the maximum amount of runners.
        """
        # We do a all and len here as count() and with_for_update cannot be
        # used in combination.
        amount = len(cls.get_all_active_runners().with_for_update().all())

        max_amount = app.config['MAX_AMOUNT_OF_RUNNERS']
        can_start = amount < max_amount
        logger.info(
            'Checking if we can start more runners',
            running_runners=amount,
            maximum_amount=max_amount,
            can_start_more=can_start
        )
        if not can_start:
            logger.warning('Too many runners active', active_amount=amount)
        return can_start

    @classmethod
    def _create(cls: t.Type[_Y]) -> _Y:
        return cls()

    @classmethod
    def create_of_type(cls, typ: RunnerType) -> 'Runner':
        """Create a runner of the given type.

        :param typ: The type of runner you want to create.
        :returns: The newly created runner.
        """
        return cls.__mapper__.polymorphic_map[typ].class_._create()  # pylint: disable=protected-access

    @classmethod
    def get_all_active_runners(cls) -> types.MyQuery['Runner']:
        """Get a query to get all the currently active runners.

        .. warning::

            This query does not lock these runners so do so yourself if that is
            needed.
        """
        return db.session.query(cls).filter(
            cls.state.in_(RunnerState.get_active_states())
        )

    @classmethod
    def get_before_active_unassigned_runners(cls) -> types.MyQuery['Runner']:
        """Get all runners runners that are not running yet, and are not
        assigned.
        """
        return db.session.query(cls).filter(
            cls.state.in_(RunnerState.get_before_running_states()),
            cls.job_id.is_(None)
        )

    def make_unassigned(self) -> None:
        """Make this runner unassigned.

        .. note::

            This also starts a job to kill this runner after a certain amount
            of time if it is still unassigned.
        """
        self.job_id = None
        eta = DatetimeWithTimezone.utcnow() + timedelta(
            minutes=app.config['RUNNER_MAX_TIME_ALIVE']
        )
        runner_hex_id = self.id.hex

        callback_after_this_request(
            lambda: cg_broker.tasks.maybe_kill_unneeded_runner.apply_async(
                (runner_hex_id, ),
                eta=eta,
            )
        )

    def kill(self, *, maybe_start_new: bool, shutdown_only: bool) -> None:
        """Kill this runner and maybe start a new one.

        :param maybe_start_new: Should we maybe start a new runner after
            killing this one.
        """
        self.state = RunnerState.cleaning
        db.session.commit()
        self.cleanup_runner(shutdown_only)
        self.state = RunnerState.cleaned
        db.session.commit()

        if maybe_start_new:
            cg_broker.tasks.maybe_start_more_runners.delay()

    def __structlog__(self) -> t.Dict[str, t.Union[str, int, None]]:
        return {
            'type': str(type(self)),
            'id': self.id.hex,
            'state': self.state.name,
            'job_id': self.job_id,
            'ipaddr': self.ipaddr,
        }

    __mapper_args__ = {
        'polymorphic_on': _runner_type,
        'polymorphic_identity': '__non_existing__',
    }


class DevRunner(Runner):
    """This class represents a local runner, which provides zero additional
    sandboxing.

    .. danger:: Never use this runner during production.
    """
    __mapper_args__ = {
        'polymorphic_identity': RunnerType.dev_runner,
    }

    @classmethod
    def _create(cls: t.Type[_Y]) -> _Y:
        return cls(ipaddr='127.0.0.1')

    def start_runner(self) -> None:
        pass

    def cleanup_runner(self, shutdown_only: bool) -> None:
        pass


class TransipRunner(Runner):
    """This is a runner which runs using transip virtual machines.

    It is interesting to note that these machines are never terminated, their
    snapshots are simply restored.
    """

    def start_runner(self) -> None:
        pass

    def cleanup_runner(self, shutdown_only: bool) -> None:
        username = app.config['_TRANSIP_USERNAME']
        key_file = app.config['_TRANSIP_PRIVATE_KEY_FILE']
        vps_service = transip.service.VpsService(
            username, private_key_file=key_file
        )
        vps, = [
            vps for vps in vps_service.get_vpses()
            if vps['ipAddress'] == self.ipaddr
        ]
        assert vps['name'] == self.instance_id

        with bound_to_logger(vps=vps):
            vps_name = vps['name']
            snapshots = vps_service.get_snapshots_by_vps(vps_name)
            snapshot = min(snapshots, key=lambda s: s['dateTimeCreate'])
            self._retry_vps_action(
                'stopping vps', lambda: vps_service.stop(vps_name)
            )
            self._retry_vps_action(
                'reverting snapshot',
                lambda: vps_service.
                revert_snapshot(vps_name, snapshot['name']),
            )

    @staticmethod
    def _retry_vps_action(
        action_name: str, func: t.Callable[[], object], max_tries: int = 50
    ) -> None:
        with bound_to_logger(
            action=action_name,
        ), timed_code('_retry_vps_action'):
            for idx in range(max_tries):
                try:
                    func()
                except WebFault:
                    logger.info('Could not perform action yet', exc_info=True)
                    time.sleep(idx)
                else:
                    break
            else:
                logger.error("Couldn't perform action")
                raise TimeoutError

    __mapper_args__ = {'polymorphic_identity': RunnerType.transip}


class AWSRunner(Runner):
    """This class represents a runner which is running on the AWS platform.
    """

    def start_runner(self) -> None:
        assert self.instance_id is None
        assert self._pass is not None

        client = boto3.client('ec2')
        ec2 = boto3.resource('ec2')

        images = client.describe_images(
            Owners=['self'],
            Filters=[{
                'Name': 'tag:AutoTest',
                'Values': [app.config['AWS_TAG_VALUE']]
            }],
        ).get('Images', [])
        assert images
        image = max(images, key=lambda image: image['CreationDate'])

        logger.info(
            'Creating AWS instance',
            instance_type=app.config['AWS_INSTANCE_TYPE'],
            image_id=image['ImageId']
        )

        inst, = ec2.create_instances(
            ImageId=image['ImageId'],
            InstanceType=app.config['AWS_INSTANCE_TYPE'],
            MaxCount=1,
            MinCount=1,
            UserData="""#!/bin/bash
F="{config_dir}/.runner-pass"
echo "{password}" > "$F"
chmod 777 "$F"
            """.format(
                password=self._pass,
                config_dir=app.config['RUNNER_CONFIG_DIR'],
            )
        )

        with bound_to_logger(instance=inst):
            logger.info('Started AWS instance, waiting for network')

            self.instance_id = inst.id

            for _ in range(120):
                try:
                    inst = ec2.Instance(inst.id)
                    if inst.public_ip_address:
                        logger.info('AWS instance up')
                        self.ipaddr = inst.public_ip_address
                        return
                except ClientError as e:
                    err = e.response.get('Error', {})
                    if err.get('Code', '') != 'InvalidInstanceID.NotFound':
                        raise
                time.sleep(1)

            logger.error('Timed out waiting on AWS instance')
            raise TimeoutError

    def cleanup_runner(self, shutdown_only: bool) -> None:
        assert self.instance_id
        client = boto3.client('ec2')
        if shutdown_only:
            client.stop_instances(
                InstanceIds=[self.instance_id], Hibernate=False
            )
        else:
            client.terminate_instances(InstanceIds=[self.instance_id])

    __mapper_args__ = {'polymorphic_identity': RunnerType.aws}


@enum.unique
class JobState(enum.IntEnum):
    """This enum represents the current state of the Job.

    A job can never decrease its state, so when it is finished it can never be
    started again.
    """
    waiting_for_runner = 1
    started = 2
    finished = 3

    @property
    def is_finished(self) -> bool:
        """Is this a finished state.
        """
        return self == self.finished

    @property
    def is_waiting_for_runner(self) -> bool:
        """Is this waiting for a runner
        """
        return self == self.waiting_for_runner

    @classmethod
    def get_finished_states(cls) -> t.Sequence['JobState']:
        """Get the states that are considered finished.
        """
        return [cls.finished]


class Job(Base, mixins.TimestampMixin, mixins.IdMixin):
    """This class represents a single job.

    A job is something a CodeGrade instance needs a runner for. These jobs are
    never deleted, but its state changes during its life.
    """
    __tablename__ = 'job'

    _state = db.Column(
        'state',
        db.Enum(JobState),
        nullable=False,
        # We constantly filter on the state, so it makes to have an index on
        # this column.
        index=True,
        default=JobState.waiting_for_runner
    )

    cg_url = db.Column('cg_url', db.Unicode, nullable=False)

    # It is important that this is really unique!
    remote_id = db.Column(
        'remote_id', db.Unicode, nullable=False, index=True, unique=True
    )
    runners = db.relationship(
        Runner, back_populates='job', uselist=True, lazy='selectin'
    )

    job_metadata = db.Column('job_metadata', JSONB, nullable=True, default={})

    def update_metadata(self, new_values: t.Dict[str, object]) -> None:
        self.job_metadata = {**(self.job_metadata or {}), **new_values}

    _wanted_runners = db.Column(
        'wanted_runners',
        db.Integer,
        default=1,
        server_default='1',
        nullable=False
    )

    def _get_wanted_runners(self) -> int:
        """The amount of runners this job wants.
        """
        return self._wanted_runners

    def _set_wanted_runners(self, new_value: int) -> None:
        self._wanted_runners = min(
            max(new_value, 1),
            app.config['MAX_AMOUNT_OF_RUNNERS_PER_JOB'],
        )

    wanted_runners = hybrid_property(_get_wanted_runners, _set_wanted_runners)

    def _get_state(self) -> JobState:
        """Get the state of this job.
        """
        return self._state

    def _set_state(self, new_state: JobState) -> None:
        if new_state < self.state:
            raise ValueError(
                'Cannot decrease the state!', self.state, new_state
            )
        self._state = new_state

    state = hybrid_property(_get_state, _set_state)

    def __init__(
        self,
        remote_id: str,
        cg_url: str,
        state: JobState = JobState.waiting_for_runner,
    ) -> None:
        super().__init__(
            remote_id=remote_id,
            cg_url=cg_url,
            _state=state,
        )

    def get_active_runners(self) -> t.List[Runner]:
        return [
            r for r in self.runners
            if r.state in RunnerState.get_active_states()
        ]

    def __log__(self) -> t.Dict[str, object]:
        return {
            'state': self.state and self.state.name,
            'cg_url': self.cg_url,
            'id': self.id,
        }

    @staticmethod
    def _can_steal_runner(runner: Runner) -> bool:
        """Can this job steal the given runner.

        :param runner: The runner we might want to steal.
        :returns: If we can steal this runner.
        """
        if runner.job is None:
            return True

        # TODO: We might want to check not only if we can steal this runner,
        # but also if we need this runner more than this other job. For example
        # if we want 5 runners but have 4, and this other job wants 10 runners
        # but has 1, we might not want to steal this runner from that other
        # job.
        return any(r != runner for r in runner.job.get_active_runners())

    def maybe_use_runner(self, runner: Runner) -> bool:
        """Maybe use the given ``runner`` for this job.

        This function checks if this job is allowed to use the given
        runner. This is the case if the runner is assigned to us, if it is
        unassigned or we can steal it from another job.

        :param runner: The runner we might want to use.
        :returns: ``True`` if we can use the runner, and ``False`` if we
            cannot.
        """
        if runner in self.runners:
            return True

        active_runners = self.get_active_runners()
        before_active = set(RunnerState.get_before_running_states())

        # In this case we have enough running runners for this job.
        if sum(
            r.state not in before_active for r in active_runners
        ) >= self.wanted_runners:
            logger.info('Too many runners assigned to job')
            return False

        # We want more, but this should only be given if the runner is not
        # needed elsewhere.

        # Runner is unassigned, so get it.
        if runner.job is None:
            self.runners.append(runner)
            # However, we might assume that this runner can be used for other
            # jobs, so we might need to start more runners.
            callback_after_this_request(
                cg_broker.tasks.maybe_start_more_runners.delay
            )
            return True

        # Runner is assigned but we maybe can steal it.
        if self._can_steal_runner(runner):
            logger.info(
                'Stealing runner from job',
                new_job_id=self.id,
                other_job_id=runner.job.id,
                runner=runner,
            )
            self.runners.append(runner)
            unneeded_runner = next(
                (r for r in active_runners if r.state in before_active), None
            )
            too_many_active = len(active_runners) + 1 > self.wanted_runners
            if too_many_active and unneeded_runner:
                # In this case we now have too many runners assigned to us, so
                # make one of the runners unassigned. But only do this if we
                # have a runner which isn't already running.
                unneeded_runner.make_unassigned()

            # The runner we stole might be useful for the other job, as it
            # might have requested extra runners. So we might want to start
            # extra runners.
            callback_after_this_request(
                cg_broker.tasks.maybe_start_more_runners.delay
            )
            return True

        return False

    def __to_json__(self) -> t.Dict[str, object]:
        return {
            'id': self.remote_id,
            'state': self.state.name,
            'wanted_runners': self.wanted_runners,
        }

    def add_runners_to_job(
        self, unassigned_runners: t.List[Runner], startable: int
    ) -> int:
        """Add runners to the given job.

        This adds runners from the ``unassigned_runners`` list to the current
        job, or starts new runners as long as ``startable`` is greater than 0.

        .. note:: The ``unassigned_runners`` list may be mutated in place.

        :param unassigned_runners: Runners that are not assigned yet and can be
            used by this job.
        :param startable: The amount of runners we may start.
        :returns: The amount of new runners started.
        """
        needed = max(0, self.wanted_runners - len(self.get_active_runners()))
        to_start: t.List[uuid.UUID] = []
        created: t.List[Runner] = []

        if needed > 0 and unassigned_runners:
            # We will assign runner that were previously unassigned, so we
            # might need to start some extra runners.
            callback_after_this_request(
                cg_broker.tasks.start_needed_unassigned_runners.delay
            )

        for _ in range(needed):
            if unassigned_runners:
                self.runners.append(unassigned_runners.pop())
            elif startable > 0:
                runner = Runner.create_of_type(app.config['AUTO_TEST_TYPE'])
                self.runners.append(runner)
                db.session.add(runner)
                created.append(runner)
                startable -= 1
            else:
                break

        db.session.flush()

        for runner in created:
            to_start.append(runner.id)

        def start_runners() -> None:
            for runner_id in to_start:
                cg_broker.tasks.start_runner.delay(runner_id.hex)

        callback_after_this_request(start_runners)

        return len(created)


@dataclasses.dataclass(frozen=True)
class _PossibleSetting(t.Generic[T]):
    default_value: T
    type_convert: t.Callable[[str], T]
    input_type: str
    after_update: t.Callable[[], None]


def _after_update_minimum_amount_extra_runners() -> None:
    callback_after_this_request(
        cg_broker.tasks.start_needed_unassigned_runners.delay
    )


@enum.unique
class PossibleSetting(enum.Enum):
    """This enum lists all possible settings that can be set via the web
    interface of the broker.
    """
    minimum_amount_extra_runners = _PossibleSetting(
        default_value=0,
        type_convert=int,
        input_type='number',
        after_update=_after_update_minimum_amount_extra_runners,
    )


class Setting(Base, mixins.TimestampMixin):
    """A setting for the broker that can be changed via an interface on the
    broker's web page.
    """
    setting = db.Column(
        'settting', db.Enum(PossibleSetting), nullable=False, primary_key=True
    )
    value: object = db.Column('value', JSONB, nullable=False)

    # Unfortunately it is not yet possible to create generic enums:
    # https://github.com/python/typing/issues/535
    @classmethod
    def get(cls, setting: PossibleSetting) -> t.Any:
        """Get the current value of this setting.
        """
        found = db.session.query(cls).filter_by(setting=setting).one_or_none()
        if found is None:
            return setting.value.default_value
        return found.value

    @classmethod
    def set(cls, setting: PossibleSetting, value: object) -> None:
        """Set a new value for this setting.
        """
        assert isinstance(value, type(setting.value.default_value))
        found = db.session.query(cls).filter_by(setting=setting).one_or_none()
        logger.info(
            'Setting config setting',
            setting=setting.name,
            new_value=value,
            existing_value=found and found.value,
        )

        # This can lead to an integrity error when two users create the same
        # setting for the first time. But as the broker is only used internally
        # that is not really a problem.
        if found is not None:
            found.value = value
        else:
            new_setting = cls(setting=setting, value=value)
            db.session.add(new_setting)

        setting.value.after_update()
