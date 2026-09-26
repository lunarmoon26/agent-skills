---
title: "Preview Mode for Static Generation"
excerpt: "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Praesent elementum facilisis leo vel fringilla est ullamcorper eget. At imperdiet dui accumsan sit amet nulla facilities morbi tempus."
coverImage: "https://assets.haochuanz.net/blog/preview/cover.jpg"
date: "2020-03-16T05:35:07.322Z"
ogImage:
  url: "https://assets.haochuanz.net/blog/preview/cover.jpg"
tags:
  - software-engineering
---

# Markdown Examples

## h2 Heading

### h3 Heading

#### h4 Heading

##### h5 Heading

###### h6 Heading

## Emphasis

**This is bold text**

_This is italic text_

~~Strikethrough~~

==Highlight==

## Blockquotes

> Develop. Preview. Ship. – Vercel

## Lists

Unordered

- Lorem ipsum dolor sit amet
- Consectetur adipiscing elit
- Integer molestie lorem at massa

Ordered

1. Lorem ipsum dolor sit amet
2. Consectetur adipiscing elit
3. Integer molestie lorem at massa

## Code

Inline `code`

```js
export default function Nextra({ Component, pageProps }) {
  return (
    <>
      <Head>
        <link
          rel="alternate"
          type="application/rss+xml"
          title="RSS"
          href="/feed.xml"
        />
        <link
          rel="preload"
          href="/fonts/Inter-roman.latin.var.woff2"
          as="font"
          type="font/woff2"
          crossOrigin="anonymous"
        />
      </Head>
      <Component {...pageProps} />
    </>
  )
}
```

```mermaid
graph TD
    accTitle: Agent delivery quality-control pipeline
    accDescr: Demonstrates a human-directed agent fleet passing frontend, backend, and infrastructure work through automated checks before production approval.
    %% viewer:version 1
    %% viewer:detail Purpose | Mermaid viewer protocol fixture
    %% viewer:detail Reading direction | Top to bottom
    %% viewer:legend #A99D00 | Human direction and approval
    %% viewer:legend #9D73A8 | Agent execution
    %% viewer:legend #008F99 | Automated quality control
    %% viewer:legend #269E10 | Accepted integration
    subgraph Initiation Layer
        HA1[Human Architect] -->|Architectural Intent & Specs| OA[Orchestrator Agent]
    end
    
    subgraph Execution Fleet
        OA -->|Decompose & Route| FA[Frontend Agent]
        OA -->|Decompose & Route| BA[Backend Agent]
        OA -->|Decompose & Route| IA[Infra Agent]
    end
    
    subgraph Agentic Quality Control AQC
        FA --> AQC_Gate{AQC Gateway}
        BA --> AQC_Gate
        IA --> AQC_Gate
        AQC_Gate -->|Automated Audit| SA[Static Analysis & Vuln Scanner]
        AQC_Gate -->|Pattern Match| AD[Architectural Drift Validator]
        AQC_Gate -->|Memory Management| CC[Context Compaction Engine]
    end
    
    subgraph Resolution Layer
        SA --> IN[Integration Node]
        AD --> IN
        IN -->|Conflict-Free PR Generation| HA2[Human Architect]
        HA2 -->|Strategic Approval| PM((Production Merge))
    end

    classDef focus fill:#fffbd6,stroke:#a99d00,color:#2d2a00,stroke-width:2px
    classDef agent fill:#fbf0ff,stroke:#9d73a8,color:#302035,stroke-width:2px
    classDef check fill:#e7fcff,stroke:#008f99,color:#08272b,stroke-width:2px
    classDef ready fill:#eaffdf,stroke:#269e10,color:#14320c,stroke-width:2px
    class HA1,HA2 focus
    class OA,FA,BA,IA agent
    class AQC_Gate,SA,AD,CC check
    class IN,PM ready
```

## Tables

| **Option** | **Description**                                                                                                             |
| ---------- | --------------------------------------------------------------------------------------------------------------------------- |
| First      | Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. |
| Second     | Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. |
| Third      | Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. |

## Links

- [Next.js](https://nextjs.org)
- [Nextra](https://nextra.vercel.app/)
- [Vercel](http://vercel.com)

### Footnotes

- Footnote [^1].
- Footnote [^2].

[^1]: Footnote **can have markup**

and multiple paragraphs.

[^2]: Footnote text.
