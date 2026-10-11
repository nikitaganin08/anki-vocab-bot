# Economics and build requirements for a public multi-user LLM vocab-card product + mobile SRS app (as of 2026-10-07)

Scope: unit economics (LLM, TTS), FSRS/SRS build options, mobile stack, monetization (Telegram Stars, app stores), multi-user engineering requirements, legal/compliance. All prices are USD as fetched on 2026-10-06/07 unless noted.

Global assumptions used in calculations (explicit, not sourced):
- Card generation call, scenario A (realistic for this repo): ~1,000 input tokens (the current system prompt `backend/app/services/llm_prompt.py` is 3,325 bytes, roughly 850 tokens, plus user input and JSON overhead) and ~600 output tokens (one JSON card with 2-3 translations, explanation, 3 examples, frequency note).
- Scenario B (upper bound from the brief): 2,000 input / 2,000 output tokens.
- The repo also has `word_family_prompt.py` and `description_lookup_prompt.py`; if a card triggers extra LLM calls, multiply per-card cost by the number of calls.
- Active user = 5 / 10 / 20 new words per day x 30 days = 150 / 300 / 600 cards per month.
- Reasoning-capable models (GPT-5 nano/mini, Gemini 3.x) bill hidden reasoning tokens as output; numbers below assume reasoning is set to minimal/off.

---

## 1. LLM cost per card, per 1,000 cards, per active user; effect of a shared global dictionary cache

### Takeaway
LLM cost is small relative to any realistic subscription price: with cheap 2026 models a card costs $0.0001-0.004, i.e. ~$0.10-4.00 per 1,000 cards, and an active user (5-20 words/day) costs ~$0.02-2.40/month in scenario A. The newer Google defaults (3.5 Flash-Lite, 3.8 Flash) are 5-9x pricier than 2.5 Flash-Lite, and Google is restricting 2.5 access to existing users, so model choice matters more than volume. A shared global dictionary cache keyed before the LLM call can plausibly cut steady-state LLM spend by 70-90% for single words (inference), while one-off pre-generation of ~30k headwords costs only ~$5-85 in batch mode.

### Cited Findings
Prices (per 1M tokens, input / output):
- Gemini 2.5 Flash-Lite: $0.10 / $0.40 (text); context caching $0.01-0.03; batch = 50% of standard. Gemini 3.1 Flash-Lite: $0.25 / $1.50. Gemini 3.5 Flash-Lite: $0.30 / $2.50 (cache $0.03). Gemini 3.5 Flash: $1.50 / $9.00. Gemini 3.6/3.7/3.8 Flash: $0.75 / $3.75 "through December 31, 2026", rising to $1.50 / $7.50 "starting January 1, 2027". Page last updated 2026-10-06. Free tier: Flash/Flash-Lite "Free of charge" with limited access. — [Google Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- gemini-2.5-flash-lite: "No shutdown date announced", but the deprecations page says access to 2.5 models is being limited "to users who have actively used them in the past" and recommends "3.5 Flash-Lite or 3.8 Flash" for new projects; gemini-3.1-flash-lite shuts down May 7, 2027 (replacement gemini-3.5-flash-lite). — [Gemini deprecations](https://ai.google.dev/gemini-api/docs/deprecations)
- OpenAI: GPT-5-nano $0.05 / $0.40 (cached in $0.005); GPT-5-mini $0.25 / $2.00; GPT-4.1-nano $0.10 / $0.40; GPT-4.1-mini $0.40 / $1.60; GPT-5.4-nano $0.20 / $1.25; GPT-5.4-mini $0.75 / $4.50; Batch API = 50% off. — [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
- Anthropic Claude Haiku 4.5: $1 / $5; cache read $0.10, cache write $1.25; batch saves 50%; no newer Haiku listed. — [Claude pricing](https://claude.com/pricing)
- DeepSeek direct API: deepseek-flash (DeepSeek-V4.1-Flash) input cache-miss $0.30 peak / $0.15 off-peak, cache-hit $0.006 / $0.003, output $1.20 peak / $0.60 off-peak; deepseek-v4-pro $1.32 / $3.96 peak. Off-peak = half price; peak hours 01:00-04:00 and 06:00-10:00 UTC Mon-Fri. — [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing)
- OpenRouter live model list (fetched 2026-10-07) shows: deepseek/deepseek-v4.1-flash $0.044 / $0.30; deepseek/deepseek-v3.2 $0.28 / $0.42; qwen/qwen3.7-flash $0.03 / $0.13; qwen/qwen3.8-flash $0.15 / $0.47; qwen/qwen3-235b-a22b-2507 $0.09 / $0.55; openai/gpt-oss-120b $0.037 / $0.17; mistralai/mistral-small-2603 $0.15 / $0.60; `:batch` variants exist at ~50% for Gemini, OpenAI, Anthropic, Mistral. — [OpenRouter models API](https://openrouter.ai/api/v1/models)
- Discrepancy: OpenRouter lists DeepSeek V4.1 Flash at $0.044 / $0.30 while DeepSeek's own API lists $0.30 / $1.20 peak — OpenRouter likely routes to third-party hosts; quality/latency/data-retention may differ by provider. — [OpenRouter models API](https://openrouter.ai/api/v1/models); [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing)
- OpenRouter says it passes through provider pricing "without any markup"; it charges 5.5% ($0.80 min) on Stripe credit purchases, 5% on crypto, and 5% on BYOK usage above a monthly allowance. — [OpenRouter FAQ](https://openrouter.ai/docs/faq)
- Vocabulary distribution relevant to caching: ~8,000-9,000 word families are needed for 98% coverage of written English and 6,000-7,000 for spoken (Nation 2006, replicated). — [Cambridge Language Teaching replication](https://www.cambridge.org/core/journals/language-teaching/article/how-much-vocabulary-is-needed-to-use-english-replication-of-van-zeeland-schmitt-2012-nation-2006-and-cobb-2007/1D217A56A2E0056E67802A6A8360FDDE)

Computed cost table (my arithmetic on the prices above; standard non-batch rates, no caching):

| Model | $/1M in | $/1M out | A: $/1k cards | B: $/1k cards | A: $/user/mo @5/day | A: @10/day | A: @20/day | B: @20/day |
|---|---|---|---|---|---|---|---|---|
| gemini-2.5-flash-lite | 0.10 | 0.40 | 0.34 | 1.00 | 0.05 | 0.10 | 0.20 | 0.60 |
| gemini-3.1-flash-lite | 0.25 | 1.50 | 1.15 | 3.50 | 0.17 | 0.35 | 0.69 | 2.10 |
| gemini-3.5-flash-lite | 0.30 | 2.50 | 1.80 | 5.60 | 0.27 | 0.54 | 1.08 | 3.36 |
| gemini-3.8-flash (2026 promo) | 0.75 | 3.75 | 3.00 | 9.00 | 0.45 | 0.90 | 1.80 | 5.40 |
| gemini-3.8-flash (from 2027-01-01) | 1.50 | 7.50 | 6.00 | 18.00 | 0.90 | 1.80 | 3.60 | 10.80 |
| gpt-4.1-nano | 0.10 | 0.40 | 0.34 | 1.00 | 0.05 | 0.10 | 0.20 | 0.60 |
| gpt-5-nano (minimal reasoning) | 0.05 | 0.40 | 0.29 | 0.90 | 0.04 | 0.09 | 0.17 | 0.54 |
| gpt-5.4-nano | 0.20 | 1.25 | 0.95 | 2.90 | 0.14 | 0.29 | 0.57 | 1.74 |
| gpt-5-mini | 0.25 | 2.00 | 1.45 | 4.50 | 0.22 | 0.44 | 0.87 | 2.70 |
| gpt-5.4-mini | 0.75 | 4.50 | 3.45 | 10.50 | 0.52 | 1.04 | 2.07 | 6.30 |
| claude-haiku-4.5 | 1.00 | 5.00 | 4.00 | 12.00 | 0.60 | 1.20 | 2.40 | 7.20 |
| deepseek-v4.1-flash (OpenRouter) | 0.044 | 0.30 | 0.22 | 0.69 | 0.03 | 0.07 | 0.13 | 0.41 |
| deepseek-flash V4.1 direct, peak | 0.30 | 1.20 | 1.02 | 3.00 | 0.15 | 0.31 | 0.61 | 1.80 |
| deepseek-flash V4.1 direct, off-peak | 0.15 | 0.60 | 0.51 | 1.50 | 0.08 | 0.15 | 0.31 | 0.90 |
| deepseek-v3.2 | 0.28 | 0.42 | 0.53 | 1.40 | 0.08 | 0.16 | 0.32 | 0.84 |
| qwen3.7-flash | 0.03 | 0.13 | 0.11 | 0.32 | 0.02 | 0.03 | 0.07 | 0.19 |
| qwen3.8-flash | 0.15 | 0.47 | 0.43 | 1.24 | 0.07 | 0.13 | 0.26 | 0.74 |
| gpt-oss-120b | 0.037 | 0.17 | 0.14 | 0.41 | 0.02 | 0.04 | 0.08 | 0.25 |
| mistral-small-2603 | 0.15 | 0.60 | 0.51 | 1.50 | 0.08 | 0.15 | 0.31 | 0.90 |

Formulas: $/card = (in_tokens x in_price + out_tokens x out_price) / 1e6. Scenario A per 1k cards = in_price + 0.6 x out_price.

### Inferences
- Output tokens dominate cost for every Gemini 3.x and GPT-5.x model (e.g., 3.5 Flash-Lite: $0.30 of $1.80 per 1k cards is input). Trimming the JSON (fewer/shorter examples, no frequency_note prose) saves more than prompt caching.
- Prompt caching of the static system prompt (~850 tokens) saves at most ~0.85 x (in_price - cached_price) per 1k cards: ~$0.23 on Gemini 3.5 Flash-Lite, ~$0.08 on 2.5 Flash-Lite. Minor. Provider minimum-prefix-length rules for implicit caching were not verified (see Gaps).
- Practical default for a public launch: Gemini 3.5 Flash-Lite (Google's recommended path, $1.80/1k cards) or gpt-5-nano / gpt-4.1-nano (~$0.30/1k) with 2.5 Flash-Lite kept while the existing key still has access. DeepSeek/Qwen via OpenRouter are cheapest but quality of Russian translations and IPA must be evaluated on a golden set before switching.
- Global dictionary cache math: monthly LLM cost = new_cards x (1 - hit_rate) x cost_per_card. Example: 1,000 active users x 300 cards = 300k cards/month -> $540 on 3.5 Flash-Lite with no cache; $108 at 80% hit rate; $54 at 90%. On 2.5 Flash-Lite: $102 -> $20 at 80%.
- Expected hit rate (inference, no direct data found): learner lookups concentrate in the 2k-10k frequency band (Nation's 8-9k families for 98% coverage), so after a few hundred users or a pre-seeded headword list, single-word hit rates of 70-90% are plausible; phrasal verbs/collocations/idioms will hit less (long tail). Russian-language input (`source_language=ru`) needs its own key space (ru surface form -> en canonical), and polysemous words may need sense-level keys.
- Pre-generation: 30,000 headwords at Gemini 3.5 Flash-Lite batch ($0.15/$1.25) = ~$27 (scenario A) to ~$84 (B); at 2.5 Flash-Lite batch ($0.05/$0.20) = ~$5. This is a one-off cost below one month of a 1k-user uncached bill.
- Architectural implication for this repo: today the canonical-text dedupe happens after the LLM call (AGENTS.md workflow steps 9-11), so it saves storage, not LLM money. To save money the cache lookup must happen before the call: normalized source_text (lemma, lowercased) -> global card id; per-user cards then become references to global cards plus user-specific SRS state.
- Abuse/variance: the long tail (free-form 8-token inputs that the LLM rejects) is always a cache miss and still costs a full call; rejected inputs are not stored today, so cache negative results too.

### Gaps
- No published data on lookup overlap across vocabulary-app users (actual cache hit rates); the 70-90% figure is an inference.
- Implicit-caching minimum prompt lengths for Gemini 3.x / OpenAI were not verified in this pass.
- Real token counts for this repo's prompt/output were estimated from file size, not measured via the provider's usage fields; measure from OpenRouter generation stats before finalizing.
- Quality comparison (translation accuracy, IPA correctness, JSON validity rate) between models was not researched.

---

## 2. TTS options/costs and pronunciation (IPA) data licensing

### Takeaway
Pronunciation audio is nearly free if generated once per canonical word and cached globally: word-only audio is ~15 characters per card, so even premium voices cost cents per 1,000 cards and the Google/Azure free tiers cover small scale. The real issue is legal, not cost: edge-tts uses Microsoft's consumer Read Aloud endpoint without a contract, and Microsoft's own answer says commercial use without an Azure subscription may violate its terms; switch to Azure Speech (same Neural voice family, including en-US-EmmaNeural-class voices) or Google Cloud TTS for a public product, or on-device TTS in the mobile app. For IPA, CMUdict is BSD (ARPAbet, US only) and Wiktionary/kaikki data is CC BY-SA + GFDL (share-alike obligations).

### Cited Findings
- edge-tts commercial use: a Microsoft Q&A response says GPL repos can be commercialized under their license, "However, if these repositories rely on Microsoft's proprietary services ... commercial use without a valid Azure subscription could be a violation of their terms of service"; recommends Azure AI Speech for commercial applications. — [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/2088770/are-opensource-edge-tts-free-for-commercial-use)
- Azure Speech TTS free tier (F0): "0.5 million characters free per month"; the official page rendered dollar amounts as "$-" in fetch. — [Azure Speech pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/)
- Azure neural TTS reported at $15 per 1M characters (secondary aggregator; primary page did not render prices). — [speechactors.com (aggregator)](https://speechactors.com/article/?p=3863)
- Google Cloud TTS: Standard and WaveNet $4 per 1M characters after 4M free characters/month; Chirp 3: HD $30 per 1M after 1M free/month (from Google pricing page search snippets; full page did not render in fetch). — [Google Cloud TTS pricing](https://cloud.google.com/text-to-speech/pricing)
- OpenAI TTS: tts-1 "$15.00 / 1M characters", tts-1-hd "$30.00 / 1M characters", gpt-4o-mini-tts $0.60/1M text-in tokens + $12.00/1M audio-out tokens. — [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
- Gemini TTS: 3.8 Flash TTS $0.50 text-in / $9.00 audio-out per 1M tokens (2026 promo), 3.8 Flash-Lite TTS $0.50 / $6.00; doubling from 2027-01-01. — [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- ElevenLabs API pay-as-you-go: Flash/Turbo $0.04 per 1K characters; Multilingual v2/v3 $0.08 per 1K; promotional v4 $0.022/1K and v4 Turbo $0.011/1K ("72% off until Oct 12"); plans Starter $6 ... Business $990/month. — [ElevenLabs API pricing](https://elevenlabs.io/pricing/api)
- iOS on-device: AVSpeechSynthesizer default-quality voices sound "much worse" than enhanced/premium voices; apps cannot query which enhanced voices are downloadable but not installed. — [Apple Developer Forums](https://developer.apple.com/forums/thread/748464); [Apple Developer Forums](https://developer.apple.com/forums/thread/758460)
- Android: Google's TTS update improved standard voice quality with less storage. — [Liliputing](https://liliputing.com/android-text-speech-update-improves-voice-quality/)
- CMUdict is distributed under a BSD license (Carnegie Mellon Speech Group). — [Wikipedia: CMU Pronouncing Dictionary](https://en.wikipedia.org/wiki/CMU_Pronouncing_Dictionary)
- kaikki.org (wiktextract) data is under the same licenses as Wiktionary: "both CC-BY-SA and GFDL". — [kaikki.org](https://kaikki.org/dictionary/)
- wikt2pron converts Wiktionary dump pronunciations (IPA, X-SAMPA) to cmudict format. — [wikt2pron docs](https://wikt2pron.readthedocs.io/)

Computed TTS cost per 1,000 cards (my arithmetic; word-only ~15 chars/card; word + 3 examples ~255 chars/card):

| Provider / voice | $/1M chars | Word-only, $/1k cards | Word+3 examples, $/1k cards | Free tier/month |
|---|---|---|---|---|
| Google Standard / WaveNet | 4 | 0.06 | 1.02 | 4M chars |
| Google Chirp 3 HD | 30 | 0.45 | 7.65 | 1M chars |
| Azure Neural (aggregator price) | 15 | 0.23 | 3.83 | 0.5M chars |
| OpenAI tts-1 / tts-1-hd | 15 / 30 | 0.23 / 0.45 | 3.83 / 7.65 | none found |
| ElevenLabs Flash / v2-v3 | 40 / 80 | 0.60 / 1.20 | 10.20 / 20.40 | n/a |
| On-device (AVSpeechSynthesizer / Android TextToSpeech) | 0 | 0 | 0 | n/a |

### Inferences
- With a global audio cache (one MP3 per canonical_text, served from object storage/CDN), TTS cost scales with distinct words, not users: 30k headwords x 15 chars = 450k chars, inside Google's 4M or Azure's 0.5M free monthly tier. TTS is a rounding error; storage/egress of MP3s will exceed synthesis cost.
- Lowest-risk migration from edge-tts: Azure Speech with the same voice family (keeps the current sound), or Google WaveNet. Keep edge-tts only for the owner's private use.
- Mobile app: on-device TTS is free and offline but quality varies by device and installed voices; a hybrid (server-cached cloud MP3 for the headword, on-device for examples) balances cost and quality.
- IPA: the LLM already returns `transcription`; LLM IPA can be cross-checked against CMUdict (BSD, safe to embed) for US English. Using Wiktionary IPA or audio files imposes CC BY-SA attribution and share-alike on the derived dataset; store it separately and attribute, or avoid redistributing it.

### Gaps
- Primary Azure and Google Cloud TTS price tables did not render in fetch; figures are from search snippets/aggregators and should be rechecked on the pricing calculators.
- Whether Microsoft has actively blocked/rate-limited the edge-tts endpoint in 2026 was not established.
- Wiktionary audio (Wikimedia Commons) licenses vary per file; not researched.

---

## 3. FSRS implementation options, licenses, maturity; SRS review flow; keeping Anki .apkg export

### Takeaway
FSRS is a solved, permissively licensed component: ts-fsrs (MIT, TypeScript, v5.4.2, Sep 2026), py-fsrs (MIT, v6.3.2), fsrs-rs (BSD-3, scheduler + optimizer, v6.6.2) and fsrs-browser (BSD-3, WASM optimizer) are all actively maintained by the open-spaced-repetition org, so a solo dev can use them in a closed-source commercial app. Anki itself is AGPL-3.0 and must not be copied into a closed app, but generating .apkg files with genanki (MIT) or talking to AnkiConnect (GPL-3, user-installed add-on, now hosted on sourcehut) keeps Anki as an export option.

### Cited Findings
- open-spaced-repetition/ts-fsrs: MIT, 808 stars, pushed 2026-10-03, latest release v5.4.2 (2026-09-01); supports ESM, CommonJS, UMD. — [GitHub ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs)
- open-spaced-repetition/py-fsrs: MIT, 504 stars, latest release v6.3.2 (2026-08-09). — [GitHub py-fsrs](https://github.com/open-spaced-repetition/py-fsrs)
- open-spaced-repetition/fsrs-rs: BSD-3-Clause, "FSRS for Rust, including Optimizer and Scheduler", latest v6.6.2 (2026-08-28). — [GitHub fsrs-rs](https://github.com/open-spaced-repetition/fsrs-rs)
- fsrs-browser: BSD-3-Clause, "FSRS for the browser, including Optimizer and Scheduler", pushed 2026-06. rs-fsrs (MIT) and dart-fsrs (MIT, last push 2025-06) also exist. — [GitHub fsrs-browser](https://github.com/open-spaced-repetition/fsrs-browser); [GitHub dart-fsrs](https://github.com/open-spaced-repetition/dart-fsrs)
- fsrs4anki: MIT, 4,092 stars, the FSRS scheduler integrated with Anki. — [GitHub fsrs4anki](https://github.com/open-spaced-repetition/fsrs4anki)
- Anki: "licensed under the GNU Affero General Public License, version 3 or later, with portions ... licensed under the BSD-3 license"; the logo is also AGPL3 with a limited alternative license for books/blogs/videos. — [Anki LICENSE](https://github.com/ankitects/anki/blob/main/LICENSE)
- AnkiConnect: GitHub repo archived; README says it "has permanently moved to https://git.sr.ht/~foosoft/anki-connect"; licensed GPL v3. — [GitHub FooSoft/anki-connect](https://github.com/FooSoft/anki-connect)
- genanki: MIT, "A Python 3 library for generating Anki decks", last push 2024-12-30. — [GitHub genanki](https://github.com/kerrickstaley/genanki)
- AnkiWeb direct access by third-party clients is prohibited by Anki's terms; AnkiConnect is the common route for external apps. — [Anki forums](https://forums.ankiweb.net/t/question-about-api-access-naming-anki-cards-in-external-app/66116)

### Inferences
- Minimal SRS flow (effort estimate, inference): data model = global `cards` + per-user `user_cards` (FSRS state: due, stability, difficulty, reps, lapses, state, last_review) + append-only `review_logs` (rating 1-4, timestamp, elapsed). UI = due queue -> show front -> reveal -> 4 buttons (Again/Hard/Good/Easy) -> `fsrs.next()` -> persist. With ts-fsrs in the client this is ~1-2 weeks for a working MVP, plus 1-2 weeks for new-card limits, daily caps, undo, stats and timezone/day-rollover edge cases.
- Keep review logs from day one: they enable per-user parameter optimization later (fsrs-rs / fsrs-browser optimizer) and export to Anki with history.
- Run the scheduler where reviews happen (client, offline). If the backend must recompute (e.g., Telegram-only reviews), py-fsrs and ts-fsrs implement the same algorithm; pin the same FSRS version on both sides.
- Anki export: keep two paths: (1) .apkg download generated server-side with genanki (MIT, no AGPL contamination since it does not include Anki code) for users who prefer Anki; (2) existing AnkiConnect sync for power users. Talking to AnkiConnect over HTTP does not make the product a derivative of GPL/AGPL code (inference; not legal advice).

### Gaps
- No benchmark comparison of library maturity beyond stars/release dates; FSRS algorithm version differences (FSRS-5 vs FSRS-6) across ports were not verified.
- genanki's last push is Dec 2024; compatibility with the newest Anki .apkg/.colpkg formats in 2026 was not verified.

---

## 4. Mobile stack for a solo dev and offline-first sync

### Takeaway
Given existing React/TS skills, the lowest-effort path is staged: keep the Telegram Mini App (now with DeviceStorage 5 MB, fullscreen and home-screen shortcuts) and add an SRS review screen there first; then ship an Expo/React Native app reusing TS domain code (ts-fsrs, API client, validation). Offline sync for a single-owner, append-mostly dataset (cards + review logs) does not need a CRDT or a sync vendor: simple per-row last-write-wins plus append-only review logs is enough; PowerSync (free up to 50 peak concurrent clients, Pro from $49/mo) is the off-the-shelf option if Postgres is adopted. Flutter or native Kotlin/Swift means rewriting UI and domain code in a new language.

### Cited Findings
- Telegram Mini Apps: CloudStorage "up to 1024 items per user", values "0-4096 characters"; DeviceStorage "up to 5 MB per user" persistent local storage; SecureStorage uses iOS Keychain / Android Keystore, "up to 10 items per user"; `addToHomeScreen()`; full-screen portrait and landscape. — [Telegram Mini Apps docs](https://core.telegram.org/bots/webapps)
- Latest Bot API version shown: "Bot API 10.3", dated August 24, 2026. — [Telegram Bot API](https://core.telegram.org/bots/api)
- Expo EAS: Free $0 (15 Android + 15 iOS builds, updates to 1K MAUs); Starter $19/month (3K MAUs); Production $199/month (50K MAUs). — [Expo pricing](https://expo.dev/pricing)
- PowerSync Cloud: Free $0 (2 GB synced/month, 500 MB hosted, 50 peak concurrent clients); Pro from $49/month (30 GB synced, 10 GB hosted, 1,000 peak concurrent clients); Team from $599/month; self-hosted "Open Edition" free, source-available. Backends: Postgres, MongoDB, MySQL, SQL Server; SDKs include React Native, Web, Flutter, Kotlin, Swift, Capacitor, Tauri. — [PowerSync pricing](https://www.powersync.com/pricing)
- ElectricSQL (now "Electric"): GA 1.0 in March 2025; reported acquired by Neon in August 2026 and repositioned toward AI-agent state; syncs partial Postgres replicas ("Shapes") via logical replication (read path). — [releases.sh digest (secondary)](https://releases.sh/collections/serverless-postgres/digest/2026-08-10); [Electric blog](https://electric-sql.com/blog)
- Apple 4.2: apps must offer more than "a repackaged website"; 4.7 allows HTML5 mini apps/chatbots inside apps under the guidelines. — [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)

### Inferences
Effort/trade-off table (inference for a solo dev already fluent in React/TS + FastAPI):

| Option | Effort to MVP with SRS | Pros | Cons |
|---|---|---|---|
| Telegram Mini App only | 2-4 weeks (add review UI + FSRS to existing app) | Zero install, Telegram auth for free, Stars payments, reuses code | No reliable offline, no push notifications outside bot messages, tied to Telegram ToS/ban risk, iOS/Android store reach lost |
| PWA | +1-2 weeks on top of Mini App | Same codebase, offline via service worker + IndexedDB | iOS PWA limits (storage eviction, weaker push UX), no store discovery, payments via web (Stripe etc.) |
| React Native / Expo | 6-10 weeks | Reuses TS, ts-fsrs, API client; expo-sqlite for offline; store presence; IAP | App Store review, IAP integration, Sign in with Apple, account deletion |
| Flutter | 10-16 weeks | Good performance, one codebase | New language (Dart); dart-fsrs less active (last push 2025-06) |
| Native Kotlin + Swift | 16+ weeks (two apps) | Best platform fit | Two codebases for a solo dev; worst effort ratio |

- Sync design that fits this domain: global cards are read-only reference data (download/caching); user state is (a) user_cards rows with `updated_at` LWW and (b) append-only review_logs with client-generated UUIDs (merge = union). FSRS state can be recomputed from the log if conflicts occur, so conflicts are not destructive. This is a few hundred lines of server + client code; CRDTs are unnecessary.
- PowerSync becomes attractive only after moving to Postgres and if >1 device per user with real-time sync matters; its free tier (50 peak concurrent) is too small for a public app, Pro $49/mo is a fixed cost to include in break-even.
- The Android companion should be folded into the Expo app rather than maintained separately.

### Gaps
- No primary source fetched for expo-sqlite capabilities or React Native IAP libraries (RevenueCat pricing not checked).
- iOS PWA storage/push limitations in 2026 were not verified with primary sources.

---

## 5. Monetization: freemium patterns, Telegram Stars, store commissions, price points, break-even

### Takeaway
Comparable flashcard/vocab apps price at roughly $3.5-10/month or $24-60/year, usually with a free tier that limits AI usage, synced devices or card counts. Per-user LLM+TTS cost (~$0.05-1.10/month for an active user on Flash-Lite-class models, less with a cache) is far below these prices, so margin is driven by store/Stars fees and fixed costs. Telegram mandates Stars for digital goods in bots/Mini Apps (developer receives ~$0.013 per Star, 21-day hold, payout via Fragment with KYC); Apple/Google take 15% for small developers (Google: 10% service + 5% billing in US/UK/EEA since 30 June 2026). Critical for a Russian-speaking audience: Apple stopped all App Store payments in Russia on 1 April 2026.

### Cited Findings
Telegram:
- "All payments via bots and mini apps for digital goods and services inside Telegram apps must exclusively use Telegram Stars"; refunds via `refundStarPayment`; developers must handle `/paysupport` and disputes. — [Telegram Stars payments](https://core.telegram.org/bots/payments-stars)
- Developer terms: "Developers can receive an equivalent of 0.013 USD worth of rewards for each Telegram Star"; Stars may not be available for rewards "for up to 21 days after their receipt"; rewards processing outsourced to Fragment (Fragment Corp.). A 15% fee applies to the Topics feature (6.2.6), not to general bot sales. — [Telegram Bot Platform Developer Terms](https://telegram.org/tos/bot-developers)
- Stars subscriptions: `subscription_period` must be 2592000 (30 days), currency XTR, price not more than 10,000 Stars. — [telegram.js CreateInvoiceLinkParams (mirror of Bot API)](https://telegram.js.org/docs/types/CreateInvoiceLinkParams/)
- Fragment requires KYC via Sumsub (ID scan + face scan) since Nov 2024; TON withdrawals require KYC, 2FA active for at least a week. Russian channel owners were reported (May-July 2026) to be able to withdraw ad rewards in TON via Fragment, with caveats. — [kod.ru](https://kod.ru/kyc-na-fragment); [anti-malware.ru](https://www.anti-malware.ru/news/2026-05-14-111332/50026)
- Russian users' Stars purchases: after 1 April 2026 mobile-operator top-ups stopped and App Store purchase became unavailable for some users; third-party reseller sites/bots accepting Russian cards/SBP are described as the de facto route (low-reliability SEO blog sources). — [vc.ru](https://vc.ru/life/2956296-kak-kupit-telegram-stars-v-rossii)

App stores:
- Apple Small Business Program: 15% commission for developers with up to $1M proceeds in the prior calendar year (and new developers); 10% for EU alternative terms in the program and for subscriptions after first year. — [Apple Small Business Program](https://developer.apple.com/app-store/small-business-program/)
- Apple 3.1.1: unlocking features/subscriptions in-app "must use in-app purchase"; 3.1.3(b) multiplatform services may let users access content bought on other platforms or the web. — [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- Google Play from 30 June 2026 (US, UK, EEA): service fee "10% + billing fee, if applicable" on first $1M and on subscriptions; billing fee 5% when using Play Billing; alternative billing/external links allowed with the same service fee. — [Google Play Console Help](https://support.google.com/googleplay/android-developer/answer/16954621)
- Elsewhere Google Play: 15% on first $1M per year, 15% on auto-renewing subscriptions regardless of revenue. — [Google Play service fees](https://support.google.com/googleplay/android-developer/answer/112622?hl=en)
- Apple stopped processing all App Store payments in Russia as of 1 April 2026; existing subscriptions will not renew unless the user has Apple Account balance. — [RevenueCat](https://www.revenuecat.com/blog/growth/russia-app-store-payment-block); [MacTrast](https://www.mactrast.com/2026/04/apple-turns-off-app-store-and-services-payments-in-russia/)

Comparable pricing / freemium patterns:
- Mochi: Free (unlimited cards, offline) vs Pro $5/month billed annually (sync, AI); Free AI completion 5,000 tokens/month vs Pro 500,000; TTS 200 vs 200,000 characters; dictionary 20 vs 1,000 lookups per month. — [Mochi pricing](https://mochi.cards/pricing/)
- Repetico $3.49/month or $23.49/year (free: 2 sets x 200 cards, ads); Quizlet Plus $7.99/month or $35.99/year; Flashcards Maker AI $9.99/month or $39.99/year; InstaDeck $59.99/year with 5 lifetime AI deck generations free; DuoCards free tier 20 added cards. — [mindomax.com (aggregator)](https://www.mindomax.com/best-flashcard-apps); [studycardsai.com (aggregator)](https://studycardsai.com/best-flashcard-apps-2026)

### Inferences
Net revenue per paying user per month (my arithmetic):
- $4.99/mo via App Store/Google Play at 15%: ~$4.24 net (before VAT handling by stores).
- Telegram Stars subscription priced at 300 Stars/30 days: 300 x $0.013 = $3.90 to developer (after 21-day hold, via Fragment KYC, paid in TON so FX/crypto risk applies). 400 Stars = $5.20.
- Web (Stripe-type) checkout for multiplatform access (3.1.3(b)) avoids store fees but card processing fees apply (not researched).

Suggested freemium shape (inference, aligned to cost table): free = N AI cards/day (e.g., 3-5/day, ~$0.05-0.27/month uncached on 3.5 Flash-Lite, near zero for cache hits) + unlimited reviews of own cards + Anki export; paid = higher/unlimited AI cards (fair-use cap e.g. 50/day), audio, multi-device sync, stats/FSRS optimizer. Gate generation, never reviews (reviews cost nothing server-side).

Break-even sketch (inference; fixed costs are assumptions, not sourced): fixed ~$30-80/month (VPS + backups/object storage ~$10-30, Apple developer fee ~$8/mo amortized, PowerSync Pro $49 only if used, Expo free tier). Variable LLM for a paying heavy user (20/day) ~$1.08 on 3.5 Flash-Lite uncached, ~$0.20 with 80% cache. Free users at 5/day cost ~$0.27 uncached / ~$0.05 cached. Break-even payers ~= (fixed + free_users x free_cost) / (net_price - paid_cost). Example: $60 fixed + 2,000 free users x $0.05 = $160 -> /($4.24 - $0.20) = ~40 paying users. Without a cache and on 3.5 Flash-Lite: $60 + 2,000 x $0.27 = $600 -> /($4.24 - $1.08) = ~190 payers. The cache and model choice, not infrastructure, decide break-even.

Russia-specific: iOS IAP is unusable for Russian accounts after April 2026; Telegram Stars are the only in-Telegram option but Russian buyers rely on gray resellers and the developer's payout goes through Fragment KYC in TON. A Russian-audience product likely needs a domestic payment provider and RuStore for Android (not researched here) — significant legal/financial complexity.

### Gaps
- Retail price users pay for Stars (via Apple/Google or Fragment) was not obtained from a primary source; the payments-stars page shows it only as an image.
- Freemium conversion rates for vocab/SRS apps not found; break-even uses illustrative free:paid ratios.
- RuStore commission, Russian payment providers (YooKassa, CloudPayments) fees and self-employed (НПД) taxation not researched.
- Whether Telegram Stars subscriptions can be bought by iOS users inside Telegram given Apple's Russian payment block was not established.

---

## 6. Multi-user engineering requirements: auth, abuse/LLM cost control, prompt injection, moderation, backups, SQLite vs Postgres

### Takeaway
The minimal multi-user delta is: validated Telegram initData auth (HMAC with bot token) plus, for native apps, an account system that satisfies Apple 4.8 (offer Sign in with Apple if Telegram/Google login is used) and in-app account deletion; per-user and global LLM budgets; strict JSON-schema output validation (already present) as the main prompt-injection control; and continuous off-site SQLite backups (Litestream 0.5.x) or a move to Postgres when multi-device sync/PowerSync is adopted. SQLite with WAL is sufficient for thousands of users of a write-light card app.

### Cited Findings
- Telegram Mini App auth: validate initData by comparing the hash with an "HMAC-SHA256" signature of the data-check-string using the bot token; third parties can verify with "Ed25519" and Telegram's public key. — [Telegram Mini Apps docs](https://core.telegram.org/bots/webapps)
- Apple 4.8: apps using third-party/social login (Google, Facebook, X, etc.) for the primary account "must also offer as an equivalent option another login service" that limits data to name+email, allows hiding email, and does not track for ads; exempt if the app "exclusively uses your company's own account setup and sign-in systems". — [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- Apple 5.1.1(v): "If your app supports account creation, you must also offer account deletion within the app." — [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- Apple 1.2 UGC: filtering objectionable material, reporting mechanism with timely response, blocking abusive users, published contact info. — [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- OWASP LLM01 Prompt Injection mitigations: constrain model behavior in the system prompt; define output formats validated "through deterministic code"; input/output filtering; least privilege; human approval for high-risk actions; segregate untrusted content; adversarial testing; complete prevention "remains uncertain". — [OWASP GenAI LLM01](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- Telegram developer terms prohibit data collection to build "large datasets, machine learning models and AI products", and require explicit, revocable consent for data use beyond essential operations. — [Telegram Bot Platform Developer Terms](https://telegram.org/tos/bot-developers)
- Litestream 0.5 released (Oct 2025) with a new architecture (LTX files, CGO-free builds); 0.5.1/0.5.2 fixed retention and recovery issues; a user advised waiting for stabilization before production. Ben Johnson moved away from FUSE-based LiteFS in favor of single-binary Litestream. — [Simon Willison](https://simonwillison.net/2025/Oct/3/litestream); [x-cmd blog](https://www.x-cmd.com/blog/251016); [feedbagel](https://feedbagel.com/post/litestream-050-release-user-advises-caution-before-production-deployment)
- PowerSync's supported backends are Postgres, MongoDB, MySQL, SQL Server (not SQLite as the server DB). — [PowerSync pricing](https://www.powersync.com/pricing)

### Inferences
Minimal checklist (inference):
- Auth: Telegram initData validation for the Mini App (replace the single `TELEGRAM_ALLOWED_USER_ID` gate); for native apps either own email/magic-link accounts (exempt from 4.8) or Telegram/Google login + Sign in with Apple. Account linking Telegram <-> app account via one-time code from the bot.
- Data model: add `users`; split global `cards` (shared dictionary) from per-user `user_cards` + `review_logs`; scope every API query by user_id; replace the single bearer `ANKI_SYNC_TOKEN` with per-user tokens.
- Cost/abuse controls: per-user daily quota (free vs paid), existing 5 req/min limiter generalized per user, global daily spend cap with kill switch, cap max_tokens on the LLM call, cache rejected inputs, block bulk import abuse (batch import is a cost multiplier), detect multi-account farming (Telegram account age is not available; rely on quotas).
- Prompt injection: the attack surface is small (1-8 tokens, no tools, no secrets in context, output parsed with Pydantic and rejected if invalid). Remaining risk is content: users can steer the model to put offensive/promotional text into explanation/examples. If cards enter a shared global cache, one user's poisoned output can reach others -> generate global cards from the normalized canonical form only (not raw user text), validate languages/lengths, and run a cheap moderation pass (or a moderation model like gpt-oss-safeguard, listed on OpenRouter) before promoting a card to the global cache.
- Moderation: if users can share decks publicly, Apple 1.2 UGC rules (report/block/filter/contact) apply; keeping cards private avoids most of this.
- Storage: stay on SQLite (WAL, single writer) for the first thousands of users; add Litestream to S3-compatible storage + daily snapshot; move to Postgres when (a) running more than one app instance, (b) adopting PowerSync/Electric, or (c) needing concurrent heavy writes. SQLAlchemy 2 + Alembic already in place makes the migration mechanical.
- Privacy by design: store only Telegram user id, language, cards, review logs; do not log raw prompts with user identifiers to third parties; choose LLM providers/routes with zero data retention where possible (OpenRouter provider settings — not verified here).

### Gaps
- OpenRouter per-key spend limits and zero-data-retention routing were not verified in this pass.
- No measured SQLite write-throughput numbers for this workload were researched.
- Apple's stance on Telegram Login specifically (whether it counts as "third-party login" for 4.8) is not explicitly addressed in the guidelines; treated as third-party by inference.

---

## 7. Legal/compliance basics: privacy policy, GDPR, 152-FZ, app-store AI rules, Anki licensing and trademark, EU AI Act

### Takeaway
Minimum for a public launch: a privacy policy (mandatory under Telegram developer terms and both stores), disclosure plus explicit consent before sending personal data to third-party AI (Apple 5.1.2(i)), in-app account deletion, GDPR basics (lawful basis, DPA with LLM/TTS processors, likely an Art. 27 EU representative if serving EU users from outside the EU). Targeting Russians from Russia triggers 152-FZ: Roskomnadzor notification and, since 1 July 2025, a ban on primary collection of Russian citizens' data in foreign databases, with sharply higher fines since 30 May 2025 — this conflicts with hosting on a foreign VPS and using foreign LLM APIs and needs real legal advice. Do not use "Anki" in the product name (registered trademark; Anki developers ask competitors to rename); a disclaimer like "Anki is a registered trademark of Ankitects; not affiliated" is acceptable when referencing compatibility.

### Cited Findings
Privacy / platforms:
- Telegram: "all TPA must be bound by a privacy policy that is easily accessible to their users, detailing what data they store, how they collect it, and for what purpose"; a Standard Policy applies by default if none is provided. Violations can lead to a "temporary or permanent ban from Bot Platform" without compensation. — [Telegram Bot Platform Developer Terms](https://telegram.org/tos/bot-developers)
- Apple 5.1.2(i): "You must clearly disclose where personal data will be shared with third parties, including with third-party AI, and obtain explicit permission before doing so." — [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- GDPR Art. 27: non-EU controllers offering services to EU users must appoint an EU representative unless processing is "occasional"; continuous app processing is unlikely to qualify; "being small is not the test". — [GDPRLocal](https://gdprlocal.com/gdpr-article-27-gdpr-exemptions/)
- EU AI Act Art. 50 transparency obligations apply from 2 August 2026 (chatbot disclosure; machine-readable marking of synthetic text/audio by providers); under the Digital Omnibus, Art. 50(2) applies from 2 December 2026 for systems placed on the market before 2 August 2026; fines up to EUR 15M or 3% turnover. — [Cooley](https://www.cooley.com/news/insight/2026/2026-08-03-eu-ai-act-transparency-obligations-take-effect-2-august-2026)

Russia (152-FZ):
- From 1 July 2025 the localization ban applies to the primary collection of personal data using databases located abroad (not just storage), and extends to processors acting on the operator's behalf (Law 23-FZ, Feb 2025). — [Sber Business Live](https://sberbusiness.live/publications/sbor-dannih-cherez-inostrannie-servisi-i-otkaz-ot-uproschenki-zakoni-dlya-biznesa-v-iyule); [Stonebridge Legal alert (PDF)](https://www.stonebridgelegal.ru/media/files/Alert_Izmenenie-pravil-lokalizacii-dannyh.pdf)
- Since 30 May 2025 KoAP fines rose sharply; failing to notify Roskomnadzor about processing: up to 300,000 RUB for legal entities; failing to report a leak within 24 hours: up to 3M RUB; repeat leaks: turnover fines 1-3% of revenue up to 500M RUB. All operators must notify Roskomnadzor (Art. 22), and the notification duty extends to self-employed; individual entrepreneurs bear liability like legal entities. — [Habr](https://habr.com/ru/post/925642); [Infostart](https://infostart.ru/public/2526813/)
- Localization violation (KoAP 13.11 part 8): a secondary summary claims maximum fines for legal entities of 15M RUB first offense and up to 500M RUB repeat (unverified against statute text). — [vitvet.com (secondary)](https://vitvet.com/articles/koap/spravochnik/faq-shtrafy-152-fz-personalnye-dannye/)

Anki licensing and trademark:
- Anki is AGPL-3.0-or-later (with BSD-3 portions); logo AGPL3. — [Anki LICENSE](https://github.com/ankitects/anki/blob/main/LICENSE)
- dae (Anki developer), 1 Sept 2025: "After a multi-year process, Anki has been registered as a trademark in a number of countries, and the copycats have had to rename"; approved a third-party disclaimer approach; direct AnkiWeb access by third parties is prohibited by Anki's terms. — [Anki forums](https://forums.ankiweb.net/t/question-about-api-access-naming-anki-cards-in-external-app/66116)
- Common practice: for-profit/competing apps exclude "Anki" from their name; Anki Pro was built despite being asked not to use the name. — [mindomax.com (secondary)](https://www.mindomax.com/anki-pro-vs-anki)
- AnkiConnect is GPL-3 and now hosted at sourcehut. — [GitHub FooSoft/anki-connect](https://github.com/FooSoft/anki-connect)

### Inferences
Minimal legal checklist (inference, not legal advice):
1. Rename the product: drop "anki" from bot username, app name and domain (the current repo name "anki-vocab-bot" would be risky as a public brand); describe compatibility as "exports to Anki(R)" with a non-affiliation disclaimer.
2. Privacy policy + terms of service (Telegram, App Store, Play all require one); list processors: OpenRouter/LLM provider, TTS provider, hosting, payment processor; state retention and deletion.
3. Explicit consent screen before first AI generation in the native app (Apple 5.1.2(i)); disclose that cards are AI-generated (also aligns with EU AI Act Art. 50 spirit; formal Art. 50(2) marking duty sits mainly with the model provider, but deployer disclosure is cheap).
4. In-app account deletion and data export.
5. GDPR: lawful basis = contract; DPAs with processors; EU representative (paid service) if actively marketing to EU users; cookie/analytics consent if web.
6. Russia: if the operator (the developer) is in Russia or targets Russian users, Roskomnadzor notification + primary database in Russia; sending Russian users' data (even just Telegram IDs and words) to foreign LLM APIs is cross-border transfer requiring separate analysis/notification. The lowest-risk technical design is data minimization: send only the word/phrase (no user identifiers) to the LLM, which arguably is not personal data. Get a Russian lawyer's review before monetizing Russian users.
7. AGPL hygiene: do not copy Anki source into the product; use genanki (MIT) for .apkg; keep AnkiConnect as a user-installed add-on.
8. App Store AI content: no specific rule bans AI-generated study content; 1.2 UGC rules apply only if user content is shared with other users.

### Gaps
- Exact KoAP 13.11 part 8 fine amounts and whether a Telegram user ID alone counts as personal data under 152-FZ were not verified from primary sources.
- Whether a Russian individual (no IP/self-employed status) can lawfully receive Stars/Fragment payouts and how they are taxed was not researched.
- Cost of EU representative services and template privacy policies not researched.
- Google Play-specific AI-generated content policy (Generative AI apps policy: in-app reporting of offensive AI output) was not fetched in this pass.
