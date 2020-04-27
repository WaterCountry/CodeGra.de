import * as docx from 'docx';

import { hasAttr, unzip2, flatMap1, flat1, unique } from '@/utils/typed';

type TextBlock = string;

abstract class WrapperContent {
    constructor(public readonly content: ContentBlock) {}
}

export class EmphasizedContent extends WrapperContent {}

export class BoldContent extends WrapperContent {}

export class MonospaceContent extends WrapperContent {}

// Force the content of this block to be rendered on a single line if possible
// and the document format supports it.
export class NonBreakingContent {
    constructor(public readonly content: ReadonlyArray<string>) {}
}

type ContentChunk =
    | TextBlock
    | EmphasizedContent
    | BoldContent
    | MonospaceContent
    | NonBreakingContent;

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

    abstract renderToBuffer(): Promise<Buffer>;
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
        } else if (el instanceof SubSection) {
            return this.renderSubsection(el);
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

    renderToBuffer(): Promise<Buffer> {
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

        return Promise.resolve(Buffer.from(base, 'utf8'));
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
                if (chunk instanceof NonBreakingContent) {
                    const b = chunk.content.join('~');
                    acc[0].push(LatexDocument.escape(b).replace(/[ \t]+/g, '~'));
                    return acc;
                } else if (chunk instanceof WrapperContent) {
                    const toWrap = this.renderContentBlock(chunk.content);
                    acc[0].push(`\\${LatexDocument.wrapperTag(chunk)}{`);
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

    private static wrapperTag(chunk: WrapperContent): string {
        if (chunk instanceof EmphasizedContent) {
            return 'emph';
        } else if (chunk instanceof BoldContent) {
            return 'textbf';
        } else if (chunk instanceof MonospaceContent) {
            return 'texttt';
        } else {
            throw new Error('Unsupported wrapper.');
        }
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

    renderSubsection(subsection: SubSection): [string[], Highlight[]] {
        return subsection.children.reduce(
            (accum: [string[], Highlight[]], child): [string[], Highlight[]] => {
                const res = this.renderLines(child);
                return [accum[0].concat(res[0]), accum[1].concat(res[1])];
            },
            [[`\\subsection{${LatexDocument.escape(subsection.heading)}}`], []],
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

class DocxDocument extends DocumentBackend {
    static backendName = 'DOCX';

    private codeBlockIndex: number = 0;

    constructor(public doc: DocumentRoot) {
        super(doc);
    }

    renderToBuffer(): Promise<Buffer> {
        const doc = new docx.Document({
            numbering: {
                config: [...this.codeBlockNumberings()],
            },
        });

        this.doc.children.forEach(child => {
            if (child instanceof Section) {
                this.renderSection(child, doc);
            } else {
                doc.addSection({
                    children: this.renderElement(child),
                });
            }
        });

        return docx.Packer.toBuffer(doc);
    }

    private codeBlockNumberings(): {
        readonly levels: docx.ILevelsOptions[];
        readonly reference: string;
    }[] {
        return this.getCodeBlocks().map((block, i) => ({
            levels: [
                {
                    level: 0,
                    format: 'decimal',
                    start: block.firstLine,
                    text: '%1',
                    alignment: docx.AlignmentType.START,
                    style: {
                        paragraph: {
                            indent: { left: 720, hanging: 260 },
                        },
                    },
                },
            ],
            reference: `decimal-ordered-${i}`,
        }));
    }

    private getCodeBlocks(): CodeBlock[] {
        function getBlocks(els: ReadonlyArray<DocumentNode | SubSection>): CodeBlock[] {
            return els.reduce((acc: CodeBlock[], el: DocumentNode | SubSection): CodeBlock[] => {
                if (el instanceof Section) {
                    return acc.concat(getBlocks(el.children));
                } else if (el instanceof SubSection) {
                    return acc.concat(getBlocks(el.children));
                } else if (el instanceof ColumnLayout) {
                    return acc.concat(getBlocks(el.blocks));
                } else if (el instanceof ContentBlock || el instanceof NewPage) {
                    return acc;
                } else {
                    return acc.concat(el);
                }
            }, []);
        }

        return getBlocks(this.doc.children);
    }

    renderSection(el: Section, doc: docx.Document): void {
        doc.addSection({
            headers: {
                default: new docx.Header({
                    children: [new docx.Paragraph(el.heading)],
                }),
            },
            children: flatMap1(el.children, child => this.renderElement(child)),
        });
    }

    renderElement(el: DocumentNode): docx.Paragraph[] {
        if (el instanceof Section) {
            throw new Error('Sections should be handled at the top level');
        } else if (el instanceof SubSection) {
            return this.renderSubSection(el);
        } else if (el instanceof ColumnLayout) {
            return this.renderColumn(el);
        } else if (el instanceof ContentBlock) {
            return [new docx.Paragraph({ children: this.renderContentBlock(el) })];
        } else if (el instanceof NewPage) {
            return this.renderNewPage();
        } else {
            return this.renderCode(el);
        }
    }

    renderSubSection(el: SubSection): docx.Paragraph[] {
        return [
            new docx.Paragraph({
                text: el.heading,
                heading: docx.HeadingLevel.HEADING_3,
            }),
            ...flatMap1(el.children, child => this.renderElement(child)),
        ];
    }

    renderColumn(el: ColumnLayout<DocumentContentNode | Section>): docx.Paragraph[] {
        // TODO: Actually render columns...
        return flatMap1(el.blocks, block => this.renderElement(block));
    }

    renderContentBlock(el: ContentBlock, opts: docx.IRunOptions = {}): docx.TextRun[] {
        return flatMap1(el.chunks, chunk => this.renderContentChunk(chunk, opts));
    }

    renderContentChunk(el: ContentChunk, opts: docx.IRunOptions): docx.TextRun[] {
        const childOpts = (key: string, value: any) => Object.assign({}, opts, { [key]: value });

        if (el instanceof EmphasizedContent) {
            return this.renderContentBlock(el.content, childOpts('italics', true));
        } else if (el instanceof BoldContent) {
            return this.renderContentBlock(el.content, childOpts('bold', true));
        } else if (el instanceof MonospaceContent) {
            return this.renderContentBlock(el.content, childOpts('font', { name: 'Courier new' }));
        } else if (el instanceof NonBreakingContent) {
            // TODO: Try to make this non-breaking.
            return el.content.map(str => new docx.TextRun(childOpts('text', str)));
        } else {
            return [new docx.TextRun(childOpts('text', el))];
        }
    }

    // eslint-disable-next-line class-methods-use-this
    renderNewPage(): docx.Paragraph[] {
        return [new docx.Paragraph({ pageBreakBefore: true })];
    }

    // eslint-disable-next-line class-methods-use-this
    renderCode(el: CodeBlock): docx.Paragraph[] {
        const shadings: { [lnum: number]: string } = {};
        const colors: { [lnum: number]: string } = {};
        el.highlights.forEach(hl => {
            for (let i = hl.start; i <= hl.end; i++) {
                shadings[i] = DocxDocument.colorToString(hl.highlight.background);
                colors[i] = DocxDocument.colorToString(hl.highlight.foreground);
            }
        });

        const start = el.firstLine;
        const blockIdx = this.codeBlockIndex++;

        const pars = el.lines.map((line, offset) => {
            const lnum = start + offset;
            return new docx.Paragraph({
                numbering: {
                    reference: `decimal-ordered-${blockIdx}`,
                    level: 0,
                },
                children: [
                    new docx.TextRun({
                        text: line,
                        font: { name: 'Courier New' },
                        color: colors[lnum],
                        shading: {
                            type: docx.ShadingType.SOLID,
                            fill: 'fill',
                            color: shadings[lnum],
                        },
                    }),
                ],
            });
        });

        if (el.caption != null) {
            pars.push(
                new docx.Paragraph({
                    alignment: docx.AlignmentType.CENTER,
                    children: this.renderContentBlock(el.caption),
                }),
            );
        }

        return pars;
    }

    static colorToString(color: Color): string {
        const toHex = (x: number) => {
            const s = x.toString(16);
            return s.length === 1 ? `0${s}` : s;
        };
        return `${toHex(color.red)}${toHex(color.green)}${toHex(color.blue)}`;
    }
}

export const backends = {
    [LatexDocument.backendName]: LatexDocument,
    [DocxDocument.backendName]: DocxDocument,
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
