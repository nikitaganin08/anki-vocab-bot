# Global competitive landscape: AI/LLM card generation + spaced repetition for vocabulary (as of October 2026)

Scope note: research done 2026-10-07. Global/English-language market only; RU-specific apps are mentioned briefly. Many traction numbers come from third-party estimators or SEO comparison blogs (marked "secondary"). Several primary pages (Business of Apps, Forbes, Google Play, AppBrain) returned HTTP 403 during this research, so their figures are quoted from search-result snippets and marked as such.

## 1. Which apps already do "capture a word -> AI generates a rich card -> spaced repetition review"?

### Takeaway
The loop is now crowded and commoditised. Dozens of 2023-2026 entrants already do it: standalone apps, Telegram bots and Mini Apps, browser extensions, Anki add-ons, and open-source CLI/Android tools. Almost all are small, indie, and lightly funded. The big money in AI language learning went to conversation tutors (Speak, Praktika) and gamified general study apps (Gizmo, Quizlet), not to personal-vocabulary capture tools.

### Cited Findings

**LLM-era vocabulary apps closest to the product (capture word/phrase -> AI card -> SRS)**
- **Zunoku** is a Telegram Mini App with no install or signup. It supports English and Russian. AI turns pasted text (articles, chapters, transcripts) into flashcards with translations, IPA, examples and notes. Study modes are flip cards, typed answers and multiple choice, plus streaks and reminders. It is freemium with a one-time lifetime purchase. The developer team is Czech, and it was added to AlternativeTo on 2026-07-14 — [AlternativeTo](https://alternativeto.net/software/zunoku/about/). This is the closest direct analogue found (Telegram + EN/RU + IPA + examples + SRS), but it is text-to-deck rather than single-lexical-unit capture.
- **VocaSave** is a Chrome extension. It does AI-powered word lookup, saves the word, and runs reviews through a "proactive Telegram Bot assistant" — [Chrome Web Store](https://chromewebstore.google.com/detail/dnpnkkkdfpfdpbdobphnkhakhdjoemcf).
- **VocabellaBot** is a Telegram bot. You bring words you met in real life, and it quizzes you back with spaced repetition — [hunted.space](https://hunted.space/product/vocabellabot).
- **LingoCop** is a Telegram bot that works as translator plus vocabulary trainer. It sends flashcard reminders on fixed days 1, 3, 7, 14 and 30 (fixed intervals, not FSRS) — [LingoCop Notion](https://lingocop.notion.site/Learn-foreign-words-on-autopilot-with-bite-sized-practice-94bb794d70c6492f8e94807d8f6ff3e8).
- **Behappy Speak** is an AI tutor in Telegram for English and German. It offers dialogues, error analysis and spaced-repetition quizzes — [hunted.space](https://hunted.space/product/behappy-speak).
- **VibeLing** (iOS/Android) lets you add words and phrases from movies, books, podcasts and conversations. The AI builds translation, examples and audio, and you train them with adaptive spaced repetition. Languages: EN, ES, DE, FR, RO, SR, **RU** — [VibeLing blog](https://vibeling.app/en/blog/best-ai-vocabulary-apps-2026). This is a self-published listicle, so treat it as marketing.
- **Vocabuo** (web, iOS, Android) launched on Product Hunt in July 2024 and got 360 upvotes (#2 of the day). It extracts vocabulary from YouTube, web pages or text and auto-generates cards with DALL-E 3 images, cloze examples and audio. SRS intervals are customisable, there is deliberately "no gamification", and it supports ES/DE/EN — [Product Hunt](https://www.producthunt.com/products/vocabuo-the-vocabulary-app?launch=vocabuo-the-vocabulary-app). An HN commenter cited a ~$30/year option — [HN Flowery thread](https://news.ycombinator.com/item?id=40717052).
- **Vocabulex** launched on Product Hunt in 2026 as "AI Vocabulary Flashcards that Adapt to Your Memory", with adaptive SRS and AI explanations and examples — [Product Hunt](https://www.producthunt.com/products/vocabulex); [vocabulex.app](https://vocabulex.app/).
- **Flowery** (Show HN, 2024-06-19) is a web dictionary/thesaurus plus LLM-generated cloze cards plus SRS. It cost $15.64/month with no free trial. HN feedback criticised the confusing onboarding, the paywall with no trial, and the unclear role of the LLM — [HN](https://news.ycombinator.com/item?id=40717052).
- **Other small "AI vocab + SRS" apps seen in 2026 search results:**
  - VocabAI (Android, gamified) — [Google Play](https://play.google.com/store/apps/details?id=com.dv.vocabai&hl=en)
  - Wordwise: Personal Dictionary (iOS; translate, save with context, SRS) — [App Store](https://apps.apple.com/us/app/wordwise-personal-dictionary/id6753231075)
  - My Words (Android; tap a word to save it, SRS) — [Google Play](https://play.google.com/store/apps/details?id=ru.babkin.mywords&hl=en)
  - My Personal Dictionary (Chrome; AI translate on select, save, SRS) — [Chrome Web Store](https://chromewebstore.google.com/detail/my-personal-dictionary-le/emhbabjelpapfkflfcdfodndpclhcloe)
  - Flashi (free iPhone app that turns word lists into AI decks) — [flashi.app](https://www.flashi.app/blog/2026-04-27-anki-flashcards-for-language-learning-the-better-app)
  - Card AI (Android) — [Google Play](https://play.google.com/store/apps/details?id=com.vocabulary.flashcards&amp%3Bhl=en)
  - "A1-C1: Learn words in context" (iOS) — [App Store](https://apps.apple.com/app/id6740411916)

**General-purpose AI flashcard makers (topic/PDF -> deck, not word capture)**
- **AlgoApp**: cross-platform, AI card generation, **FSRS**, image occlusion, cloud sync — [algoapp.ai](https://www.algoapp.ai/)
- Dekki, FlashRecall, Studr and Retain Cards are AI flashcard makers with SRS — [Dekki](https://www.dekki.ai/); [FlashRecall](https://flashrecall.app/); [Studr](https://studr.app/blog/ai-note-taking-app-with-flashcards/); [Retain Cards](https://apps.apple.com/us/app/-/id6745344282)
- **Gizmo** turns notes into gamified quizzes and flashcards with leaderboards, streaks and lives. It raised a **$22M Series A on 2026-04-16** (led by Shine Capital) and has **13M users** in 120+ countries, up from 300K in 2023. The same article cites competitors **Knowt (7M+ users)** and Yuno (1M downloads) — [Yahoo Finance](https://finance.yahoo.com/sectors/technology/articles/ai-learning-app-gizmo-levels-183810791.html); seed of $3.5M in 2023 — [TechCrunch](https://techcrunch.com/2023/09/21/ai-startup-gizmo-funding-gamified-quizzes-flashcards-make-learning-fun/).
- **Noji (formerly "Anki Pro")** by Vedas Apps Ltd was released 2021-06-29. It has AI-generated decks from prompts or documents and an "AI Assist" for card editing. Plans are monthly, annual and lifetime, with a 3-day trial — [ScreensDesign](https://screensdesign.com/apps/anki-pro-study-flashcards/).

**Anki add-ons and Anki-feeding tools that call LLMs**
- **AnkiBrain (AnkiChatGPT)** is an AnkiWeb add-on. Its listing title references "GPT-5.6", so it is maintained in 2026. It does auto-cards and document analysis, and needs either a paid balance or the user's own OpenAI key — [AnkiWeb](https://ankiweb.net/shared/info/1915225457).
- **Anki AI Utils** (Show HN) bulk-autogenerates any field via LLM, plus images and TTS — [HN](https://news.ycombinator.com/item?id=42534931).
- **Anki-LLM** (Show HN) bulk-processes and generates Anki cards with LLMs — [HN](https://news.ycombinator.com/item?id=45790443).
- **MasterFlasher** (Show HN, roughly Jan 2026) is very close to the owner's Android companion. It is an Android app where you "silently share" content from any app into an inbox, then batch-generate cards with the **Gemini API** (fact extraction -> scoring -> card generation) and push them to **AnkiDroid**. It is free, open source, uses bring-your-own key, and is a hobby project that got 3 HN points — [HN](https://news.ycombinator.com/item?id=46459623).
- Open-source and extension tools:
  - **ankery** (CLI; LLM or dictionary lookup -> AnkiConnect) — [GitHub](https://github.com/razorgecko/ankery)
  - **gpt-anki-creator** (ChatGPT + AnkiConnect) — [GitHub](https://github.com/s-bogelund/gpt-anki-creator)
  - **Lanki** (Chrome; capture words with context or OCR, batch-generate via local LLMs, 1-click export) — [GitHub](https://github.com/osumy/lanki)
  - **Anki Vocab Card Generator** (Chrome; ChatGPT -> Anki) — [Chrome Web Store](https://chromewebstore.google.com/detail/anki-vocab-card-generator/geoefcmpjikdfngmkdnihfbnaanimbje)
  - **ChatGPT to Anki Flashcards** (Chrome) — [Chrome Web Store](https://chromewebstore.google.com/detail/chatgpt-to-anki-flashcard/hdpooobddhbjnfmblknkfhmpcghipbgo?hl=en-US)
  - **AnkiLingoFlash** — [GitHub](https://github.com/pictoune/AnkiLingoFlash)
  - **anki-ai-dynamic-cards** (generates fresh example sentences) — [GitHub](https://github.com/AleksandrFurmenkovOfficial/anki-ai-dynamic-cards)
  - **Auto Anki** (Obsidian plugin) — [obsidianstats](https://www.obsidianstats.com/plugins/auto-anki)
  - **fluentcards-ai** (Kindle Vocabulary Builder -> AI explanations -> Anki) — [GitHub](https://github.com/gustavostz/fluentcards-ai)
- The FSRS "awesome" list includes several AI-vocab apps on FSRS:
  - Rhythm Word ("iOS vocabulary app with AI context sentences")
  - SpacedCards (iOS, AI generation)
  - Discito (iOS, AI generation)
  - KaChiKa (photo-to-flashcard for language learners)
  - BrioVocab (French CEFR vocab)
  - Read Frog (browser extension)
  - LinGoat
  - [awesome-fsrs](https://github.com/open-spaced-repetition/awesome-fsrs)

**Incumbent reading/immersion tools that save words (with partial or AI-assisted cards)**
- **Language Reactor** (Chrome; Netflix/YouTube dual subtitles):
  - Traction: **2,000,000 Chrome Web Store users**, 4.2 stars from about 3.8K ratings — [search snippet of Chrome Web Store](https://chromewebstore.google.com/detail/hoombieeljmmljlkjmnheibnpciblicm).
  - Features: it saves phrases to a library with "a basic flashcard view" and CSV export, but has **no proper SRS scheduler and no native Anki sync**. It is desktop only. Pro adds AI explanations, which are still "popup translations, not full vocabulary cards" — [TubeVocab review, 2026-05-10](https://www.tubevocab.com/blog/en/language-reactor-review). TubeVocab is a competitor, so the review is biased.
- **LingQ**:
  - Pricing: Premium is $14.99/month or $119.99/year; Premium Plus is $29.99/month or $269.99/year — [wordbyword.io](https://wordbyword.io/en/blog/lingq-alternatives).
  - Features: AI Definitions, "Explain This", AI Chat (2025), AI-powered lessons (July 2025), SRS vocabulary review, 50+ languages — [stork.ai](https://www.stork.ai/en/lingq) (secondary).
- **Readlang**:
  - Pricing: Premium is $6/month or $48/year; Premium Plus is $15/month — [wordbyword.io](https://wordbyword.io/en/blog/lingq-alternatives).
  - Features: one-click translation creates flashcards with built-in SRS, AI context-aware translations, 119 languages — [stork.ai](https://www.stork.ai/en/readlang) (secondary).
- **Migaku** does click-to-define and instant Anki card creation from Netflix/YouTube subtitles, at about $5/month according to an older guide — [Coto Academy](https://cotoacademy.com/how-to-use-migaku-browser-extension/). The price is possibly outdated (undated secondary source).
- **Reverso (translate and learn)** builds flashcards and quizzes from your search history and favourites. Premium is €4.99/month or €39.99/year — [App Store](https://apps.apple.com/us/app/reverso-translate-and-learn/id919979642?at=+&uo=4).
- **Kindle Vocabulary Builder** collects looked-up words with their context. Tools such as Fluentcards and vocabulary-to-anki convert this to Anki — [Goodreads blog](https://www.goodreads.com/author_blog_posts/17831432-how-to-create-anki-flashcards-from-your-kindle-vocabulary-builder?tab=book); [npm vocabulary-to-anki](https://npmjs.com/package/vocabulary-to-anki).

**Curated-vocabulary apps with AI layers (content-driven, not personal capture)**
- **WordUp** (Geeks Ltd):
  - Content: "25,000 most common English words, prioritized for you".
  - AI: AI teacher "Lexi", AI-generated images.
  - SRS with nine challenge types.
  - Traction: 4.8 stars from 14,000+ ratings (US App Store).
  - Pricing: Pro $9.99-10.99/month, $49/year, $149.99 lifetime.
  - Reviews: users report crashes, sync failures and removed features — [App Store](https://apps.apple.com/us/app/wordup-vocabulary-builder/id1365078730).
- **Clozemaster**: Pro is $12.99/month or $69.99/year ($79.99/year on iOS), or $199 lifetime. It adds GPT-powered sentence explanations — [search snippet citing alllanguageresources / App Store](https://www.alllanguageresources.com/?p=11253).
- **Quizlet**:
  - Plus costs $7.99/month or $35.99/year.
  - **Q-Chat (its ChatGPT tutor) was discontinued in June 2025** — [Quizgecko](https://quizgecko.com/blog/best-q-chat-alternative); [myengineeringbuddy](https://www.myengineeringbuddy.com/blog/quizlet-reviews-alternatives-pricing-offerings/).
  - "Magic Notes" still auto-generates flashcards.
  - Learn mode is adaptive but limited in the free tier; cross-session "Scheduled Review" is Plus-only — [learnclash](https://learnclash.com/blog/does-quizlet-have-spaced-repetition) (secondary).

### Inferences
- The owner's core loop (LLM validates and enriches a lexical unit, then SRS) is **not novel on its own**. At least ~25 products or tools implement some version of it, and at least 4-5 of them use Telegram as the capture or review surface (Zunoku, VocaSave, VocabellaBot, LingoCop, Behappy Speak).
- Most entrants are "text/PDF -> deck" generators. Fewer focus on **single-lexical-unit capture with canonicalisation and deduplication** (for example, recognising that "give up", "gave up on" and "сдаться" are the same entry). That is where the owner's design is more specific.
- Bring-your-own-key and open-source Anki tools (MasterFlasher, ankery, Lanki, AnkiBrain) cover power users for free. A public product would compete with "free + my own Gemini key" for the Anki crowd.

### Gaps
- No download or revenue data found for Zunoku, VocaSave, VibeLing, Vocabuo, Vocabulex or the Telegram bots. Their traction is unknown and likely small.
- Knowji, Vocabulary.com (paid tier, AI features) and Mochi's AI features were not verified in this session.
- No public data on how many Telegram Mini Apps exist in this niche.

## 2. Competitor details: core loop, platforms, SRS algorithm, pricing, traction, strengths/weaknesses

### Takeaway
Traction concentrates in (a) Duolingo, (b) AI conversation tutors (Speak > $100M ARR, Praktika ~$20M revenue), and (c) gamified AI study apps (Gizmo 13M users, Knowt 7M+). Pure vocabulary/flashcard apps earn single-digit millions per year or less. Noji, a polished "AI + SRS" Anki clone, is estimated at roughly $85K-300K/month depending on the estimator. FSRS has become the default choice for new SRS apps.

### Cited Findings

**Market context**
- Language learning apps earned **$1.54B in 2025 (+18.8% YoY)** and had 327M downloads. Duolingo alone made $1.03B — [Business of Apps (search snippet; page 403)](https://www.businessofapps.com/data/language-learning-app-market/).
- Duolingo Q2 2026: **58.7M DAU (+23%)**, 140.6M MAU, revenue $298.5M (+18%), 12.7M paid subscribers — [Barchart / Duolingo Q2 2026 release](https://www.barchart.com/story/news/3672969/duolingo-reports-second-quarter-2026-results); [SEC 8-K](https://www.sec.gov/Archives/edgar/data/0001562088/000162828026053299/q2fy26duolingo6-30x26share.htm).

**AI conversation tutors (adjacent; they take learners' budget, not the capture niche)**
- **Speak**:
  - Funding: $78M Series C at a **$1B valuation** (Dec 2024, led by Accel, with the OpenAI Startup Fund), about $162M raised in total — [TechFundingNews](https://techfundingnews.com/openai-backed-speak-closes-78m-at-1b-valuation-for-ai-powered-language-tutor/).
  - Revenue: **ARR above $100M as of Nov 2025**, up from roughly $50M at end-2024 — [readthesignal](https://readthesignal.co/p/speak-hit-100m-arr-the-ai-that-answers).
  - Users and B2B: about 15M downloads, 6 languages, about 500 corporate customers (KPMG, HD Hyundai). Paid plans are "$80 and $200" — [Yahoo Finance](https://finance.yahoo.com/news/1-billion-ai-startup-backed-144613265.html).
- **Praktika** (AI avatar tutors): $35.5M Series A in May 2024 led by Blossom Capital, 1.2M MAU in 100 countries, nearly $20M revenue in the trailing 12 months — [Yahoo Finance/TechCrunch](https://uk.finance.yahoo.com/news/praktika-raises-35-5m-ai-122549635.html). No newer round was found as of 2026 — [CB Insights](https://www.cbinsights.com/company/praktikaai/financials).

**Flashcard/SRS platforms**
- **Noji (Anki Pro)**: revenue estimates conflict. One source puts it at $85K/month (page title) or $150K/month with about 25K installs (page body) — [ScreensDesign](https://screensdesign.com/apps/anki-pro-study-flashcards/). Others put it at about $250-300K/month with 95-200K monthly downloads, and cumulative downloads at about 2.4M — [search snippets aggregating AppBrain/other trackers](https://www.appbrain.com/app/noji-study-anki-flashcards/com.noji.flashcards). Rating is 4.6.
- **RemNote** costs about $8/month with a free tier and supports both SM-2 and FSRS. **Brainscape** costs about $7.99/month with a free tier and uses its own "confidence-based repetition". **Mochi** is free or $5/month — [venture-lab.org](https://venture-lab.org/2026/best-flashcard-apps-2026/); [RemNote vs Brainscape](https://www.remnote.com/brainscape). Both sources are secondary. Note that venture-lab wrongly says Anki has FSRS "as an add-on"; FSRS has been built in since 23.10.
- Apps listed as using FSRS: Anki, Mochi, RemNote, Logseq, Obsidian plugins, SiYuan, plus many small AI-vocab apps. FSRS libraries exist in about 20 languages, including **Kotlin (android-fsrs), Swift, Dart, TypeScript (ts-fsrs), Python (py-fsrs) and Rust (fsrs-rs)** — [awesome-fsrs](https://github.com/open-spaced-repetition/awesome-fsrs).
- **Memrise**:
  - Revenue (conflicting): about **$13.3M in 2024, its third annual decline** — [Business of Apps (snippet)](https://www.businessofapps.com/data/memrise-statistics/). This is **contradicted** by about $35M in 2024 — [skillademia](https://www.skillademia.com/statistics/memrise-statistics/) (low-quality aggregator).
  - Headcount: about 140 (2022) -> about 100 (2024) -> 57 (2026) — [skillademia](https://www.skillademia.com/statistics/memrise-statistics/); [Tracxn](https://tracxn.com/d/companies/memrise/__nkiQ7iwxCIFVRakUxzDFKUTeOm7s2q6xGM0OgUHW6S0).
  - Strategy: it pivoted from community flashcards to curated content, native-speaker video and AI conversation — [skillademia](https://www.skillademia.com/statistics/memrise-statistics/).
- **Lingvist** (Estonia, adaptive vocabulary) raised **€5.1M in June 2025** led by Rubio Impact Ventures — [Estonian World](https://estonianworld.com/business/estonian-edtech-startup-lingvist-raises-e5-1-million-in-funding/).
- **Drops** still operates and is owned by Kahoot! — [Wikipedia](https://en.wikipedia.org/wiki/Drops_(app)).

**Pricing benchmarks (for a would-be public product)**

| Product | Price |
|---|---|
| Language Reactor Pro | $5.95/month or $39.95/year ([wordbyword](https://wordbyword.io/en/blog/lingq-alternatives)); **conflicts with** ~$9/month or ~$5/month billed yearly ([TubeVocab](https://www.tubevocab.com/blog/en/language-reactor-review)) |
| Readlang | $48/year |
| LingQ | $119.99/year |
| Quizlet Plus | $35.99/year |
| Reverso | €39.99/year |
| WordUp Pro | $49/year |
| Clozemaster | $69.99/year |
| AnkiMobile | $24.99 one-time |
| Flowery | $15.64/month (met with pushback) |
| Vocabuo | ~$30/year |

Sources are the ones cited above.

**Review-based strengths and weaknesses**
- Language Reactor: strong for immersion; weak on SRS, depth (no IPA or collocations) and mobile — [TubeVocab](https://www.tubevocab.com/blog/en/language-reactor-review).
- WordUp: strong, curated English content; reviews complain of crashes, sync failures and removed features — [App Store](https://apps.apple.com/us/app/wordup-vocabulary-builder/id1365078730).
- Memrise: strong negative reaction after community courses were removed from the app (31 Mar 2024) — [Kimola review analysis](https://kimola.com/reports/uncover-the-impact-memrise-apps-user-feedback-report-app-store-us-147885); [Wikipedia](https://en.wikipedia.org/wiki/Memrise).
- Flowery: HN users balked at a paywall with no trial and at confusing onboarding — [HN](https://news.ycombinator.com/item?id=40717052).

### Inferences
- A consumer subscription in this niche realistically lands at about $30-60/year. Users balk at higher prices without a strong free tier (Flowery), and Anki is free on desktop and Android.
- Since no one owns "personal vocabulary capture", the realistic commercial upside for a new entrant is modest, comparable to Noji or Readlang scale at best, unless it adds a conversation or tutor layer (where the money is) or a strong distribution channel.
- FSRS is open-source in Kotlin, Swift and TS, so building in-house SRS is not a moat. Every competitor can have the same algorithm.

### Gaps
- No Sensor Tower or Appfigures data was accessible for WordUp, Clozemaster, LingQ, Readlang or Reverso revenue.
- No verified MAU for Language Reactor beyond the Chrome "users" count.
- Mochi, RemNote and Brainscape pricing is from secondary blogs, not their pricing pages.

## 3. State of Anki itself (desktop, AnkiDroid, AnkiMobile), FSRS adoption, AnkiConnect/AnkiWeb ecosystem

### Takeaway
Anki is healthy and growing, but its stewardship changed in 2026. Damien Elmes announced on 2026-02-02 a gradual handover of business operations and open-source stewardship to **AnkiHub** (no investors, already profitable, "no pricing changes planned"). AnkiDroid grew from 3.2M to 4.0M unique users in 2025. FSRS has shipped in Anki since 23.10 (Oct 2023), and its default parameters come from about 727M reviews. No reliable total-user or language-learner share is published.

### Cited Findings
- **Ownership transition**:
  - Announcement: on **2 February 2026**, Damien Elmes ("dae") announced he is stepping back after 19 years, citing burnout, and gradually transitioning business operations and open-source stewardship to AnkiHub.
  - AnkiHub's commitments: Anki's core stays open source; "both Anki and AnkiHub are already profitable"; there are no investors; pricing commitment is "fair pricing that supports users rather than exploiting them".
  - Expected improvements: better UI/UX, add-on ecosystem, broader support beyond medical — [Anki Forums: "Anki's Growing Up"](https://forums.ankiweb.net/t/ankis-growing-up/68610).
  - AnkiHub was founded by Nick ("The AnKing", a resident physician) and Andrew Sanchez — [search summary of same thread](https://forums.ankiweb.net/t/ankis-growing-up/68610/2).
- **June 2026 team update** (2026-06-16): a new graphical installer/launcher, unified docs, a new logo, and a planned **add-on system overhaul** (modelled on Obsidian's add-on architecture). There was no mention of mobile, AI, FSRS or pricing changes — [Anki Forums](https://forums.ankiweb.net/t/updates-from-the-anki-team-june-2026/70120).
- **AnkiHub AI**: reported AI card auto-generation from PDFs or lecture recordings, and work on RAG and semantic search in Anki — [search summary citing youngju.dev 2026-05-16 and Anki forum](https://forums.ankiweb.net/t/what-s-the-cutting-edge-future-of-ai-and-spaced-repetition-anyone-know-the-technical-details/50115/19). This is secondary and not verified on an AnkiHub page.
- **AnkiMobile (iOS)**: **$24.99 one-time**, no subscriptions or IAP, rated 4.0 from 2.3K US ratings, **#1 Education (paid)**. Version 25.09 shipped 2025-09-08. "Sales of this app support the development of both the computer and mobile version" — [App Store](https://apps.apple.com/us/app/ankimobile-flashcards/id373493387).
- **AnkiDroid**:
  - Users: unique users **3.2M -> 4.0M during 2025** and devices 3.65M -> 4.48M (Google Play only), described as "DOUBLE last year's" growth.
  - Community: 1,708+ new Open Collective backers and about 85 contributors.
  - Releases: 7 major releases in 2025.
  - 2026 plans: rebuilding the JS API "in preparation for addon support" — [AnkiDroid 2025 #wrapped (2025-12-31)](https://opencollective.com/ankidroid/updates/ankidroid-2025-wrapped).
  - Other reported figures (secondary): "over ten million Google Play downloads", 4.77 stars from 150K+ ratings, "estimated 3 million active users" — [flashcard-maker.cc](https://flashcard-maker.cc/blog/ankidroid-review/). Full FSRS support since 2.17 — [same](https://flashcard-maker.cc/blog/ankidroid-review/).
- **FSRS**:
  - Integrated in **Anki 23.10 (released 31 Oct 2023)**. Default parameters are "based on about 727 million reviews from 10 thousand users" — [Wikipedia](https://en.wikipedia.org/wiki/Anki_(software)); [Wikipedia: Anki](https://en.wikipedia.org/wiki/Anki).
  - Default vs opt-in is disputed. Wikipedia says it was integrated "as an optional feature" ([Wikipedia](https://en.wikipedia.org/wiki/Anki_(software))). A search summary claimed it "replaced SM-2 as the default" ([search result](https://en.wikipedia.org/wiki/Anki)). Treat it as **opt-in but widely recommended**; for example, guides say "Anki Desktop with FSRS enabled" is the 2026 standard setup — [slidetoanki](https://slidetoanki.com/blog/how-to-use-fsrs-anki-guide).
  - The open-spaced-repetition "awesome-fsrs" repo has about 715 stars and lists about 20 language implementations and 40+ apps — [GitHub](https://github.com/open-spaced-repetition/awesome-fsrs).
- **Licensing and services**: desktop is AGPLv3+, AnkiDroid is GPLv3, and AnkiWeb is a "free and proprietary online service" — [Wikipedia](https://en.wikipedia.org/wiki/Anki_(software)).
- **Usage by segment**:
  - 2024 survey: **86.2% of US medical students** use Anki and 66.5% use it daily. The AnKing deck has been downloaded 300K+ times — [Wikipedia](https://en.wikipedia.org/wiki/Anki_(software)).
  - Forum participants say no usage statistics by purpose (language vs exam) exist: "I don't think there are usage statistics like that available" — [Anki Forums](https://forums.ankiweb.net/t/how-many-users-use-anki-for-long-term-retention/54053).

### Inferences
- Anki's centre of gravity, and AnkiHub's commercial focus, is **medical education**. Language learners are a large but under-served Anki segment: no AI vocab features, and a manual note-type setup that new learners find hard. That is a niche for "Anki-compatible AI capture" tools like the owner's.
- AnkiConnect plus a running desktop Anki is a friction point for mass-market users. It works for power users, but a public product syncing via AnkiConnect will reach only the desktop-Anki subset. The planned add-on overhaul and AnkiDroid's add-on JS API may open new integration paths in 2026-27.
- AnkiDroid's 4M users and fast growth show there is still large demand for free SRS on Android. A paid in-house SRS app would compete head-on with a free, trusted, FSRS-equipped incumbent.

### Gaps
- No official total Anki user count, AnkiWeb account count, or share of language learners was found.
- No AnkiConnect install count was found (AnkiWeb add-on pages don't publish downloads).
- AnkiMobile's worldwide rating count is unknown; the US store shows 2.3K, which seems low and may be a regional subset.

## 4. Which gaps remain unaddressed?

### Takeaway
No product found combines all of the owner's elements:
- capture of single **multi-word lexical units** (phrasal verbs, idioms, collocations) from anywhere (messenger, Android text selection);
- LLM **validation and canonicalisation with deduplication**;
- native-language (RU) translations plus English explanation, IPA, frequency and word family;
- either Anki sync or a built-in FSRS.

Each piece exists separately. The remaining differentiation lies in quality on multi-word expressions, capture friction, and L1-specific output. The algorithm and "AI cards" are commodities.

### Cited Findings
- **Capture friction is the recognised pain point.** MasterFlasher's creator: the moment "I should remember this" is "rarely the moment you want to stop and make flashcards" — [HN](https://news.ycombinator.com/item?id=46459623). The Show HN was titled "A holiday side project to make Anki flashcards without breaking flow". A separate Show HN pitched "Anki-like flashcards for non tech-savvy users (language learning)", pointing to Anki's usability barrier — [HN](https://news.ycombinator.com/item?id=43278688).
- **Immersion tools lack SRS and depth.** Language Reactor (2M users) has no SRS, no native Anki sync, no IPA, collocations or examples, and no mobile app — [TubeVocab](https://www.tubevocab.com/blog/en/language-reactor-review).
- **AI card quality and trust are a live concern**:
  - An Anki forum view: autogenerated decks are "usually a bad idea" because learners weren't exposed to the information first — [Anki Forums](https://forums.ankiweb.net/t/use-generative-ai-to-generate-flash-cards/45401).
  - A blogger concluded that using LLMs for Anki cards is "not worth the risk" due to subtle errors — [denovo substack](https://denovo.substack.com/p/ai-generated-anki-cards-are-not-to).
  - A developer put AI example sentences below verified content because they are not a "source of truth" — [search summary of sowcow/serbian-anki-deck](https://github.com/sowcow/serbian-anki-deck).
  - Research (Memdora, arXiv, July 2026): learners value automation but "require editable, transparent AI outputs to maintain cognitive ownership" — [arXiv 2607.25096](https://arxiv.org/pdf/2607.25096) (via search snippet).
- **Phrasal verbs and idioms are served mainly by static content apps** (for example "Learn English Phrasal Verbs" and "English Phrasal Verbs in Use") rather than by personal-capture AI tools — [App Store](https://apps.apple.com/us/app/learn-english-phrasal-verbs/id6444289868); [Google Play](https://play.google.com/store/apps/details?id=com.arturagapov.phrasalverbs&hl=en_US). No competitor found explicitly markets canonicalisation or deduplication of inflected multi-word expressions.
- **Native-language-specific output**: most AI vocab apps are English-UI and multi-language. Only a few explicitly support RU (Zunoku, VibeLing) — [AlternativeTo](https://alternativeto.net/software/zunoku/about/); [VibeLing](https://vibeling.app/en/blog/best-ai-vocabulary-apps-2026).
- **Messenger capture exists but is shallow**: the Telegram bots use fixed intervals (LingoCop: 1/3/7/14/30 days), text-to-deck generation (Zunoku), or quiz-back (VocabellaBot) — sources in Section 1. None was found that syncs to Anki.
- **Monetisation of capture layers is hard.** Babbel's CEO on Toucan: "Web extensions are notoriously hard to monetize" — [TechCrunch](https://techcrunch.com/2023/09/19/babbel-acquires-language-learning-browser-extension-toucan/).

### Inferences
- **Defensible differentiation candidates**, from strongest to weakest:
  1. Measurable quality on multi-word lexical units (accept/reject validity, canonical form, dedup across inflections and L1/L2 input). Competitors don't advertise this, and it is hard to fake.
  2. Zero-friction, OS-level capture (Telegram + Android share/selection + browser) feeding a single deduplicated personal dictionary.
  3. L1-specific (RU-first, then other L1s) translations and learner-relevant metadata (frequency, word family, register).
  4. "Bring your own SRS": a first-class Anki/AnkiDroid bridge plus an optional built-in FSRS, rather than forcing a switch.
- Building a standalone FSRS mobile app mostly re-creates what AnkiDroid (free, 4M users) and Noji or Mochi already offer. The value is in the capture-and-quality layer, not the review layer.
- Telegram distribution is a meaningful channel advantage in RU/CIS markets but weaker in the US and Western Europe. Zunoku's choice of EN/RU plus Telegram suggests others see the same opening.

### Gaps
- No systematic evaluation was found comparing LLM card accuracy for phrasal verbs or idioms across products. The quality claim would need the owner's own benchmark.
- No user-survey data on willingness to pay for a capture-only tool versus a full SRS app.

## 5. Failed or shut-down startups in this space and why

### Takeaway
Failures and retreats cluster around business-model problems, not technology. Hard-to-monetise extensions (Toucan) and community/UGC features that didn't fit a curated subscription product (Memrise community courses, Lang-8) are the clearest cases. Even large players retired AI chat features (Quizlet Q-Chat, June 2025).

### Cited Findings
- **Toucan** (browser extension that swaps words on web pages into the target language):
  - Funding: raised about **$30M** (including a $20M Series A) — [TechCrunch 2023](https://techcrunch.com/2023/09/19/babbel-acquires-language-learning-browser-extension-toucan/); $4.5M seed in 2021 — [TechCrunch 2021](https://techcrunch.com/2021/04/27/toucan-seed-funding/).
  - Wind-down: it had 300K+ Chrome downloads (4.7 stars) but "wasn't able to become a profitable business". It **wound down in early 2023**, and **Babbel acquired the technology only** in Sept 2023, with no staff joining. Babbel moved paid features into the free tier — [TechCrunch](https://techcrunch.com/2023/09/19/babbel-acquires-language-learning-browser-extension-toucan/).
- **Quizlet Q-Chat** (an "AI tutor built with OpenAI's ChatGPT", launched 2023) was **discontinued in June 2025** without a detailed public explanation — [Quizgecko](https://quizgecko.com/blog/best-q-chat-alternative); original launch: [Quizlet blog](https://quizlet.com/blog/meet-q-chat).
- **Memrise community courses**: Memrise announced the "sunset" of user-created courses in Nov 2023, removed them from the app on **31 Mar 2024**, and moved them to a separate site. This triggered negative reviews. Revenue reportedly declined for three straight years to about $13.3M in 2024 (disputed, see Section 2) — [Wikipedia](https://en.wikipedia.org/wiki/Memrise); [Kimola](https://kimola.com/reports/uncover-the-impact-memrise-apps-user-feedback-report-app-store-us-147885); [Business of Apps snippet](https://www.businessofapps.com/data/memrise-statistics/).
- **Lang-8** (language-exchange correction site, adjacent) shut down on **29 Feb 2024** and redirected users to HiNative — [Wikipedia](https://en.wikipedia.org/wiki/Lang-8.com).
- **Flowery** (LLM vocab + SRS, 2024) got a lukewarm HN reception over its no-trial $15.64/month paywall. No evidence was found that it is still active — [HN](https://news.ycombinator.com/item?id=40717052).

### Inferences
- The recurring failure mode is that **capture/enrichment tools are features, not businesses**. They get acquired for tech (Toucan), absorbed into bigger apps, or survive as low-revenue indie products. A public version of the owner's bot should plan for low or no direct monetisation, or attach to a higher-value layer (tutoring/practice, B2B/teachers, or a paid Anki-integration niche).
- Removing user-generated or personal content (Memrise) alienates exactly the "personal dictionary" users the owner targets. Data portability (Anki export) is a trust feature.

### Gaps
- Not verified in this session: Duolingo Tinycards shutdown (2020, older), Cerego, Knowji status, and whether Flowery or small Telegram vocab bots are still running.
- No post-mortems found from 2024-2026 AI-flashcard startups specifically. Most small entrants appear to stagnate rather than announce closures.
- RU-market apps (Lingualeo, Skyeng Words, ReWord, Easy Ten) are deliberately out of scope here and covered by the other researcher. "My Words" (package `ru.babkin.mywords`) and Zunoku (EN/RU) are the only RU-relevant items surfaced in this global search.
