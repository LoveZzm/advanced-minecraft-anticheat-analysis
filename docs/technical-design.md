# Technical Design

## Objective

This portfolio project demonstrates an explainable, data-driven approach to
prioritizing Minecraft-style gameplay sessions for human review. It operates on
simulated aggregate session telemetry and is intentionally separate from
punishment or enforcement.

## Detection Approach

### 1. Feature engineering

Raw counters are normalized into comparable rates such as clicks per second,
target switches per minute, resources per minute, and actions per minute.
Bounded ratios describe click consistency, tracking, path repetition, and path
efficiency. Input rows are validated before analysis so malformed telemetry
fails with an actionable error.

### 2. Explainable rule categories

Each requested behavior has an independent 0-100 score:

- **Autoclicker:** sustained click rate and unusually consistent timing
- **Reach:** maximum observed interaction distance
- **Aim assist:** snap rate, perfect tracking, and target-switch frequency
- **Bot behavior:** highly efficient repeated paths and low action diversity
- **Macro farming:** collection rate, repeated routes, duration, and overnight activity
- **Multi-signal:** escalation when independent categories trigger together

Soft and hard thresholds turn each measurement into a gradual severity rather
than a brittle pass/fail decision. Triggered checks become plain-language
evidence in the report.

### 3. Statistical outliers

The pipeline fits a population profile using the median and median absolute
deviation (MAD). The three strongest robust z-scores form the outlier score.
This layer can expose unexpected combinations without defining a rule for every
possible pattern, while remaining more resistant to extreme values than mean
and standard deviation.

### 4. Lightweight model

A small logistic regression is trained on a deterministic simulated reference
corpus that is separate from the sessions being analyzed. Inputs are
standardized, training uses batch gradient descent, and prediction produces a
supporting probability. The implementation is dependency-free and inspectable.

This is a workflow demonstration, not a valid model evaluation: the included
model trains and scores on the same synthetic population. A real system would
use time-based train/validation/test splits, mode-aware calibration, class
imbalance handling, model versioning, and monitored threshold selection.

### 5. Risk aggregation and review

Configurable weights combine rules, outliers, and model probability. Sessions
crossing the review threshold are sorted into review, high, and critical tiers.
The HTML report shows summary metrics, risk distribution, category breakdown,
top sessions, and evidence. CSV exports support deeper analysis.

## Limitations

- Aggregate telemetry cannot reconstruct packet timing, line-of-sight,
  knockback, lag compensation, or server-authoritative movement state.
- Simulated patterns are much cleaner than real adversarial behavior.
- Thresholds are illustrative and are not calibrated by mode, version, ping,
  input device, player skill, or accessibility needs.
- Labels are synthetic, so the model has no demonstrated precision, recall, or
  false-positive rate on real players.
- A session-level score may hide short-lived behavior changes.
- Overnight activity and long sessions are context signals only; neither is
  inherently suspicious.

For those reasons, no individual signal or combined score should directly
trigger punishment.

## Scaling To A Real Network

1. **Capture server-authoritative events.** Publish versioned combat, movement,
   interaction, and economy events to a durable stream with clear ownership and
   privacy controls.
2. **Build windowed features.** Compute short combat windows and longer player
   baselines, partitioned by game mode, protocol version, ping band, and other
   relevant context.
3. **Separate detection from enforcement.** Emit evidence-rich cases into a
   review service. Apply policy in a separate, auditable system with appeals.
4. **Create reliable labels.** Join moderator outcomes, replay review, controlled
   test clients, and high-confidence detections. Track label provenance.
5. **Evaluate by time and segment.** Measure precision-recall, calibration,
   review yield, and false positives across modes and player cohorts.
6. **Operate detections as products.** Version rules and models, shadow-test
   changes, monitor drift, define rollback paths, and record every decision.
7. **Harden against adaptation.** Combine server invariants, sequence models,
   graph/link analysis, randomized probes where appropriate, and adversarial
   evaluation without relying on obscurity.

The most valuable production outcome is not the largest number of flags. It is
a trustworthy system that gives investigators high-quality evidence while
minimizing harm to legitimate players.
