<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
<div class="multiple-files-uploader"
     :class="{
        'no-border': noBorder,
        'no-hard-bottom-corners': noHardBottomCorners,
        disabled,
    }">
    <vue-dropzone ref="dropzone"
                  :id="uploaderId"
                  class="dropzone"
                  :class="`dropzone-amount-files-${amountOfFiles}`"
                  :disabled="disabled"
                  :options="dropzoneOptions"
                  :use-custom-slot="true"
                  :include-styling="false"
                  @vdropzone-file-added="fileAdded"
                  @vdropzone-removed-file="fileRemoved"
                  @vdropzone-drag-enter="dropzoneEntered"
                  @vdropzone-drag-leave="dropzoneLeft"
                  @vdropzone-drop="resetDragOverlay">
        <div v-if="showDropzoneOverlay" class="dz-hover-overlay"
             :class="{ hovered: dropzoneHovered }"/>

        <a class="dz-custom-message">
            <span class="center">
                <slot>
                    Click here or drop file(s) to upload.
                </slot>
            </span>
        </a>
    </vue-dropzone>
</div>
</template>

<script>
import VueDropzone from 'vue2-dropzone';

import { getUniqueId } from '@/utils';

export default {
    name: 'multiple-files-uploader',

    props: {
        value: {
            type: Array,
            required: true,
        },

        noBorder: {
            type: Boolean,
            default: false,
        },

        noHardBottomCorners: {
            type: Boolean,
            default: false,
        },

        disabled: {
            type: Boolean,
            default: false,
        },
    },

    computed: {
        dropzoneOptions() {
            return {
                url: '/api/v1/non-existing',
                multiple: true,
                autoProcessQueue: false,
                createImageThumbnails: false,
                addRemoveLinks: true,
            };
        },
    },

    data() {
        return {
            showDropzoneOverlay: 0,
            dropzoneHovered: 0,
            uploaderId: `submission-uploader-${getUniqueId()}`,
            filesToAdd: [],
            filesToRemove: [],
            ignoreInput: 0,
            ignoreEvent: 0,
            amountOfFiles: 0,
        };
    },

    mounted() {
        document.body.addEventListener('dragenter', this.bodyDragEnter, true);
        document.body.addEventListener('dragleave', this.bodyDragLeave, true);
        document.body.addEventListener('mouseup', this.resetDragOverlay, true);
    },

    destroyed() {
        document.body.removeEventListener('dragenter', this.dropzoneEntered);
        document.body.removeEventListener('dragleave', this.dropzoneLeft);
        document.body.removeEventListener('mouseup', this.resetDragOverlay);
    },

    watch: {
        value: {
            async handler(newVal, oldVal) {
                this.amountOfFiles = this.value.length;

                if (oldVal == null || this.ignoreInput) {
                    return;
                }
                await this.$nextTick();

                this.ignoreEvent++;

                const drop = this.$refs.dropzone;
                drop.removeAllFiles();
                this.value.forEach(f => drop.manuallyAddFile(f, '/api/v1/non-existing'));

                await this.$nextTick();

                this.ignoreEvent--;
            },
            immediate: true,
        },

        disabled: {
            immediate: true,
            async handler() {
                const drop = await this.$waitForRef('dropzone');
                if (drop == null) {
                    return;
                }

                if (this.disabled) {
                    drop.disable();
                } else {
                    drop.enable();
                }
            },
        },
    },

    methods: {
        fileAdded(added) {
            if (this.ignoreEvent) {
                return;
            }
            this.filesToAdd.push(added);
            this.$nextTick(this.flushQueue);
        },

        fileRemoved(removed) {
            if (this.ignoreEvent) {
                return;
            }
            this.filesToRemove.push(removed);
            this.$nextTick(this.flushQueue);
        },

        flushQueue() {
            if (!this.filesToAdd.length && !this.filesToRemove.length) {
                return;
            }
            this.ignoreInput++;
            this.$emit(
                'input',
                [...this.value, ...this.filesToAdd].filter(f => !this.filesToRemove.includes(f)),
            );
            this.filesToAdd = [];
            this.filesToRemove = [];
            this.$nextTick(() => {
                this.ignoreInput--;
            });
        },

        resetDragOverlay() {
            this.dropzoneHovered = 0;
            this.showDropzoneOverlay = 0;
        },

        bodyDragEnter() {
            this.showDropzoneOverlay++;
        },

        bodyDragLeave() {
            if (this.showDropzoneOverlay > 0) {
                this.showDropzoneOverlay--;
            }
        },

        dropzoneEntered() {
            this.dropzoneHovered++;
        },

        dropzoneLeft() {
            if (this.dropzoneHovered > 0) {
                this.dropzoneHovered--;
            }
        },
    },

    components: {
        VueDropzone,
    },
};
</script>

<style lang="less">
@import '~mixins.less';

.multiple-files-uploader.disabled .dropzone {
    opacity: 0.65;

    .dz-hover-overlay {
        display: none;
        background-color: rgba(0, 0, 0, 0) !important;
    }

    .dz-message {
        cursor: not-allowed;

        &:hover {
            background-color: rgba(0, 0, 0, 0);
            text-decoration: none;
        }
    }
}

.multiple-files-uploader {
    &:not(.no-border) .dropzone {
        border: 1px solid rgba(0, 0, 0, 0.125);
        border-top-left-radius: @border-radius;
        border-top-right-radius: @border-radius;

        &.dropzone-amount-files-0 .dz-custom-message:hover,
        .dz-hover-overlay {
            border-top-left-radius: @border-radius;
            border-top-right-radius: @border-radius;
        }
    }

    &.no-hard-bottom-corners .dropzone {
        border-bottom-right-radius: @border-radius;
        border-bottom-left-radius: @border-radius;

        &.dropzone-amount-files-0 .dz-custom-message:hover,
        .dz-hover-overlay {
            border-bottom-right-radius: @border-radius;
            border-bottom-left-radius: @border-radius;
        }
    }

    .dropzone {
        position: relative;
        display: flex;
        flex-direction: column;
        height: 100%;
        margin-bottom: -1px;

        @{dark-mode} {
            border-color: @color-primary-darker;
        }

        .dz-hover-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 20;
            background-color: rgba(0, 0, 0, 0.25);
            pointer-events: none;

            &.hovered {
                background-color: rgba(0, 0, 0, 0.35);

                @{dark-mode} {
                    background-color: rgba(0, 0, 0, 0.4);
                }
            }

            &::after {
                content: 'Drop files here.';
                position: absolute;
                top: 0.75rem;
                left: 0.75rem;
                right: 0.75rem;
                bottom: 0.75rem;
                border: 2px dashed white;
                border-radius: 2 * @border-radius;
                color: white;
                font-size: 2rem;
                text-align: center;
                display: flex;
                justify-content: center;
                align-items: center;

                @{dark-mode} {
                    color: @text-color-dark;
                    border-color: @text-color-dark;
                }
            }
        }

        .dz-message {
            display: flex;
            flex: 1 1 auto;
            width: 100%;
            min-height: 4.5rem;
            cursor: pointer;
            color: @color-primary;
            text-decoration: underline;
            order: 1;

            &:hover {
                background-color: rgba(0, 0, 0, 0.075);
                text-decoration: underline;
            }

            .dz-custom-message {
                flex: 1 1 100%;
                align-self: stretch;
                position: relative;

                .center {
                    position: absolute;
                    display: block;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 100%;
                    text-align: center;
                }
            }
        }

        .dz-hover-overlay + .dz-custom-message {
            display: none;
        }

        .dz-preview {
            position: relative;
            z-index: 10;
            display: flex;
            padding: 0.75rem;
            background-color: @color-lighter-gray;
            border-bottom: 1px solid rgba(0, 0, 0, 0.125);

            &:nth-child(2) {
                border-top-right-radius: 0.25rem;
                border-top-left-radius: 0.25rem;
            }

            &:nth-child(2n) {
                background-color: white;
            }

            @{dark-mode} {
                background-color: darken(@color-primary, 2.5%);
                border-color: @color-primary-darker;

                &:nth-child(2n) {
                    background-color: @color-primary;
                }
            }
        }

        .dz-details {
            display: flex;
            font-size: 1rem;
            flex: 1 1 auto;
            flex-direction: row-reverse;
            justify-content: flex-end;
            min-width: 0;

            .dz-filename {
                flex: 1 1 auto;
                word-break: all;
                min-width: 0;

                span {
                    max-width: 100%;
                    text-overflow: ellipsis;
                    display: block;
                    overflow-x: hidden;
                }
            }

            .dz-size {
                flex: 0 0 auto;
                margin: 0 0.75rem;
            }
        }

        .dz-remove {
            flex: 0 0 auto;
            top: auto;
            bottom: auto;
            font-size: 0;
            margin: -0.25rem -0.5rem;
            padding: 0.25rem 0.5rem;
            text-decoration: none !important;

            &::after {
                content: '✖';
                font-size: 1rem;
                transition: all 250ms;
                color: @color-primary;

                @{dark-mode} {
                    color: @text-color-dark;
                }
            }

            &:hover::after {
                color: @color-danger !important;
            }
        }

        .dz-image,
        .dz-progress,
        .dz-error-mark,
        .dz-success-mark,
        .dz-error-message {
            display: none;
        }
    }
}
</style>
