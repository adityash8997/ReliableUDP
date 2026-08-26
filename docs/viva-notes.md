# Viva Notes

## UDP

- UDP provides best-effort datagram delivery without reliability.
- Packets can be lost, duplicated, reordered, or corrupted.
- The reliability layer must add sequence numbers, ACKs, and retransmission logic.

## Packet format

- A custom packet format is needed to keep the implementation explicit and explainable.
- Checksums detect corruption.
- Sequence numbers help identify duplicates and out-of-order packets.

## Channel emulator

- Deterministic seeds allow experiment reproducibility.
- The emulator supports controlled impairments so we can test protocol behavior under realistic conditions.

## Academic boundary

The core ARQ algorithms remain student-owned and will be implemented in later phases; the infrastructure here exists to support them cleanly.
