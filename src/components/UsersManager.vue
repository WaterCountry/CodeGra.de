<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<loader v-if="loading" page-loader/>
<div class="users-manager" v-else>
    <div ref="copyContainer" />
    <div class="registration-link-wrapper" v-if="course.permissions.can_edit_course_users && UserConfig.features.course_register">
        <table class="registration-table table">
            <thead>
                <tr>
                    <th />
                    <th>
                        Link
                        <description-popover hug-text>
                            This is the link users can use to register an
                            automatically enroll in this course. The link does
                            not enroll already logged-in users.
                        </description-popover>
                    </th>
                    <th>
                        Expiration date
                        <description-popover hug-text>
                            After this date the link will no longer work.
                        </description-popover>
                    </th>
                    <th>
                        Role
                        <description-popover hug-text>
                            The role users will get in the course after
                            registering with this link.
                        </description-popover>
                    </th>
                    <th />
                </tr>
            </thead>
            <tbody>
                <tr v-for="link in registrationLinks"
                    :key="link.trackingId"
                    v-if="!link.deleted"
                    class="registration-links">
                    <template v-if="link.id == null">
                        <td  />
                        <td class="align-middle">
                            This link has not been saved yet
                        </td>
                    </template>
                    <template v-else>
                        <td>
                            <div v-b-popover.top.hover="isLinkExpired(link) ? 'This link has expired, therefore it cannot be copied anymore.' : ''">
                                <submit-button :submit="() => copyLink(link)" class="mr-3"
                                               :disabled="isLinkExpired(link)"
                                               variant="secondary">
                                    Copy
                                </submit-button>
                            </div>
                        </td>
                        <td class="align-middle">
                            <div class="d-flex">
                                <code style="word-break: break-all"
                                      :style="{ textDecoration: isLinkExpired(link) ? 'line-through' : 'none' }">
                                    {{ getRegistrationLinkUrl(link) }}
                                </code>
                            </div>
                        </td>
                    </template>
                    <td>
                        <datetime-picker v-model="link.expiration_date"
                                         placeholder="None set"/>
                    </td>
                    <td>
                        <b-dropdown :text="link.role.name"
                                    class="role-dropdown">
                            <b-dropdown-header>Select the new role</b-dropdown-header>
                            <b-dropdown-item v-for="role in roles"
                                             @click="$set(link, 'role', role)"
                                             :key="role.id">
                                {{ role.name }}
                            </b-dropdown-item>
                        </b-dropdown>
                    </td>
                    <td>
                        <div class="save-link-wrapper">
                            <submit-button :submit="() => saveLink(link)" label="Save"
                                           :disabled="link.role.id == null || link.expiration_date == null"
                                           class="mr-1"/>
                            <submit-button :submit="() => deleteLink(link)"
                                           @after-success="$set(link, 'deleted', true)"
                                           label="Delete"
                                           :confirm="link.id ? 'Are you sure you want to delete this link? This invalidates the link.' : ''"
                                           variant="danger"
                                           />
                        </div>
                    </td>
                </tr>
                <tr v-if="registrationLinks.filter(x => !x.deleted).length === 0">
                    <td colspan="5" class="text-muted font-italic">
                        There are no registration links yet.
                    </td>
                </tr>

                <tr>
                    <td colspan="5">
                        <b-btn @click="addRegistrationLink"
                               class="float-right"
                               name="add-registration-link"
                               variant="primary">
                            Add new
                        </b-btn>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

    <b-table striped
             ref="table"
             v-if="canListUsers"
             class="users-table"
             :items="filteredUsers"
             :fields="fields"
             :sort-compare="sortTable"
             sort-by="User">

        <template slot="User" slot-scope="item">
            <span class="username">{{item.value.name}} ({{item.value.username}})</span>
        </template>

        <template slot="CourseRole" slot-scope="item">
            <loader :scale="2" v-if="updating[item.item.User.id]"/>
            <b-dropdown :text="item.value.name"
                        disabled
                        class="role-dropdown"
                        v-b-popover.top.hover="'You cannot change your own role'"
                        v-else-if="item.item.User.name == userName"/>
            <b-dropdown :text="item.value.name"
                        class="role-dropdown"
                        v-else>
                <b-dropdown-header>Select the new role</b-dropdown-header>
                <b-dropdown-item v-for="role in roles"
                                 @click="changed(item.item, role)"
                                 :key="role.id">
                    {{ role.name }}
                </b-dropdown-item>
            </b-dropdown>
        </template>
    </b-table>

    <b-alert show variant="danger" v-else>
        You can only actually manage users when you also have the 'list course
        users' ('can_list_course_users') permission
    </b-alert>

    <b-popover class="new-user-popover"
               :triggers="course.is_lti ? 'hover' : ''"
               target="new-users-input-field">
        You cannot add users to a lti course.
    </b-popover>
    <b-form-fieldset class="add-student"
                     id="new-users-input-field">
        <b-input-group>
            <user-selector v-model="newStudentUsername"
                           placeholder="New student"
                           :use-selector="canListUsers && canSearchUsers"
                           :extra-params="{ exclude_course: course.id }"
                           :disabled="course.is_lti"/>

            <template slot="append">
                <b-dropdown class="drop"
                            :text="newRole ? newRole.name : 'Role'"
                            :disabled="course.is_lti">
                    <b-dropdown-item v-for="role in roles"
                                     v-on:click="() => {newRole = role; error = '';}"
                                     :key="role.id">
                        {{ role.name }}
                    </b-dropdown-item>
                </b-dropdown>
                <submit-button class="add-user-button"
                               label="Add"
                               :submit="addUser"
                               @success="afterAddUser"
                               :disabled="course.is_lti"/>
            </template>
        </b-input-group>
    </b-form-fieldset>
</div>
</template>

<script>
import moment from 'moment';

import { mapGetters } from 'vuex';
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/times';
import 'vue-awesome/icons/pencil';
import 'vue-awesome/icons/floppy-o';
import 'vue-awesome/icons/ban';

import { cmpNoCase, cmpOneNull, waitAtLeast } from '@/utils';
import Loader from './Loader';
import SubmitButton from './SubmitButton';
import UserSelector from './UserSelector';
import DatetimePicker from './DatetimePicker';

import DescriptionPopover from './DescriptionPopover';

export default {
    name: 'users-manager',
    props: {
        course: {
            type: Object,
            required: true,
        },

        filter: {
            type: String,
            default: '',
        },
    },

    data() {
        return {
            roles: [],
            users: [],
            loading: true,
            updating: {},
            newStudentUsername: null,
            canListUsers: false,
            canSearchUsers: false,
            newRole: '',
            error: '',
            fields: {
                User: {
                    label: 'Name',
                    sortable: true,
                    key: 'User',
                },
                CourseRole: {
                    label: 'role',
                    sortable: true,
                    key: 'CourseRole',
                },
            },

            registrationLinks: [],
            UserConfig,
        };
    },

    computed: {
        ...mapGetters('user', {
            userName: 'name',
        }),

        courseId() {
            return this.course.id;
        },

        filteredUsers() {
            return this.users.filter(this.filterFunction);
        },
    },

    watch: {
        course(newVal, oldVal) {
            if (newVal.id !== oldVal.id) {
                this.loadData();
            }
        },
    },

    mounted() {
        this.loadData();
    },

    methods: {
        filterFunction(item) {
            if (!this.filter) {
                return true;
            }

            const terms = [item.User.name, item.User.username, item.CourseRole.name];
            return (this.filter || '')
                .toLowerCase()
                .split(' ')
                .every(word => terms.some(t => t.toLowerCase().indexOf(word) >= 0));
        },

        async loadData() {
            this.loading = true;

            [
                ,
                ,
                this.canListUsers,
                this.canSearchUsers,
                this.registrationLinks,
            ] = await Promise.all([
                this.getAllUsers(),
                this.getAllRoles(),
                this.$hasPermission('can_list_course_users', this.courseId),
                this.$hasPermission('can_search_users'),
                this.getRegistrationLinks(),
            ]);

            this.loading = false;
            this.$nextTick(() => {
                this.$refs.table.sortBy = 'User';
            });
        },

        getRegistrationLinks() {
            return this.$http.get(`/api/v1/courses/${this.course.id}/registration_links/`).then(
                ({ data }) =>
                    data.map(link => {
                        link.expiration_date = this.$utils.formatDate(link.expiration_date);
                        link.trackingId = this.$utils.getUniqueId();
                        return link;
                    }),
                () => [],
            );
        },

        sortTable(a, b, sortBy) {
            if (typeof a[sortBy] === 'number' && typeof b[sortBy] === 'number') {
                return a[sortBy] - b[sortBy];
            } else if (sortBy === 'User') {
                const first = a[sortBy];
                const second = b[sortBy];

                const ret = cmpOneNull(first, second);

                return ret === null ? cmpNoCase(first.name, second.name) : ret;
            } else if (sortBy === 'CourseRole') {
                const first = a.CourseRole;
                const second = b.CourseRole;

                const ret = cmpOneNull(first, second);

                return ret === null ? cmpNoCase(first.name, second.name) : ret;
            }
            return 0;
        },

        getAllUsers() {
            return this.$http.get(`/api/v1/courses/${this.courseId}/users/`).then(
                ({ data }) => {
                    this.users = data;
                },
                () => [],
            );
        },

        getAllRoles() {
            return this.$http.get(`/api/v1/courses/${this.courseId}/roles/`).then(({ data }) => {
                this.roles = data;
            });
        },

        changed(user, role) {
            for (let i = 0, len = this.users.length; i < len; i += 1) {
                if (this.users[i].User.id === user.User.id) {
                    this.$set(user, 'CourseRole', role);
                    this.$set(this.users, i, user);
                    break;
                }
            }
            this.$set(this.updating, user.User.id, true);
            const req = this.$http.put(`/api/v1/courses/${this.courseId}/users/`, {
                user_id: user.User.id,
                role_id: role.id,
            });

            waitAtLeast(250, req)
                .then(() => {
                    this.$set(this.updating, user.User.id, false);
                    delete this.updating[user.User.id];
                })
                .catch(err => {
                    // TODO: visual feedback
                    // eslint-disable-next-line
                    console.dir(err);
                });
        },

        addUser() {
            if (this.newRole === '') {
                throw new Error('You have to select a role!');
            } else if (this.newStudentUsername == null || this.newStudentUsername.username === '') {
                throw new Error('You have to add a non-empty username!');
            }

            return this.$http.put(`/api/v1/courses/${this.courseId}/users/`, {
                username: this.newStudentUsername.username,
                role_id: this.newRole.id,
            });
        },

        afterAddUser(response) {
            this.newRole = '';
            this.newStudentUsername = null;
            this.users.push(response.data);
        },

        addRegistrationLink() {
            this.registrationLinks.push({
                id: undefined,
                role: {
                    name: 'Select a default role',
                },
                expiration_date: null,
                trackingId: this.$utils.getUniqueId(),
            });
        },

        saveLink(link) {
            if (link.role == null) {
                throw new Error('You have to select a default role');
            }
            return this.$http
                .put(`/api/v1/courses/${this.course.id}/registration_links/`, {
                    id: link.id,
                    role_id: link.role.id,
                    expiration_date: this.$utils.convertToUTC(link.expiration_date),
                })
                .then(response => {
                    response.data.expiration_date = link.expiration_date;
                    Object.assign(link, response.data);
                    return response;
                });
        },

        deleteLink(link) {
            if (link.id == null) {
                return null;
            }
            return this.$http.delete(
                `/api/v1/courses/${this.course.id}/registration_links/${link.id}`,
            );
        },

        getRegistrationLinkUrl(link) {
            const { host, protocol } = window.location;
            const linkId = link.id;
            return `${protocol}//${host}/register/?course_register_link_id=${linkId}&course_id=${
                this.course.id
            }&register_for=${encodeURIComponent(this.course.name)}`;
        },

        copyLink(link) {
            return this.$copyText(this.getRegistrationLinkUrl(link), this.$refs.copyContainer);
        },

        isLinkExpired(link) {
            if (link.expiration_date == null) {
                return false;
            }
            return this.$root.$now.isAfter(moment(link.expiration_date, moment.ISO_8601).local());
        },
    },

    components: {
        Icon,
        Loader,
        SubmitButton,
        UserSelector,
        DatetimePicker,
        DescriptionPopover,
    },
};
</script>

<style lang="less">
.users-table tr :nth-child(2) {
    text-align: center;
}

.users-manager .users-table,
.users-manager .registration-table {
    th,
    td {
        &:last-child {
            width: 1px;
        }
    }
}

.users-table td {
    vertical-align: middle;
}

.users-table .dropdown .btn {
    width: 10rem;
}

.add-student .drop .btn {
    border-radius: 0;
}

.new-user-popover button {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
}

.username {
    word-wrap: break-word;
    word-break: break-word;
    -ms-word-break: break-all;

    -webkit-hyphens: auto;
    -moz-hyphens: auto;
    -ms-hyphens: auto;
    hyphens: auto;
}

.role-dropdown .dropdown-toggle {
    padding-top: 3px;
    padding-bottom: 4px;
}

.registration-table .role-dropdown .btn {
    padding: 0.375rem 0.75rem;
}

.add-user-button {
    .btn {
        border-top-left-radius: 0;
        border-bottom-left-radius: 0;
        height: 100%;
    }
}

.save-link-wrapper {
    display: flex;
}
</style>