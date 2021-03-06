<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="canvas-setup">
    <cg-wizard-wrapper
        v-model="wizardPage"
        use-local-header
        :get-next-page-disabled-popover="nextPageDisabled">
        <template #header-wrapper="{ position }"
                  v-if="showLogo">
            <cg-logo :inverted="!darkMode"
                     :style="{ opacity: position === 'prepend' ? 0 : 1 }" />
        </template>
        <template #title="{ page, totalPages }">
            Connect CodeGrade to Canvas {{ page }} / {{ totalPages }}

        </template>

        <template #page-1="{ nextPage }">
            <p>
                First we need to create a new "Developer Key" for CodeGrade.
            </p>

            <p>
                To do this first open Canvas and login as administrator. Now
                select the "Admin" item in the sidebar and navigate to
                "Developer Keys". A button should appear at the top left of
                your screen with the text "+ Developer Key"; click this button
                and select "LTI Key" in the appearing dropdown.
            </p>

            <p>
                A page should load to configure the new developer key. First change the configure method,
                by selecting the "Enter URL" option from the "method"
                selector. In the field for the "JSON Url" please insert the
                following url:
            </p>

            <pre><code>{{ jsonUrl }}</code></pre>

            <p>
                Now please enter the following urls in the "Redirect URIs" box:
            </p>

            <pre><code>{{ redirectUrl }}</code></pre>

            <p>
                Last, but not least, insert a name for the new key, something
                like "CodeGrade" seems appropriate. Finally click the "save"
                button at the bottom right of your screen, and
                <a href="#" @click.prevent="nextPage" class="inline-link">continue to the next step</a>.
            </p>
        </template>

        <template #page-2="{ nextPage }">
            <p>
                You should now have created the developer keys, and you should
                be back on the overview page for all the Developer keys in
                Canvas. Under the category "Details" there should be a
                relatively long number for the just created key, this is the
                "client id" for CodeGrade. Please copy it, and paste it in the
                input below.

            </p>

            <b-form-group class="mb-3 d-block">
                <b-input-group prepend="Client ID">
                    <input class="form-control" v-model="newClientId"
                           placeholder="The client id from Canvas" />
                    <b-input-group-append>
                        <cg-submit-button :submit="submitClientId" />
                    </b-input-group-append>
                </b-input-group>
            </b-form-group>

            <p v-if="ltiProvider.client_id">
                We received the client id, you can
                <a href="#" class="inline-link"
                   @click.prevent="nextPage">continue to the next step</a>.
            </p>
        </template>

        <template #page-3>
            <p>
                For the final step we need to add CodeGrade as an external app
                to the canvas installation.  Select the "Settings" option in the
                sidebar in Canvas, and select the "Apps" tab, and click the
                button to add an app. A modal should appear, and select "By
                Client ID" for the "Configuration Type". For the "Client ID"
                insert <code>{{ ltiProvider.client_id }}</code>.
            </p>

            <p>
                After adding the app please insert the url on which your Canvas
                instance is hosted, and click the "Finalize" button below.
            </p>

            <advanced-collapse class="mb-3">
                <p>
                    These options are the same for all Canvas default production
                    instances, however you can change them if you have a custom
                    Canvas setup.
                </p>

                <b-form-group>
                    <b-input-group prepend="Key set url">
                        <input class="form-control"
                               v-model="keySetUrl"
                               :placeholder="defaultKeySetUrl" />
                    </b-input-group>
                </b-form-group>

                <b-form-group>
                    <b-input-group prepend="Auth token url">
                        <input class="form-control"
                               v-model="authTokenUrl"
                               :placeholder="defaultAuthTokenUrl" />
                    </b-input-group>
                </b-form-group>

                <b-form-group class="mb-0">
                    <b-input-group prepend="Auth login url">
                        <input class="form-control"
                               v-model="authLoginUrl"
                               :placeholder="defaultAuthLoginUrl" />
                    </b-input-group>
                </b-form-group>
            </advanced-collapse>

            <b-form-group>
                <b-input-group>
                    <input class="form-control"
                           v-model="canvasBaseUrl"
                           placeholder="https://canvas." />
                    <b-input-group-append>
                        <cg-submit-button
                            confirm="After finalizing your configuration you cannot edit it anymore. Are you sure you want to finalize your configuration?"
                            label="Finalize"
                            :submit="finalizeProvider"
                            @after-success="afterFinalizeProvider" />
                    </b-input-group-append>
                </b-input-group>
            </b-form-group>
        </template>

        <template #page-4>
            <p class="text-center">
                Your Canvas integration has been finalized, and is now ready to use!
            </p>
        </template>
    </cg-wizard-wrapper>
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

import { mapGetters } from 'vuex';
import * as api from '@/api/v1';

// @ts-ignore
import AdvancedCollapse from '@/components/AdvancedCollapse';

@Component({
    components: {
        AdvancedCollapse,
    },
    computed: {
        ...mapGetters('pref', ['darkMode']),
    },
})
export default class CanvasSetup extends Vue {
    @Prop({ required: true }) ltiProvider!: api.lti.NonFinalizedLTI1p3ProviderServerData;

    @Prop({ required: true }) secret!: string | null;

    wizardPage: number = 1;

    readonly darkMode!: boolean;

    newClientId: string | null = this.ltiProvider.client_id;

    keySetUrl: string | null = null;

    authTokenUrl: string | null = null;

    authLoginUrl: string | null = null;

    canvasBaseUrl: string | null = null;

    get defaultAuthTokenUrl() {
        return `${this.canvasBaseUrl ?? ''}/login/oauth2/token`;
    }

    get defaultAuthLoginUrl() {
        return `${this.canvasBaseUrl ?? ''}/api/lti/authorize_redirect`;
    }

    get defaultKeySetUrl() {
        return `${this.canvasBaseUrl ?? ''}/api/lti/security/jwks`;
    }

    get showLogo(): boolean {
        return (this.$root as any).$isMediumWindow;
    }

    get redirectUrl(): string {
        return (<const>['launch_to_latest_submission', 'launch']).map(
            extraPath => this.$utils.buildUrl(
                ['api', 'v1', 'lti1.3', extraPath],
                {
                    baseUrl: this.$userConfig.externalUrl,
                },
            ),
        ).join('\n');
    }

    get jsonUrl(): string {
        return this.$utils.buildUrl(
            ['api', 'v1', 'lti1.3', 'providers', this.ltiProvider.id, 'config'],
            {
                baseUrl: this.$userConfig.externalUrl,
            },
        );
    }

    nextPageDisabled(currentPage: number): string | null {
        if (currentPage === 3) {
            return 'Please finalize the provider';
        } else if (currentPage === 2 && !this.ltiProvider.client_id) {
            return 'Please fill in the client id from Canvas.';
        }
        return null;
    }

    submitClientId() {
        if (!this.newClientId) {
            throw new Error('Please insert the client id');
        }

        return api.lti.updateLti1p3Provider(this.ltiProvider, this.secret, {
            client_id: this.newClientId,
        }).then(({ data }) => {
            this.$emit('update-provider', data);
        });
    }

    finalizeProvider() {
        if (!this.canvasBaseUrl) {
            if (!this.keySetUrl || !this.authTokenUrl || !this.authLoginUrl) {
                throw new Error('Please insert a base url');
            }
        } else if (!this.$utils.isValidHttpUrl(this.canvasBaseUrl)) {
            throw new Error('The base url does not look like a valid url');
        }

        return api.lti.updateLti1p3Provider(this.ltiProvider, this.secret, {
            auth_token_url: this.authTokenUrl ?? this.defaultAuthTokenUrl,
            auth_login_url: this.authLoginUrl ?? this.defaultAuthLoginUrl,
            key_set_url: this.keySetUrl ?? this.defaultKeySetUrl,
            finalize: true,
        });
    }

    afterFinalizeProvider() {
        this.wizardPage = 4;
    }
}
</script>

<style lang="less" scoped>
@import '~mixins.less';

.cg-logo {
    height: 1.5rem;
    width: auto;
}

pre {
    display: block;
    margin-bottom: 1rem;
    color: @color-code;
}
</style>
