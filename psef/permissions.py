"""This file contains all permissions used by CodeGrade in a python enum.

.. warning::

  Do not edit this enum as it is automatically generated by
  "generate_permissions_py.py".

SPDX-License-Identifier: AGPL-3.0-only
"""
# pylint: disable=line-too-long
# flake8: noqa=E501
# yapf: disable

import enum
import typing as t

from . import exceptions

AnyPermission = t.TypeVar(  # pylint: disable=invalid-name
    'AnyPermission', 'GlobalPermission', 'CoursePermission'
)
__T = t.TypeVar('__T', bound='BasePermission')  # pylint: disable=invalid-name

_PermissionValue = t.NamedTuple('_PermissionValue', [('item', object), ('default_value', bool)])


def init_app(app: t.Any, skip_perm_check: bool) -> None:
    """Initialize flask app
    """
    if skip_perm_check:
        return
    database_permissions_sanity_check(app)  # pragma: no cover


def database_permissions_sanity_check(app: t.Any) -> None:
    """Check if database has all the correct permissions.
    """
    from . import models
    with app.app_context():
        import structlog

        logger = structlog.get_logger()

        from_enum = set((p, p.value.default_value) for p in list(GlobalPermission) + list(CoursePermission))
        from_database = set((p.value, p.default_value) for p in models.db.session.query(models.Permission).all())
        if from_enum != from_database:  # pragma: no cover
            logger.error('Not all permissions were found in the database', difference=from_enum ^ from_database)
            assert from_enum == from_database


CoursePermMap = t.NewType('CoursePermMap', t.Mapping[str, bool])
GlobalPermMap = t.NewType('GlobalPermMap', t.Mapping[str, bool])


class BasePermission(enum.Enum):
    """The base of a permission.

    Do not use this class to get permissions, as it has none!
    """

    @staticmethod
    def create_map(mapping: t.Any) -> t.Any:
        """Create a map.
        """
        return {k.name: v for k, v in mapping.items()}

    @classmethod
    def get_by_name(cls: t.Type['__T'], name: str) -> '__T':
        """Get a permission by name.

        :param name: The name of the permission.
        :returns: The found permission.

        :raises exceptions.APIException: When the permission was not found.
        """
        try:
            return cls[name]
        except KeyError:
            raise exceptions.APIException(
                ('The requested permission '
                 '"{}" does not exist').format(name),
                'The requested course permission was not found',
                exceptions.APICodes.OBJECT_NOT_FOUND, 404
            )

    def __to_json__(self) -> str:  # pragma: no cover
        """Convert a permission to json.

        :returns: The name of the permission.
        """
        return self.name


    def __lt__(self, other: 'BasePermission') -> bool:  # pragma: no cover
        return self.value < other.value  # pylint: disable=comparison-with-callable


@enum.unique
class GlobalPermission(BasePermission):
    """The global permissions used by CodeGrade.

    .. warning::

      Do not edit this enum as it is automatically generated by
      "generate_permissions_py.py".

    :ivar can_add_users: Users with this permission can add other users to the website.
    :ivar can_use_snippets: Users with this permission can use the snippets feature on the website.
    :ivar can_edit_own_info: Users with this permission can edit their own personal information.
    :ivar can_edit_own_password: Users with this permission can edit their own password.
    :ivar can_create_courses: Users with this permission can create new courses.
    :ivar can_manage_site_users: Users with this permission can change the global permissions for other users on the site.
    :ivar can_search_users: Users with this permission can search for users on the side, this means they can see all other users on the site.
    """

    @staticmethod
    def create_map(mapping: t.Mapping['GlobalPermission', bool]) -> GlobalPermMap:
        return BasePermission.create_map(mapping)

    can_add_users = _PermissionValue(item=0, default_value=False)
    can_use_snippets = _PermissionValue(item=1, default_value=True)
    can_edit_own_info = _PermissionValue(item=2, default_value=True)
    can_edit_own_password = _PermissionValue(item=3, default_value=True)
    can_create_courses = _PermissionValue(item=4, default_value=False)
    can_manage_site_users = _PermissionValue(item=5, default_value=False)
    can_search_users = _PermissionValue(item=6, default_value=True)


@enum.unique
class CoursePermission(BasePermission):
    """The course permissions used by CodeGrade.

    .. warning::

      Do not edit this enum as it is automatically generated by
      "generate_permissions_py.py".

    :ivar can_submit_others_work: Users with this permission can submit work to an assignment for other users. This means they can submit work that will have another user as the author.
    :ivar can_submit_own_work: Users with this permission can submit their work to assignments of this course. Usually only students have this permission.
    :ivar can_edit_others_work: Users with this permission can edit files in the submissions of this course. Usually TAs and teachers have this permission, so they can change files in the CodeGra.de filesystem if code doesn't compile, for example.
    :ivar can_grade_work: Users with this permission can grade submissions.
    :ivar can_see_grade_before_open: Users with this permission can see the grade for a submission before an assignment is set to "done".
    :ivar can_see_others_work: Users with this permission can see submissions of other users of this course.
    :ivar can_see_assignments: Users with this permission can view the assignments of this course.
    :ivar can_see_hidden_assignments: Users with this permission can view assignments of this course that are set to "hidden".
    :ivar can_use_linter: Users with this permission can run linters on all submissions of an assignment.
    :ivar can_edit_assignment_info: Users with this permission can update the assignment info such as name, deadline and status.
    :ivar can_assign_graders: Users with this permission can assign a grader to submissions of assignments.
    :ivar can_edit_cgignore: Users with this permission can edit the .cgignore file for an assignment.
    :ivar can_upload_bb_zip: Users with this permission can upload a zip file with submissions in the BlackBoard format.
    :ivar can_edit_course_roles: Users with this permission can assign or remove permissions from course roles and add new course roles.
    :ivar can_edit_course_users: Users with this permission can add users to this course and assign roles to those users.
    :ivar can_create_assignment: Users with this permission can create new assignments for this course.
    :ivar can_upload_after_deadline: Users with this permission can submit their work after the deadline of an assignment.
    :ivar can_see_assignee: Users with this permission can see who is assigned to assess a submission.
    :ivar manage_rubrics: Users with this permission can update the rubrics for the assignments of this course.
    :ivar can_view_own_teacher_files: Users with this permission can view the teacher's revision of their submitted work.
    :ivar can_see_grade_history: Users with this permission can see the grade history of an assignment.
    :ivar can_delete_submission: Users with this permission can delete submissions.
    :ivar can_update_grader_status: Users with this permission can change the status of graders for this course, whether they are done grading their assigned submissions or not.
    :ivar can_update_course_notifications: Users with this permission can change the all notifications that are configured for this course. This includes when to send them and who to send them to.
    :ivar can_edit_maximum_grade: Users with this permission can edit the maximum grade possible, and therefore also determine if getting a 'bonus' for an assignment is also possible.
    :ivar can_view_plagiarism: Users with this permission can view the summary of a plagiarism check and see details of a plagiarism case. To view a plagiarism case between this and another course, the user must also have either this permission, or both "See assignments" ("can_see_assignment") and "See other's work" ("can_see_others_work") in the other course.
    :ivar can_manage_plagiarism: Users with this permission can add and delete plagiarism runs.
    :ivar can_list_course_users: Users with this permission can see all users of this course including the name of their role.
    """

    @staticmethod
    def create_map(mapping: t.Mapping['CoursePermission', bool]) -> CoursePermMap:
        return BasePermission.create_map(mapping)

    can_submit_others_work = _PermissionValue(item=0, default_value=False)
    can_submit_own_work = _PermissionValue(item=1, default_value=True)
    can_edit_others_work = _PermissionValue(item=2, default_value=False)
    can_grade_work = _PermissionValue(item=3, default_value=False)
    can_see_grade_before_open = _PermissionValue(item=4, default_value=False)
    can_see_others_work = _PermissionValue(item=5, default_value=False)
    can_see_assignments = _PermissionValue(item=6, default_value=True)
    can_see_hidden_assignments = _PermissionValue(item=7, default_value=False)
    can_use_linter = _PermissionValue(item=8, default_value=False)
    can_edit_assignment_info = _PermissionValue(item=9, default_value=False)
    can_assign_graders = _PermissionValue(item=10, default_value=False)
    can_edit_cgignore = _PermissionValue(item=11, default_value=False)
    can_upload_bb_zip = _PermissionValue(item=12, default_value=False)
    can_edit_course_roles = _PermissionValue(item=13, default_value=False)
    can_edit_course_users = _PermissionValue(item=14, default_value=False)
    can_create_assignment = _PermissionValue(item=15, default_value=False)
    can_upload_after_deadline = _PermissionValue(item=16, default_value=False)
    can_see_assignee = _PermissionValue(item=17, default_value=False)
    manage_rubrics = _PermissionValue(item=18, default_value=False)
    can_view_own_teacher_files = _PermissionValue(item=19, default_value=True)
    can_see_grade_history = _PermissionValue(item=20, default_value=False)
    can_delete_submission = _PermissionValue(item=21, default_value=False)
    can_update_grader_status = _PermissionValue(item=22, default_value=False)
    can_update_course_notifications = _PermissionValue(item=23, default_value=False)
    can_edit_maximum_grade = _PermissionValue(item=24, default_value=False)
    can_view_plagiarism = _PermissionValue(item=25, default_value=False)
    can_manage_plagiarism = _PermissionValue(item=26, default_value=False)
    can_list_course_users = _PermissionValue(item=27, default_value=True)

# yapf: enable
