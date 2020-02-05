<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<b-card no-body class="auto-test-run">
    <collapse v-model="resultsCollapsed">
        <b-card-header
            slot="handle"
            class="d-flex justify-content-between align-items-center">
            <span class="toggle flex-grow-1">
                <icon name="chevron-down" :scale="0.75" />
                Results
            </span>
        </b-card-header>

        <table class="table results-table border-bottom"
               :id="tableId"
               :class="{ 'table-hover': run.results.length > 0 }">
            <thead>
                <tr>
                    <th class="name">Name</th>
                    <th class="score">Score</th>
                    <th class="state">State</th>
                </tr>
            </thead>

            <component :is="doTransitions ? 'transition-group' : 'tbody'" v-if="sortedResults.length > 0" tag="tbody" name="result">
                <tr v-for="result in visibleResults"
                    :key="`${result.id}-${result.state}`"
                    @click="openResult(result)">
                    <td class="name">
                        <div v-if="submissions[result.submissionId]">
                            <user :user="submissions[result.submissionId].user"/>
                        </div>
                        <div v-else class="name-loader">
                            <loader :center="false" :scale="1"/>
                        </div>
                    </td>
                    <td class="score">
                        <div>
                            <span v-if="submissions[result.submissionId]">
                                <icon v-if="submissions[result.submissionId].grade_overridden"
                                    v-b-popover.top.hover="'This submission\'s calculated grade has been manually overridden'"
                                    name="exclamation-triangle"/>
                            </span>
                            {{ $utils.toMaxNDecimals($utils.getProps(result, '-', 'pointsAchieved'), 2) }} /
                            {{ $utils.toMaxNDecimals(autoTest.pointsPossible, 2) }}
                        </div>
                    </td>
                    <td class="state">
                        <div>
                            <auto-test-state :result="result" show-icon />
                        </div>
                    </td>
                </tr>
            </component>
            <tbody v-else>
                <tr>
                    <td colspan="3">No results</td>
                </tr>
            </tbody>
        </table>

        <b-pagination
            class="pagination mt-3"
            v-if="run.results.length > 0 && run.results.length > perPage"
            v-model="currentPage"
            :limit="10"
            :total-rows="run.results.length"
            :per-page="perPage"
            :aria-controls="tableId"
            @click.native.capture="disableTransitions"/>
    </collapse>
</b-card>
</template>

<script>
import { mapActions } from 'vuex';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/chevron-down';
import 'vue-awesome/icons/exclamation-triangle';

import Collapse from './Collapse';
import SubmitButton from './SubmitButton';
import AutoTestState from './AutoTestState';
import Loader from './Loader';
import User from './User';

export default {
    name: 'auto-test-run',

    props: {
        assignment: {
            type: Object,
            required: true,
        },

        autoTest: {
            type: Object,
            required: true,
        },

        run: {
            type: Object,
            required: true,
        },

        editable: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        const id = this.$utils.getUniqueId();

        return {
            resultsCollapsed: false,
            resultsCollapseId: `auto-test-results-collapse-${id}`,
            submissions: {},
            submissionsLoading: true,
            currentPage: 1,
            perPage: 15,
            tableId: `auto-test-results-table-${this.$utils.getUniqueId()}`,
            doTransitions: true,
        };
    },

    computed: {
        permissions() {
            return this.$utils.getProps(this, {}, 'assignment', 'course', 'permissions');
        },

        deleteResultsPopover() {
            if (!this.permissions.can_delete_autotest_run) {
                return 'You do not have permission to delete AutoTest results.';
            } else {
                return '';
            }
        },

        runId() {
            return this.$utils.getProps(this.run, null, 'id');
        },

        results() {
            return this.$utils.getProps(this.run, [], 'results');
        },

        sortedResults() {
            return this.results.slice().sort((a, b) => {
                if (a.finished) {
                    return b.finished ? (b.startedAt || '').localeCompare(a.startedAt || '') : 1;
                } else {
                    if (b.finished) {
                        return -1;
                    }

                    const aRunning = a.state === 'running';
                    const bRunning = b.state === 'running';

                    if (aRunning && bRunning) {
                        return (a.startedAt || '').localeCompare(b.startedAt || '');
                    } else if (!aRunning && !bRunning) {
                        return a.createdAt.localeCompare(b.createdAt);
                    } else {
                        // a before b.
                        return aRunning ? -1 : 1;
                    }
                }
            });
        },

        visibleResults() {
            const allRes = this.sortedResults;
            const start = this.perPage * (this.currentPage - 1);
            const end = this.perPage * this.currentPage;

            return allRes.slice(start, end);
        },

        submissionIds() {
            return this.visibleResults.map(res => res.submissionId);
        },
    },

    watch: {
        runId() {
            this.currentPage = 1;
        },

        currentPage() {
            this.disableTransitions();
        },

        submissionIds: {
            immediate: true,
            handler(newSubIds) {
                const subIds = newSubIds.filter(id => !(id in this.submissions));

                if (subIds.length === 0) {
                    return;
                }

                this.storeLoadGivenSubmissions({
                    assignmentId: this.assignment.id,
                    submissionIds: newSubIds,
                }).then(subs => {
                    subs.forEach(sub => {
                        this.$set(this.submissions, sub.id, sub);
                    });
                });
            },
        },
    },

    methods: {
        ...mapActions('submissions', {
            storeLoadGivenSubmissions: 'loadGivenSubmissions',
        }),

        ...mapActions('autotest', {
            storeDeleteAutoTestResults: 'deleteAutoTestResults',
        }),

        openResult(result) {
            this.$emit('open-result', result);
        },

        disableTransitions() {
            this.doTransitions = false;
            this.$nextTick(() => {
                this.doTransitions = true;
            });
        },
    },

    components: {
        Icon,
        Collapse,
        Loader,
        SubmitButton,
        AutoTestState,
        User,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.results-table {
    margin-bottom: 0;

    th {
        border-top: 0;
    }

    .submitted,
    .score,
    .state {
        width: 1px;
        white-space: nowrap;
    }

    .score {
        text-align: right;

        .fa-icon {
            transform: translateY(2px);
            margin-right: 0.5rem;
        }
    }

    .state {
        text-align: center;
    }
}

.name-loader {
    transform: translateY(2px);
}

.result-enter-active,
.result-leave-active,
.result-enter-active td,
.result-leave-active td,
.result-enter-active td > div,
.result-leave-active td > div {
    transition-duration: 400ms;
    transition-timing-function: linear;
}

.result-enter td,
.result-leave-to td {
    transition-property: padding;
    overflow: hidden;
}
.result-enter td > div,
.result-leave-to td > div {
    transition-property: max-height, opacity;
    overflow: hidden;
}

.result-enter td,
.result-leave-to td {
    padding: 0;
}

.result-enter td > div,
.result-leave-to td > div {
    max-height: 0;
    opacity: 0;
}

.result-enter-to td > div,
.result-leave td > div {
    max-height: 3rem;
    opacity: 1;
}
</style>

<style lang="less">
@import '~mixins.less';

.auto-test-run .pagination {
    display: flex;
    justify-content: center;

    .page-item {
        .page-link {
            &:active,
            &:focus {
                box-shadow: none;
            }

            #app.dark & {
                border-color: @color-primary-darkest;
                background-color: @color-primary;
                color: @text-color-dark;

                &:hover {
                    background-color: rgba(0, 0, 0, 0.125);
                }
            }
        }

        &.active .page-link {
            border-color: @color-primary;
            background-color: @color-primary;
            color: @text-color-dark;

            #app.dark & {
                background-color: @color-primary-darkest;
            }
        }
    }
}
</style>