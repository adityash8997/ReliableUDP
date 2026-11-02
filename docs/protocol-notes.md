# Protocol Notes

## Stop-and-Wait (implemented)

The current Stop-and-Wait protocol exchanges START metadata, sequential DATA packets, and FIN. It waits for the matching ACK after each packet, retransmits after a socket timeout up to its configured retry limit, and rejects a completed transfer if file size or SHA-256 does not match. The actual experiment runner currently uses this implementation only on a clean localhost channel.

## Go-Back-N and Selective Repeat (not implemented)

The classes exist to preserve the protocol interface, but their transfer and packet operations raise `NotImplementedError`. They must not be used to claim actual transfer or performance results.

## Timeout and measurements

The configured RTO in milliseconds controls the sender's ACK socket timeout and receiver polling timeout in the current Stop-and-Wait path. A timeout increments timeout and retransmission metrics; a timeout-associated RTO sample records that configured value. There is no adaptive RTO estimator, Jacobson/Karels calculation, or implemented Karn algorithm. Measurement omits RTT samples for retransmitted packets because the ACK's matching send attempt cannot be identified safely.

## Channel emulator boundary

The standalone deterministic emulator supports packet impairment tests, but it is not connected to the active UDP sender/receiver path. Nonzero impairment settings in actual experiment configurations are rejected. Only explicitly marked synthetic demonstrations can generate illustrative values for unavailable protocols or impairment scenarios; those values are not protocol measurements.