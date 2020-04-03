<template>
<b-card class="analytics-submission-date"
        header-class="d-flex"
        :body-class="noSubmissionWithinRange ? 'center' : ''">
    <template #header>
        <div class="flex-grow-1">
            Students submitted on
        </div>

        <div class="d-flex flex-grow-0">
            <b-button :variant="relative ? 'primary' : 'outline-primary'"
                      @click="relative = !relative"
                      v-b-popover.top.hover="'Relative to filter group'"
                      class="ml-3">
                <icon name="percent" />
            </b-button>

            <datetime-picker :value="range"
                             @on-close="updateRange"
                             placeholder="Select dates"
                             :config="{
                                 mode: 'range',
                                 enableTime: false,
                                 minDate: minDate.toISOString(),
                                 maxDate: maxDate.toISOString(),
                             }"
                             class="ml-2 text-center"/>

            <b-input-group class="mb-0">
                <input :value="binSize"
                        @input="updateBinSize"
                        type="number"
                        min="1"
                        step="1"
                        class="form-control ml-2 pt-1"
                        style="max-width: 4rem;"/>

                <b-form-select :value="binUnit"
                                @input="updateBinUnit"
                                :options="binUnits"
                                class="pt-1"
                                style="max-width: 7.5rem"/>
            </b-input-group>

            <div class="icon-button danger"
                 @click="resetParams"
                 v-b-popover.top.hover="'Reset'">
                <icon name="reply" />
            </div>

            <description-popover class="icon-button ml-1"
                                 placement="bottom"
                                 :scale="1">
                <p class="mb-2">
                    This histogram shows at what times students have submitted
                    their work.  You can change the range of dates that is
                    displayed and the bin size of the histogram.
                </p>

                <p>
                    By default this shows the percentage of students in the
                    respective filter group that have submitted in some
                    interval.  You can see the total number of students by
                    clicking the <icon name="percent" :scale="0.75" class="mx-1" />
                    button.
                </p>
            </description-popover>
        </div>
    </template>

    <template v-if="noSubmissionWithinRange">
        <h3 class="p-3 text-muted font-italic">
            No submissions within this range!
        </h3>
    </template>

    <template v-else-if="tooMuchBins && !forceRender">
        <p class="p-3 text-muted font-italic">
            The selected range contains a lot of data points and rendering the
            graph may freeze your browser.  Please select fewer bins or click
            the button below to render the dataset anyway.
        </p>

        <b-button variant="primary"
                  class="float-right"
                  @click="forceRender = true">
            Render anyway
        </b-button>
    </template>

    <bar-chart v-else
               :chart-data="histogramData"
               :options="histogramOptions"
               :width="300"
               :height="$root.$isXLargeWindow ? 75 : 100"/>
</b-card>
</template>

<script>
import moment from 'moment';
import * as stat from 'simple-statistics';

import Icon from 'vue-awesome/components/Icon';
import 'vue-awesome/icons/percent';
import 'vue-awesome/icons/reply';

import { deepEquals, filterObject } from '@/utils';

import { BarChart } from '@/components/Charts';
import DatetimePicker from '@/components/DatetimePicker';
import DescriptionPopover from '@/components/DescriptionPopover';

export default {
    name: 'analytics-submission-date',

    props: {
        value: {
            type: Object,
            default: {},
        },
        filterResults: {
            type: Array,
            required: true,
        },
    },

    data() {
        return {
            ...this.fillSettings(this.value),

            // Changing the submission date bin size can cause a lot of
            // bins to be drawn, especially when typing something like
            // `10`, where the value is temporarily `1`. We debounce the
            // event of the bin size input with this timer to prevent
            // temporary page freezes or flickering of the "too many bins"
            // message when editing the bin size.
            binSizeTimer: null,

            // When there are a lot of datapoints to draw in a chart the
            // browser may freeze, so we put a soft cap at 100. Users can
            // still choose to render the chart anyway, in which case this
            // boolean is temporarily set to true.
            forceRender: false,
        };
    },

    computed: {
        filterLabels() {
            return this.filterResults.map(f => f.filter.toString());
        },

        submissionSources() {
            return this.filterResults.map(r => r.submissions);
        },

        minDate() {
            const firstPerSource = this.submissionSources.map(source => source.firstSubmissionDate);
            return firstPerSource.reduce(
                (f, d) => (f == null || f.isAfter(d) ? d : f),
                null,
            ).local().startOf('day');
        },

        maxDate() {
            const lastPerSource = this.submissionSources.map(source => source.lastSubmissionDate);
            return lastPerSource.reduce(
                (l, d) => (l == null || l.isBefore(d) ? d : l),
                null,
            ).local().endOf('day');
        },

        binUnits() {
            return ['minutes', 'hours', 'days', 'weeks', 'years'];
        },

        noSubmissionWithinRange() {
            const datasets = this.histogramData.datasets;
            return stat.sum(datasets.flatMap(ds => ds.data)) === 0;
        },

        tooMuchBins() {
            return this.histogramData.labels.length > 100;
        },

        histogramData() {
            const subs = this.submissionSources.map(source =>
                source.binSubmissionsByDate(this.range, this.binSize, this.binUnit),
            );

            const format = this.dateFormatter;
            const dateLookup = subs.reduce((acc, bins) => {
                Object.values(bins).forEach(bin => {
                    if (!acc[bin.start]) {
                        acc[bin.start] = format(bin.start, bin.end);
                    }
                });
                return acc;
            }, {});
            const allDates = Object.keys(dateLookup).sort();

            const datasets = subs.map((bins, i) => {
                const absData = allDates.map(d => (bins[d] == null ? 0 : bins[d].data.length));
                const nSubs = stat.sum(absData);
                const relData = absData.map(x => (nSubs > 0 ? (100 * x) / nSubs : 0));

                return {
                    label: this.filterLabels[i],
                    absData,
                    relData,
                    data: this.relative ? relData : absData,
                };
            });

            return {
                labels: allDates.map(k => dateLookup[k]),
                datasets,
            };
        },

        dateFormatter() {
            const unit = this.binUnit;

            const format = (d, fmt) =>
                moment(d)
                    .utc()
                    .format(fmt);

            switch (unit) {
                case 'minutes':
                    return start => format(start, 'ddd DD-MM HH:mm');
                case 'hours':
                    return start => format(start, 'ddd DD-MM HH:00');
                default:
                    return (start, end) => {
                        const fmt = 'ddd DD-MM';
                        // The times reported per bin are UTC UNIX epoch timestamps.
                        const s = format(start, fmt);
                        const e = format(end, fmt);
                        return s === e ? s : `${s} — ${e}`;
                    };
            }
        },

        histogramOptions() {
            const getDataset = (tooltipItem, data) =>
                data.datasets[tooltipItem.datasetIndex];

            const label = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                return ds.label;
            };

            const afterLabel = (tooltipItem, data) => {
                const ds = getDataset(tooltipItem, data);
                const abs = ds.absData[tooltipItem.index];
                const rel = ds.relData[tooltipItem.index];

                // Do not escape, chart.js does its own escaping.
                return [
                    `Number of students: ${abs}`,
                    `Percentage of students: ${this.to2Dec(rel)}`,
                ];
            };

            const labelString = this.relative
                ? 'Percentage of students'
                : 'Number of students';

            return {
                scales: {
                    yAxes: [
                        {
                            ticks: {
                                beginAtZero: true,
                            },
                            scaleLabel: {
                                display: true,
                                labelString,
                            },
                        },
                    ],
                },
                tooltips: {
                    callbacks: { label, afterLabel },
                },
            };
        },

        settings() {
            const defaults = this.fillSettings({});
            const settings = {
                relative: this.relative,
                range: this.range,
                binSize: this.binSize,
                binUnit: this.binUnit,
            };

            return filterObject(settings, (val, key) => !deepEquals(val, defaults[key]));
        },
    },

    methods: {
        fillSettings(settings) {
            return Object.assign({
                relative: true,
                range: [],
                binSize: 1,
                binUnit: 'days',
            }, settings);
        },

        resetParams() {
            Object.assign(this, this.fillSettings({}));

            this.forceRender = false;
            clearTimeout(this.binSizeTimer);
        },

        updateRange(event) {
            const curRange = this.range;
            const newRange = event.map(d => moment(d));

            console.log(newRange.map(d => d.toISOString()), this.minDate.toISOString());

            if (
                newRange.length !== curRange.length ||
                // Check if all the dates are the same as the previous to
                // prevent a rerender, e.g. in case a user just opened the
                // popover and immediately closes it by clicking somewhere
                // in the page.
                !newRange.every((d, i) => d.isSame(curRange[i]))
            ) {
                this.forceRender = false;
                this.range = event;
            }
        },

        updateBinSize(event) {
            clearTimeout(this.binSizeTimer);
            this.binSizeTimer = setTimeout(() => {
                const newSize = parseFloat(event.target.value);
                if (!Number.isNaN(newSize) && newSize !== this.binSize && newSize > 0) {
                    this.binSize = Number(newSize);
                    this.forceRender = false;
                }
            }, 500);
        },

        updateBinUnit(unit) {
            this.forceRender = false;
            this.binUnit = unit;
        },

        to2Dec(x) {
            return this.$utils.toMaxNDecimals(x, 2);
        },
    },

    watch: {
        settings: {
            immediate: true,
            handler() {
                this.$emit('input', this.settings);
            },
        },
    },

    components: {
        Icon,
        BarChart,
        DatetimePicker,
        DescriptionPopover,
    },
};
</script>