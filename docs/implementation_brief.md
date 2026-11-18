# Implementation Brief: Should This Use AI?
**Joshua Weaver | November 17, 2026 | Version 1**

## 1. My workflow
Twice weekly, I compare Marquette and Elk City hunts by switching between two weather sites, lunar information, and sunrise/sunset information. My October 28 [baseline](baseline_log.md): **14:07, confidence 4/5**—one timed entry, not an average. Wasted trips sacrifice limited rut-season opportunities amid classes and personal obligations.

## 2. Should this use AI?
**A. Checklist:** organizes criteria at no added subscription cost; manual gathering, copying errors, and staleness remain.
**B. Dashboard/SQL:** combines both towns’ weather/astronomy; $0/month within free limits, plus maintenance. Staleness and misleading summaries remain risks.
**C. B plus LLM interview:** ask follow-up questions and explain personalized tradeoffs; adds AI cost and privacy/testing work; risks invented explanations and overlooked limits.

**Build B first; test C narrowly.** Fetching, calculations, freshness, and numeric filters need code/SQL; forms can collect preferences. AI adds follow-up questions. Confirm morning/evening availability, stand/ground approach, rifle/bow, precipitation tolerance, and wind limits. Ask about missing context; terrain/access/sightings come from me. AI considers my weather experience without guaranteeing deer movement. I make the final choice.

## 3. Value hypothesis
**Target: ≤5 minutes**, versus the single 14:07 baseline. Time at least five real decisions in the Milestone 4 [usage log](usage_log.md), including follow-up/outside verification; compare median time with target. Record confidence/gaps/rejections; compare dashboard-only versus AI sessions. Reliability means current data, preference compliance, explanations, and uncertainty—not deer encounters. Savings remain unproven.

## 4. Early cost estimate
Assume nine sessions/month × 20 AI responses, averaging 4,000 input and 1,000 billed output tokens/response, including billed reasoning. GPT-6.1 Terra [pricing](https://developers.openai.com/api/docs/models/gpt-6.1-terra): $1/million input and $5/million output, or **$0.009/response; $1.62/month**. History, retries, tests, and visitors add cost.

Budget **$0/month each**, within limits: [Supabase](https://supabase.com/pricing), standard public-repository [Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions), [Render Free](https://render.com/docs/free) (sleeps idle), and [Visual Crossing](https://www.visualcrossing.com/resources/documentation/what-can-i-do-with-the-visual-crossing-weather-free-plan/) (normally four forecast units/day versus my verified 1,000/day). Excludes labor/taxes/domain/subscriptions; prices checked November 17, 2026.

Before Milestone 5: **$20 prepaid OpenAI credit, auto-reload off**, a $20 [hard limit](https://developers.openai.com/api/docs/guides/spend-limits), and an app cutoff below $20 for in-flight headroom. Controls remain planned; enforcement can lag. Limit requests; at cutoff, pause AI, retain dashboard. Measure costs in Milestone 5. Credit is separate from ChatGPT subscriptions.

## 5. Risks and governance
Wrong advice wastes trips and misleads visitors about safety/deer activity. Show source, forecast/refresh times, and stale/missing-data warnings. Town weather does not establish stand conditions, access rights, regulations, or safety. Publish town-level data only. Protect private spots/schedules/interviews; obtain approval before saving preferences and minimize provider disclosures.

AI must never assume permission, override limits, disclose private details, alter weather, book travel, or commit me to a hunt. Chatbot access stays read-only; later agent writes require narrow permissions/approval. I own maintenance, failure review, and decisions.

## 6. Scorecard self-assessment — version 1
- **Real user/workflow — Green:** recurring decision and timed baseline exist.
- **Data access — Green:** live forecasts and manual Actions succeeded.
- **Data understanding — Yellow:** meanings documented; quality/coverage checks unfinished.
- **Freshness/monitoring — Yellow:** scheduling/logging exist; sustained scheduled evidence unverified.
- **Grounding — Yellow:** SQL works; AI grounding is untested.
- **Bounded autonomy — Yellow:** reader restrictions verified; AI boundaries remain planned.
- **Evaluation — Red:** golden-question and recommendation tests incomplete.
- **Measured value/cost — Red:** one baseline; savings and AI costs unmeasured.
- **Adoption — Yellow:** continued use depends on demonstrated reliability.
- **Governance/accountability — Yellow:** owner identified; privacy controls need implementation.

**Weakest-factor plans:** Evaluation—complete golden questions; test preferences, grounding, freshness warnings, and refusals. Value/cost—measure decision times and charges; retain AI only if it improves on the dashboard. Reassess at user testing and the final business case.