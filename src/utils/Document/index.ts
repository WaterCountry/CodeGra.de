import { hasAttr, unzip2, flat1, unique } from '@/utils/typed';

type TextBlock = string;

abstract class WrapperContent {
    constructor(public readonly content: ContentBlock) {}

    abstract wrapperTag: string;
}

export class EmphasizedContent extends WrapperContent {
    wrapperTag = 'emph';
}

export class BoldContent extends WrapperContent {
    wrapperTag = 'textbf';
}

export class MonospaceContent extends WrapperContent {
    wrapperTag = 'texttt';
}

type ContentChunk = TextBlock | EmphasizedContent | BoldContent | MonospaceContent;

export class ContentBlock {
    constructor(public readonly chunks: ReadonlyArray<ContentChunk>) {}
}

export interface CodeBlock {
    // Line number of the first line in the block.
    firstLine: number;

    // The lines of text to render.
    lines: string[];

    // Specification for lines to be highlighted.
    highlights: HighlightRange[];

    // Optional caption.
    caption?: ContentBlock;
}

interface HighlightRange {
    start: number;
    end: number;
    highlight: Highlight;
}

type HighlightID = string;

export class Highlight {
    static getHighlightId: () => HighlightID = (() => {
        let curId = 0;
        return () => `${curId++}`;
    })();

    public id: HighlightID;

    constructor(public background: Color, public foreground: Color) {
        this.id = Highlight.getHighlightId();
    }
}

export interface Color {
    red: number;
    green: number;
    blue: number;
}

export class ColumnLayout<T> {
    constructor(public readonly blocks: ReadonlyArray<T>) {}
}

export class SubSection {
    constructor(
        public readonly heading: string,
        public readonly children: ReadonlyArray<DocumentContentNode>,
    ) {}
}

export class Section {
    constructor(
        public readonly heading: string,
        public readonly children: ReadonlyArray<DocumentContentNode | SubSection>,
    ) {}
}

export class NewPage {}

type DocumentContentNode = CodeBlock | ContentBlock | NewPage;

export type DocumentNode =
    | DocumentContentNode
    | Section
    | ColumnLayout<DocumentContentNode | Section>;

export class DocumentRoot {
    private constructor(public readonly children: ReadonlyArray<DocumentNode>) {}

    public addChildren(children: DocumentNode[]) {
        return new DocumentRoot([...this.children, ...children]);
    }

    static makeEmpty() {
        return new DocumentRoot([]);
    }
}

abstract class DocumentBackend {
    static backendName: string;

    constructor(public doc: DocumentRoot) {}

    abstract renderToBuffer(): Buffer;
}

class LatexDocument extends DocumentBackend {
    static backendName: 'LaTeX' = 'LaTeX';

    private static readonly endListingRegex = new RegExp('\\\\end{lstlisting}', 'g');

    private static readonly reUnescapedLatex = /[{}\\#$%&^_~]/g;

    private static readonly reHasUnescapedLatex = RegExp(LatexDocument.reUnescapedLatex.source);

    private static readonly latexEscapes: Record<string, string> = Object.freeze({
        '{': '\\{',
        '}': '\\}',
        '\\': '\\textbackslash{}',
        '#': '\\#',
        $: '\\$',
        '%': '\\%',
        '&': '\\&',
        '^': '\\textasciicircum{}',
        _: '\\_',
        '~': '\\textasciitilde{}',
    });

    private static escape(input: string): string {
        if (input && LatexDocument.reHasUnescapedLatex.test(input)) {
            const map = LatexDocument.latexEscapes;
            return input.replace(LatexDocument.reUnescapedLatex, ent => map[ent]);
        }
        return input;
    }

    constructor(public doc: DocumentRoot) {
        super(doc);
    }

    renderLines(el: DocumentNode): [string[], Highlight[]] {
        if (el instanceof Section) {
            return this.renderSection(el);
        } else if (el instanceof ColumnLayout) {
            return this.renderColumn(el);
        } else if (el instanceof ContentBlock) {
            return this.renderContentBlock(el);
        } else if (el instanceof NewPage) {
            return [['\\clearpage{}'], []];
        } else {
            return this.renderCode(el);
        }
    }

    renderToBuffer(): Buffer {
        const [lines, highlights] = unzip2(this.doc.children.map(child => this.renderLines(child)));

        const base = `\\documentclass{article}
\\usepackage{listings}
\\usepackage{xcolor}
\\usepackage[T1]{fontenc}
\\usepackage[utf8]{inputenc}
\\usepackage{textcomp}
\\usepackage{paracol}
\\usepackage[margin=0.5in]{geometry}

% XXX: This may break when the package "lstlinebgrd" is updated. If compilation
% of this document fails with the error "Error: Numbers none unknown", try to
% delete everything from "START fix" to "END fix", and uncomment the line below
% this one.
%\\usepackage{lstlinebgrd}
% START Fix for incompatibility between newer versions of listings and
% lstlinebgrd
\\makeatletter
\\let\\old@lstKV@SwitchCases\\lstKV@SwitchCases
\\def\\lstKV@SwitchCases#1#2#3{}
\\makeatother
\\usepackage{lstlinebgrd}
\\makeatletter
\\let\\lstKV@SwitchCases\\old@lstKV@SwitchCases

\\lst@Key{numbers}{none}{%
    \\def\\lst@PlaceNumber{\\lst@linebgrd}%
    \\lstKV@SwitchCases{#1}%
    {none:\\\\%
     left:\\def\\lst@PlaceNumber{\\llap{\\normalfont
                \\lst@numberstyle{\\thelstnumber}\\kern\\lst@numbersep}\\lst@linebgrd}\\\\%
     right:\\def\\lst@PlaceNumber{\\rlap{\\normalfont
                \\kern\\linewidth \\kern\\lst@numbersep
                \\lst@numberstyle{\\thelstnumber}}\\lst@linebgrd}%
    }{\\PackageError{Listings}{Numbers #1 unknown}\\@ehc}}
\\makeatother
% END fix

\\definecolor{bluekeywords}{rgb}{0.13, 0.13, 1}
\\definecolor{greencomments}{rgb}{0, 0.5, 0}
\\definecolor{redstrings}{rgb}{0.9, 0, 0}
\\definecolor{graynumbers}{rgb}{0.5, 0.5, 0.5}

${this.defineColors(flat1(highlights)).join('\n')}

\\lstset{
    numbers=left,
    columns=fullflexible,
    showspaces=false,
    showtabs=false,
    breaklines=true,
    showstringspaces=false,
    breakatwhitespace=false,
    commentstyle=\\color{greencomments},
    keywordstyle=\\color{bluekeywords},
    stringstyle=\\color{redstrings},
    numberstyle=\\color{graynumbers},
    basicstyle=\\ttfamily\\footnotesize,
    xleftmargin=12pt,
    rulesepcolor=\\color{graynumbers},
    tabsize=4,
    captionpos=b,
    frame=L,
    upquote=true
}

\\begin{document}
${flat1(lines).join('\n')}
\\end{document}`;

        return Buffer.from(base, 'utf8');
    }

    // eslint-disable-next-line class-methods-use-this
    private defineColors(highlights: Highlight[]): string[] {
        return unique(highlights, h => h.id).reduce(
            (acc: string[], highlight) => {
                const id = highlight.id;
                const bg = highlight.background;
                const fg = highlight.foreground;
                acc.push(
                    `\\definecolor{bg-color-${id}}{RGB}{${bg.red}, ${bg.green}, ${bg.blue}}`,
                    `\\definecolor{fg-color-${id}}{RGB}{${fg.red}, ${fg.green}, ${fg.blue}}`,
                );
                return acc;
            },
            ['% Unfortunately the foreground colors are not used.'],
        );
    }

    renderContentBlock(contentBlock: ContentBlock): [[string], Highlight[]] {
        const [content, highlights] = contentBlock.chunks.reduce(
            (acc: [string[], Highlight[]], chunk) => {
                if (chunk instanceof WrapperContent) {
                    const toWrap = this.renderContentBlock(chunk.content);
                    acc[0].push(`\\${chunk.wrapperTag}{`);
                    acc[0].push(toWrap[0][0]);
                    acc[0].push('}');
                    return [acc[0], acc[1].concat(toWrap[1])];
                } else {
                    acc[0].push(LatexDocument.escape(chunk));
                    return acc;
                }
            },
            [[], []],
        );

        return [[content.join('')], highlights];
    }

    renderSection(section: Section): [string[], Highlight[]] {
        return section.children.reduce(
            (accum: [string[], Highlight[]], child): [string[], Highlight[]] => {
                const res = this.renderLines(child);
                return [accum[0].concat(res[0]), accum[1].concat(res[1])];
            },
            [[`\\section{${LatexDocument.escape(section.heading)}}`], []],
        );
    }

    private renderCode(code: CodeBlock): [string[], Highlight[]] {
        // TODO: don't render caption when none given.
        let caption: string = '';
        let highlights: Highlight[] = [];
        if (code.caption) {
            [[caption], highlights] = this.renderContentBlock(code.caption);
        }

        return [
            [
                '\\begin{lstlisting}[',
                `    firstnumber=${code.firstLine},`,
                `    linebackgroundcolor=${this.makeHighlights(code.highlights)},`,
                `    caption = {${caption}}]`,
                ...code.lines.map(line =>
                    line.replace(LatexDocument.endListingRegex, '\\end {lstlisting}'),
                ),
                '\\end{lstlisting}',
            ],
            highlights.concat(code.highlights.map(range => range.highlight)),
        ];
    }

    private makeHighlights(ranges: HighlightRange[]): string {
        const sorted = ranges.sort((a, b) => a.end - b.end);
        return this.makeHighlightsSorted(sorted);
    }

    private makeHighlightsSorted(ranges: HighlightRange[]): string {
        // Ranges must be sorted and not overlap. Because there is no "and"
        // operator in TeX that is the only way we can guarantee that the
        // nested if-else below will work correctly.
        // TODO: Find a way to change the foreground color of specific lines.
        // Maybe simply wrapping each line in a {\color{fg-color-${id}} ...}
        // will work.

        const [cur, ...rest] = ranges;

        if (rest.length === 0) {
            return `
\\ifnum\\value{lstnumber}<${cur.end + 1}%
    \\ifnum\\value{lstnumber}>${cur.start - 1}%
        \\color{bg-color-${cur.highlight.id}}%
    \\fi%
\\fi
            `.trim();
        } else {
            return `
\\ifnum\\value{lstnumber}<${cur.end + 1}%
    \\ifnum\\value{lstnumber}>${cur.start - 1}%
        \\color{bg-color-${cur.highlight.id}}%
    \\fi%
\\else%
    ${this.makeHighlightsSorted(rest)}%
\\fi
            `.trim();
        }
    }

    renderColumn(column: ColumnLayout<DocumentContentNode | Section>): [string[], Highlight[]] {
        const columns = column.blocks.length;
        return column.blocks.reduce(
            (acc: [string[], Highlight[]], block, index) => {
                const res = this.renderLines(block);
                acc[0] = acc[0].concat(res[0]);
                if (index !== column.blocks.length - 1) {
                    acc[0].push('\\switchcolumn');
                } else {
                    acc[0].push('\\end{paracol}');
                }
                acc[1] = acc[1].concat(res[1]);
                return acc;
            },
            [[`\\begin{paracol}{${columns}}`], []],
        );
    }
}

export const backends = {
    [LatexDocument.backendName]: LatexDocument,
} as const;

export function render(
    backendName: keyof typeof backends,
    document: DocumentRoot,
): Promise<Buffer> {
    if (!hasAttr(backends, backendName)) {
        throw new Error(`Invalid backend: ${backendName} `);
    }
    return Promise.resolve(new backends[backendName](document).renderToBuffer());
}