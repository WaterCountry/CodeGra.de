<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="lti-provider-setup">
    <div v-if="ltiProvider.finalized">
        <local-header show-logo title="Provider setup was already finished" />

        <p>
            This LTI provider has already been setup. If this was <b>not</b>
            done by you please contact support as soon as possible!
        </p>
    </div>
    <component :is="wantedComponent"
               @update-provider="$emit('update-provider', $event)"
               v-else
               :secret="secret"
               :lti-provider="ltiProvider" />
</div>
</template>

<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

import * as api from '@/api/v1';

import CanvasSetup from './CanvasSetup';
import MoodleSetup from './MoodleSetup';
import BlackboardSetup from './BlackboardSetup';
import BrightspaceSetup from './BrightspaceSetup';

@Component({})
export default class LtiProviderSetup extends Vue {
    @Prop({ required: true }) ltiProvider!: api.lti.LTI1p3ProviderServerData;

    @Prop({ required: true }) secret!: string | null;

    get wantedComponent() {
        switch (this.ltiProvider.lms) {
            case 'Canvas':
                return CanvasSetup;
            case 'Moodle':
                return MoodleSetup;
            case 'Blackboard':
                return BlackboardSetup;
            case 'Brightspace':
                return BrightspaceSetup;
            default:
                return this.$utils.AssertionError.assertNever(this.ltiProvider.lms, `Unknown lms: ${this.ltiProvider.lms}`);
        }
    }
}
</script>
