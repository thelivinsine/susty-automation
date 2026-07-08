# EF Version Explainer: Vision, Audience & Scope

Purpose of this doc: reformulate the project around GENUINE USEFULNESS to a
specific sustainability audience as the primary goal, with "getting hired" as an
explicit side effect. Produced from a six-persona expert panel (LCA practitioner,
climate-SaaS strategist, standards/assurance expert, solo-consultant end user,
skeptical VC, community/GTM lead) plus two adversarial critiques and a synthesis.
Competitive and regulatory claims are web-grounded where cited.

## 1. Verdict: is it genuinely useful today?

**Partly. Genuinely useful in concept and in its trust discipline, but not yet in
the shape a practitioner would open twice, because it runs against a toy 5-line
BOM instead of their real factor register.**

That is not a hedge. It is the unanimous verdict of a six-person panel chosen for
opposing biases. Every one of them said "partly." Not one said "yes." When even
the friendliest possible reader cannot get past "partly," the honest reading is
that the shipped thing is not yet the useful thing, and everyone sees the gap in
the same place.

**Where it is genuinely useful today, and to whom:** to a UK solo or boutique
carbon consultant, the parts already built and hard to replicate are real value:

- The **relabel-family reconciliation** that collapses DEFRA's ~500 added and
  ~500 removed rows (the "HGV (all diesel)" to "HGV (non-refrigerated, all
  diesel)" churn) into a handful of readable rename families. Even the hostile VC
  called this "the real product." It is unglamorous, recurring, genuinely hard
  work that no free blog and no lazy platform does for your specific factors.
- The **no-guess discipline enforced in code**: exact to fuzzy to `needs_review`
  matching, and the verbatim "No official reason found in the DEFRA changes
  report" fallback. This is what lets a consultant put their name on the output,
  and what they cannot get from a raw ChatGPT prompt.

**Where it is not useful yet, and why the verdict is "partly" not "yes":**

1. **It eats a toy BOM, not the user's real data.** The differentiating value
   (materiality judged against *my* inventory, a memo about *my* 47 factors) is
   precisely the part not built. What is built is the commodity part: diff, flag,
   recompute, generic explanation. The tool is strongest exactly where it is least
   defensible and absent exactly where the moat lives. This is the single most
   important fact in the whole exercise.
2. **The output is a Markdown page, not a fileable client deliverable.** The
   consultant still re-keys it into a branded document.
3. **The stated wedge ("nobody explains the DEFRA delta") is false.** Within days
   of each release, Acclaro Advisory, EmissionFactors.net, Circular Ecology and
   the EMA publish free "what changed and why" explainers, and DEFRA itself ships
   a methodology report and a major-changes report every year. The headline movers
   (the ~26% grid-electricity drop, aviation, rail) are already explained for
   free. Your value is only on the **long tail**: complete, per-factor,
   against-*your*-register, reproducible coverage no blog produces.

The fix is subtraction plus one hard build, not a bigger surface. Three moves
(ingest my real register, judge materiality against my inventory, export a cited
dated memo), all anchored by the honesty discipline you already nail, flip the
whole panel from "partly" to "yes."

## 2. Vision and Mission

**Vision (recommended):** A world where updating to the new year's DEFRA factors
is a documented, defensible decision that takes an afternoon, not a fortnight of
Excel archaeology, and where every material change in a footprint traces to an
official, cited reason instead of a shrug.

Alternatives:
- Every UK carbon consultant, however small, can explain a factor-version change
  as defensibly as a big-platform team.
- The reference-data layer of carbon accounting should be as transparent and
  reproducible as the code that consumes it.

**Mission (recommended):** Turn each annual DEFRA update into a grounded, no-guess,
cited memo of what changed and why, run against the factors the practitioner
actually uses and their own inventory, so they can defend the number to an auditor
in an afternoon.

Alternatives:
- Give UK carbon consultants an auditable DEFRA re-baselining record that
  quantifies every material movement against a real inventory, cites it verbatim
  to DEFRA, and never guesses.
- Turn the yearly DEFRA factor update from a lost day of VLOOKUP-and-hunt into a
  defensible "what changed and why" memo for the budget-constrained consultant
  and SME lead.

## 3. Primary and secondary audience

### Primary ICP: the UK solo or boutique carbon/LCA consultant ("Priya")

Producing client-facing SECR and voluntary footprint deliverables on free DEFRA
factors.

- **Who:** ex-Big-4 or ex-Quantis, now independent or a two-person shop, serving
  8 to 15 SME clients on annual UK GHG reporting. Uses free DEFRA factors because
  clients will not pay for a Watershed or Persefoni seat. Lives in Excel.
- **Pain:** every June DEFRA drops, last year's client numbers move for no
  operational reason, and they must find which of the specific factors *their*
  clients use moved materially, restate the prior-year footprint, and hand-write a
  defensible "why did the number change" memo per client. The relabel churn makes
  a naive diff read as noise.
- **Current painful workaround:** VLOOKUP across two DEFRA workbooks, eyeball the
  material movers, hunt the methodology paper and What's new tab for the reason by
  hand, hand-write the "why" paragraph, reformat into Word or PDF.
- **Why this tool:** it automates exactly that loop, and the part they dread most
  (the defensible "why" write-up) is drafted for them, grounded in DEFRA's own
  notes with a no-guess rule they can stake their reputation on. Local and free
  suits a once-a-year task they will never buy a SaaS seat for.
- **Reachability: easy.** It is the owner's own warm network, so cold-start is
  nearly free.

**Why the primary beats the others:** it is the only segment rated "easy" by
consensus; the pain is acute, recurring, and billable-hours-obvious; the artifact
the tool produces is one they currently make by hand; the credibility bar
(no-guess, no-invented-reason) exactly matches how they already work; and,
decisively, **this segment is the people who hire the owner.** In a pond sized at
"low hundreds, not thousands" of people who write methodology-grade delta notes,
being visibly useful to this exact pond makes "getting hired" the automatic side
effect. That collapses the owner's two goals into one move.

### Secondary audience: the in-house UK carbon/sustainability lead at a DEFRA-reporting SME or mid-market firm

- **Pain:** owns the whole footprint alone, no platform budget, and the board,
  CFO, and assurer ask "did our number change and why" every year with no analyst
  to answer it. Must separate real performance from factor drift.
- **Why this tool:** a defensible, documented version reconciliation without
  hiring a consultant or buying Persefoni, with client data never leaving the
  laptop. CSRD moves from limited assurance (FY2025/26) to reasonable assurance
  (from 2028), so the year-on-year comparability narrative is becoming audited,
  not decorative. *Note: whether a given UK SME is in CSRD scope is firm-specific;
  treat the CSRD driver as applying to the larger/EU-linked end of this segment.*
- **Reachability: medium.**

**The open-source / civic-data community is NOT a third ICP. It is the
distribution engine.** A public changelog is how the two audiences above discover
the tool and how the owner becomes visible. Treat it as GTM, not a user segment to
serve, and not a v1 build commitment.

## 4. The core job-to-be-done, in the user's own words

> "When DEFRA publishes the June release, tell me which of the factors I actually
> use moved past materiality and why, grounded in DEFRA's own words, so I can
> decide in an afternoon whether to restate and hand my client (or their auditor)
> a dated, cited memo I can defend, without rebuilding the reasoning from scratch.
> And when DEFRA is silent, tell me so honestly instead of inventing a reason I
> would have to retract."

Supporting jobs: separate genuine movement from the ~500 relabels so I do not
present administrative churn as real change; flag every line I could not match
with confidence so I review it by hand; tell me the coverage % so I know how much
of the number is solid.

## 5. Reformulated goal

**Primary goal: be genuinely, annually useful to the UK DEFRA solo/boutique
consultant** on the one day in June they open the tool, by handing them a fileable,
cited memo about their own numbers that would otherwise cost them a
billable-but-boring week.

**Getting hired is an explicit side effect, and here is exactly how it still gets
served:** in a pond this small, the public artifact *is* the hiring strategy. The
private app delivers the value; the public presence delivers the owner. Concretely:
(a) an open repo with the CI quality gates visible as a reproducibility and
credibility signal, (b) the owner writing publicly each June about that year's real
DEFRA movements using the tool's output, and (c) the tool's no-guess honesty being
visibly the discipline a serious hire brings. **Do not monetize the tool; let the
tool monetize the owner.** The revenue is reputation, consulting pull, and job
offers, not a SaaS seat. That also dissolves the seasonality objection, which only
bites if you charge a subscription for an annual tool.

## 6. Scope

### IN (build or keep)

| Item | Status | Why |
|---|---|---|
| **Forgiving factor-register / inventory ingest** (tolerant CSV template + light column-mapping; anything ambiguous drops to `needs_review`, never guessed) | **Build first** | The single hard feature that separates demo from tool. Real client files have arbitrary columns, blended units, messy activity strings. This is the crux. |
| **Materiality scored against the user's own inventory** (rank flags by impact on their actual number, not DEFRA's generic 5%/10%) | **Build second** | Cheap once ingest exists; the value multiplier. A 3% move on grid electricity may be a whole Scope 2; a 20% move on a 0.01% line is noise. |
| **Dated, cited, portable memo as a first-class output** (clean HTML one-pager with a provenance header: source file, sheet, row, DEFRA publication date, verbatim quoted note, retrieval date; prints to PDF) | **Build third** | The artifact the consultant actually files. HTML-to-PDF respects the no-heavy-deps rule; Word export is a nice-to-have, not v1. |
| **Relabel-family grouping** | Keep as is | Already built, already works, your realest differentiator. Foreground it. |
| **No-guess matching + "No official reason found" verbatim fallback, enforced in code** | Keep as is | The credibility floor that lets a consultant sign the output. |
| **Widen grounding to DEFRA's full annual methodology report PDF** | Build (small) | Directly attacks the biggest value-cap: the What's new tab is thin, so a per-factor report can honestly come back majority "no reason found." The methodology report explains many per-fuel revisions the tab omits. |
| Two-workbook diff, DEFRA-threshold flagging, recompute, coverage % | Keep (table stakes) | Necessary hygiene, but do not claim it as the moat. |
| DEFRA/DESNZ only, carbon (kg CO2e) only, local, single-user | Keep | Unanimous. This is a focused utility, not a platform. |

### OUT (resist)

| Item | Why cut |
|---|---|
| **"AI explains your carbon delta" as the headline/moat** | Falsified by free explainers and DEFRA's own reports; a hallucination liability in an audit context. Demote the AI to a labelled quoter of DEFRA's verbatim words. |
| **SBTi / base-year recalc trigger helper** | Compliance liability and scope creep. The moment the output reads "this triggers a recalculation" instead of "this *may* be a trigger, confirm against your own policy," you take on exposure a solo tool cannot carry. Advise and document; never determine. |
| **Any second database** (ecoinvent, EPA, IEA, exiobase) | It is a ceiling *and* a moat; own the UK niche. Breadth dilutes the wedge. |
| **Other impact categories** beyond carbon | Carbon proves it. |
| **Public annual changelog page as a v1 commitment** | A recurring public commitment a solo non-dev will eventually miss. Revisit only once the core tool earns a following. |
| **Verifier / Big-4 assurance segment as a launch target** | Hardest to win, last to convert; an LLM near their audit trail is a red flag until citation is bulletproof. Let them come to you. |
| **Database / login / cloud / SaaS / multi-tenant** | Unanimous. Local file tool plus, later, a public static page. |
| **The toy BOM as the hero** | Reframe every demo around a real inventory the moment ingest ships. |
| **Auto-restating the user's official numbers** | Advise and document the decision; never silently overwrite a filing. |

## 7. Positioning

**For the UK solo or boutique carbon consultant who has to defend every
year-on-year footprint movement to a client's auditor, EF Version Explainer is a
grounded DEFRA re-baselining tool that reconciles the new factors against your own
register and hands you a dated, cited memo of exactly what moved and why, unlike
free release-day blogs (which only explain the three headline factors) and big
platforms like Watershed or Persefoni (which recompute the number but leave the
explaining to you).**

## 8. Honest risks and what would kill genuine usefulness

Ranked by how quietly lethal each is.

1. **Input friction (the silent killer).** If the tool cannot eat the user's
   actual spreadsheet without reformatting, they try it once, hit the wall, and
   never come back. *Mitigation:* the forgiving-ingest feature, tolerant template,
   light column-mapping; ambiguity drops to `needs_review`, never a guess.
2. **The toy-data gap.** The genuinely useful product is the part not built; the
   built part is the commodity. *Mitigation:* moves 1-2 in Section 9. Until it
   ships, every demo overstates delivered value.
3. **Value-cap when DEFRA is silent.** A per-factor report can honestly come back
   50-70% "No official reason found." *Mitigation:* widen grounding to the
   methodology report PDF, and reframe silence in the UI as "transparency about
   what DEFRA does and does not disclose," not a broken feature.
4. **Output shape.** A Markdown page is not a client deliverable. *Mitigation:* the
   cited HTML-to-PDF memo (move 3).
5. **Once-a-year frequency.** *Mitigation:* do not fight it. The business model is
   reputation, not subscription, so seasonality is irrelevant to the plan.
6. **Confidentiality / hosted-LLM.** Sending client BOMs to Gemini is a non-starter
   for some clients. *Mitigation:* make offline/local the default; hosted LLM
   opt-in only. The code-level grounding guard and offline fallback already exist.
7. **Cold-start trust.** Year one the careful consultant spot-checks every
   explanation; one fabricated-looking reason means no year two. *Mitigation:*
   verbatim DEFRA quote first, labelled paraphrase second; never let the model
   analyze.
8. **Maintenance for a solo non-dev owner.** *Mitigation:* architect next year's
   run as one command; keep the public commitment out of v1.

**The single biggest threat to genuine usefulness is the toy-data gap, not
DEFRA-narrowness, not the LLM, not the owner.** DEFRA-narrowness caps market size,
not usefulness. The one thing that determines whether a real user gets real value
on the day they open the tool is: does it consume their real register and hand back
a fileable, cited memo about *their* numbers? Today it does neither.

## 9. Recommended next 3 moves, in priority order

1. **Validate before building more:** take three warm consultants from your network
   and re-run *last* year's real client reconciliation with the current tool this
   month, and watch whether the output survives their spot-check against DEFRA.
2. **Build forgiving ingest of the user's own factor register / client inventory,**
   with materiality scored against that inventory, and kill the toy BOM as the hero
   (this one hard build is the entire demo-to-tool jump).
3. **Ship the dated, cited, printable memo** (HTML provenance header to PDF) as the
   first-class output, widen grounding to DEFRA's methodology report PDF, and
   reframe every message from "AI explains your delta" to "the grounded, no-guess
   DEFRA re-baselining memo for UK carbon consultants."
</content>
</invoke>
