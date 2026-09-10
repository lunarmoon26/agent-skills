---
name: tech-breakdown-in-chinese
description: Use when writing a Chinese-language article or note that explains a new architecture, framework, runtime, library, protocol, or system design by deriving it from zero instead of listing APIs. Triggers include requests to explain a system step by step in Chinese, write a "from scratch" breakdown, distill how a technology works for a general CS audience, or adapt an existing technical explanation into this derivation style. Do not use for API reference writing, release notes, translation of existing docs, or content aimed at literal children.
---

# Tech Breakdown in Chinese

Write technical breakdowns that let a reader *watch an architecture grow out of
necessity*, one requirement at a time. The method derives abstractions from
pain points rather than presenting them as definitions to memorize.

## Audience calibration

The target reader is **not a child**. Assume:

- General CS background (undergraduate-level), but no prior exposure to the
  specific technology being explained.
- Native-level Chinese sensitivity: prose reads naturally in Chinese.
- Professional fluency in English: keep established terms in English.

"Explaining to a primary schooler" is the *tone* goal — concrete examples,
short sentences, no assumed vocabulary — not the audience level.

## Core workflow

### 1. Pick a seed example

Choose one tiny, concrete program that needs **no framework at all** and can be
implemented with plain code in ~10-20 lines. It should be everyday-domain
(greeter, todo list, cache) so nothing distracts from the mechanism. This same
example runs through the entire piece; do not switch examples midway.

### 2. Build the requirement ladder

Grow requirements one at a time, each small enough that the previous solution
still mostly works. Write down the ladder explicitly, e.g.:

```text
一个变量
   ↓
多个实现
   ↓
资源清理
   ↓
动态依赖
   ↓
生命周期管理
```

Each rung must correspond to exactly one abstraction you will eventually
introduce. If a concept has no rung, either add a rung or cut the concept.

### 3. Gate every abstraction behind a pain point

For each rung: first show the vanilla implementation straining, then introduce
the framework/abstraction as the answer. Pain points are things like ghost
listeners never cleaned up, forgotten refresh calls causing silent state
drift, glue code copying itself as modules multiply. The reader should feel
*"I would have hit this bug too"* before meeting the fix.

Never present an abstraction before its pain point exists. Never introduce two
abstractions against one pain point.

### 4. Pair vanilla and target implementations

Show the same logic twice: plain code vs. the framework version. Keep both
minimal and parallel so the diff is legible. Then name the exact line where
they diverge and say what it means, e.g. `greeter.greet(...)` becoming
`ctx.greeter.greet(...)` means the dependency moved from "some object" to "a
capability registered in the runtime".

Attribute complexity honestly: if the framework version is longer at this
stage, say so.

### 5. Account costs honestly

State plainly when the simple solution is still better. Locate the value of
the new architecture in **marginal cost under scaling** (adding the Nth module,
the Nth dependency edge), not in lines of code on the hello-world. A breakdown
that oversells early wins loses trust.

### 6. Recap into one mental map

End with a chapter that introduces no new requirements. Recycle each concept
back to its original pain point, compress the whole chain into a single bolded
one-line judgment (see style rules), then map the toy example onto a real
production scenario (e.g. Greeter/Clock/Farewell → Model/CodingAgent/Tools) so
the abstractions land in reality.

## Chinese style rules

- **Language split**: prose in natural Chinese; keep established technical
  terms in English (Context, Plugin, dispose, listener, inject). Translate
  only terms where a stable Chinese equivalent exists and is widely used.
- **Question-form headings**: prefer 设问句 like 「为什么这里一定要 dispose？」
  and 「inject 真正在管理什么」over noun-phrase headings.
- **Arrow-chain summary**: open each section with a compressed path of the
  argument (text arrows like the ladder above). Optionally add a Mermaid
  diagram; if you do, include native `accTitle`/`accDescr`.
- **One decisive line**: when showing code, isolate the single line that
  carries the meaning (`super(ctx, 'greeter')`) and explain just that line;
  omit boilerplate.
- **Bold blockquote thesis**: state the core judgment once per piece as a
  bolded quote contrasting what it does *not* solve with what it does:
  「Cordis 不是在解决"怎么调用一个 Service"，而是在解决……」
- Sentence rhythm: short declarative sentences; one idea per paragraph; use
  「这一篇要解决的问题」framing to open sections.
- Each section ends with a bridge sentence naming the next requirement, so
  the chain stays connected even if sections are read independently.

## Source verification gate (mandatory)

Before publishing or delivering the piece:

1. List every checkable technical claim (error messages, semantics of an API,
   lifecycle behavior, ordering guarantees).
2. Verify each claim against the actual source code of the specific version
   being explained — read the repository, not blog posts about it. Error
   message wording must match verbatim.
3. If a claim cannot be verified (source unavailable, behavior undocumented),
   mark it explicitly in the text as unverified or soften the assertion.
4. Do not silently correct or editorialize third-party articles being adapted;
   verify claims independently and write only what the source supports.

## Quality checklist

Before delivery, confirm:

- [ ] Seed example needs no framework and appears throughout
- [ ] Every abstraction has exactly one preceding pain point
- [ ] Vanilla and framework implementations are paired per stage
- [ ] Honest statement of when the simple solution still wins
- [ ] Final chapter recaps concepts and maps them to a real scenario
- [ ] Terms kept in English where appropriate; prose fully natural Chinese
- [ ] All technical claims verified against source, or marked unverified
