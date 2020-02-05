/* SPDX-License-Identifier: AGPL-3.0-only */
import moment from 'moment';
import { store } from '@/store';

import * as mutationTypes from '@/store/mutation-types';

import { Assignment } from '@/models';

import * as assignmentState from '@/store/assignment-states';
import { formatDate } from '@/utils';

jest.useFakeTimers();

describe('assignment model', () => {
    function makeAssig(data) {
        const course = Object.assign({}, data.course || {});
        const assig = Object.assign({}, data);
        delete assig.course;

        course.assignments = [assig];
        course.id = 0;
        assig.id = assig.id || 1;

        store.commit(
            `courses/${mutationTypes.SET_COURSES}`,
            [
                [course],
                { 0: false },
                { 0: false },
                { 0: false },
                { 0: Object.assign({}, course.permissions || {}) },
            ],
        );
        return store.getters['courses/assignments'][assig.id];
    }

    describe('canSeeGrade', () => {
        it.each([
            assignmentState.HIDDEN,
            assignmentState.SUBMITTING,
            assignmentState.GRADING,
            assignmentState.OPEN,
        ])('should return false when the assignment state is %s and you don\'t have permission can_see_grade_before_open', (state) => {
            const assig = makeAssig({
                state,
                course: {
                    permissions: {
                        can_see_grade_before_open: false,
                    },
                },
            });

            expect(assig.canSeeGrade()).toBe(false);
        });

        it('should return true when the assignment state is done', () => {
            const assig = makeAssig({
                state: assignmentState.DONE,
                course: {
                    permissions: {
                        can_see_grade_before_open: false,
                    },
                },
            });

            expect(assig.canSeeGrade()).toBe(true);
        });

        it.each([
            assignmentState.HIDDEN,
            assignmentState.SUBMITTING,
            assignmentState.GRADING,
            assignmentState.OPEN,
        ])('should return true when you have the permission can_see_grade_before_open for every state', (state) => {
            const assig = makeAssig({
                state,
                course: {
                    permissions: {
                        can_see_grade_before_open: true,
                    },
                },
            });

            expect(assig.canSeeGrade()).toBe(true);
        });
    });

    describe('canUploadWork', () => {
        it('should return false when you cannot submit work', () => {
            const assig = makeAssig({
                course: {
                    permissions: {
                        can_submit_own_work: false,
                        can_submit_others_work: false,
                    },
                },
            });
            expect(assig.canUploadWork()).toBe(false);
        });

        it.each([
            [false],
            [true],
        ])('should return false when the assignment is hidden', (submitOwn) => {
            const assigData = {
                state: assignmentState.HIDDEN,
                course: {
                    permissions: {
                        can_submit_own_work: true,
                        can_submit_others_work: false,
                    },
                },
            };
            let assig = makeAssig(assigData);

            expect(assig.canUploadWork()).toBe(false);

            assigData.course.permissions = {
                can_submit_own_work: false,
                can_submit_others_work: true,
            };
            assig = makeAssig(assigData);
            expect(assig.canUploadWork()).toBe(false);

            assigData.course.permissions.can_submit_own_work = true;
            assig = makeAssig(assigData);
            expect(assig.canUploadWork()).toBe(false);
        });

        it('should return false when the deadline has passed and you do not have permission to submit after the deadline', () => {
            const now = moment();
            const assigData = {
                state: assignmentState.OPEN,
                deadline: formatDate(moment(now).add(-1, 'days')),
                course: {
                    permissions: {
                        can_submit_own_work: true,
                        can_submit_others_work: false,
                        can_upload_after_deadline: false,
                    },
                },
            };
            let assig = makeAssig(assigData);

            function updatePerms(perms) {
                Object.assign(assigData.course.permissions, perms);
                assig = makeAssig(assigData);
            }

            expect(assig.canUploadWork(now)).toBe(false);

            updatePerms({
                can_submit_own_work: false,
                can_submit_others_work: true,
            });
            expect(assig.canUploadWork(now)).toBe(false);

            updatePerms({ can_submit_own_work: true });
            expect(assig.canUploadWork(now)).toBe(false);

            assigData.state = assignmentState.DONE;
            assigData.course.permissions.can_submit_others_work = false;
            assig = makeAssig(assigData);
            expect(assig.canUploadWork(now)).toBe(false);

            updatePerms({
                can_submit_own_work: false,
                can_submit_others_work: true,
            });
            expect(assig.canUploadWork(now)).toBe(false);

            updatePerms({can_submit_own_work: true});
            expect(assig.canUploadWork(now)).toBe(false);

        });

        it('should return true when you can submit work, the assignment is not hidden, and the deadline has not passed', () => {
            const now = moment();
            const assigData = {
                state: assignmentState.OPEN,
                deadline: moment(now).add(1, 'days'),
                course: {
                    permissions: {
                        can_submit_own_work: true,
                        can_submit_others_work: false,
                    },
                },
            };
            let assig = makeAssig(assigData);

            expect(assig.canUploadWork(now)).toBe(true);

            assigData.state = assignmentState.DONE;
            assig = makeAssig(assigData);
            expect(assig.canUploadWork(now)).toBe(true);
        });
    });

    describe('deadlinePassed', () => {
        it.each([
            [-1, 'minutes'],
            [-1, 'hours'],
            [-1, 'days'],
            [-1, 'months'],
            [-1, 'years'],
            [1, 'minutes'],
            [1, 'hours'],
            [1, 'days'],
            [1, 'months'],
            [1, 'years'],
        ])('should return true (false) when the deadline has (not) passed', (delta, type) => {
            const now = moment.utc();
            const givenDeadline = now.clone().add(delta, type).toISOString();
            const assig = makeAssig({
                deadline: givenDeadline,
            });

            expect(assig.deadlinePassed(now)).toBe(delta < 0 ? true : false);
            // It should default to 'now'.
            expect(assig.deadlinePassed()).toBe(delta < 0 ? true : false);
        });
    });

});