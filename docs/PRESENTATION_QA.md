# Presentation and professor Q&A

## What has been implemented?

The project validates a dataset-based path from repeated SRAM measurements to
stability analysis, stable-bit selection, fuzzy-extractor key material,
HMAC-SHA256 challenge-response, and MQTT transport. The MQTT integration uses a
generated test key registry, not a live SRAM read on a microcontroller.

## Why 84 devices but 81 fuzzy-extractor records?

84 devices appear in the stability summary. The historical fuzzy-extractor
artifact contains 81 records, so every final figure must declare its cohort and
include a manifest that lists excluded UIDs and their eligibility reason. Do not
present 84 and 81 as interchangeable populations.

## Why are 2,816 stable bits consumed?

The default extractor creates 256 key bits and repeats each bit 11 times for
majority-vote correction: `256 × 11 = 2,816`. This is consumption by the chosen
prototype configuration, not the total stable-bit count available on a device.

## Is Inter-HD ideal?

No. The recorded mean is approximately 0.2703, below the ideal 0.5. This is
reported as dataset bias and motivates reliability-aware preprocessing; it is not
evidence of ideal raw-PUF uniqueness.

## Does helper data leak nothing?

No such claim is made. Helper data is public in the construction, but leakage
depends on PUF entropy, bias, selected positions, and the extractor design. A
formal leakage analysis remains future work.

## What remains future work?

Live SRAM acquisition, device-side `Rep()` on a microcontroller, protected
server-side enrollment records, constrained-device latency measurements, and a
formal helper-data leakage analysis.
