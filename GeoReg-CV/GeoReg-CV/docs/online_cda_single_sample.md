# Online CDA-FastReg single-sample localization

## Purpose

`pipelines/run_online_cda_sample.py` localizes one explicitly selected
AnyVisLoc sample without modifying the official project under
`D:/GD/Benchmark`.

The online decision uses only PnP success and inlier count. Ground-truth
position and localization error are retained for AnyVisLoc evaluation, but are
not used to choose the route.

## Flow

1. Initialize CAMP and RoMa once.
2. Load the reference map/DSM and execute retrieval once.
3. Match and localize candidate 1.
4. Accept when PnP succeeds and `best_inliers >= 1000`.
5. Otherwise match only candidates 2..N with the same model instances.
6. Save one final `cda_result.json` and `cda_result.csv`.

The fallback does not repeat model initialization, image retrieval, or Top1
matching.

## True Top2 fallback

```cmd
conda activate anyvisloc
cd /d D:\GeoReg-CV
python -u pipelines\run_online_cda_sample.py --sample-id L01_0120 --scene Scene_01 --fallback-topk 2 --visualize
```

The default center-localization policy is now cross-scene safe Direct-first:

```text
RoMa Top1 dense warp -> center certainty + forward/backward cycle check
  pass -> output the dense center correspondence and skip PnP
  fail -> reuse the same RoMa matches for PnP, then Top2/Top5 if needed
```

The default gates are `--center-confidence-threshold 0.10` and
`--center-cycle-threshold-px 2.0`.  They depend only on inference outputs;
ground truth is used after inference for evaluation only.

To force both Direct and PnP for an ablation comparison:

```cmd
python -u pipelines\run_online_cda_sample.py --sample-id L01_0120 --scene Scene_01 --center-execution-mode evaluation_both --no-visualize
```

To reproduce the original PnP-only behavior:

```cmd
python -u pipelines\run_online_cda_sample.py --sample-id L01_0120 --scene Scene_01 --center-execution-mode pnp_only --no-visualize
```

## Top5 fallback matching the historical ablation configuration

```cmd
conda activate anyvisloc
cd /d D:\GeoReg-CV
python -u pipelines\run_online_cda_sample.py --sample-id L01_0120 --scene Scene_01 --fallback-topk 5 --visualize
```

The historical directory named `fast_v3_top2_k1500_r03_limit120` used
`retrieval_k=2` for retrieval evaluation, while its runtime YAML still had
`RETRIEVAL_TOPN=5`. Its PnP files therefore contain five candidate results.
Use `--fallback-topk 5` when comparing with that historical result.

## Output

Results are stored under:

```text
D:/GeoReg-CV/outputs/online_cda/<scene>/<sample_id>/<timestamp>/
```

Important files:

- `cda_result.json`: final position, confidence, route, timing, and artifact paths.
- `cda_result.csv`: one-row tabular result.
- `localization_panel.png`: observer image, retrieval candidates, best PnP matches, map position, route, confidence, and timing.
- `position_map.png`: aerial-map overview with GT, prediction, and error connection.
- `online_cda.log`: complete console log for the single process.
- `VG_data_<sample_id>.pkl`: combined retrieval, matching, PnP, and route data.
- `retrieval/`: retrieval visualization output.
- `top1/`: candidate 1 matching visualization.
- `fallback_candidates_2_to_N/`: incremental fallback visualizations when used.

`output_status` is one of:

- `localized_high_confidence`
- `localized_low_confidence`
- `localization_failed`

## Verified performance

For `Scene_01/L01_0120` with Top5 fallback:

- Two-process implementation: 73.34 seconds wall time.
- Single-process model reuse: 29.42 seconds wall time.
- Speedup: about 2.49x.
- Final error: 0.446 m.
- Candidate inliers: `[169, 342, 140, 385, 2988]`.

For `Scene_01/L01_0001`, Top1 was accepted with 2966 inliers, no fallback was
executed, and the wall time was 21.53 seconds.
