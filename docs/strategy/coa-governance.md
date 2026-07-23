# COA Strategy Governance

`engine/coa_math.py` is the frozen COA baseline. It may be changed only through a documented strategy-version proposal, tests showing impact, a research experiment, and explicit approval.

Research variants must be registered as separate strategy versions. Their configuration, input dataset, replay assumptions, validation policy, risk policy, and results are immutable references. A promotion evaluation may recommend a version, but transition to `APPROVED` or `PRODUCTION` requires a named human approver.

This boundary prevents hindsight tuning from silently changing the results of already completed paper-trading research.
