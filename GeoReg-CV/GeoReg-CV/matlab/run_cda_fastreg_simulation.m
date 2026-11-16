function summary = run_cda_fastreg_simulation(jsonPath, outputDir)
% Replay CDA-FastReg localization results in MATLAB.

if nargin < 1 || isempty(jsonPath)
    jsonPath = 'D:\GeoReg-CV\outputs\scene01_cda_fastreg_demo\scene01_cda_simulation_points.json';
end
if nargin < 2 || isempty(outputDir)
    outputDir = 'D:\GeoReg-CV\outputs\matlab_simulation';
end
if ~isfile(jsonPath)
    error('Simulation JSON not found: %s', jsonPath);
end
if ~isfolder(outputDir)
    mkdir(outputDir);
end

jsonText = fileread(jsonPath);
% Python exports UTF-8-with-BOM JSON on Windows; remove the BOM for MATLAB.
if ~isempty(jsonText) && double(jsonText(1)) == 65279
    jsonText = jsonText(2:end);
end
payload = jsondecode(jsonText);
if isstruct(payload) && isfield(payload, 'entities')
    entities = payload.entities;
    nestedFormat = true;
else
    % Also accept scene01_cda_all_geo_positions.json, which is a flat array.
    entities = payload;
    nestedFormat = false;
end
if isempty(entities) || ~isstruct(entities)
    error('The simulation JSON contains no valid entities.');
end
n = numel(entities);

sampleId = strings(n, 1);
route = strings(n, 1);
gt = zeros(n, 3);
pred = zeros(n, 3);
errors = nan(n, 1);
runtime = nan(n, 1);
top1Inliers = nan(n, 1);
success1 = false(n, 1);
success3 = false(n, 1);
success5 = false(n, 1);

for i = 1:n
    e = entities(i);
    sampleId(i) = string(e.sample_id);
    if nestedFormat
        route(i) = string(e.adaptive_strategy.route);
        gt(i, :) = [e.observer_view.gt_position.x, e.observer_view.gt_position.y, e.observer_view.gt_position.z];
        pred(i, :) = [e.estimated_geo_position.x, e.estimated_geo_position.y, e.estimated_geo_position.z];
        errors(i) = double(e.estimated_geo_position.error_m);
        runtime(i) = double(e.runtime.total_time_s);
        top1Inliers(i) = double(e.adaptive_strategy.top1_best_inliers);
        success1(i) = logical(e.status.success_1m);
        success3(i) = logical(e.status.success_3m);
        success5(i) = logical(e.status.success_5m);
    else
        route(i) = string(e.adaptive_route);
        gt(i, :) = [e.gt_x, e.gt_y, e.gt_z];
        pred(i, :) = [e.pred_x, e.pred_y, e.pred_z];
        errors(i) = double(e.error_m);
        runtime(i) = double(e.total_time_s);
        top1Inliers(i) = double(e.top1_best_inliers);
        success1(i) = logical(e.success_1m);
        success3(i) = logical(e.success_3m);
        success5(i) = logical(e.success_5m);
    end
end

[~, order] = sort(sampleId);
sampleId = sampleId(order); route = route(order);
gt = gt(order, :); pred = pred(order, :);
errors = errors(order); runtime = runtime(order);
top1Inliers = top1Inliers(order);
success1 = success1(order); success3 = success3(order); success5 = success5(order);

summary = struct();
summary.json_path = jsonPath;
summary.output_dir = outputDir;
summary.samples = n;
summary.mean_error_m = mean(errors, 'omitnan');
summary.median_error_m = median(errors, 'omitnan');
summary.max_error_m = max(errors, [], 'omitnan');
summary.success_at_1m_pct = mean(success1) * 100;
summary.success_at_3m_pct = mean(success3) * 100;
summary.success_at_5m_pct = mean(success5) * 100;
summary.mean_runtime_s = mean(runtime, 'omitnan');
summary.median_runtime_s = median(runtime, 'omitnan');
summary.route_counts = count_routes(route);

resultTable = table(sampleId, route, gt(:, 1), gt(:, 2), gt(:, 3), ...
    pred(:, 1), pred(:, 2), pred(:, 3), errors, runtime, top1Inliers, ...
    success1, success3, success5, ...
    'VariableNames', {'sample_id', 'route', 'gt_x', 'gt_y', 'gt_z', ...
    'pred_x', 'pred_y', 'pred_z', 'error_m', 'runtime_s', 'top1_inliers', ...
    'success_1m', 'success_3m', 'success_5m'});
writetable(resultTable, fullfile(outputDir, 'cda_fastreg_matlab_records.csv'));
save(fullfile(outputDir, 'cda_fastreg_matlab_data.mat'), ...
    'summary', 'resultTable', 'gt', 'pred', 'errors', 'runtime', 'route');

fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100, 100, 1500, 900]);
tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

nexttile;
plot(gt(:, 1), gt(:, 2), 'go-', 'LineWidth', 1.2, 'MarkerSize', 4, 'DisplayName', 'Ground truth');
hold on;
plot(pred(:, 1), pred(:, 2), 'r.-', 'LineWidth', 1.0, 'MarkerSize', 10, 'DisplayName', 'Prediction');
for i = 1:n
    plot([gt(i, 1), pred(i, 1)], [gt(i, 2), pred(i, 2)], '-', ...
        'Color', [0.75, 0.75, 0.75], 'HandleVisibility', 'off');
end
grid on; axis equal; xlabel('X / m'); ylabel('Y / m');
title('Ground-truth and predicted image positions'); legend('Location', 'best');

nexttile;
plot(1:n, errors, 'b.-', 'LineWidth', 1.1, 'MarkerSize', 9); hold on;
yline(1, 'g--', '1 m'); yline(5, 'r--', '5 m'); yline(20, 'k--', '20 m');
grid on; xlabel('Sample index'); ylabel('Localization error / m'); title('Localization error');

nexttile;
plot(1:n, runtime, 'Color', [0.15, 0.35, 0.75], 'LineWidth', 1.1);
grid on; xlabel('Sample index'); ylabel('Runtime / s');
title(sprintf('Runtime (mean %.2f s)', summary.mean_runtime_s));

nexttile;
[routeNames, ~, routeIndex] = unique(route, 'stable');
routeCounts = accumarray(routeIndex, 1);
bar(categorical(routeNames), routeCounts, 'FaceColor', [0.2, 0.55, 0.75]);
grid on; xlabel('Adaptive route'); ylabel('Samples'); title('Route distribution'); xtickangle(25);

sgtitle(sprintf('CDA-FastReg MATLAB replay | N=%d | Success@5m=%.2f%%', ...
    n, summary.success_at_5m_pct));
exportgraphics(fig, fullfile(outputDir, 'cda_fastreg_matlab_overview.png'), 'Resolution', 160);
close(fig);

write_summary_text(summary, fullfile(outputDir, 'cda_fastreg_matlab_summary.txt'));
fprintf('MATLAB simulation complete. Outputs: %s\n', outputDir);
fprintf('Samples: %d | Success@5m: %.2f%% | Mean error: %.3f m | Mean time: %.3f s\n', ...
    summary.samples, summary.success_at_5m_pct, summary.mean_error_m, summary.mean_runtime_s);
end

function counts = count_routes(route)
names = unique(route, 'stable');
values = zeros(numel(names), 1);
for i = 1:numel(names)
    values(i) = sum(route == names(i));
end
counts = struct();
for i = 1:numel(names)
    counts.(matlab.lang.makeValidName(char(names(i)))) = values(i);
end
end

function write_summary_text(summary, path)
fid = fopen(path, 'w');
if fid < 0
    warning('Could not write summary text: %s', path);
    return;
end
cleanup = onCleanup(@() fclose(fid)); %#ok<NASGU>
nl = newline;
fprintf(fid, ['CDA-FastReg MATLAB replay summary', nl]);
fprintf(fid, ['================================', nl]);
fprintf(fid, ['Samples: %d', nl], summary.samples);
fprintf(fid, ['Mean error (m): %.6f', nl], summary.mean_error_m);
fprintf(fid, ['Median error (m): %.6f', nl], summary.median_error_m);
fprintf(fid, ['Max error (m): %.6f', nl], summary.max_error_m);
fprintf(fid, ['Success@1m (%%): %.4f', nl], summary.success_at_1m_pct);
fprintf(fid, ['Success@3m (%%): %.4f', nl], summary.success_at_3m_pct);
fprintf(fid, ['Success@5m (%%): %.4f', nl], summary.success_at_5m_pct);
fprintf(fid, ['Mean runtime (s): %.6f', nl], summary.mean_runtime_s);
fprintf(fid, ['Median runtime (s): %.6f', nl], summary.median_runtime_s);
end
