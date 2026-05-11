# Separate Cleanup Agent View From Private Evaluation

Roboclaws cleanup harnesses must separate the Cleanup Agent's public inputs from
the Mess Generator and Scorer's private truth. The next real-world-style cleanup
harness will expose only a metric map, room-level fixture hints, public fixture
IDs, and robot-local visible-object detections to the Cleanup Agent, while the
Generated Mess Set, acceptable destination sets, and target counts remain private
Scorer data shown only in post-run evaluation artifacts. Deterministic scoring
stays authoritative for v1 so harness metrics are repeatable; model-assisted
scoring may be added later as advisory evidence.
