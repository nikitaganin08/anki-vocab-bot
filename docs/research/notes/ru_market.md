# Russian-speaking market for English vocabulary apps and Telegram learning tools (as of October 2026)

Scope: Russia plus CIS/diaspora. Product evaluated: a Telegram bot + Mini App that turns a word, phrasal verb, idiom or collocation (ru/en, 1-8 tokens) into an LLM-generated card (canonical English form, IPA, 2-3 Russian translations, English explanation, 3 examples, frequency, word family), stored and synced to Anki. Options under consideration: (a) go public, (b) build a mobile app with built-in SRS instead of Anki.

Research date: 2026-10-07. About 55 search/fetch calls. Dates are given for anything older than 2026.

## 1. Key players and their current state

### Takeaway
The incumbents are old (Lingualeo, Easy Ten, ReWord, EnglishDom ED Words) or are large schools that use vocabulary features to support paid tutoring (Skyeng, Yandex Practicum). None of the incumbents I checked offers "send any phrase and get an LLM-generated card with explanation and examples" as a standalone personal-dictionary product. Yandex has the closest AI pieces (Alice chat in Translate; an AI translator inside Practicum courses that gives transcription, meanings and examples), but they are not built around personal vocabulary or SRS. Only Skyeng publishes revenue: 12.7 bn RUB in 2025, growing slowly.

### Cited Findings

**Skyeng**
- Skyeng ranked #3 among Russian EdTech companies in 2025 with 12.7 bn RUB revenue, +5.2% YoY. It is the only language company in the Smart Ranking top 10 (published 2026-02-06). — [Skillbox Media / Smart Ranking](https://skillbox.ru/media/edtech/v-2025-godu-rossiyskiy-edtech-vyros-vsego-na-12/)
- In Q3 2024 Skyeng had 3.5 bn RUB revenue (+8.06%) and lost its market-leader position (2024-11-01). — [Kommersant](https://www.kommersant.ru/doc/7268167)
- The Skyeng app lets users add words to a personal dictionary and drill them in a trainer. It is free for Skyeng students; other users get a 2-week trial and in-app purchases. Exact standalone prices were not found. — [Skyeng magazine](https://skyeng.ru/magazine/mozhno-li-vyuchit-anglijskij-v-telefone-korotkij-otvet-da/), [App Store RU](https://apps.apple.com/ru/app/skyeng-%D0%B0%D0%BD%D0%B3%D0%BB%D0%B8%D0%B9%D1%81%D0%BA%D0%B8%D0%B9-%D1%8F%D0%B7%D1%8B%D0%BA-%D1%81-%D0%BD%D1%83%D0%BB%D1%8F/id1065290732?l=ru)

**Lingualeo**
- App Store RU listing: rating 4.5 from about 19,000 ratings. In-app prices: 499 RUB per month, 790 RUB per month Premium, 2,990 RUB per 12 months (4,190 RUB per 12 months shown with a "30% discount"), 4,490 RUB per 12 months Premium. Features: personal dictionary with instant word saving, adaptive repetition, an AI chatbot "Leo-chat" for dialogue practice, grammar videos, LeoNews, gamification. The fetched page showed v5.3.38 (2024-09-18) as the latest update. This may be a stale cache, but it may also mean the iOS app has not been updated recently. — [App Store RU](https://apps.apple.com/ru/app/480952151)
- A Skillbox review quotes 749 RUB per month for the subscription (date unclear; this conflicts with 499 RUB on the App Store). — [Skillbox Media](https://skillbox.ru/media/growth/apps-for-learning-english/)
- The listing claims more than 23 million users worldwide. Lingualeo does not disclose revenue; the last public estimate was about $5M for 2013. — [ruwiki / CB Insights via search](https://ru.ruwiki.ru/wiki/LinguaLeo)
- Complaints about Lingualeo: prices at checkout differing from those displayed, course-progress bugs, YouTube-based content breaking in Russia, an outdated interface and poor audio, and slow email support. — [a2is.ru reviews](https://a2is.ru/catalog/samoobuchenie/lingualeo/reviews-lingualeo), [otzovik](https://otzovik.com/review_233764.html)

**ReWord (developer Valeriy Streltsov)**
- RuStore listing: 100,000+ downloads, rating 4.8 (about 1,100 ratings, 211 reviews), latest version 4.3.4 on 2026-08-17. Freemium: 5 new words per day for free, unlimited review, a paid "Full Version" (RUB price not shown). Features: SRS; 50+ categories; Oxford 3000/5000 and GSL lists; custom cards with automatic translation, transcription and images; native-speaker audio; offline mode; streaks. — [RuStore](https://rustore.ru/catalog/app/ru.poas.englishwords)
- A RuStore review says the app "lacks explanations for word usage context" and that the execution does not justify the price. — [RuStore](https://rustore.ru/catalog/app/ru.poas.englishwords)

**Easy Ten ("10 words a day")**
- The App Store RU listing claims more than 1,500,000 users. The app supports EN/DE/FR/ES/IT/PT and has an auto-renewing premium subscription. — [App Store RU](https://apps.apple.com/ru/app/582671477), [iPhones.ru (old review)](https://www.iphones.ru/iNotes/303294)

**"Английский язык с Words" (EngWordsLab; a different app from Easy Ten)**
- RuStore listing: 1,000+ downloads, rating 4.8 (49 ratings), last update 2026-09-01. Features: SRS, custom words, 11,000+ illustrated words A1-C2, 7 exercise types. Users describe the subscription price as very low. — [RuStore](https://www.rustore.ru/catalog/app/com.nltsm.words)

**EnglishDom (ED Words)**
- ED Words is sold by Virtual Mentor, Inc. App Store US listing: rating 4.4 (83 ratings), prices $5.99 per month, $9.99 per 3 months, $24.99 per year, last update 2025-01-18 (v4.2.2). It uses Ebbinghaus-based SRS and lets users make their own sets alongside 350 themed collections. The listing is now mainly aimed at Ukrainian speakers; the AI tutor is a separate app, "Charlie AI". — [App Store](https://apps.apple.com/us/app/-/id1282915927)

**Yandex**
- Yandex Translate added an "Alice" AI chat for English learners on 2025-06-19. It explains translation choices, tenses, idioms, slang and abbreviations. It is a free beta with request limits and requires a Yandex ID. — [Habr news](https://habr.com/en/news/919886)
- Yandex Translate already had "collections" (подборки): users save words and phrases in 95 languages and study them as cards. — [Yandex support](https://yandex.com/support/translate-mobile/ru/collections), [Rozetked](https://rozetked.me/news/3067-podborki-slov-v-yandeks-perevodchike-pomogut-uchit-yazyki)
- On 2025-05-20 Yandex Practicum added a YandexGPT-based AI translator to its English courses. It gives context-aware translations, transcriptions, extra meanings, usage examples, explanations of phrasal verbs and idioms, and English definitions. It works only inside Practicum lessons. — [Habr / Yandex Practicum](https://habr.com/ru/companies/yandex_praktikum/news/910740)
- Yandex Practicum had 8.8 bn RUB revenue in 2025 (+6.7%) across all subjects. — [Skillbox / Smart Ranking](https://skillbox.ru/media/edtech/v-2025-godu-rossiyskiy-edtech-vyros-vsego-na-12/)

**Duolingo in Russia**
- After a Roskomnadzor investigation for "LGBT propaganda" (a fine of up to 4M RUB or a ban was possible), Duolingo removed LGBT references from its Russian version. — [NBC News](https://www.nbcnews.com/nbc-out/out-news/duolingo-deletes-lgbt-references-russia-warning-moscow-rcna155590), [The Record](https://therecord.media/language-app-duolingo-lgbtq-removes)
- I found no Russia-specific Duolingo user or download numbers. — (searched; see Gaps)

**Small and new entrants (RuStore)**
- "Лексора" by Lexora English School was released 2026-05-15. It has up to 1,000 downloads, a 5.0 rating from 11 ratings, is free with no ads, and works offline. It covers 5,000 words and 1,000 grammar exercises. — [RuStore](https://www.rustore.ru/catalog/app/ru.lexora.app)

### Inferences
- The space is crowded with list-based vocabulary trainers (curated word lists plus SRS) priced at roughly 300-800 RUB per month. The product's differentiator is the reverse workflow: the user captures their own word or idiom, and an LLM builds a rich card with explanation, examples and frequency. ReWord's complaint about missing usage context supports that this matters.
- Yandex is the biggest strategic risk. It already has the LLM (YandexGPT/Alice), a word-collection feature in Translate and an AI explainer in Practicum. Combining them into an "AI personal dictionary" would be a small step for Yandex.
- Lingualeo was the original "personal dictionary + word capture" product in Russia. Its old interface and billing complaints leave room for a modern AI-first replacement.

### Gaps
- No current RUB prices for Puzzle English, Easy Ten, Skyeng standalone, or ReWord full version (the Puzzle English site could not be fetched because of redirects).
- No Google Play download counts were collected; RuStore was checked for some apps. The Lingualeo RuStore page returned HTTP 429.
- Memrise and Englex in Russia: no data found.
- No revenue or user numbers for Lingualeo, Puzzle English, EnglishDom or Englex in 2024-2026; they do not appear in the public Smart Ranking top-10 excerpts.

## 2. Telegram as a channel (bots, Mini Apps, audience, blocking risk)

### Takeaway
Telegram was the largest messenger in Russia in early 2026, at about 96M monthly users. Since February 2026, however, it has been officially throttled by Roskomnadzor and has reportedly reached a near-blocked state on many networks (OONI recorded about 95% anomalies in April 2026). In Russia it increasingly works only through VPN, while the state messenger Max is growing. English-learning bots and Mini Apps exist, but those I found are small indie projects without public traction numbers. Telegram is risky as the only channel for users inside Russia, and much safer for CIS and diaspora users.

### Cited Findings

**Audience**
- Mediascope monthly reach in Russia (users aged 12+): Telegram had 93.6M in December 2025, 95.98M in January 2026 and 95.69M in February 2026. WhatsApp had 94.5M, 89.4M and 80.3M. Max had 73.7M in January 2026 and 77.6M in February 2026. — [kod.ru (Mediascope)](https://kod.ru/telegram-oboshel-whatsapp-v-russia)
- Reuters (July 2025) reported 90.8M Telegram users in Russia, cited in a Habr article. — [Habr](https://habr.com/en/articles/1003196)

**Restrictions timeline**
- Telegram and WhatsApp calls were restricted from August 2025, WhatsApp blocking started in late November 2025, and the Telegram slowdown started on 2026-02-10. — [kod.ru](https://kod.ru/telegram-oboshel-whatsapp-v-russia), [RBC 2026-02-10](https://www.rbc.ru/technology_and_media/10/02/2026/698afe729a79470c08a17b91)
- Russian Wikipedia's timeline:
  - Blocking in Chechnya and Dagestan.
  - Official nationwide slowdown confirmed 2026-02-10, affecting media, voice messages and video.
  - A 35M RUB fine on 2026-03-16.
  - OONI blocking anomalies at about 95% by 2026-04-10.
  - Durov's claim (April 2026) that about 65M Russians still use Telegram daily via VPN.
  - A report that Durov was put on a wanted list on 2026-06-29.
  - Peskov encouraging people to use Max.
  
  I did not verify the Wikipedia claims independently. — [ru.wikipedia](https://ru.wikipedia.org/wiki/%D0%91%D0%BB%D0%BE%D0%BA%D0%B8%D1%80%D0%BE%D0%B2%D0%BA%D0%B0_Telegram_%D0%B2_%D0%A0%D0%BE%D1%81%D1%81%D0%B8%D0%B8_(2026))
- On 2026-07-26 there was a mass Telegram outage, which Roskomnadzor called part of "sequential measures". — [techora.ru](https://techora.ru/news/massovyy-sboy-telegram-v-rossii-roskomnadzor-2026-07-26)
- As of 2026-10-06, users in many regions (especially southern Russia) still report Telegram malfunctions. Roskomnadzor has not announced a date for a full block, and DPI filtering makes Telegram unreachable on most networks without extra tools. — [Mail.ru Hi-Tech](https://hi-tech.mail.ru/news/145611-chto-segodnya-s-telegram/), [Bitrix24 journal](https://www.bitrix24.ru/journal/blokirovka-telegram/)
- A Duma deputy speculated about a full block by September 2026; colleagues rejected this as speculation (January 2026). — [ppc.world](https://ppc.world/news/deputat-delyagin-dopustil-blokirovku-telegram-v-rossii-k-sentyabryu-2026-goda/), [amic.ru](https://www.amic.ru/news/v-gosdume-oprovergli-blokirovku-telegram-k-sentyabryu-2026-goda-576881)

**Existing English-learning bots and Mini Apps**
- Crazy Llama English is a Telegram Mini App launched 2025-04-30 by a solo developer after 1.5 years of work. It has 20,000 curated words, AI hints via the DeepSeek API, energy purchases with Stars, and NFT avatars on TON. The developer said in May 2025 that "there are not many users yet". — [T-Zh dev story](https://t-j.ru/dev-story-telegram-prilozhenie-dlia-izucheniia-angliiskogo/), [vc.ru](https://vc.ru/life/1985874-sozdanie-telegram-prilozheniya-dlya-izucheniya-angliyskogo-yazyka)
- StudyWords is a Telegram SRS bot for vocabulary; a Habr sandbox article lists desired features such as cross-device sync, word adding from any device, import/export, Telegram reminders and statistics. — [Habr sandbox](https://habr.com/ru/sandbox/276362)
- Several Habr authors have built personal Telegram vocabulary/Anki bots with aiogram, mostly as pet projects. — [Habr](https://habr.com/ru/post/471196), [Habr](https://habr.com/ru/articles/345864), [Tproger](https://tproger.ru/articles/pet-proekt-spasaet-ot-vygoraniya-i-kachaet-mozg)

**Monetization through Telegram**
- Stars (2024 data):
  - In Russia, Stars could be bought via @PremiumBot for about 1.76-2.08 RUB per Star, or via the App Store for about 2.26-2.40 RUB per Star. Google Play purchase was not available in Russia.
  - Developers can withdraw 21 days after receipt, via Fragment, converted to Toncoin at $0.013 per Star. Stars spent on Telegram ads count as $0.02.
  - About 65% of the user's payment reaches the developer after store fees and taxes.
  
  — [kod.ru (2024-06-11)](https://kod.ru/telegram-stars-razbor)
- Stars are mandatory for digital goods in bots and Mini Apps (Apple/Google policy compliance), and Telegram has subscription APIs for Star subscriptions. — [Telegram Stars ToS](https://telegram.org/tos/stars), [merge.rocks guide](https://merge.rocks/blog/telegram-mini-apps-2026-monetization-guide-how-to-earn-from-telegram-mini-apps)
- From May 2026, Russian channel owners can withdraw TON ad revenue via Fragment. This requires KYC through Sumsub, and only impressions outside Russia, Belarus, Ukraine and a few other countries count. — [anti-malware.ru (2026-05-14)](https://www.anti-malware.ru/news/2026-05-14-111332/50026)
- Marketing sources (exitbid.io, adsgram) claim that Stars-enabled bots convert 3-6x better than bots with external payment links and that Stars processed more than $500M. These are low-quality, unverified sources. — [exitbid.io](https://exitbid.io/blog/telegram-stars-bot-exits-2026), [adsgram](https://adsgram.ai/blog/adsgram/monetizing-a-telegram-bot)

### Inferences
- For a Russia-first launch, a Telegram-only product depends on users having VPN access. Durov's claim that about 65M people still use it daily suggests a large audience still reaches Telegram, but acquisition and reliability inside Russia are degraded, and further restrictions are plausible. A web version, a native app, or a Max bot fallback would reduce the risk.
- Stars are an awkward rail for a Russian resident developer. The payout is in TON via Fragment with KYC, the developer keeps about 50-65% of what the user pays, and turning crypto into rubles has legal and tax friction. This suits small tips or "energy" packs more than a main subscription business.
- No English-vocabulary bot found has proven traction. The niche looks open, but also unproven as a business.

### Gaps
- No tgstat or catalog figures (users, MAU) for specific English-learning bots or Mini Apps were found; this could not be verified with the tools available.
- Telegram audience figures for Kazakhstan, Uzbekistan, Belarus and other CIS countries were not collected.
- Whether Mini Apps and bot webhooks are specifically disrupted by the throttling (as opposed to media) was not confirmed.

## 3. Payment and distribution constraints for a Russian developer (2025-2026)

### Takeaway
Both global app stores are effectively closed to Russian-resident monetization. Google Play has blocked all payments to Russian developers since 2024-12-26. Apple stopped processing payments in Russia on 2026-04-01; purchases now work only from a pre-funded Apple ID balance. Paid distribution therefore runs through RuStore (Android) and direct web or Telegram payments via Russian processors (YooKassa and others), with self-employed (самозанятый) or sole-proprietor (ИП) registration. The personal data law 152-FZ became considerably stricter in 2025: data must first be collected and recorded in Russia, and fines are much higher.

### Cited Findings

**Google Play**
- Since May 2022, Russian developers cannot upload or update paid apps. From 2024-12-26, Google Play rejects all purchases, in-app purchases and subscription renewals for developers with Russian bank accounts; the final payout was 2025-01-15 and the suspension is "indefinite". — [3DNews](https://3dnews.ru/1115389/google-play-zapretit-monetizatsiyu-prilogeniy-rossiyskih-razrabotchikov), [RuStore blog](https://www.rustore.ru/developer/blog/google-play-prekrashhaet-rabotu-s-rossijskimi-razrabotchikami-chto-nuzhno-znat)

**Apple App Store**
- From 2026-04-01, Apple stopped processing payments for purchases and subscriptions in Russia (App Store, in-app, Apple Music, iCloud+ and other services). New or renewed subscriptions work only from a positive Apple ID balance. Existing apps still update and free apps remain available. — [iPhones.ru](https://www.iphones.ru/iNotes/apple-prokommentirovala-blokirovku-oplaty-v-rossii-est-horoshaya-novost)
- Russian developers have been unable to publish paid apps or use built-in monetization since summer 2023 (sanctions). Apple also revised payout calculations after Russia raised VAT from 20% to 22%. — [Habr / vc.ru search summary](https://habr.com/ru/articles/991298)

**RuStore**
- Mediascope: average monthly audience of 68M users in Q1 2025. Another report gives about 50M users (December 2024) versus about 80M for Google Play in Russia. RuStore has about 110k apps. — [kod.ru (Mediascope)](https://kod.ru/rustore-rating-mediascope), [3DNews (2025-01-21)](https://3dnews.ru/1117039/rustore-stal-vtorim-po-populyarnosti-magazinom-tsifrovogo-kontenta-dlya-androidustroystv-v-rossii)
- RuStore cut its commission from 15% to 3.35% for Russian developers on the first 1M RUB of turnover per product (March 2023; I did not find a 2026 update). — [Habr news](https://habr.com/ru/news/724374)
- In November 2024 the Duma passed in first reading a bill requiring RuStore to be preinstalled on devices. — [3DNews](https://3dnews.ru/1117039/rustore-stal-vtorim-po-populyarnosti-magazinom-tsifrovogo-kontenta-dlya-androidustroystv-v-rossii)

**Payment processors and legal form**
- YooKassa accepts payments for ИП and самозанятые: cards, SBP, SberPay, ЮMoney, T-Pay. — [Cleverence](https://www.cleverence.ru/articles/elektronnaya-kommertsiya/-yukassa-dlya-ip-i-samozanyatyh-podklyuchenie/), [Yandex Pay blog](https://pay.yandex.ru/blog/articles/priem-platezhej-dlya-samozanyatyh)
- Self-employed status has an income cap of 2.4M RUB per year. — [vc.ru](https://vc.ru/id5293162/2803353-limit-dokhoda-2-4-mln-rubley-dlya-samozanyatykh), [Robokassa](https://robokassa.com/blog/articles/vozmozhnosti-i-ogranicheniya-dlya-vedeniya-biznesa-so-statusom-samozanyatyy/)

**Personal data (152-FZ)**
- Collection, recording, systematization, accumulation, storage, clarification and retrieval of Russian citizens' personal data must be done on servers in Russia. Data first landing on a foreign server through a site, app or form is a violation. — [Habr](https://habr.com/ru/articles/943422), [Harant](https://harant.ru/blog/grazhdanskoe-pravo/pro-personalnye-dannye-v-rabote-yuridicheskih-licz-i-ip-v-2025g-obzor-izmenenij/)
- From 2025-05-30, Federal Law 420-FZ (amending the Code of Administrative Offences, КоАП) sharply raised fines. For example, a leak of 1,000-10,000 subjects' data costs a legal entity 3-5M RUB, and these changes apply to small SaaS and startups too. — [Habr](https://habr.com/ru/articles/943422), [Tproger](https://tproger.ru/articles/it-zakonodatelstvo-2025--razbor-izmeneniy-dlya-biznesa-i-specialistov)

### Inferences
- A Russian-resident developer's realistic monetization stack is:
  - RuStore in-app payments for Android.
  - Web checkout via YooKassa, CloudPayments or Prodamus (CloudPayments and Prodamus were not researched in detail) for iOS and web users.
  - Telegram Stars as a secondary option.
  
  Charging iOS users in Russia through Apple is effectively impossible now.
- A native mobile app (option b) does not unlock store billing in Russia; it mainly adds distribution and reliability. A PWA or web app plus a RuStore Android build may cover most of the value at lower cost. Built-in SRS removes the dependency on Anki/AnkiConnect, which are desktop-heavy and unfamiliar to mass users.
- To go public with Russian users, the backend database (currently SQLite on a VPS) must be hosted in Russia, or at least the primary collection of Telegram ID and other personal data must happen there. The owner must also file the Roskomnadzor operator notification and publish a privacy policy. Personal-data compliance is a real cost even for a hobby-scale launch.
- Serving only CIS/diaspora users via a foreign entity would avoid store bans, but that is a different business setup.

### Gaps
- The current (2026) RuStore commission schedule was not confirmed.
- No sources were found for CloudPayments or Prodamus terms, or for whether a самозанятый can lawfully receive Telegram Stars/TON proceeds. Crypto income for individuals is a legal grey area that I did not research.
- The Roskomnadzor operator-notification details and the September 2025 separate-consent rule were not confirmed (the RBC guide returned HTTP 401).

## 4. Market size and trends

### Takeaway
Language learning is a large but slowly growing part of Russian EdTech. Skyeng, the segment leader, grew only 5.2% in 2025 to 12.7 bn RUB, while the overall top-100 grew 12%. Roughly 40% of adults have at least minimal English, and around a fifth of learners use apps. There is no reliable published figure for a "vocabulary app" sub-market.

### Cited Findings
- The top-100 Russian EdTech companies grew 12% YoY in 2025 (19% in 2024). Leaders were Synergy (16.1 bn RUB), Skillbox (12.8 bn), Skyeng (12.7 bn, +5.2%), Yandex Practicum (8.8 bn) and Uchi.ru (7.2 bn). — [Skillbox Media / Smart Ranking (2026-02-06)](https://skillbox.ru/media/edtech/v-2025-godu-rossiyskiy-edtech-vyros-vsego-na-12/)
- The top-100 earned about 42 bn RUB in Q3 2025 (+12% YoY) and 34.2 bn RUB in Q2 2025 (+10%, the slowest growth since late 2022). — [Skillbox Q3 2025](https://skillbox.ru/media/edtech/opublikovan-reyting-rossiyskih-edtech-kompaniy-po-vyruchke-v-tretem-kvartale-2025-goda/), [Skillbox Q2 2025](https://skillbox.ru/media/edtech/stali-izvestny-itogi-vtorogo-kvartala-2025-goda-dlya-rossiyskogo-edtech-rynka/)
- On the GetCourse platform, the "foreign languages" niche had 2 bn RUB of school revenue in 2025, out of 158 bn RUB total platform turnover. AI courses grew from 0.955 bn to 1.7 bn RUB. — [GetCourse analytics 2025](https://getcourse.ru/magazine/analitika_2025), [Inc. Russia](https://incrussia.ru/news/roditelskoe-obrazovanie-v-2025-godu-stalo-odnim-iz-samyh-perspektivnyh-napravlenij-rynka/)
- English proficiency:
  - FOM: 40% of adults know English at least at a minimal level.
  - About 3% speak any foreign language fluently, and about 5.1M people reported speaking English in the 2020 census.
  - Russia ranks 44th of 116 in the EF EPI (2024).
  - More than 81k students took the English Unified State Exam (ЕГЭ) in 2025.
  - 70% of Russians are not interested in learning languages.
  
  — [T-Zh](https://t-j.ru/foreign-languages-stat/)
- VTsIOM: only 5% claim fluent English. — [Mel.fm](https://mel.fm/novosti/1847902-vtsiom), [VTsIOM](https://wciom.ru/analytical-reviews/analiticheskii-obzor/inostrannyj-yazyk-perspektivnaya-investicziya)
- FOM: 9% of adults want to learn English. A quarter of learners study on their own, about 20% use mobile apps or online courses, and 19% use language schools. — [T-Zh / FOM via search](https://t-j.ru/foreign-languages-stat/)
- Avito Services (2024): 44% planned to learn a foreign language in 2024. Of those, 63% planned self-study via apps, 38% online schools and 21% in-person groups. Motives: travel 38%, communication 19%, work 18%. — [T-Zh](https://t-j.ru/foreign-languages-stat/)

### Inferences
- A rough addressable audience: Russia has about 120M adults, and 9% wanting to learn English gives about 10M. Of those, 20-60% are app users, so a few million potential app users in Russia alone, before counting the CIS and diaspora.
- The serious "personal dictionary" niche (intermediate and advanced learners capturing phrases from real content) is a smaller subset, likely in the hundreds of thousands. This is an inference, not a sourced number.
- Slow growth at Skyeng and the overall market slowdown suggest a price-sensitive market, consistent with low-cost apps like Words being praised for cheap subscriptions.

### Gaps
- A search-engine summary said Smart Ranking described the foreign-language segment as "practically stagnating (+3%)" because of competition and AI assistants. I could not find this passage in the Q2 2025, Q3 2025, full-year 2025 or Kommersant articles I opened, so it is **unverified**.
- No EdMarket or other report gives a specific RUB size for B2C self-study language apps.
- No figures for CIS or diaspora market size.

## 5. Learner complaints and demand signals for AI-generated cards and personal dictionaries

### Takeaway
Complaints cluster around shallow cards (no usage context), billing and price, outdated interfaces, and content limited to fixed word lists. Developers keep building DIY "send a word to Telegram, get a card in Anki" bots on Habr, which is a clear signal from power users. Incumbents (Lingualeo Leo-chat, Yandex Alice, Yandex Practicum) are adding LLM features, which confirms the direction but also crowds the space.

### Cited Findings
- ReWord review (RuStore): the concept is good but it "lacks explanations for word usage context" and the execution does not justify the cost. — [RuStore](https://rustore.ru/catalog/app/ru.poas.englishwords)
- Lingualeo complaints:
  - Prices at checkout differ from those shown.
  - Course-progress bugs.
  - YouTube-based content unavailable in Russia.
  - Outdated interface and poor audio.
  - Slow email support.
  - An App Store user asked for full-sentence translation, not just single words.
  
  — [a2is.ru](https://a2is.ru/catalog/samoobuchenie/lingualeo/reviews-lingualeo), [otzovik](https://otzovik.com/review_233764.html), [App Store RU](https://apps.apple.com/ru/app/480952151)
- Words (EngWordsLab) reviewers praise the low subscription price and long-period discounts compared with competitors. — [RuStore](https://www.rustore.ru/catalog/app/com.nltsm.words)
- Habr and Tproger have repeated DIY projects: aiogram bots that create vocabulary cards and Anki entries, audio flashcard SRS bots, and an LLM-enhanced English bot as a pet project. — [Habr 471196](https://habr.com/ru/post/471196), [Habr 345864](https://habr.com/ru/articles/345864), [Tproger](https://tproger.ru/articles/pet-proekt-spasaet-ot-vygoraniya-i-kachaet-mozg)
- A Habr sandbox article lists desired features: easy word adding from any device, cross-device sync, import/export, Telegram notifications, SRS and statistics. — [Habr sandbox 276362](https://habr.com/ru/sandbox/276362)
- T-Zh published a guide on using ChatGPT to generate Quizlet flashcards, which suggests mainstream interest in AI-made cards. — [T-Zh](https://t-j.ru/chatgpt-for-kartochki-quizlet/)
- Yandex built its AI English features (Alice in Translate, the AI translator in Practicum) around exactly what this product's card contains: context-aware meanings, transcription, examples, and explanations of phrasal verbs and idioms. — [Habr 919886](https://habr.com/en/news/919886), [Habr 910740](https://habr.com/ru/companies/yandex_praktikum/news/910740)

### Inferences
- Several signals point to demand for "capture any phrase and get a rich, contextual card": the ReWord complaint, the Lingualeo sentence-translation request, the recurring DIY bots and Yandex's product choices. The product's English explanation, three examples and frequency score directly address the "no usage context" complaint.
- Weak monetization signals (price-sensitive users, praise for cheap apps, Lingualeo billing anger) suggest pricing near or below about 300-500 RUB per month, or a generous free tier with paid LLM usage.
- The DIY-bot trend also means the most motivated users can build their own. The value of a public product would be polish, built-in SRS and zero setup (no Anki or AnkiConnect).

### Gaps
- No systematic scrape of Google Play or RuStore review text was possible (RuStore rate-limited the Lingualeo reviews page). The complaint themes are based on a small sample.
- No Pikabu or vc.ru discussion threads specifically about AI-card apps were found.
- No public conversion or retention numbers for any Russian vocabulary app or Telegram learning bot.
