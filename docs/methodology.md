# Methodology

## Estimand and analysis population

The primary estimand is the intention-to-treat difference in the probability of purchase within 24 hours among all users randomized at their first eligible checkout. User-level assignment prevents cross-session switching. No post-assignment engagement condition is used to define the analysis population.

## Prospective planning

The design uses a 45% baseline, 1.5 percentage-point absolute MDE, two-sided α=0.05, and 80% power. The normal approximation requires 17,315 users per arm. A separate 0.75-point business hurdle is used for commercial decision context; it is not retrofitted as the statistical MDE or treated as a universal rule requiring a confidence bound to cross it before shipping.

## Validity checks

The SRM chi-square test compares observed arm counts with the planned 50/50 allocation before outcomes are analyzed. Standardized differences assess balance on device, returning status, prior purchase, sessions, and revenue. Required-field missingness, eligibility, duration, daily volume, and assignment uniqueness are also checked. A non-significant SRM result is necessary reassurance, not proof of valid randomization.

## Inference

The primary binary metric uses a difference in proportions with an unpooled standard error and two-sided 95% confidence interval. Continuous metrics use differences in means with independent-arm standard errors. Effect sizes and intervals drive interpretation; p-values summarize compatibility with a zero-effect null.

Revenue per assigned user is the preferred commercial metric because it preserves ITT. AOV and refund rate among buyers condition on a post-treatment event and may mix causal effects with changed buyer composition. The public results therefore report refunds per assigned user and label conditional AOV appropriately.

## CUPED

The CUPED covariate is purchase during the 28-day pre-period, recorded before assignment. The adjustment is `Y_adj = Y − θ(X − mean(X))`, where θ is the outcome–covariate covariance divided by covariate variance. Randomization makes the covariate mean-balanced in expectation, so the effect estimate should remain similar while variance can fall.

The realized correlation is only 0.107, yielding 1.15% variance reduction. This modest result is retained. CUPED cannot fix invalid assignment, treatment-dependent missingness, or use of post-treatment covariates.

## Heterogeneity and time

Device and new/returning status are the only pre-specified segment families. Logistic interaction terms test differences between treatment effects directly. Individual subgroup p-values are not compared as proof of heterogeneity. With two declared families and inconclusive interactions, subgroup findings remain directional.

Time dynamics are summarized weekly and tested with a treatment-by-experiment-day interaction. The 28-day endpoint is fixed. Daily or cumulative monitoring is diagnostic only and is not used for optional stopping.

## Synthetic construction

`src/generate_data.py` assigns treatment independently after generating pre-treatment attributes. Purchase probability is generated coherently from latent intent and observed attributes, with a modest treatment effect that varies by device and a small early novelty component. Treatment also changes latency and has pre-specified order-value, refund, and support parameters. These inputs are fixed in code and were not revised after observing realized results.

Because the analyst controls the synthetic world, this case cannot establish external validity. It demonstrates design, estimation, validation, and decision discipline.

