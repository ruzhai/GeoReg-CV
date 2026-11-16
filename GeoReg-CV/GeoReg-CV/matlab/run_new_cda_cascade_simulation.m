function summary = run_new_cda_cascade_simulation(inputRoot, outputDir)
% Replay the new Top1 -> Top2 -> Top5 CDA-FastReg cascade.
% The input can be a directory containing per-sample cda_result.json files,
% one cda_result.json file, or an already exported simulation JSON file.

if nargin < 1 || isempty(inputRoot)
    inputRoot = 'D:\GeoReg-CV\outputs\online_cda\Scene_01';
end
if nargin < 2 || isempty(outputDir)
    outputDir = 'D:\GeoReg-CV\outputs\matlab_cascade_simulation';
end
if ~isfolder(outputDir)
    mkdir(outputDir);
end

jsonPath = fullfile(outputDir, 'matlab_cascade_input.json');
payload = collect_payload(inputRoot);
write_json_without_bom(payload, jsonPath);

summary = run_cda_fastreg_simulation(jsonPath, outputDir);
summary.input_root = inputRoot;
summary.route_counts = count_payload_routes(payload.entities);

save(fullfile(outputDir, 'cda_cascade_summary.mat'), 'summary');
write_route_summary(summary, fullfile(outputDir, 'cda_cascade_route_summary.txt'));
fprintf('New cascade simulation complete. Samples: %d\n', summary.samples);
end

function payload = collect_payload(inputRoot)
if isfile(inputRoot)
    payload = decode_json_file(inputRoot);
    if isfield(payload, 'entities')
        return;
    end
    if isfield(payload, 'localization')
        payload = struct('coordinate_system', 'AnyVisLoc Scene local metric coordinate', ...
            'entities', cda_result_to_entity(payload));
        return;
    end
    error('Unsupported JSON format: %s', inputRoot);
end

files = dir(fullfile(inputRoot, '**', 'cda_result.json'));
if isempty(files)
    error('No cda_result.json files found under: %s', inputRoot);
end

latest = containers.Map('KeyType', 'char', 'ValueType', 'any');
for i = 1:numel(files)
    filePath = fullfile(files(i).folder, files(i).name);
    result = decode_json_file(filePath);
    if ~isfield(result, 'sample_id')
        continue;
    end
    scene = char(result.scene_name);
    key = [scene, '/', char(result.sample_id)];
    item = struct('result', result, 'filePath', filePath, 'datenum', files(i).datenum);
    if ~isKey(latest, key) || item.datenum > latest(key).datenum
        latest(key) = item;
    end
end

keysList = keys(latest);
if isempty(keysList)
    error('No valid cda_result.json records found under: %s', inputRoot);
end
entities = repmat(cda_result_to_entity(latest(keysList{1}).result), 1, numel(keysList));
for i = 1:numel(keysList)
    entities(i) = cda_result_to_entity(latest(keysList{i}).result);
end
payload = struct('coordinate_system', 'AnyVisLoc Scene local metric coordinate', ...
    'entities', entities);
end

function entity = cda_result_to_entity(result)
loc = result.localization;
gt = result.ground_truth;
strategy = result.adaptive_strategy;
timing = result.timing;
entity = struct();
entity.scene = result.scene_name;
entity.sample_id = result.sample_id;
entity.observer_view = struct('source', '', 'gt_position', struct('x', gt.x, 'y', gt.y, 'z', gt.z));
entity.uav_reference_view = struct('source', 'aerial');
entity.estimated_geo_position = struct('x', loc.pred_x, 'y', loc.pred_y, 'z', loc.pred_z, 'error_m', loc.pred_error_m);
entity.status = struct('success_1m', loc.pred_error_m <= 1, 'success_3m', loc.pred_error_m <= 3, 'success_5m', loc.pred_error_m <= 5);
entity.runtime = struct('total_time_s', timing.online_pipeline_wall_time_s);
entity.adaptive_strategy = struct('route', strategy.route, ...
    'top1_best_inliers', strategy.top1_best_inliers, ...
    'confidence_threshold', strategy.confidence_threshold, ...
    'fallback_used', strategy.fallback_used, ...
    'source_method', 'CDA-FastReg');
end

function payload = decode_json_file(path)
text = fileread(path);
if ~isempty(text) && double(text(1)) == 65279
    text = text(2:end);
end
payload = jsondecode(text);
end

function write_json_without_bom(payload, path)
fid = fopen(path, 'w');
if fid < 0
    error('Cannot write temporary JSON: %s', path);
end
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
fwrite(fid, jsonencode(payload), 'char');
end

function counts = count_payload_routes(entities)
routes = strings(numel(entities), 1);
for i = 1:numel(entities)
    routes(i) = string(entities(i).adaptive_strategy.route);
end
names = unique(routes, 'stable');
counts = struct();
for i = 1:numel(names)
    counts.(matlab.lang.makeValidName(char(names(i)))) = sum(routes == names(i));
end
end

function write_route_summary(summary, path)
fid = fopen(path, 'w');
if fid < 0
    return;
end
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
fprintf(fid, 'New CDA-FastReg cascade simulation\n');
fprintf(fid, '===================================\n');
fprintf(fid, 'Input: %s\n', summary.input_root);
fprintf(fid, 'Samples: %d\n', summary.samples);
fprintf(fid, 'Success@5m: %.4f%%\n', summary.success_at_5m_pct);
fprintf(fid, 'Mean error: %.6f m\n', summary.mean_error_m);
fprintf(fid, 'Mean runtime: %.6f s\n', summary.mean_runtime_s);
end
