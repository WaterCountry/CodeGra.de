<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="rubric-viewer-row normal"
     :class="{ editable, locked }"
     @mouseenter="lockPopoverVisible = true"
     @mouseleave="lockPopoverVisible = false">
    <div class="row-description d-flex border-bottom">
        <p v-if="rubricRow.description"
           class="flex-grow-1 my-2 px-3 text-wrap-pre">{{
            rubricRow.description
        }}</p>
        <p v-else
           class="flex-grow-1 my-2 px-3 text-muted font-italic">
            This category has no description.
        </p>

        <template v-if="locked">
            <!-- Due to a rendering issue in edge, giving the icon
                 a margin-right moves it left by twice that amount... -->
            <icon name="lock"
                  class="rubric-lock my-2"
                  :class="{ 'mr-3': !$root.isEdge, 'mr-2': $root.isEdge }"
                  :id="`rubric-lock-${id}`" />

            <!-- We need to key this popover to make sure it actually
                 changes when the content changes. -->
            <b-popover :show="lockPopoverVisible"
                       :target="`rubric-lock-${id}`"
                       :content="lockPopover"
                       :key="lockPopover"
                       triggers=""
                       placement="top"
                       boundary="window" />
        </template>
    </div>

    <div class="rubric-row-items position-relative d-flex flex-row">
        <div v-for="item, i in rowItems"
             class="rubric-item pt-2 pl-2"
             :class="{
                 selected: item.id === selectedId,
                 'border-left': i > 0,
                 'pb-4': showProgressMeter,
             }"
             :style="{ flex: `0 0 ${itemWidth}`, maxWidth: itemWidth  }"
             @click="toggleItem(item)">
            <b class="mb-2">
                {{ item.points }} - {{ item.header }}

                <icon v-if="item.id === selectedId"
                      name="check"
                      class="float-right mr-2" />
            </b>

            <p class="description mb-0 pb-2 pr-2 text-justify text-wrap-pre">{{ item.description }}</p>
        </div>

        <div class="progress-meter"
             :style="{
                 opacity: showProgressMeter ? 1 : 0,
                 width: `${autoTestProgress}%`,
             }">
            <small :class="`progress-${readableAutoTestProgress}`">
                {{ readableAutoTestProgress }}%
            </small>
        </div>
    </div>
</div>
</template>

<script>
import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/lock';
import 'vue-awesome/icons/check';

import { AutoTestResult, RubricRow, RubricResult } from '@/models';

export default {
    name: 'rubric-viewer-normal-row',

    props: {
        value: {
            type: RubricResult,
            required: true,
        },
        rubricRow: {
            type: RubricRow,
            required: true,
        },
        assignment: {
            type: Object,
            required: true,
        },
        autoTest: {
            type: Object,
            default: null,
        },
        autoTestResult: {
            type: AutoTestResult,
            default: null,
        },
        editable: {
            type: Boolean,
            default: false,
        },
        active: {
            type: Boolean,
            default: false,
        },
    },

    data() {
        return {
            id: this.$utils.getUniqueId(),
            lockPopoverVisible: false,
        };
    },

    computed: {
        rowItems() {
            return this.rubricRow.items;
        },

        selectedItem() {
            return this.value.selected[this.rubricRow.id];
        },

        selectedId() {
            return this.$utils.getProps(this.selectedItem, null, 'id');
        },

        locked() {
            return this.rubricRow.locked;
        },

        showProgressMeter() {
            return this.locked === 'auto_test' && this.autoTestProgress != null;
        },

        lockPopover() {
            return this.rubricRow.lockMessage(this.autoTest, this.autoTestResult, this.value);
        },

        autoTestProgress() {
            if (this.autoTestResult == null) {
                return null;
            }

            const state = this.$utils.getProps(this.autoTestResult, null, 'state');
            const percentage = this.$utils.getProps(
                this.autoTestResult,
                null,
                'rubricResults',
                this.rubricRow.id,
                'percentage',
            );

            return state === 'not_started' ? null : percentage;
        },

        readableAutoTestProgress() {
            const progress = this.autoTestProgress;
            return progress == null ? 0 : progress.toFixed(0);
        },

        itemWidth() {
            return `${100 / this.rowItems.length}%`;
        },
    },

    methods: {
        toggleItem(item) {
            if (!this.editable || this.locked) {
                return;
            }

            this.$emit(
                'input',
                item.id === this.selectedId ? null : Object.assign({}, item, { multiplier: 1 }),
            );
        },
    },

    components: {
        Icon,
    },
};
</script>

<style lang="less" scoped>
@import '~mixins.less';

.rubric-item {
    line-height: 1.3;

    .rubric-viewer.editable .rubric-viewer-row.normal:not(.locked) & {
        cursor: pointer;

        &:hover {
            background-color: rgba(0, 0, 0, 0.125);
        }
    }

    &.selected {
        background-color: rgba(0, 0, 0, 0.09375);
    }

    .description {
        max-height: 5rem;
        overflow: auto;
    }
}
</style>
