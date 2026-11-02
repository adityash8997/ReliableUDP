# Graph generation status

No graph is generated unless at least one protocol has two distinct actual parameter settings with the other recorded controls held fixed.

No performance graph was generated: the available actual dataset does not vary any required parameter.

## goodput_vs_loss_rate: BLOCKED

No actual nonzero loss-rate measurements exist; live actual execution rejects impaired channels.

## goodput_vs_window_size: INSUFFICIENT_DATA

Actual evidence does not vary window size within an implemented protocol and fixed control settings.

## retransmissions_vs_reordering_probability: BLOCKED

No successful actual records declare that reordering impairment was applied; configured probability alone is not evidence of applied reordering.

## rto_sensitivity: INSUFFICIENT_DATA

Configured RTO does not vary across controlled actual runs, so sensitivity cannot be assessed. Configured RTO is not the same as a measured RTO; timeout-derived samples are only present when timeouts occur.
