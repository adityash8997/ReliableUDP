# Viva Notes

## Why UDP needs a reliability layer

UDP sends datagrams but does not guarantee delivery, order, uniqueness, or integrity. ReliableUDP adds packet types, sequence numbers, checksums, ACKs and retransmission behavior above UDP. The current working transfer is Stop-and-Wait: it waits for an ACK for each sent packet before advancing.

## Integrity

The packet checksum validates an individual protocol datagram. The file-level SHA-256 compares the source bytes with the reconstructed destination bytes after transfer. These solve different problems; successful packet checksums alone do not prove that the complete file was reconstructed correctly.

## Metrics

Transfer duration uses a monotonic clock. Throughput is the number of serialized protocol-datagram bytes transmitted by both endpoints, including ACK/control traffic and retransmissions, multiplied by eight and divided by seconds; IP and UDP headers are excluded. Goodput is uniquely accepted application payload bytes multiplied by eight and divided by seconds. A retransmitted DATA packet is another transmission but not new useful payload. RTT is sampled only for first-attempt packets. Loss is null unless the live path can actually observe valid channel losses.

## Experiments and reproducibility

Each run stores source, status, configuration, seed, repetition, metrics and hashes. Generated source bytes are deterministic for the seed, but measured timing may vary with operating-system scheduling and machine load. Synthetic demo records are visibly labeled and never count as actual transfers. Legacy records without provenance remain unverified.

## Honest current scope

Two clean-channel Stop-and-Wait runs demonstrate transfer and integrity and provide only a small repeated-run observation; they do not establish a performance trend. GBN and SR remain stubs. The standalone channel emulator is not on the live UDP path, so loss/reordering/corruption/duplication/delay experiments are blocked. Only one actual RTO setting is represented; no RTO sensitivity conclusion is justified. See [experiments.md](experiments.md) for formulas, commands, schemas and family statuses.