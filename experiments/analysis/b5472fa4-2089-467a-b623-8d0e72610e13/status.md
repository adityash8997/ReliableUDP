# Actual-result analysis status

Valid successful actual runs: 2

## goodput_vs_loss_rate: BLOCKED

No actual nonzero loss-rate measurements exist; live actual execution rejects impaired channels.

## goodput_vs_window_size: INSUFFICIENT_DATA

Actual evidence does not vary window size within an implemented protocol and fixed control settings.

## retransmissions_vs_reordering_probability: BLOCKED

No successful actual records declare that reordering impairment was applied; configured probability alone is not evidence of applied reordering.

## rto_sensitivity: INSUFFICIENT_DATA

Configured RTO does not vary across controlled actual runs, so sensitivity cannot be assessed. Configured RTO is not the same as a measured RTO; timeout-derived samples are only present when timeouts occur.
