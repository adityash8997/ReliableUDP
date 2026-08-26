# Packet Format

The custom packet format is intentionally simple and deterministic.

## Layout

The packet is serialized in network byte order using the struct format `!BBHIIH` for the header plus a trailing 2-byte checksum and payload.

```text
+---------------------+
| Version (1 byte)    |
+---------------------+
| Packet type (1 byte)|
+---------------------+
| Flags (1 byte)      |
+---------------------+
| Reserved (1 byte)   |
+---------------------+
| Sequence number     |
| (4 bytes)           |
+---------------------+
| Ack number (4 bytes)|
+---------------------+
| Window (2 bytes)    |
+---------------------+
| Payload length      |
| (2 bytes)           |
+---------------------+
| Checksum (2 bytes)  |
+---------------------+
| Payload             |
+---------------------+
```

## Packet types

- DATA = 0x01
- ACK = 0x02
- START = 0x03
- FIN = 0x04
- ERROR = 0x05

## Validation rules

- packet must be at least 18 bytes long
- version must be 1
- packet type must be known
- declared payload length must match actual payload length
- checksum must match the serialized header and payload
- malformed packets are rejected with a validation error

## Checksum

The checksum is computed using a simple 16-bit checksum over the packet header and payload bytes.
