# Lightweight Backbone Experiment

The current AnyVisLoc baseline is frozen under
`experiments/baseline_anyvisloc/frozen_20260823`.

The first step is an encoder-only MobileNetV3-Large benchmark. It does not
change CAMP, RoMa, PnP, or any existing result. A trained retrieval checkpoint
is required before it can be used for localization. Retrieval Recall@1/5/10
must be measured before running the full CDA-FastReg pipeline.
