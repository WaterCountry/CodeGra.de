"""This module defines a File.

SPDX-License-Identifier: AGPL-3.0-only
"""
import os
import enum
import uuid
import shutil
import typing as t
import datetime
from collections import defaultdict

from flask import current_app
from sqlalchemy import event
from sqlalchemy_utils import UUIDType

import psef
from cg_sqlalchemy_helpers.mixins import TimestampMixin

from . import Base, db, _MyQuery
from .. import auth, helpers
from ..exceptions import APICodes, APIException
from ..permissions import CoursePermission

if t.TYPE_CHECKING and getattr(t, 'SPHINX', False):  # pragma: no cover
    # pylint: disable=unused-import
    from . import auto_test as auto_test_models
    from . import work as work_models

T = t.TypeVar('T')


@enum.unique
class FileOwner(enum.IntEnum):
    """Describes to which version of a submission (student's submission or
    teacher's revision) a file belongs. When a student adds or changes a file
    after the deadline for the assignment has passed, the original file's owner
    is set `teacher` and the new file's to `student`.

    :param student: The file is in the student's submission, but changed in the
        teacher's revision.
    :param teacher: The inverse of `student`. The file is added or changed in
        the teacher's revision.
    :param both: The file is not changed in the teacher's revision and belongs
        to both versions.
    """

    student: int = 1
    teacher: int = 2
    both: int = 3


class FileMixin(t.Generic[T]):
    """A mixin for representing a file in the database.
    """

    # The given name of the file.
    name: str = db.Column('name', db.Unicode, nullable=False)

    # This is the filename for the actual file on the disk. This is probably a
    # randomly generated uuid.
    filename: t.Optional[str]
    filename = db.Column('filename', db.Unicode, nullable=True)

    @property
    def id(self) -> T:
        """Get the id in the database of this file.
        """
        raise NotImplementedError

    @property
    def is_directory(self) -> bool:
        """Is this file a directory.
        """
        raise NotImplementedError

    def delete_from_disk(self) -> None:
        """Delete the file from disk if it is not a directory.

        >>> import os
        >>> f = FileMixin()
        >>> f.filename = 'NON_EXISTING'
        >>> f.get_diskname = lambda: f.filename
        >>> f.delete_from_disk() is None
        True
        >>> open('new_file_name', 'w').close()
        >>> f.filename = 'new_file_name'
        >>> os.path.isfile(f.filename)
        True
        >>> f.delete_from_disk()
        >>> os.path.isfile(f.filename)
        False

        :returns: Nothing.
        """
        try:
            os.remove(self.get_diskname())
        except (AssertionError, FileNotFoundError):
            pass

    def get_diskname(self) -> str:
        """Get the absolute path on the disk for this file.

        :returns: The absolute path.
        """
        assert self.filename
        assert not self.is_directory

        return psef.files.safe_join(
            current_app.config['UPLOAD_DIR'], self.filename
        )

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            'id': str(self.id),
            'name': self.name,
        }

    def _inner_list_contents(
        self,
        cache: t.Mapping[T, t.Sequence['FileMixin[T]']],
    ) -> 'psef.files.FileTree[T]':
        entries = None
        if self.is_directory:
            entries = [
                c._inner_list_contents(cache)  # pylint: disable=protected-access
                for c in cache[self.id]
            ]
        return psef.files.FileTree(name=self.name, id=self.id, entries=entries)


NFM_T = t.TypeVar('NFM_T', bound='NestedFileMixin')  # pylint: disable=invalid-name


class NestedFileMixin(FileMixin[T]):
    """A mixin representing nested files, i.e. a structure of directories where
    the children can be either normal files or directories again.

    This mixin should be used by database tables, not for intermediate
    representation of a directory.
    """
    modification_date = db.Column(
        'modification_date', db.DateTime, default=datetime.datetime.utcnow
    )

    if t.TYPE_CHECKING:  # pragma: no cover
        # pylint: disable=unused-argument
        def __init__(
            self,
            name: str,
            parent: t.Optional['NestedFileMixin[T]'],
            is_directory: bool,
            filename: t.Optional[str] = None,
            **extra_opts: object,
        ) -> None:
            ...

    @property
    def parent_id(self) -> T:
        """The id of the parent.
        """
        raise NotImplementedError

    @property
    def parent(self) -> t.Optional['NestedFileMixin[T]']:
        """The parent of this file.

        If ``None`` this file has no parent, i.e. it is a toplevel
        directory/file.
        """
        raise NotImplementedError

    @classmethod
    def create_from_extract_directory(
        cls: 't.Type[NFM_T]',
        tree: 'psef.files.ExtractFileTreeDirectory',
        top: t.Optional['NFM_T'],
        creation_opts: t.Dict[str, t.Any],
    ) -> 'NFM_T':
        """Add the given tree to the session with top as parent.

        :param tree: The file tree as described by
                          :py:func:`psef.files.rename_directory_structure`
        :param top: The parent file
        :returns: Nothing
        """
        new_top = cls(
            is_directory=True,
            name=tree.name,
            parent=top,
            **creation_opts,
        )

        for child in tree.values:
            if isinstance(child, psef.files.ExtractFileTreeDirectory):
                cls.create_from_extract_directory(
                    child, new_top, creation_opts
                )
            elif isinstance(child, psef.files.ExtractFileTreeFile):
                cls(
                    name=child.name,
                    filename=child.disk_name,
                    is_directory=False,
                    parent=new_top,
                    **creation_opts,
                )
            else:
                # The above checks are exhaustive, so this cannot happen
                assert False
        return new_top


class File(NestedFileMixin[int], Base):
    """
    This object describes a file or directory that stored is stored on the
    server.

    Files are always connected to :class:`.work_models.Work` objects. A
    directory file does not physically exist but is stored only in the database
    to preserve the submitted work structure. Each submission should have a
    single top level file. Each other file in a submission should be directly
    or indirectly connected to this file via the parent attribute.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['File']]
    __tablename__ = "File"

    id: int = db.Column('id', db.Integer, primary_key=True)
    work_id: int = db.Column(
        'Work_id',
        db.Integer,
        db.ForeignKey('Work.id', ondelete='CASCADE'),
        nullable=False,
    )

    fileowner: FileOwner = db.Column(
        'fileowner',
        db.Enum(FileOwner),
        default=FileOwner.both,
        nullable=False
    )

    is_directory: bool = db.Column('is_directory', db.Boolean)
    parent_id = db.Column('parent_id', db.Integer, db.ForeignKey('File.id'))

    # This variable is generated from the backref from the parent
    children: '_MyQuery["File"]'

    parent = db.relationship(
        'File',
        remote_side=[id],
        backref=db.backref('children', lazy='dynamic')
    )  # type: 'File'

    work = db.relationship(
        'Work',
        foreign_keys=work_id,
        backref=db.backref(
            'files', lazy='select', uselist=True, cascade='all,delete'
        )
    )  # type: 'work_models.Work'

    @staticmethod
    def get_exclude_owner(owner: t.Optional[str], course_id: int) -> FileOwner:
        """Get the :class:`.FileOwner` the current user does not want to see
        files for.

        The result will be decided like this, if the given str is not
        `student`, `teacher` or `auto` the result will be `FileOwner.teacher`.
        If the str is `student`, the result will be `FileOwner.teacher`, vica
        versa for `teacher` as input. If the input is auto `student` will be
        returned if the currently logged in user is a teacher, otherwise it
        will be `student`.

        :param owner: The owner that was given in the `GET` paramater.
        :param course_id: The course for which the files are requested.
        :returns: The object determined as described above.
        """
        auth.ensure_logged_in()

        teacher, student = FileOwner.teacher, FileOwner.student
        if owner == 'student':
            return teacher
        elif owner == 'teacher':
            return student
        elif owner == 'auto':
            if psef.current_user.has_permission(
                CoursePermission.can_edit_others_work, course_id
            ):
                return student
            else:
                return teacher
        else:
            return teacher

    def get_path(self) -> str:
        return '/'.join(self.get_path_list())

    def get_path_list(self) -> t.List[str]:
        """Get the complete path of this file as a list.

        :returns: The path of the file as a list, without the topmost ancestor
            directory.
        """
        if self.parent is None:
            return []
        upper = self.parent.get_path_list()
        upper.append(self.name)
        return upper

    def list_contents(
        self,
        exclude: FileOwner,
    ) -> 'psef.files.FileTree[int]':
        """List the basic file info and the info of its children.

        :param exclude: The file owner to exclude from the tree.

        :returns: A :class:`psef.files.FileTree` object where the given file is
            the root object.
        """
        cache = self.work.get_file_children_mapping(exclude)
        return self._inner_list_contents(cache)

    def rename_code(
        self,
        new_name: str,
        new_parent: 'File',
        exclude_owner: FileOwner,
    ) -> None:
        """Rename the this file to the given new name.

        :param new_name: The new name to be given to the given file.
        :param new_parent: The new parent of this file.
        :param exclude_owner: The owner to exclude while searching for
            collisions.
        :returns: Nothing.

        :raises APIException: If renaming would result in a naming collision
            (INVALID_STATE).
        """
        if new_parent.children.filter_by(name=new_name).filter(
            File.fileowner != exclude_owner,
        ).first() is not None:
            raise APIException(
                'This file already exists within this directory',
                f'The file "{new_parent.id}" has '
                f'a child with the name "{new_name}"', APICodes.INVALID_STATE,
                400
            )

        self.name = new_name

    def __to_json__(self) -> t.Mapping[str, object]:
        """Creates a JSON serializable representation of this object.


        This object will look like this:

        .. code:: python

            {
                'name': str, # The name of the file or directory.
                'id': str, # The id of this file.
                'is_directory': bool, # Is this file a directory.
            }

        :returns: A object as described above.
        """
        return {
            **super().__to_json__(),
            'is_directory': self.is_directory,
        }


class AutoTestFixture(Base, FileMixin[int], TimestampMixin):
    """This class represents a single fixture for an AutoTest configuration.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestFixture']]
    __tablename__ = 'AutoTestFixture'

    id: int = db.Column('id', db.Integer, primary_key=True)
    auto_test_id: int = db.Column(
        'auto_test_id',
        db.Integer,
        db.ForeignKey('AutoTest.id', ondelete='CASCADE'),
        nullable=False,
    )

    def delete_fixture(self) -> None:
        """Delete the this fixture.

        This function deletes the fixture from the database and after the
        request the saved file is also deleted.
        """
        db.session.delete(self)
        psef.helpers.callback_after_this_request(self.delete_from_disk)

    @property
    def is_directory(self) -> bool:
        return False

    hidden: bool = db.Column(
        'hidden', db.Boolean, nullable=False, default=True
    )

    auto_test: 'auto_test_models.AutoTest' = db.relationship(
        'AutoTest',
        foreign_keys=auto_test_id,
        back_populates='fixtures',
        lazy='joined',
        innerjoin=True,
    )

    def __to_json__(self) -> t.Mapping[str, object]:
        return {
            **super().__to_json__(),
            'hidden': self.hidden,
        }

    def copy(self) -> 'AutoTestFixture':
        """Copy this AutoTest fixture.

        :returns: The copied AutoTest fixture.

        .. note::

            The connected file is only copied after this request has finished,
            so there is a very small period of time where this fixture is
            committed to the database, but where it does not have an underlying
            file yet.
        """
        path, filename = psef.files.random_file_path()
        old_path = self.get_diskname()
        helpers.callback_after_this_request(
            lambda: shutil.copy(old_path, path)
        )

        return AutoTestFixture(
            hidden=self.hidden,
            name=self.name,
            filename=filename,
        )


class AutoTestOutputFile(Base, NestedFileMixin[uuid.UUID], TimestampMixin):
    """This class represents an output file from an AutoTest run.

    The output files are connected to both a
    :class:`.auto_test_models.AutoTestResult` and a
    :class:`.auto_test_models.AutoTestSuite`.
    """
    if t.TYPE_CHECKING:  # pragma: no cover
        query: t.ClassVar[_MyQuery['AutoTestOutputFile']]

    id: uuid.UUID = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)

    is_directory: bool = db.Column('is_directory', db.Boolean, nullable=False)
    parent_id: uuid.UUID = db.Column(
        'parent_id', UUIDType, db.ForeignKey('auto_test_output_file.id')
    )

    auto_test_result_id = db.Column(
        'auto_test_result_id',
        db.Integer,
        db.ForeignKey('AutoTestResult.id'),
    )

    result: 'auto_test_models.AutoTestResult' = db.relationship(
        'AutoTestResult',
        foreign_keys=auto_test_result_id,
        innerjoin=True,
        backref=db.backref('files', lazy='dynamic', cascade='all,delete')
    )

    auto_test_suite_id: int = db.Column(
        'auto_test_suite_id',
        db.Integer,
        db.ForeignKey('AutoTestSuite.id'),
        nullable=False
    )

    suite: 'auto_test_models.AutoTestSuite' = db.relationship(
        'AutoTestSuite',
        foreign_keys=auto_test_suite_id,
        innerjoin=True,
    )

    # This variable is generated from the backref from the parent
    children: '_MyQuery["AutoTestOutputFile"]'

    parent = db.relationship(
        'AutoTestOutputFile',
        remote_side=[id],
        backref=db.backref('children', lazy='dynamic')
    )  # type: 'AutoTestOutputFile'

    def list_contents(self) -> 'psef.files.FileTree[uuid.UUID]':
        """List the basic file info and the info of its children.
        """
        cache: t.Mapping[uuid.UUID, t.
                         List[AutoTestOutputFile]] = defaultdict(list)

        for f in AutoTestOutputFile.query.filter_by(
            auto_test_result_id=self.auto_test_result_id,
            auto_test_suite_id=self.auto_test_suite_id
        ).order_by(AutoTestOutputFile.name):
            cache[f.parent_id].append(f)

        return self._inner_list_contents(cache)


@event.listens_for(AutoTestOutputFile, 'after_delete')
def _receive_after_delete(
    _: object, __: object, target: AutoTestOutputFile
) -> None:
    """Listen for the 'after_delete' event"""
    helpers.callback_after_this_request(target.delete_from_disk)
