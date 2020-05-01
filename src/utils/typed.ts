import moment from 'moment';
// eslint-disable-next-line
import type { ICompiledMode } from 'highlightjs';
import { getLanguage, highlight } from 'highlightjs';

import { visualizeWhitespace } from './visualize';

export class Right<T> {
    static readonly tag = 'right';

    constructor(public result: T) {
        Object.freeze(this);
    }
}
export class Left<T> {
    static readonly tag = 'left';

    constructor(public error: T) {
        Object.freeze(this);
    }
}
export type Either<T, TT> = Left<T> | Right<TT>;

export type ValueOf<T> = T[keyof T];

export function coerceToString(obj: Object | null | undefined) {
    if (obj == null) return '';
    else if (typeof obj === 'string') return obj;
    return `${obj}`;
}

const reUnescapedHtml = /[&<>"'`]/g;
const reHasUnescapedHtml = RegExp(reUnescapedHtml.source);
/** Used to map characters to HTML entities. */
const htmlEscapes: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
    '`': '&#96;',
};
export function htmlEscape(inputString: string) {
    const str = coerceToString(inputString);
    if (str && reHasUnescapedHtml.test(str)) {
        return str.replace(reUnescapedHtml, ent => htmlEscapes[ent]);
    }
    return str;
}


export type AllOrNone<T> = T | { [K in keyof T]?: never };

export function fromEntries<T>(vals: [string | number, T][]): Record<string, T> {
    return (Object as any).fromEntries(vals);
}

export function hasAttr<T>(obj: T, key: PropertyKey): key is keyof T {
    return Object.hasOwnProperty.call(obj, key);
}

export function filterObject<T>(
    obj: { [key: string]: T },
    f: (v: T, k: string) => boolean,
): Record<string, T> {
    return fromEntries(Object.entries(obj).filter(([key, val]) => f(val, key)));
}

export function forEachObject<T, V>(
    obj: { [key: string]: T },
    fun: (v: T, k: string) => V,
): void {
    Object.entries(obj).forEach(([key, val]) => [key, fun(val, key)]);
}

type KeyLike = string | number;

export function mapObject<T, V>(
    obj: Record<KeyLike, T>,
    fun: (v: T, k: string) => V,
): Record<string, V> {
    return fromEntries(Object.entries(obj).map(([key, val]) => [key, fun(val, key)]));
}

// Map over an array, allowing to provide a custom map function for the first
// or last element.
export function mapCustom<T, V>(
    arr: Array<T>,
    fun: (v: T, i: number) => V,
    first: (v: T, i: number) => V = fun,
    last: (v: T, i: number) => V = fun,
): Array<V> {
    const max = arr.length - 1;
    return arr.map((v, i) => {
        if (i === 0) {
            return first(v, i);
        } else if (i === max) {
            return last(v, i);
        } else {
            return fun(v, i);
        }
    });
}

export function flatMap1<T, TT>(
    arr: ReadonlyArray<T>,
    mapper: (val: T, index: number) => TT[],
): TT[] {
    return arr.reduce((acc: TT[], elem: T, index: number) => acc.concat(mapper(elem, index)), []);
}

export function zip<T, Y>(a: T[], b: Y[]): [T, Y][];
export function zip<T, Y>(...a: [T, Y][]): [T[], Y[]];
export function zip(...lists: any[][]): any {
    if (lists.length === 0) {
        return [];
    }

    const acc = [];
    const end = Math.min(...lists.map(l => l.length));
    let i = 0;
    const getter = (l: any[]) => l[i];

    for (; i < end; i++) {
        acc.push(lists.map(getter));
    }
    return acc;
}

export function unzip2<T, Y>(arr: readonly (readonly [T, Y])[]): [T[], Y[]] {
    const base: [T[], Y[]] = [[], []];

    return arr.reduce((acc, item: readonly [T, Y]) => {
        acc[0].push(item[0]);
        acc[1].push(item[1]);
        return acc;
    }, base);
}

export function flat1<T>(arr: readonly (readonly T[])[]): Readonly<T[]> {
    return arr.reduce((acc, elem) => acc.concat(elem), []);
}

export function unique<T, V>(arr: ReadonlyArray<T>, getKey: (item: T) => V): T[] {
    const seen = new Set();
    return arr.reduce((acc: T[], item: T) => {
        const key = getKey(item);
        if (!seen.has(key)) {
            seen.add(key);
            acc.push(item);
        }
        return acc;
    }, []);
}

export class AssertionError extends Error {
    static assert(condition: false, msg?: string): never;

    static assert(condition: boolean, msg?: string): asserts condition;

    static assert(condition: boolean, msg?: string): asserts condition {
        if (!condition) {
            throw new AssertionError(msg);
        }
    }
}

export function buildUrl(
    parts: ReadonlyArray<string | number> | string,
    args: {
        query?: Record<string, string>;
        hash?: string;
        addTrailingSlash?: boolean;
    } & AllOrNone<{
        host: string;
        protocol: string;
    }> = {},
): string {
    let mainPart;
    let initialSlash = '';
    if (typeof parts === 'string') {
        mainPart = parts;
    } else {
        initialSlash = '/';
        mainPart = parts.map(part => encodeURIComponent(part)).join('/');
    }
    if (args.addTrailingSlash) {
        mainPart = `${mainPart}/`;
    }

    let prefix = '';
    if (args.protocol != null) {
        initialSlash = '/';
        prefix = `${args.protocol.toString()}//${args.host.toString()}`;
    }

    let query = '';
    if (args.query) {
        const params = Object.entries(args.query)
            .reduce((acc, [key, value]) => {
                acc.append(key, value);
                return acc;
            }, new URLSearchParams())
            .toString();
        query = `?${params}`;
    }

    let hash = '';
    if (args.hash) {
        hash = `#${encodeURIComponent(args.hash)}`;
    }

    return `${prefix}${initialSlash}${mainPart}${query}${hash}`;
}

export function capitalize(str: string): string {
    if (str.length === 0) return str;
    return str[0].toUpperCase() + str.substr(1);
}

export const getUniqueId = (() => {
    let id = 0;
    return () => id++;
})();

export function waitAtLeast<T>(time: number, promise: Promise<T>): Promise<T>;

export function waitAtLeast<T, Y>(
    time: number,
    promise: Promise<T>,
    ...promises: Promise<Y>[]
): Promise<[T, ...Y[]]>;

export function waitAtLeast<T>(time: number, ...promises: Promise<T>[]): Promise<T | T[]> {
    const timeout: Promise<undefined> = new Promise(resolve => setTimeout(resolve, time));

    return Promise.all([timeout, Promise.all(promises)]).then(([_, vals]) => {
        if (promises.length === 1) {
            return vals[0];
        } else {
            return vals;
        }
    });
}

export function getProps<TObj extends object, TKey extends keyof TObj, TDefault>(
    object: TObj | null | undefined,
    defaultValue: TDefault,
    prop: TKey,
): Exclude<TObj[TKey], undefined | null> | TDefault;

export function getProps<TObj extends object, TKey extends keyof TObj, TDefault>(
    object: TObj,
    defaultValue: TDefault,
    prop: Omit<string, TKey>,
): TDefault;

export function getProps<
    TObj extends object,
    TKey1 extends keyof TObj,
    TKey2 extends keyof TObj[TKey1],
    TDefault
>(
    object: TObj,
    defaultValue: TDefault,
    prop1: TKey1,
    prop2: TKey2,
): Exclude<TObj[TKey1][TKey2], undefined> | TDefault;

export function getProps<
    TObj extends object,
    TKey1 extends keyof TObj,
    TKey2 extends keyof TObj[TKey1],
    TKey3 extends keyof TObj[TKey1][TKey2],
    TDefault
>(
    object: TObj,
    defaultValue: TDefault,
    prop1: TKey1,
    prop2: TKey2,
    prop3: TKey3,
): Exclude<TObj[TKey1][TKey2][TKey3], undefined> | TDefault;

export function getProps<
    TObj extends object,
    TKey1 extends keyof TObj,
    TKey2 extends keyof TObj[TKey1],
    TKey3 extends keyof TObj[TKey1][TKey2],
    TDefault
>(
    object: TObj,
    defaultValue: TDefault,
    prop1: Omit<string, TKey1>,
    ...otherProps: string[]
): TDefault;

export function getProps<T, Y, K extends string>(
    object: Record<K, T> | null | undefined,
    defaultValue: Y,
    ...props: K[]
): T | Y {
    let res: Record<string, Object> | undefined | null = object;
    for (let i = 0; res != null && i < props.length; ++i) {
        res = res[props[i]];
    }
    if (res == null) {
        return defaultValue;
    }
    return res as any;
}

export function ensureArray<T>(obj: T | ReadonlyArray<T>): T[] {
    return Array.isArray(obj) ? obj : [obj];
}

// https://stackoverflow.com/questions/13405129/javascript-create-and-save-file
export function downloadFile(data: string, filename: string, contentType: string) {
    const file = new Blob([data], { type: contentType });
    if (window.navigator.msSaveOrOpenBlob) {
        // IE10+
        window.navigator.msSaveOrOpenBlob(file, filename);
    } else {
        const url = URL.createObjectURL(file);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 0);
    }
}

export function highlightCode(
    sourceArr: ReadonlyArray<string>, language: string, maxLen: number = 5000,
) {
    if (sourceArr.length > maxLen) {
        return sourceArr.map(htmlEscape);
    }

    if (getLanguage(language) === undefined) {
        return sourceArr.map(htmlEscape).map(visualizeWhitespace);
    }

    let state: ICompiledMode | undefined;
    const lastLineIdx = sourceArr.length - 1;

    return sourceArr.map((line, idx) => {
        const { top, value } = highlight(language, line, true, state);

        state = top;
        // Make sure that if the last line is empty we emit this as an empty
        // line. We do this to make sure that our detection for trailing
        // newlines (or actually the absence of them) works correctly.
        if (idx === lastLineIdx && line === '') {
            return visualizeWhitespace(htmlEscape(line));
        }
        return visualizeWhitespace(value);
    });
}

export function deepEquals(a: any, b: any): boolean {
    if (typeof a !== 'object') {
        return a === b;
    } else if (a == null || b == null) {
        // eslint-disable-next-line eqeqeq
        return a == b;
    } else if (typeof b !== 'object') {
        return false;
    } else {
        const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
        return [...keys].every(key => deepEquals(a[key], b[key]));
    }
}

function toMoment(date: moment.Moment | string): moment.Moment {
    if (moment.isMoment(date)) {
        return date.clone();
    } else {
        return moment.utc(date, moment.ISO_8601);
    }
}

export function readableFormatDate(date: moment.Moment | string): string {
    return toMoment(date)
        .local()
        .format('YYYY-MM-DD HH:mm');
}

export function filterMap<T, TT>(
    arr: ReadonlyArray<T>, filterMapper: (arg: T) => Either<unknown, TT>,
): TT[] {
    return arr.reduce((acc: TT[], item) => {
        const toAdd = filterMapper(item);
        if (toAdd instanceof Right) {
            acc.push(toAdd.result);
        }
        return acc;
    }, []);
}

export function formatGrade(grade: string | number): string | null {
    let g;
    if (typeof grade !== 'number') {
        g = parseFloat(grade);
    } else {
        g = grade;
    }
    return Number.isNaN(g) ? null : g.toFixed(2);
}


// Get all items that are either in set A or in set B, but not in both.
export function setXor<T>(A: Set<T>, B: Set<T>): Set<T> {
    return new Set([...A, ...B].filter(el => {
        const hasA = A.has(el);
        if (hasA) {
            return !B.has(el);
        } else {
            return B.has(el);
        }
    }));
}

export function toMaxNDecimals<T extends number | number | undefined>(
    num: T, n: number
): T extends number ? string : null;
export function toMaxNDecimals(num: number | null | undefined, n: number): string | null {
    if (num == null) {
        return null;
    }

    let str = num.toFixed(n);
    if (n === 0) {
        return str;
    }
    while (str[str.length - 1] === '0') {
        str = str.slice(0, -1);
    }
    if (str[str.length - 1] === '.') {
        str = str.slice(0, -1);
    }
    return str;
}

export function parseOrKeepFloat(num: string | number | null | undefined): number {
    if (typeof num === 'number') {
        return num;
    } else if (num == null) {
        return NaN;
    }
    return parseFloat(num);
}

export function formatDate(date: string | moment.Moment): string {
    return toMoment(date)
        .local()
        .format('YYYY-MM-DDTHH:mm');
}

export function mapToObject<T extends Object, KK extends keyof T = keyof T>(
    arr: ReadonlyArray<KK>,
    // eslint-disable-next-line no-undef
    mapper: (el: KK, index: number) => [KK, T[typeof el]],
    initial: T = <T>{},
): T {
    return arr.reduce((acc, el, index) => {
        const [key, value] = mapper(el, index);
        acc[key] = value;
        return acc;
    }, initial);
}

export function mapFilterObject<T, V>(
    obj: Record<KeyLike, T>,
    fun: (v: T, k: string) => Either<unknown, V>,
): Record<string, V> {
    return fromEntries(filterMap(
        Object.entries(obj),
        ([key, val]) => {
            const either = fun(val, key);
            if (either instanceof Right) {
                return new Right([key, either.result]);
            }
            return either;
        },
    ));
}
