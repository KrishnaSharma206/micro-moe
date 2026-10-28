%% analyze.m  --  analysis of the multi-seed, multi-model dataset
% Reads dataset.csv (from sweep.py: one row per simulation run) and
% produces, for each traffic density in the dataset:
%   * one figure per metric with every car-following model set overlaid
%     (mean +/- 95% CI vs. AV penetration)                     <metric>_<period>_models.png
%   * one box plot per metric and model set (spread over seeds) <metric>_<period>_<model>_box.png
%   * summary.csv: per model/metric/penetration -- n, mean, sd, 95% CI,
%     paired difference vs 0% AV with its own 95% CI, % change, p-value label
%
% Changes vs. the 0% AV baseline are PAIRED within each model set: the same seed
% gives the same trip demand at every penetration rate. CIs and p-values use a
% normal approximation (fine for ~50+ seeds). With hundreds of seeds p-values
% become vanishingly small and uninformative, so they are reported as "<0.001";
% report the paired difference and its CI instead.
%
% Run with F5 or run('analyze.m'). No toolboxes required.

csv_path = 'ps1_dataset.csv';

csv_full = which(csv_path);
if isempty(csv_full)
    error('Could not find %s. cd into its folder first, or set csv_path to a full path.', csv_path);
end
out_dir = fullfile(fileparts(csv_full), 'figures');
if ~isfolder(out_dir)
    [ok, msg] = mkdir(out_dir);
    if ~ok
        out_dir = fullfile(tempdir, 'ps1_figures');
        warning('Cannot write next to the CSV (%s). Saving to %s instead.', msg, out_dir);
        if ~isfolder(out_dir), mkdir(out_dir); end
    end
end

T = readtable(csv_full);
if ~ismember('model_set', T.Properties.VariableNames)   % older single-model dataset
    T.model_set = repmat({'krauss'}, height(T), 1);
end
T.model_set = string(T.model_set);
models  = unique(T.model_set, 'stable');
periods = unique(T.period);
fprintf('Loaded %d runs from %s\n', height(T), csv_full);

metrics = { ...
    'avg_delay_s',       'Average delay (s)'; ...
    'avg_speed_mps',     'Average speed (m/s)'; ...
    'avg_travel_time_s', 'Average travel time (s)'; ...
    'avg_queue_length',  'Average queue length (vehicles)' ...
};

%% Data-quality check per model set
fprintf('\nData quality (should be 0 unfinished trips and 0 collisions):\n');
for imod = 1:numel(models)
    S = T(T.model_set == models(imod), :);
    fprintf('  %-24s runs=%4d  unfinished trips=%d  collisions=%d\n', ...
        char(models(imod)), height(S), sum(S.unfinished_trips), sum(S.collisions));
end

summary = {};

for ip = 1:numel(periods)
    period = periods(ip);
    tag = sprintf('period%g', period);
    Sper = T(T.period == period, :);

    fprintf('\n===== Traffic density: insertion period %g s =====\n', period);

    for im = 1:size(metrics, 1)
        field = metrics{im, 1};
        ylab  = metrics{im, 2};

        fprintf('\n%s\n', ylab);
        fprintf('  %-22s %6s %5s %10s %9s %10s %12s %10s\n', ...
            'model', 'AV %', 'n', 'mean', 'sd', '95% CI +/-', '% vs 0% AV', 'p (paired)');

        overlay = struct('model', {}, 'x', {}, 'mu', {}, 'ci', {});

        for imod = 1:numel(models)
            model = models(imod);
            S = Sper(Sper.model_set == model, :);
            if isempty(S), continue; end
            pens = unique(S.penetration);
            base = S(S.penetration == min(pens), :);

            mu = zeros(numel(pens), 1);
            ci = zeros(numel(pens), 1);

            for k = 1:numel(pens)
                Sk = S(S.penetration == pens(k), :);
                x = Sk.(field);
                n = numel(x);
                mu(k) = mean(x);
                sdv = std(x);
                ci(k) = 1.96 * sdv / sqrt(n);

                if pens(k) == min(pens)
                    pct = 0; md = 0; dlo = NaN; dhi = NaN; plab = '-';
                else
                    [~, ia, ib] = intersect(base.seed, Sk.seed);   % match runs by seed
                    d = Sk.(field)(ib) - base.(field)(ia);
                    nd = numel(d);
                    md = mean(d);
                    sed = std(d) / sqrt(nd);
                    dlo = md - 1.96 * sed;
                    dhi = md + 1.96 * sed;
                    pct = md / mean(base.(field)(ia)) * 100;
                    if sed > 0
                        p = erfc(abs(md / sed) / sqrt(2));   % two-sided, normal approx
                    else
                        p = NaN;
                    end
                    if isnan(p)
                        plab = 'n/a';
                    elseif p < 0.001
                        plab = '<0.001';
                    else
                        plab = sprintf('%.3f', p);
                    end
                end

                fprintf('  %-22s %6.0f %5d %10.3f %9.3f %10.3f %11.1f%% %10s\n', ...
                    char(model), pens(k) * 100, n, mu(k), sdv, ci(k), pct, plab);
                summary(end + 1, :) = {char(model), period, ylab, pens(k) * 100, n, mu(k), sdv, ...
                    mu(k) - ci(k), mu(k) + ci(k), md, dlo, dhi, pct, plab}; %#ok<SAGROW>
            end

            overlay(end + 1) = struct('model', char(model), 'x', pens * 100, 'mu', mu, 'ci', ci); %#ok<SAGROW>

            % ---- box plot: spread across seeds, one per model ----
            try
                fig = figure('Visible', 'off');
                ax = axes(fig);
                boxchart(ax, categorical(S.penetration * 100), S.(field));
                xlabel(ax, 'AV Penetration Rate (%)');
                ylabel(ax, ylab);
                title(ax, sprintf('%s: spread across seeds (%s)', strtrim(strtok(ylab, '(')), ...
                    strrep(char(model), '_', ' ')));
                grid(ax, 'on');
                style_light(fig, ax);
                save_fig(fig, fullfile(out_dir, sprintf('%s_%s_%s_box.png', field, tag, char(model))));
                close(fig);
            catch
                if exist('fig', 'var') && isgraphics(fig), close(fig); end
            end
        end

        % ---- all model sets overlaid: mean +/- 95% CI ----
        fig = figure('Visible', 'off');
        ax = axes(fig);
        hold(ax, 'on');
        for k = 1:numel(overlay)
            errorbar(ax, overlay(k).x, overlay(k).mu, overlay(k).ci, '-o', 'LineWidth', 1.6, ...
                'MarkerSize', 5, 'CapSize', 6, ...
                'DisplayName', strrep(overlay(k).model, '_', ' '));
        end
        hold(ax, 'off');
        legend(ax, 'Location', 'best');
        xlabel(ax, 'AV Penetration Rate (%)');
        ylabel(ax, ylab);
        title(ax, sprintf('%s vs. AV Penetration (mean \\pm 95%% CI)', strtrim(strtok(ylab, '('))));
        grid(ax, 'on');
        style_light(fig, ax);
        save_fig(fig, fullfile(out_dir, sprintf('%s_%s_models.png', field, tag)));
        close(fig);
    end
end

summary_tbl = cell2table(summary, 'VariableNames', ...
    {'model_set', 'period', 'metric', 'penetration_pct', 'n', 'mean', 'sd', ...
     'ci95_lo', 'ci95_hi', 'mean_diff_vs_0', 'diff_ci95_lo', 'diff_ci95_hi', ...
     'pct_change_vs_0', 'p_paired'});
writetable(summary_tbl, fullfile(fileparts(csv_full), 'ps1_summary.csv'));
fprintf('\nSaved figures to %s\nSaved summary table to %s\n', out_dir, ...
    fullfile(fileparts(csv_full), 'ps1_summary.csv'));

%% ---- local helpers (must stay at the end of the script) ----
function style_light(fig, ax)
% White background + dark text so figures drop straight into a paper,
% even if MATLAB is running a dark theme.
    try, theme(fig, 'light'); catch, end    % R2025a+ only; ignored otherwise
    set(fig, 'Color', 'w');
    set(ax, 'Color', 'w', 'XColor', 'k', 'YColor', 'k', 'GridColor', [0.6 0.6 0.6]);
    ax.Title.Color = 'k';
    ax.XLabel.Color = 'k';
    ax.YLabel.Color = 'k';
end

function save_fig(fig, path)
    try
        exportgraphics(fig, path, 'Resolution', 300);
    catch
        saveas(fig, path);
    end
end
