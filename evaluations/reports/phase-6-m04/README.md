# M04 verification reports

All inputs are synthetic; no microphone or external model provider was used. Human acceptance and full-lecture qualification remain open.

| Report | Observation |
| --- | --- |
| [Initial v2](v2-initial.json) | 2/3 structurally valid; rejected inconsistent coverage; assistant review identified missing formulas and unsupported elaboration. |
| [v3 before repair](v3-before-repair.json) | 2/3 valid; correction fixture still rejected for coverage mismatch. |
| [Repaired CS draft adapter](draft-cs.json) | 3/3 valid, about 74, 31 and 27 seconds. The app computes source quotes, immutable references and coverage; the LLM writes prose and chooses supporting passages. |
| [Initial universal trials](universal-before-style-fix.json) | Biology/history generated valid notes, but the requested presentation was not followed. |
| [History style](history-style.json) | Three brief questions and answers, preserving long-term cause versus trigger and evidence limitations; about 49 seconds. |
| [Biology style](biology-style.json) | Cornell question cues covering osmosis, relative concentrations and equilibrium; about 50 seconds. |
| [Saved lecture](saved-lecture.json) | Actual Qwen3 note revision 2 from the previously failing synthetic speech lecture; canonical validation, saved export and all 14 cited audio excerpts passed authenticated HTTP checks. |
| [Saved Markdown](saved-lecture.md) | The actual exported revision with its portable original-source appendix. |

Earlier wall times can include competing development model requests and are not comparable latency benchmarks. Model metadata records context/output settings and hashes; these are not a live-performance qualification. The later adapter adds a hash of the fully composed messages so presentation instructions are traceable as well as the static prompt.

Assistant inspection found remaining quality issues. The initial repaired binary-search fixture did not classify the unavailable board proof as a missing visual, although the unused source is exposed for review. The correction fixture labels an explicitly resolved correction as a conflict. The live second revision omits constant auxiliary space and does not follow the requested numbered-step presentation. Source validity verifies where evidence came from, not that every generated claim is fully supported or every detail preserved. These limits remain M04/G01/G02 work.

Application verification: 102 PostgreSQL backend tests, 60 JavaScript tests, frontend type checks, production builds, migration comparison, browser source playback and authenticated saved-export/audio checks. See [M04 implementation](../../../docs/implementation/phase-6-m04.md).
