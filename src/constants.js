/* SPDX-License-Identifier: AGPL-3.0-only */

export const MANAGE_AUTOTEST_PERMISSIONS = Object.freeze([
    'can_run_autotest',
    'can_delete_autotest_run',
    'can_edit_autotest',
]);

export const MANAGE_ASSIGNMENT_PERMISSIONS = Object.freeze([
    'can_edit_assignment_info',
    'can_assign_graders',
    'can_edit_cgignore',
    'can_grade_work',
    'can_update_grader_status',
    'can_use_linter',
    'can_update_course_notifications',
    'manage_rubrics',
    'can_upload_bb_zip',
    'can_submit_others_work',
    'can_edit_maximum_grade',
    'can_view_plagiarism',
    'can_manage_plagiarism',
    'can_edit_group_assignment',
    ...MANAGE_AUTOTEST_PERMISSIONS,
]);

export const MANAGE_GENERAL_COURSE_PERMISSIONS = Object.freeze([
    'can_edit_course_users',
    'can_edit_course_roles',
    'can_edit_group_set',
    'can_manage_course_snippets',
    'can_view_course_snippets',
    'can_email_students',
]);

export const MANAGE_COURSE_PERMISSIONS = Object.freeze([
    ...new Set([...MANAGE_ASSIGNMENT_PERMISSIONS, ...MANAGE_GENERAL_COURSE_PERMISSIONS]),
]);

export const MANAGE_SITE_PERIMSSIONS = Object.freeze([
    'can_manage_site_users',
    'can_impersonate_users',
]);

export const PASSWORD_UNIQUE_MESSAGE =
    'Please make sure you use a unique password, and at least different from the password you use for your LMS.';

export const NO_LOGIN_ALLOWED_ROUTES = new Set(['login', 'register']);

export const NO_LOGIN_REQUIRED_ROUTES = new Set([
    'login',
    'forgot',
    'reset-password',
    'register',
    'lti-launch',
    'login_and_redirect',
    'unsubscribe',
]);

export const NO_SIDEBAR_ROUTES = new Set(['lti-launch', 'unsubscribe']);

export const NO_FOOTER_ROUTES = new Set(['submission', 'submission_file', 'plagiarism_detail']);

// Indicates an object in the store that has been requested but not returned by
// the server, e.g. if it does not exist or the user has no permission to see
// the object.
export const NONEXISTENT = {};

// Indicates that a value has not yet been set (e.g. in a model cache).
export const UNSET_SENTINEL = {};

export const RUBRIC_BADGE_AT =
    '<div class="ml-1 badge badge-primary" title="This is an AutoTest category">AT</div>';
