<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader center v-if="loading"/>

<div class="submissions d-flex flex-column" v-else>
    <local-header always-show-extra-slot
                  :back-route="headerBackRoute">
        <template slot="title" v-if="assignment && Object.keys(assignment).length">
            {{ assignment.name }}

            <small v-if="assignment.hasDeadline">- due {{ assignment.getFormattedDeadline() }}</small>
            <small v-else class="text-muted"><i>- No deadline</i></small>
        </template>

        <div slot="extra" v-show="!isStudent">
            <hr class="separator top-separator"/>

            <category-selector slot="extra"
                               default=""
                               v-model="selectedCat"
                               :disabled="loadingInner"
                               :categories="categories"/>
        </div>

        <b-input-group>
            <b-button-group>
                <b-button :to="manageAssignmentRoute"
                          variant="secondary"
                          v-if="assignment.canManage"
                          v-b-popover.bottom.hover="'Manage assignment'"
                          class="manage-assignment-button">
                    <icon name="gear"/>
                </b-button>

                <submit-button :wait-at-least="500"
                               name="refresh-button"
                               :submit="submitForceLoadSubmissions"
                               v-b-popover.bottom.hover="'Reload submissions'">
                    <icon name="refresh"/>
                    <icon name="refresh" spin slot="pending-label"/>
                </submit-button>
            </b-button-group>
        </b-input-group>

        <cg-logo v-if="isStudent"
                 :inverted="!darkMode" />
    </local-header>

    <div class="cat-container d-flex flex-column">
        <div v-if="error != null">
            <b-alert variant="danger" show>
                {{ $utils.getErrorMessage(error) }}
            </b-alert>
        </div>

        <loader center page-loader v-else-if="loadingInner" />

        <template v-else>
            <div v-if="selectedCat === 'student-start'"
                 class="action-buttons flex-grow-1 d-flex flex-wrap">
                <template v-if="canUploadForSelf || canUploadForOthers">
                    <div class="action-button m-2 m-md-3 rounded text-center"
                         :class="{ 'variant-danger': latestSubmissionAfterDeadline }"
                         v-b-popover.top.hover="latestSubmissionDisabled">
                        <div class="content-wrapper border rounded p-3 pt-4"
                             :class="{ disabled: latestSubmissionDisabled }"
                             @click.prevent="latestSubmissionDisabled || openLatestUserSubmission()">
                            <div class="icon-wrapper mb-2">
                                <icon name="file-o" :scale="actionIconFactor * 6" />
                                <icon name="history" :scale="actionIconFactor * 2" class="center" />
                            </div>
                            <p class="mb-0">
                                Latest submission
                                <late-submission-icon v-if="latestSubmission"
                                                      :submission="latestSubmission"
                                                      :assignment="assignment" />
                            </p>
                            <p class="text-muted mb-0 grade"
                               v-if="latestSubmissionGrade != null">
                                Grade: {{ latestSubmissionGrade }}
                            </p>
                        </div>
                    </div>

                    <div class="action-button m-2 m-md-3 rounded text-center"
                         v-b-popover.top.hover="uploadDisabledMessage">
                        <div class="content-wrapper border rounded p-3 pt-4"
                             :class="{ disabled: uploadDisabledMessage }"
                             @click.prevent="uploadDisabledMessage || openCategory('hand-in')">
                            <div class="icon-wrapper mb-2">
                                <icon name="file-o" :scale="actionIconFactor * 6" />
                                <icon name="plus" :scale="actionIconFactor * 2" class="center" />
                            </div>
                            <p class="mb-0">Upload files</p>
                        </div>
                    </div>

                    <div v-if="assignment.webhook_upload_enabled"
                         class="action-button git m-2 m-md-3 border-0 p-0 rounded text-center"
                         v-b-popover.top.hover="webhookDisabledMessage">
                        <submit-button variant="secondary"
                                       class="content-wrapper border rounded p-3 pt-4"
                                       :disabled="webhookDisabledMessage.length > 0"
                                       :submit="loadGitData"
                                       @success="openCategory('git')">
                            <div slot="pending-label">
                                <div>
                                    <loader :scale="3" :center="false" class="mb-2 p-0" />
                                </div>
                                Loading webhook data&#8230;
                            </div>

                            <div class="icon-wrapper mb-2">
                                <icon name="code-fork" :scale="actionIconFactor * 6" />
                            </div>
                            <p class="mb-0">Set up Git</p>
                        </submit-button>
                    </div>
                </template>

                <div v-if="rubric != null"
                     class="action-button m-2 m-md-3 rounded text-center"
                     @click="openCategory('rubric')">
                    <div class="content-wrapper border rounded p-3 pt-4">
                        <div class="icon-wrapper mb-2">
                            <icon name="th" :scale="actionIconFactor * 6" />
                        </div>
                        <p class="mb-0">Rubric</p>
                    </div>
                </div>

                <div v-if="assignment.group_set != null"
                     class="action-button m-2 m-md-3 rounded text-center"
                     @click="openCategory('groups')">
                    <div class="content-wrapper border rounded p-3 pt-4">
                        <div class="icon-wrapper mb-2">
                            <icon name="users" :scale="actionIconFactor * 6" />
                        </div>
                        <p class="mb-0">Groups</p>
                    </div>
                </div>
            </div>

            <!-- We can't use v-if here because the <submission-list> MUST
                 always be rendered so we can get the filtered list of
                 submissions. Because v-show doesn't add an !important to its
                 style rule, but d-flex does, we must disable the d-flex class
                 when the element isn't shown. -->
            <div class="flex-grow-1 flex-column"
                 :class="selectedCat === 'hand-in' ? 'd-flex' : 'd-none'">
                <submission-list v-if="!isStudent"
                                 :assignment="assignment"
                                 :rubric="rubric"
                                 :graders="graders"
                                 :can-see-assignee="canSeeAssignee"
                                 :can-assign-grader="canAssignGrader"
                                 :can-see-others-work="canSeeOthersWork"
                                 @filter="filteredSubmissions = $event.submissions"
                                 class="mb-3" />

                <b-card v-else-if="assigHandinReqs"
                        class="mb-3"
                        no-body>
                        <b-card-header>
                            Hand-in instructions
                        </b-card-header>

                        <c-g-ignore-file :assignmentId="assignment.id"
                                         :editable="false"
                                         summary-mode />
                    </collapse>
                </b-card>

                <b-alert show
                         variant="warning"
                         class="no-deadline-alert"
                         v-if="uploaderDisabled">
                    <p v-if="!assignment.hasDeadline">
                        The deadline for this assignment has not yet been set.

                        <span v-if="canEditDeadline && deadlineEditable">
                            You can update the deadline
                            <router-link :to="manageAssigURL" class="inline-link">here</router-link>.
                        </span>

                        <span v-else-if="canEditDeadline">
                            Please update the deadline in {{ lmsName }}.
                        </span>

                        <span v-else>
                            Please ask your teacher to set a deadline before you
                            can submit your work.
                        </span>
                    </p>

                    <p v-if="ltiUploadDisabledMessage">
                        {{ ltiUploadDisabledMessage }}
                    </p>
                </b-alert>

                <template v-else>
                    <b-alert show
                             variant="info"
                             class="group-assignment-alert assignment-alert"
                             v-if="assignment.group_set">
                        This is a group assignment.

                        <template v-if="assignment.group_set.minimum_size > 1">
                            To submit you have to be in a group with at least
                            {{ assignment.group_set.minimum_size }} members.
                        </template>

                        <template v-else>
                            You don't have to be member of group to submit.
                        </template>

                        You can create or join groups
                        <router-link :to="{ hash: '#groups' }"
                                     class="inline-link">here</router-link>.
                        When submitting you will always submit for your entire
                        group.
                    </b-alert>

                    <submission-uploader v-if="canUpload"
                                         :assignment="assignment"
                                         :for-others="canUploadForOthers"
                                         :can-list-users="canListUsers"
                                         :disabled="uploaderDisabled"
                                         :maybe-show-git-instructions="!isStudent"
                                         @created="goToSubmission"
                                         :class="isStudent ? 'flex-grow-1' : ''" />
                </template>
            </div>

            <div v-if="selectedCat === 'rubric'"
                 class="flex-grow-1">
                <rubric-editor :assignment="assignment"
                               grow />
            </div>

            <div v-if="selectedCat === 'hand-in-instructions'"
                 class="flex-grow-1">
                <c-g-ignore-file class="border rounded mb-3"
                                 :assignmentId="assignment.id"
                                 :editable="false"
                                 summary-mode/>
            </div>

            <div v-if="selectedCat === 'git'"
                 class="flex-grow-1">
                <webhook-instructions :data="gitData"
                                      :style="{ margin: '0 auto', maxWidth: '42rem' }" />
            </div>

            <div v-if="selectedCat === 'groups'"
                 class="flex-grow-1">
                <groups-management :assignment="assignment"
                                   :course="assignment.course"
                                   :group-set="assignment.group_set"
                                   :show-lti-progress="showGroupLTIProgress"
                                   :show-add-button="showAddGroupButton" />
            </div>

            <div v-show="selectedCat === 'export'"
                 class="flex-grow-1">
                <submissions-exporter :get-submissions="filter => filter ? filteredSubmissions : submissions"
                                      :assignment-id="assignment.id"
                                      :filename="exportFilename" />
            </div>
        </template>
    </div>
</div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/gear';
import 'vue-awesome/icons/file-o';
import 'vue-awesome/icons/history';
import 'vue-awesome/icons/plus';
import 'vue-awesome/icons/refresh';
import 'vue-awesome/icons/th';
import 'vue-awesome/icons/users';
import 'vue-awesome/icons/chevron-down';
import 'vue-awesome/icons/code-fork';
import 'vue-awesome/icons/git';

import ltiProviders from '@/lti_providers';
import { NONEXISTENT } from '@/constants';
import * as assignmentState from '@/store/assignment-states';
import GroupsManagement from '@/components/GroupsManagement';
import {
    CgLogo,
    Loader,
    Collapse,
    LocalHeader,
    CGIgnoreFile,
    RubricEditor,
    SubmitButton,
    SubmissionList,
    CategorySelector,
    LateSubmissionIcon,
    SubmissionUploader,
    SubmissionsExporter,
    WebhookInstructions,
} from '@/components';

import { setPageTitle, pageTitleSep } from './title';

export default {
    name: 'submissions-page',

    data() {
        return {
            loading: true,
            loadingInner: true,
            wrongFiles: [],
            ltiProviders,
            selectedCat: '',
            filteredSubmissions: [],
            gitData: null,
            error: null,
        };
    },

    computed: {
        ...mapGetters('user', { userId: 'id' }),
        ...mapGetters('pref', ['darkMode']),
        ...mapGetters('courses', ['assignments']),
        ...mapGetters('rubrics', { allRubrics: 'rubrics' }),
        ...mapGetters('submissions', ['getLatestSubmissions']),
        ...mapGetters('users', ['getGroupInGroupSetOfUser']),

        categories() {
            return [
                {
                    id: 'student-start',
                    name: '',
                    enabled: this.isStudent,
                },
                {
                    id: 'hand-in',
                    name: !this.isStudent ? 'Submissions' : 'Hand in',
                    enabled: true,
                },
                {
                    id: 'git',
                    name: 'Git instructions',
                    enabled: this.isStudent && this.assignment.webhook_upload_enabled,
                },
                {
                    id: 'rubric',
                    name: 'Rubric',
                    enabled: true,
                },
                {
                    id: 'hand-in-instructions',
                    name: 'Hand-in instructions',
                    enabled: !this.isStudent && this.assigHandinReqs,
                },
                {
                    id: 'groups',
                    name: 'Groups',
                    enabled: this.assigGroupSet,
                },
                {
                    id: 'export',
                    name: 'Export',
                    enabled: !this.isStudent,
                },
            ];
        },

        defaultCat() {
            return this.isStudent ? 'student-start' : 'hand-in';
        },

        manageAssigURL() {
            return {
                name: 'manage_assignment',
                params: {
                    courseId: this.courseId,
                    assignmentId: this.assignmentId,
                },
            };
        },

        groupSetPageLink() {
            return {
                name: 'manage_groups',
                params: {
                    courseId: this.assignment.course.id,
                    groupSetId: this.assignment.group_set && this.assignment.group_set.id,
                },
                query: { sbloc: 'g' },
            };
        },

        assignment() {
            return this.assignments[this.assignmentId];
        },

        submissions() {
            return this.getLatestSubmissions(this.assignmentId);
        },

        rubric() {
            const rubric = this.allRubrics[this.assignmentId];
            return rubric === NONEXISTENT ? null : rubric;
        },

        graders() {
            return (this.assignment && this.assignment.graders) || null;
        },

        assignmentId() {
            return Number(this.$route.params.assignmentId);
        },

        courseId() {
            return this.$route.params.courseId;
        },

        lmsName() {
            return this.assignment.lms_name;
        },

        uploadDisabledReason() {
            const assig = this.assignment;
            const perms = assig.course.permissions;

            if (!(perms.can_submit_own_work || perms.can_submit_others_work)) {
                return 'you cannot submit work for this course.';
            } else if (assig.state === assignmentState.HIDDEN) {
                return 'the assignment is hidden.';
            } else if (!assig.hasDeadline) {
                return "the assignment's deadline has not yet been set.";
            } else if (!perms.can_upload_after_deadline && assig.deadlinePassed(this.$root.$now)) {
                return "the assignment's deadline has passed.";
            } else {
                return '';
            }
        },

        uploadDisabledMessage() {
            let reason = this.uploadDisabledReason;

            if (!reason && !this.assignment.files_upload_enabled) {
                reason = 'file uploads are disabled for this assignment.';
            }

            return reason ? `You cannot upload work because ${reason}` : '';
        },

        webhookDisabledMessage() {
            const reason = this.uploadDisabledReason;
            return reason ? `You cannot view the webhook instructions because ${reason}` : '';
        },

        ltiUploadDisabledMessage() {
            if (this.assignment.is_lti && !this.$inLTI) {
                return `You can only submit this assignment from within ${this.lmsName}.`;
            } else if (this.$inLTI && this.$LTIAssignmentId == null) {
                return (
                    "You didn't launch the assignment using LTI, please " +
                    "navigate to the 'Assignments' page and submit your " +
                    'work there.'
                );
            } else if (this.$inLTI && this.assignmentId !== this.$LTIAssignmentId) {
                return (
                    'You launched CodeGrade for a different assignment. ' +
                    'Please retry opening the correct assignment.'
                );
            }

            return '';
        },

        uploaderDisabled() {
            return !!(this.ltiUploadDisabledMessage || !this.assignment.hasDeadline);
        },

        deadlineEditable() {
            return !this.$utils.getProps(ltiProviders, false, this.lmsName, 'supportsDeadline');
        },

        latestSubmissionDisabled() {
            if (this.submissions.length === 0) {
                return 'You have not yet submitted your work';
            } else {
                return '';
            }
        },

        latestSubmissionAfterDeadline() {
            if (this.latestSubmission == null) {
                return false;
            }

            return this.latestSubmission.isLate();
        },

        // It should not be possible that `assignment` is null. Still we use getProps below just in
        // case it ever is.

        assigHandinReqs() {
            return this.$utils.getProps(this.assignment, null, 'cgignore');
        },

        assigGroupSet() {
            return this.$utils.getProps(this.assignment, null, 'group_set');
        },

        isStudent() {
            return this.$utils.getProps(this.assignment, true, 'course', 'isStudent');
        },

        manageAssignmentRoute() {
            return {
                name: 'manage_assignment',
                params: {
                    courseId: this.assignment.course.id,
                    assignmentId: this.assignment.id,
                },
            };
        },

        latestSubmission() {
            if (this.submissions.length > 1) {
                return this.submissions.find(s => s.user.group != null);
            } else {
                return this.submissions[0];
            }
        },

        latestSubmissionGrade() {
            return this.$utils.getProps(this.latestSubmission, null, 'grade');
        },

        exportFilename() {
            return this.assignment
                ? `${this.assignment.course.name}-${this.assignment.name}.csv`
                : null;
        },

        headerBackRoute() {
            if (!this.isStudent || this.selectedCat === 'student-start') {
                return null;
            } else {
                return Object.assign({}, this.$route, { hash: '' });
            }
        },

        actionIconFactor() {
            return this.$root.$isSmallWindow ? 0.75 : 1;
        },

        coursePermissions() {
            return this.$utils.getProps(this.assignment, {}, 'course', 'permissions');
        },

        canSeeAssignee() {
            return this.coursePermissions.can_see_assignee;
        },

        canAssignGrader() {
            return this.coursePermissions.can_assign_graders;
        },

        canUploadForSelf() {
            return this.coursePermissions.can_submit_own_work;
        },

        canUploadForOthers() {
            return this.coursePermissions.can_submit_others_work;
        },

        canListUsers() {
            return this.coursePermissions.can_list_course_users;
        },

        canUpload() {
            return this.assignment.canUploadWork(this.$root.$now);
        },

        canSeeOthersWork() {
            return this.coursePermissions.can_see_others_work;
        },

        canEditDeadline() {
            return this.coursePermissions.can_edit_assignment_info;
        },

        currentGroup() {
            const groupSetId = this.$utils.getProps(this.assignment, null, 'group_set', 'id');
            return this.getGroupInGroupSetOfUser(groupSetId, this.userId);
        },

        showAddGroupButton() {
            if (this.currentGroup == null) {
                return true;
            }
            // When there is a group, only show the add button if you are not a student.
            return !this.isStudent;
        },
    },

    watch: {
        submissions(newVal) {
            if (newVal.length === 0) {
                this.loadData();
            }
        },

        assignmentId: {
            immediate: true,
            handler() {
                this.gitData = null;
                this.loadData();
            },
        },
    },

    methods: {
        ...mapActions('courses', {
            loadCourses: 'loadCourses',
        }),

        ...mapActions('submissions', {
            loadSubmissions: 'loadSubmissions',
            forceLoadSubmissions: 'forceLoadSubmissions',
        }),

        ...mapActions('rubrics', {
            storeLoadRubric: 'loadRubric',
        }),

        async loadData() {
            this.error = null;

            // Don't set loading if we already have the assignment data to
            // prevent the LocalHeader from disappearing for a fraction of
            // a second.
            if (this.assignment == null) {
                this.loading = true;
                await this.loadCourses();
            }

            // Always set loading to false, otherwise you'd get an infinite
            // when the page/component is reloaded in dev mode.
            this.loading = false;
            this.loadingInner = true;

            const promises = [
                this.loadSubmissions(this.assignmentId),
                this.loadRubric(),
                this.$afterRerender(),
            ];

            // This uses the hash because this.selectedCat may still be unset on page load.
            if (this.$route.hash === '#git') {
                promises.push(this.loadGitData());
            }

            setPageTitle(`${this.assignment.name} ${pageTitleSep} Submissions`);

            Promise.all(promises).then(
                () => {
                    this.loadingInner = false;
                },
                err => {
                    this.error = err;
                    this.loadingInner = false;
                },
            );
        },

        loadGitData() {
            if (!this.assignment.webhook_upload_enabled) {
                return Promise.reject(new Error('Webhooks are not enabled for this assignment'));
            } else if (this.gitData != null) {
                return Promise.resolve();
            }

            return this.$http
                .post(`/api/v1/assignments/${this.assignment.id}/webhook_settings?webhook_type=git`)
                .then(
                    res => {
                        this.gitData = res.data;
                        return res;
                    },
                    err => {
                        this.gitData = null;
                        throw err;
                    },
                );
        },

        loadRubric() {
            return this.storeLoadRubric({
                assignmentId: this.assignmentId,
            }).catch(err => {
                if (this.$utils.getProps(err, 500, 'response', 'status') !== 404) {
                    throw err;
                }
            });
        },

        submitForceLoadSubmissions() {
            return this.forceLoadSubmissions(this.assignment.id);
        },

        goToSubmission(submission) {
            this.$router.push({
                name: 'submission',
                params: { submissionId: submission.id },
            });
        },

        openLatestUserSubmission() {
            const sub = this.latestSubmission;

            if (sub != null) {
                this.goToSubmission(sub);
            }
        },

        openCategory(cat) {
            this.$router.push(
                Object.assign({}, this.$route, {
                    hash: `#${cat}`,
                }),
            );
        },

        showGroupLTIProgress(group) {
            if (this.assignment.is_lti && this.currentGroup && this.currentGroup.isGroup) {
                return this.currentGroup.group.id === group.id;
            }
            return false;
        },
    },

    components: {
        Icon,
        CgLogo,
        Loader,
        Collapse,
        LocalHeader,
        CGIgnoreFile,
        RubricEditor,
        SubmitButton,
        SubmissionList,
        CategorySelector,
        GroupsManagement,
        SubmissionUploader,
        SubmissionsExporter,
        WebhookInstructions,
        LateSubmissionIcon,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.loader {
    padding-top: 3.5em;
}

.cg-logo {
    height: 1.5rem;
    width: auto;
}

.cat-container {
    margin: -1rem -15px 0;
    padding: 1rem 15px 0;
    background-color: white;
    flex: 1 1 auto;

    #app.dark & {
        background-color: @color-primary;
    }
}

.cat-wrapper {
    flex: 1 1 auto;
}

.chevron {
    margin-right: 0.5rem;
    transform: rotate(0);
    transition: transform @transition-duration;

    .x-collapsing &,
    .x-collapsed & {
        transform: rotate(-90deg);
    }
}

.alert p:last-child {
    margin-bottom: 0;
}

.action-buttons {
    max-width: 48rem;
    width: 100%;
    margin: 0 auto;
    justify-content: center;

    @media @media-no-small {
        align-content: center;
        align-items: center;
    }

    @media @media-small {
        align-content: flex-start;
        align-items: flex-start;
    }
}

.action-button {
    position: relative;
    flex: 0 0 ~'calc(33.33% - 2rem)';
    height: 12rem;

    @media @media-small {
        flex-basis: ~'calc(50% - 1rem)';
        height: 10rem;
    }

    @media (max-width: 17.5rem) {
        flex-basis: ~'calc(100% - 1rem)';
    }

    &.variant-danger {
        color: @color-danger;
        background-color: fade(@color-danger, 25%) !important;

        .content-wrapper {
            border-color: @color-danger !important;
        }
    }

    .content-wrapper {
        width: 100%;
        height: 100%;
        transition: background-color @transition-duration;

        &:not(.disabled):hover {
            cursor: pointer;
            background-color: rgba(0, 0, 0, 0.125) !important;
        }

        &.disabled {
            cursor: not-allowed !important;
            opacity: 0.5;
        }
    }

    .icon-wrapper {
        position: relative;
        display: inline-block;
    }

    .center {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
    }

    &.git {
        .submit-button {
            box-shadow: none !important;
        }
    }
}
</style>