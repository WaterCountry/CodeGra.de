/* SPDX-License-Identifier: AGPL-3.0-only */
import Vue from 'vue';
import moment from 'moment';

// @ts-ignore
import { readableFormatDate } from '@/utils';

export default Vue.extend({
    functional: true,

    props: {
        date: {
            type: Object,
            validator: moment.isMoment,
        },

        now: {
            type: Object,
            validator: moment.isMoment,
        },
    },

    render(h, ctx) {
        return h(
            'span',
            {
                attrs: Object.assign(
                    {
                        title: readableFormatDate(ctx.props.date),
                    },
                    ctx.data.attrs,
                ),
                class: ctx.data.staticClass,
                style: ctx.data.style,
            },
            [ctx.props.date.from(ctx.parent.$root.$now)],
        );
    },
});
