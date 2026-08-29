# Grill Session: liang-restoration-event-chain

Started: 2026-08-25
Last updated: 2026-08-25
Status: complete
Domain: EU4 alternate-history event-chain, political-mechanic, and player-choice design

## Summary

The completed design is a standard-1444 single-player opening chain about Zhang Chengzuo and Duan Shoujie seeking restoration of the dormant `LGU` Liang polity. It begins at the Tianzi court after 90 days, makes one randomized circuit through five-province Zhou polities, and either ends permanently after universal refusal or restores Liang in a lowest-development temporary grant as the patron's vanilla March and Zhou member. A later Wuwei–Jingyuan–Yongchang settlement returns the surviving original grant, preserves March status, and lets the patron honor or repudiate the compact with defined rewards and penalties.

## Decision Log

### RESOLVED: Liang's opening gameplay state
- **Resolution**: Liang is not an active country at the start. The repository contains a dormant `LNG` country shell, but no province ownership/core usage or active Zhou-system role was found; the opening actor therefore needs to be understood as a court-in-exile, claimant household, or envoy community unless the design later decides otherwise.
- **Date**: 2026-08-25

### DECIDED: Dedicated Liang country tag
- **Decision**: Use new tag `LGU` for 凉, leaving vanilla `LNG` as 梁. `LGU` starts dormant with no owner, controller, core, or Zhou membership; its country history uses Wuwei (708), `gdd_long`, the mod's Ritual Teaching engine key `confucianism`, Chinese technology, and a rank-one feudal monarchy without a forced fixed capital.
- **Rationale**: A separate tag prevents semantic and asset collisions with 梁, while the core-free opening state prevents ordinary release mechanics from bypassing the event chain or transferring unintended homeland provinces.
- **Date**: 2026-08-25

### DECIDED: Liang flag style
- **Decision**: `LGU` uses the shared Zhuxia small-seal stamp-flag system with the traditional inscription “涼”. The user-approved black-on-white glyph image is stored as the authoritative reference; generation only removes the white field and normalizes its scale and placement.
- **Rationale**: This keeps Liang visually consistent with the other Zhuxia polities and makes the existing deterministic flag generator authoritative.
- **Date**: 2026-08-25

### DECIDED: First-year opening window
- **Decision**: In a standard 1444-11-11 campaign, the first player-facing event that introduces the exiled Liang petition fires on a deterministic delay of about 90 days (approximately 1445-02-09), independent of wars, regencies, or player actions. The first-year deadline applies only to the introduction; the envoys' later circulation among feudatories and the eventual acceptance or failure may continue for multiple years.
- **Rationale**: Liang's exile and search for a restoring patron are intended to be an opening premise, while the delay keeps the event clear of the existing day-one Zhou-system overview. Deterministic scheduling guarantees that the premise cannot drift to the end of the first year or fail because of unrelated conditions.
- **Date**: 2026-08-25

### DECIDED: Petition begins at the Tianzi court
- **Decision**: The 90-day introduction occurs first at the Tianzi's court. The exiled Liang claimant obtains recognition of its surviving legitimacy and permission to circulate among the feudatories before asking individual states to grant restoration land.
- **Rationale**: Tianzi recognition explains why the Zhou feudatories treat a landless claimant as a legitimate fallen polity rather than as an ordinary refugee group, and gives the nationwide petition a common ceremonial starting point.
- **Date**: 2026-08-25

### DECIDED: Tianzi recognition is non-binding
- **Decision**: The Tianzi recognizes the continuity of Liang's ancestral rites and claimant legitimacy and grants the envoys ceremonial credentials and safe passage, but does not order any feudatory to provide land. Refusing the petition carries no inherent punishment; voluntarily restoring Liang is the meritorious act.
- **Rationale**: A binding restoration edict would logically require the Tianzi to designate the land or donor directly and would contradict the intended wandering petition. Non-binding recognition preserves meaningful choice and makes the eventual patron's permanent reward earned rather than compulsory.
- **Date**: 2026-08-25

### DECIDED: One fixed claimant throughout the petition
- **Decision**: The same named Liang heir remains the narrative actor throughout the entire petition circuit. The event chain does not simulate off-map death or succession; if restoration succeeds, that claimant is created directly as Liang's first ruler. Dynastic continuity remains background lore rather than an event mechanic.
- **Rationale**: The full circuit normally spans only four to five years, so modeling claimant death would add state and failure cases without improving the campaign-scale story.
- **Date**: 2026-08-25

### DECIDED: Claimant and envoy identities
- **Decision**: The fixed Liang claimant is Zhang Chengzuo (张承祚), and the senior envoy is Duan Shoujie (段守节). Zhang is restrained and frames restoration as continuation of ancestral rites rather than personal enrichment; Duan carries the Tianzi's credentials and conducts the practical negotiations with feudatory courts.
- **Rationale**: Original characters give the chain a consistent human voice without tying the alternate-history Liang polity to a specific historical Liang dynasty.
- **Date**: 2026-08-25

### DECIDED: Zhang Chengzuo's restoration ruler profile
- **Decision**: When Liang is restored, Zhang Chengzuo is created as a 26-year-old ruler with `ADM 3`, `DIP 5`, `MIL 2`, and claim `90`, without an additional powerful ruler personality. Duan Shoujie remains a narrative event character and is not generated as an advisor.
- **Rationale**: High diplomacy reflects the successful multi-court petition, while ten total monarch-skill points make Zhang capable but not exceptional; keeping Duan narrative-only avoids unnecessary reward and lifecycle state.
- **Date**: 2026-08-25

### DECIDED: Liang's three-province eastern homeland
- **Decision**: Liang's historical homeland for the later restoration settlement is Wuwei (708), Jingyuan (2182), and Yongchang (5295). Zhangye (5296) and Jiayu (5297) are outside the mandatory homeland and do not gate the return event.
- **Rationale**: The three eastern provinces form a Wuwei-centered core and all begin under WGS, producing a coherent restoration objective without requiring the patron to conquer two separate opening owners merely to complete the chain.
- **Date**: 2026-08-25

### DECIDED: Dynamic randomized recipient pool
- **Decision**: The petition does not follow a fixed list of major feudatories. It makes one randomized circuit through qualifying Zhou polities with at least five owned provinces, visiting each selected state at most once. The first acceptance ends the circuit in restoration; if the entire circuit refuses, the event chain ends permanently and does not restart after ruler changes or later political developments.
- **Rationale**: A capacity threshold avoids meaningless petitions to tiny states, while a single non-repeating circuit gives the wandering mission a real possibility of final failure and prevents recurring petition spam.
- **Date**: 2026-08-25

### DECIDED: Departure-time roster snapshot
- **Decision**: When the envoys depart, the chain records every Zhou polity that directly owns at least five provinces and randomizes a non-repeating visit order. States that later fall below five provinces, cease to exist, or leave the Zhou system are skipped when reached; states that become eligible only after departure are not added. If all recorded states refuse or become invalid, the chain fails permanently.
- **Rationale**: This preserves dynamic campaign-dependent eligibility while giving the phrase “one circuit” a finite, auditable endpoint and preventing the target list from expanding indefinitely during a multi-year journey.
- **Date**: 2026-08-25

### DECIDED: Automatic lowest-development land grant
- **Decision**: Neither human nor AI patrons choose the grant manually. On acceptance, Liang receives the patron's lowest-total-development owned province that is not the patron's capital; if the absolute lowest-development province is the capital, selection proceeds to the next-lowest province.
- **Rationale**: A uniform automatic rule prevents human optimization through manual province dumping and makes the restoration cost consistent between player and AI patrons.
- **Date**: 2026-08-25

### DECIDED: Strict grant eligibility and tie-breaking
- **Decision**: Grant selection considers completed city provinces only and excludes the patron's capital and Liang's three homeland provinces. It chooses the lowest total development; equal-development ties are randomized. Forts, centers of trade, monuments, islands, and enclaves receive no exemption, while unfinished colonies are ineligible.
- **Rationale**: This keeps the promised uniform lowest-development rule authoritative and prevents either human or AI patrons from optimizing strategic exceptions, while ensuring Liang begins in a valid city rather than an unfinished colony.
- **Date**: 2026-08-25

### DECIDED: Vanilla March subject status
- **Decision**: “Garrison state” means EU4's vanilla March subject type. Once restored in the granted province, Liang becomes the restoring patron's March; the province need not lie on a geographic frontier.
- **Rationale**: The term refers to the native diplomatic subject relationship and its existing military mechanics, not to a separate geographic eligibility rule for the granted province.
- **Date**: 2026-08-25

### DECIDED: March status survives homeland restoration
- **Decision**: When Liang later receives Wuwei, Jingyuan, and Yongchang and returns its original grant to the patron, it remains the same patron's vanilla March. Homeland restoration relocates and enlarges Liang but does not make it independent or change overlords.
- **Rationale**: The later settlement fulfills the original restoration promise while preserving the patron–garrison relationship that justified the first land grant and permanent patron reward.
- **Date**: 2026-08-25

### DECIDED: Restored Liang joins the Zhou realm immediately
- **Decision**: As soon as `LGU` appears in the initial granted province, it is registered as a Zhou-realm member. It simultaneously remains the restoring patron's vanilla March, and it retains Zhou membership after later relocating to its three-province homeland.
- **Rationale**: Tianzi recognition and the patron's land grant restore Liang as a legitimate polity at the first restoration event; membership should not wait for the separate territorial completion of homeland recovery.
- **Date**: 2026-08-25

### DECIDED: Joint patron–Liang homeland trigger
- **Decision**: The later settlement becomes eligible when Wuwei, Jingyuan, and Yongchang are all owned by either the original patron or its Liang March in any combination. Ownership by other subjects or allies, and mere wartime occupation, do not count. Settlement consolidates all three provinces under Liang and returns Liang's original granted province to the patron.
- **Rationale**: Liang's own reconquest should advance rather than block restoration, while excluding other subjects prevents the event from silently stripping a third polity's land.
- **Date**: 2026-08-25

### DECIDED: Direct restoration when the patron already holds the homeland
- **Decision**: If an accepting patron already owns Wuwei, Jingyuan, and Yongchang, Liang is restored directly in those provinces as the patron's March and no temporary grant is made. If the patron owns only one or two homeland provinces, all three homeland provinces are excluded from temporary-grant selection; Liang receives the lowest-development eligible non-capital province elsewhere and later follows the normal settlement.
- **Rationale**: This avoids redundant back-to-back grant and return events and prevents a homeland province from being simultaneously treated as the temporary grant that must return to the patron and as permanent Liang territory.
- **Date**: 2026-08-25

### DECIDED: Only the surviving original grant is returned
- **Decision**: The settlement tracks only the single original temporary grant. If Liang still owns it, it returns to the original patron; if a third party has taken it, the event neither steals it back nor blocks homeland settlement. Any other non-homeland provinces Liang acquires remain Liang territory.
- **Rationale**: The compact promised the return of a specific grant, not a general territorial rollback. Third-party ownership must be respected, and losing the grant should not permanently prevent consolidation of the three homeland provinces.
- **Date**: 2026-08-25

### DECIDED: Diplomatic-legitimacy patron reward
- **Decision**: The restoring patron receives a permanent modifier whose sole effect is `+0.33` diplomatic reputation. It does not also grant improved relations, yearly prestige, legitimacy, or military effects.
- **Rationale**: The patron already gains a vanilla March, so a compact fractional diplomatic-reputation reward is enough to express the public moral authority of “preserving the fallen and continuing the extinct” without eclipsing the mod's doctrine bonuses or compounding military power.
- **Date**: 2026-08-25

### SUPERSEDED: Patron reward is irrevocable
- **Former decision**: The permanent `+0.33` diplomatic-reputation modifier would never be removed because of Liang's later status.
- **Superseded by**: The homeland-refusal branch below. The modifier is permanent only for a patron that does not repudiate the restoration compact.
- **Date**: 2026-08-25

### DECIDED: Patron may repudiate the homeland settlement
- **Decision**: When all three homeland provinces are assembled, the patron may refuse to transfer them to Liang. Refusal removes the permanent `+0.33` diplomatic-reputation reward, adds 100 liberty-desire points to Liang, and applies the twenty-year repudiation modifier to the patron.
- **Rationale**: Refusal remains a genuine political branch rather than an obviously superior land-retention option: the patron keeps the homeland but publicly breaks the original restoration compact and creates a maximally disloyal March.
- **Date**: 2026-08-25

### DECIDED: Refusal creates disloyalty, not a forced war
- **Decision**: The 100-liberty-desire consequence leaves Liang as a disloyal March operating under normal subject mechanics. Refusal does not immediately launch an independence war; Liang waits for sufficient strength, foreign support, or another normal opportunity to rebel.
- **Rationale**: Normal subject AI and diplomacy provide a more organic consequence than a scripted unavoidable war and allow the crisis to develop differently across campaigns.
- **Date**: 2026-08-25

### DECIDED: Twenty-year repudiation penalty
- **Decision**: Refusing the homeland settlement removes the patron's permanent `+0.33` diplomatic-reputation modifier and applies “Repudiated the Liang Restoration Compact” for twenty years: `-0.5` diplomatic reputation, `-10%` improve relations, and `-0.5` yearly prestige.
- **Rationale**: The resulting `-0.83` diplomatic-reputation swing is meaningful compensation for retaining the three homeland provinces, while the twenty-year diplomatic and prestige penalty remains recoverable rather than disabling the country for a generation.
- **Date**: 2026-08-25

### DECIDED: Early voluntary destruction counts as repudiation
- **Decision**: If the patron voluntarily revokes Liang's March status before homeland settlement, it loses the `+0.33` reward, receives the same twenty-year repudiation modifier, and Liang gains 100 liberty-desire points. If the patron voluntarily annexes Liang, the reward and penalty changes still occur but no liberty-desire effect remains to apply. Losing Liang involuntarily to an enemy does not count as repudiation.
- **Rationale**: The patron cannot evade the homeland-refusal consequences by dismantling the relationship before the request event, while forced military loss is distinguished from deliberate betrayal.
- **Date**: 2026-08-25

### DECIDED: Compact follows the patron entity but is not inherited
- **Decision**: A patron tag change preserves the compact, modifier, and tracked grant because the underlying country entity continues. If Liang is forcibly transferred to another overlord, the new overlord inherits neither the compact nor its reward, and the original patron is not punished. If the original patron is destroyed, the special homeland-exchange branch closes rather than passing to the conqueror; Liang remains an existing Zhou-realm polity under its resulting normal diplomatic status.
- **Rationale**: Restoration credit and obligations belong to the polity that actually made the grant, while tag changes should not erase continuity and unrelated conquerors should not receive unearned rights or duties.
- **Date**: 2026-08-25

### DECIDED: Homeland request waits for stable peace
- **Decision**: Once the joint ownership condition is met, the homeland request becomes pending. It fires only after both patron and Liang are at peace, none of the three homeland provinces is enemy-occupied, and those conditions remain stable for about thirty days. A renewed war pauses rather than cancels the pending request.
- **Rationale**: Delayed peacetime settlement avoids changing province ownership during active occupations or peace resolution while ensuring a temporary war cannot permanently erase earned restoration eligibility.
- **Date**: 2026-08-25

### DECIDED: AI restoration succeeds in roughly two campaigns out of three
- **Decision**: In a typical AI-only campaign, the single petition circuit targets an aggregate restoration success rate of roughly 60–70%. A representative ten-state roster therefore begins around a 10% per-state acceptance baseline, with contextual AI weighting to move individual states above or below that baseline.
- **Rationale**: Liang should usually but not inevitably find a patron. A roughly two-thirds aggregate success rate keeps both restoration and permanent failure visible across repeated campaigns without making the first randomly visited state an automatic patron.
- **Date**: 2026-08-25

### DECIDED: Contextual AI acceptance weights
- **Decision**: The implemented 1444 roster contains about 28 independent eligible states, so AI begins from a calibrated 4:96 accept/refuse weight (rather than the representative ten-state draft's 10:90) to preserve the agreed 60–70% aggregate target. Acceptance is multiplied by about `0.75` for 5–7 provinces and `1.5` for 15 or more; `1.5` for sound finances with no loans and `0.5` for debt or negative balance; `0.5` while at war; `1.5` for ruler diplomacy 4 or higher and `0.75` for diplomacy 2 or lower; `0.5` when at or above diplomatic-relations capacity; and `0.5` when the selected grant has at least 10 development. Personality-specific weights are omitted to avoid DLC-dependent behavior.
- **Rationale**: Large, solvent, diplomatically minded states can afford the moral gesture and subject slot, while war, debt, diplomatic overextension, or an unusually costly minimum-development province make refusal rational. The multipliers preserve the aggregate two-thirds target while producing legible variation between patrons.
- **Date**: 2026-08-25

### DECIDED: Petition travel cadence
- **Decision**: The Tianzi-court introduction fires about 90 days after campaign start; the first feudatory petition follows about 90 days later. Each refusal schedules the next valid stop after 180 days. A recorded target that has become invalid delays the route by only 30 days before being skipped.
- **Rationale**: A typical ten-state failed circuit therefore lasts roughly four to five years, long enough to feel like a genuine wandering mission without becoming a decades-long background queue. Short invalid-target skips prevent dead states from consuming full travel intervals.
- **Date**: 2026-08-25

### DECIDED: Failed-circuit epilogue
- **Decision**: If every recorded target refuses or becomes invalid, the envoys return their credentials to the Tianzi, the Liang heir dissolves the court-in-exile, and the royal household retires into ordinary registered life. Zhou-realm members receive one closing “Liang Envoys Return Empty-Handed” notice, no country is punished, `LGU` remains dormant, and the chain closes permanently.
- **Rationale**: Formal dissolution explains why a surviving dynasty does not simply repeat the petition later, while a realm-wide epilogue gives the single-circuit failure a visible narrative ending without contradicting the decision that refusals are individually lawful.
- **Date**: 2026-08-25

### DECIDED: Scope limited to standard 1444 single-player starts
- **Decision**: The chain is designed only for a fresh standard 1444 campaign. It does not add compatibility behavior for later bookmarks or existing saves, does not define special multiplayer notification or recipient rules, and does not handle the edge case in which the Tianzi disappears before the 90-day introduction.
- **Rationale**: Constraining the supported scenario keeps the opening chain focused and avoids expanding the design around situations the user does not currently want to support.
- **Date**: 2026-08-25

### DECIDED: Core and capital lifecycle
- **Decision**: Initial restoration gives Liang a core on its temporary grant, makes that province its capital, and adds Liang cores to Wuwei, Jingyuan, and Yongchang without changing the grant's culture or religion. On an honored homeland settlement, Liang's capital moves to Wuwei, the three homeland provinces remain or become Liang cores and territory, the patron's cores on those provinces are removed, the surviving temporary grant returns with a patron core, and Liang's core on that grant is removed. Other Liang conquests are untouched.
- **Rationale**: Immediate homeland cores support subject reconquest gameplay, while moving the capital and cleaning both sides' cores makes the promised territorial exchange final and prevents recurring claims on the returned grant.
- **Date**: 2026-08-25

## Open Threads

- None. The core event-chain design is ready for implementation.

## Parking Lot

- Exact localized event prose, titles, pictures, and tooltip wording.
- Technical state-tracking architecture, scripted-effect reuse, validation, and in-game test matrix.
- Later bookmarks, existing-save migration, multiplayer-specific behavior, and Tianzi-loss-before-introduction are explicitly out of scope.
