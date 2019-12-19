<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader center v-if="loading"/>
<div class="submission-list d-flex flex-column" v-else>
    <submission-list :assignment="assignment"
                     :canDownload="canDownload"
                     :rubric="rubric"
                     :graders="graders"
                     :can-see-assignee="canSeeAssignee"
                     :can-assign-grader="canAssignGrader"
                     :can-see-others-work="canSeeOthersWork"
                     @assigneeUpdated="updateAssignee"
                     :show-loader="loadingInner" />

    <div v-if="!loadingInner && (canUpload || !assignment.deadline)">
        <b-alert show variant="warning"
                 class="no-deadline-alert disabled-warning"
                 v-if="uploaderDisabled">
            <p v-if="!assignment.deadline">
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

            <p v-if="fileUploaderDisabledMessage">
                {{ fileUploaderDisabledMessage }}
            </p>
        </b-alert>

        <span v-else>
            <b-alert show
                     variant="info"
                     class="group-assignment-alert assignment-alert"
                     v-if="assignment.group_set">
                This assignment is a group assignment.
                <template v-if="assignment.group_set.minimum_size > 1">
                    To submit you have to be in a group with at least
                    {{ assignment.group_set.minimum_size }} members.
                </template>
                <template v-else>
                    You don't have to be member of group to submit.
                </template>
                You can create or join groups
                <router-link class="inline-link"
                             :to="groupSetPageLink">here</router-link>.
                When submitting you will always submit for your entire group.
            </b-alert>
            <submission-uploader :assignment="assignment"
                                 :for-others="canUploadForOthers"
                                 :can-list-users="canListUsers"
                                 :disabled="fileUploaderDisabled"
                                 @created="goToSubmission"/>
        </span>
    </div>
</div>
</template>

<script>
import { SubmissionList, Loader, SubmitButton, SubmissionUploader } from '@/components';
import { mapGetters, mapActions } from 'vuex';

import ltiProviders from '@/lti_providers';
import * as assignmentState from '@/store/assignment-states';

import { setPageTitle, pageTitleSep } from './title';

export default {
    name: 'submissions-page',

    data() {
        return {
            loading: true,
            loadingInner: true,
            canUpload: false,
            canUploadForOthers: false,
            canDownload: false,
            canListUsers: null,
            canSeeAssignee: false,
            canAssignGrader: false,
            canSeeOthersWork: false,
            canEditDeadline: false,
            wrongFiles: [],
            ltiProviders,
        };
    },

    computed: {
        ...mapGetters('courses', ['assignments']),
        ...mapGetters('submissions', ['latestSubmissions']),

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
            return this.latestSubmissions[this.assignmentId] || [];
        },

        rubric() {
            return (this.assignment && this.assignment.rubric) || null;
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

        fileUploaderDisabledMessage() {
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

        fileUploaderDisabled() {
            if (this.assignment.is_lti && !this.$inLTI) {
                return true;
            } else if (this.$inLTI && this.$LTIAssignmentId == null) {
                return true;
            } else if (this.$inLTI && this.assignmentId !== this.$LTIAssignmentId) {
                return true;
            } else {
                return false;
            }
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

        uploaderDisabled() {
            return this.fileUploaderDisabledMessage || !this.assignment.deadline;
        },

        deadlineEditable() {
            return !this.$utils.getProps(ltiProviders, false, this.lmsName, 'supportsDeadline');
        },
    },

    watch: {
        submissions(newVal) {
            if (newVal.length === 0) {
                this.loadData();
            }
        },

        assignment(newVal, oldVal) {
            if (oldVal != null && newVal.id !== oldVal.id && !this.loading) {
                this.loadData();
            }
        },
    },

    mounted() {
        this.loadData();
    },

    methods: {
        ...mapActions('courses', {
            loadCourses: 'loadCourses',
        }),

        ...mapActions('submissions', {
            loadSubmissions: 'loadSubmissions',
            updateSubmission: 'updateSubmission',
        }),

        async loadData() {
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

            Promise.all([
                this.loadSubmissions(this.assignmentId),
                this.$hasPermission(
                    [
                        'can_see_assignee',
                        'can_assign_graders',
                        'can_submit_others_work',
                        'can_see_others_work',
                        'can_see_grade_before_open',
                        'can_list_course_users',
                        'can_edit_assignment_info',
                    ],
                    this.courseId,
                ),
                this.$afterRerender(),
            ]).then(
                ([
                    ,
                    [
                        seeAssignee,
                        assignGrader,
                        submitOthers,
                        others,
                        before,
                        canList,
                        canEditDeadline,
                    ],
                ]) => {
                    setPageTitle(`${this.assignment.name} ${pageTitleSep} Submissions`);
                    this.canSeeAssignee = seeAssignee;
                    this.canAssignGrader = assignGrader;
                    this.canUploadForOthers = submitOthers;
                    this.canListUsers = canList;
                    this.canUpload = this.$utils.canUploadWork(this.assignment, this.$root.$now);

                    this.canSeeOthersWork = false;
                    this.canDownload = false;

                    if (others) {
                        this.canSeeOthersWork = true;

                        if (this.assignment.state === assignmentState.DONE) {
                            this.canDownload = true;
                        } else {
                            this.canDownload = before;
                        }
                    }
                    this.canEditDeadline = canEditDeadline;
                    this.loadingInner = false;
                },
                err => {
                    // TODO: visual feedback
                    // eslint-disable-next-line
                    console.error(err);
                    this.loadingInner = false;
                },
            );
        },

        goToSubmission(submission) {
            this.$router.push({
                name: 'submission',
                params: { submissionId: submission.id },
            });
        },

        updateAssignee(submission, assignee) {
            this.updateSubmission({
                assignmentId: this.assignmentId,
                submissionId: submission.id,
                submissionProps: { assignee },
            });
        },
    },

    components: {
        SubmissionUploader,
        SubmissionList,
        Loader,
        SubmitButton,
    },
};
</script>

<style lang="less" scoped>
.loader {
    padding-top: 3.5em;
}

.submission-list {
    flex: 1 1 auto;
}

#wrong-files-modal ul {
    max-height: 50vh;
    overflow-y: auto;
}

.disabled-warning {
    p:last-child {
        margin-bottom: 0;
    }
}
</style>