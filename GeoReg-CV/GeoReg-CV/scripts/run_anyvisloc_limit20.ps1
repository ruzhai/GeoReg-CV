$ErrorActionPreference = "Stop"
conda activate anyvisloc
cd D:\GeoReg-CV
python .\pipelines\run_anyvisloc_baseline.py --config .\configs\anyvisloc_baseline.yaml

