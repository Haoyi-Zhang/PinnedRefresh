# Pinned-share refresh

Exact finite-field validation for **Secrecy and Cadence for Proactive Refresh with Pinned Shares**.

This directory is a standalone repository. It contains the written mathematical argument, source, literal synthetic inputs, certificates, exact distribution summaries, tests, resource records, and deterministic reproduction commands. It has no dependency on the manuscript directory, a private cache, an external solver, a network service, or a deployed recovery system.

## Result and boundary

A fixed pool stores evaluations of one degree-less-than-`k` polynomial with the secret as its constant term. An unavailable holder retains a scalar that must remain a *current* share after the other holders refresh. The refresh therefore pins that evaluation coordinate. This is not a changing-universe committee-transfer protocol, a stale-share catch-up protocol, or an implementation of secure erasure.

For public slot-exposure budgets `b[0],...,b[T-1]` and boundary pin budgets `u[0],...,u[T-2]`, define

```text
L[0]   = 0
L[e+1] = min(u[e], L[e] + b[e])
R[T-1] = 0
R[e]   = min(u[e], R[e+1] + b[e+1])
Gamma  = max_e (b[e] + L[e] + R[e]).
```

Uniform constrained refresh is secret for every permitted trace exactly when `Gamma < k`. If `Gamma >= k`, a concrete permitted trace transports `k` distinct evaluations to one slot and reconstructs the secret for every polynomial-valid pin-preserving update distribution. `Gamma` is an uncapped budget capacity; an instantiated trace still has at most `n` distinct coordinates, and all threshold decisions assume `k <= n`.

The argument also identifies `Gamma` with the minimum bottleneck width of a consecutive interval partition. That dual view gives a minimum-charge offline robust refresh schedule or an impossibility witness. It is a theorem about public worst-case budgets and known future charges, not an online predictor.

The article derives additional parameter rules without changing the model:

- `Gamma` is coordinatewise monotone and one-Lipschitz in each integer budget coordinate. If the secrecy margin is `m = k - 1 - Gamma`, any collection of budget increases with total L1 size at most `m` preserves secrecy.
- A threshold satisfying secrecy and cooperative recovery exists exactly when `Gamma + 1 <= n - u_rec`; every integer in that interval works for the two information-theoretic requirements.
- For constant budgets, `Gamma = min(T*b, ceil(T/2)*b + u, b + 2*u)`. When `b > 0` and `b + 2*u < k`, every finite horizon is safe. Otherwise the largest safe positive horizon is the maximum of `floor((k-1)/b)` and twice the nonnegative value `floor((k-1-u)/b)`.
- Every public-budget instance has a short safe partition certificate or a short unsafe transport/reconstruction certificate, and never both.
- If at least `k-1` distinct coordinates are pinned at a boundary, the zero-constant refresh space is zero-dimensional: a nominal refresh adds no entropy.

Cooperative recovery additionally requires `k <= n - u_rec`. There are no malicious-party, guaranteed-erasure, network-liveness, changing-membership, online-scheduling, or deployment-performance claims.

## Passive realization and cost ledger

The direct passive procedure lets each of the `p` online dealers sample a polynomial from the `d`-dimensional constrained refresh space, send evaluations to the other online recipients through private authenticated channels, and erase old state and transients after commit. The direct realization uses:

- `p(p-1)` transmitted field elements;
- `p*d` sampled field elements, while the aggregate update still has support dimension `d`;
- `O(p^2*k)` direct polynomial-evaluation work and `O(p^2)` recipient additions.

These are transparent operation counts, not an optimality or benchmark claim. The security proof assumes at least one honest online dealer when `d > 0`, atomic refresh, a fixed corrupt set during one refresh, ideal private channels, and actual erasure.

## Requirements

Use Python 3.10 or later on Linux or another compatible Unix. The runners use only the standard library and the Unix `resource` module. The executable contract supports prime fields; the written argument permits arbitrary finite fields. Arithmetic uses exact Python integers.

The stored case files are the reproduction inputs. Generators document how they were selected, but regenerated pseudorandom selections are not a substitute for the literal retained inputs.

## Clean reproduction

Run from this repository root, with output paths that are empty or absent:

```sh
python reproduce.py --output replay-linear
python reproduce_pinned.py --output replay-pinned
python -m unittest discover -s tests -v
```

The main runners are sequential, use one worker and no child processes, and enforce a 110-second CPU limit and 2-GiB address-space limit. A fresh final recheck produced:

- 711 generic traces: 375 hiding and 336 revealing;
- 59 pinned controls: 28 hiding and 31 revealing;
- 16 paired variable-budget concrete traces and 64 schedule subsets;
- 850 concrete traces in total: 427 hiding and 423 revealing;
- 44,111 complete field assignments in the two main clean runners;
- 770 rejected false certificate mutations;
- 42 observation-span metamorphic checks;
- 32 passing unit tests;
- 144 exhaustively visited interval partitions for retained certificate cases;
- 250 real/ideal local-message assignments with identical retained histograms;
- an independent oracle covering 2,460 capacity--partition vectors, 25,600 complete concrete pin/exposure systems (18,128 revealing), 2,565 dominating budgets, 2,145 constrained schedules, 300 constant-budget formulas, 6,820 fixed-pin formulas, and 220 horizon inversions.

Counting every direct field assignment and each retained outer/oracle check once yields 86,203 obligations. This is below the frozen 100,000-obligation retained-evidence ceiling. Historical development and clean-reproduction reruns repeat some obligations and are recorded separately in `results/campaign-accounting.json`; they add no distinct scientific case.

These are finite checks, not a machine-checked proof of the general theorem and not a workload or deployment study. The final recheck repeated existing cases after the manuscript expansion and added no new scientific case or claim. `results/campaign-accounting.json` records that this additional replay exceeds the original conservative cumulative repeated-assignment accounting while remaining far below the CPU, memory, worker, and per-run limits.

For individual outputs:

```sh
python certify.py cases/trace-example.json --output trace-certificate.json
python certify.py cases/trace-example.json --certificate trace-certificate.json
python certify_pinned.py cases/pinned-example.json --output pinned-certificate.json
python certify_pinned.py cases/pinned-example.json --certificate pinned-certificate.json
python plan_refresh.py cases/schedule-example.json --output schedule.json
```

The retained schedule example has cost 2, refresh boundaries 2 and 4, cuts `[0,2,4,7]`, and interval weights 2, 2, and 3 for threshold 4.

Optional generators are:

```sh
python make_cases.py --output generated-traces.json
python make_pinned_cases.py --output generated-pinned.json
python make_budget_cases.py --output generated-budgets.json
```

The final recheck parsed each generated JSON file and confirmed equality with the corresponding retained input in `cases/`.

## Why the checks are structurally different

`src/producer.py` constructs certificates with Gaussian elimination. `src/checker.py` imports neither the producer nor its elimination routine: it uses Horner evaluation for a normalized hiding polynomial and coefficient-basis evaluation for a revealing linear identity. The separation is useful fault detection, not independent authorship or independent peer review.

`src/oracle.py` directly enumerates independent-epoch polynomial distributions. `src/pinned.py` instead enumerates factored constrained increments and verifies pin invariants. Their conditional-distribution comparisons do not call elimination. The generic snapshot/difference model is a control only; a difference observation is not a substitute for a corrupt participant's complete state.

`src/budgets.py` computes temporal capacities, bottleneck partitions, safe schedules, root certificates, and central-share transport witnesses. `src/exhaustive_validation.py` supplies independent modular-rank, partition, and subset routines rather than reusing the producer, checker, or pinned encoder; it calls the scheduler only as the system under test and compares it with exhaustive feasible boundary subsets. `verify_transport` checks equality paths and Lagrange weights directly. The bounded implementation retains complete paths and direct interval sums for clarity, giving an unrestricted `O(T^3)` implementation; the mathematical recurrence admits an `O(T^2)` prefix-sum/predecessor implementation. No runtime-optimal code claim is made.

The local simulation case has field size 5, threshold 3, one pinned coordinate, one corrupt dealer/recipient, and two honest dealers. Its one-coordinate evaluation image is the entire field. The written simulator handles general proper images; that stronger case is not exhausted by this finite example.

## Evidence and limitations

`proofs/argument.md` is a self-contained written argument for the retained results. `claim_evidence_ledger.csv` maps each material claim to its theorem, proof, executable check, input, and raw result. `literature-calibration.csv` and `literature-calibration.md` preserve the 12+5+5 structured source-calibration matrix and the recorded access depth for each slot. `reference-audit.csv` inventories all cited entries and distinguishes fresh metadata checks from structural-only checks. `external_resources.csv` records scholarly sources, access depth, and integration limits. `PROVENANCE.md` records substantive AI generation and the external-use restrictions.

No theorem prover, independently staffed audit, malicious-party implementation, trusted-erasure mechanism, real service, or human-subject evidence was used. The 12+5+5 matrix records 22 slots over 21 unique works at the access depths stated in the ledger and supports scope-specific interface separation, not a global priority claim. For Chorus, official metadata, abstract, DOI/pages, and public artifact documentation are retained at their actual access depth; the complete paper text was not retrievable here, and no pin-equivalence or protocol-level delta is asserted. Independent human mathematical/source review, authorship/accountability approval, and truthful external-use policy review remain open. This is an internal research artifact, not a certified submission package.
