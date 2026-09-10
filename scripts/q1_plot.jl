# Question 1 visualization helpers.

using TyPlot

const Q1_COLOR_BLUE = "#2563EB"
const Q1_COLOR_GREEN = "#059669"
const Q1_COLOR_RED = "#DC2626"
const Q1_COLOR_AMBER = "#D97706"
const Q1_COLOR_PURPLE = "#7C3AED"
const Q1_COLOR_GRAY = "#4B5563"

function q1_set_figure_size(width_px, height_px)
    # TyPlot follows MATLAB-like figure properties in Syslab builds tested by examples.
    # Keep this guarded so plotting still works if a teammate's version names it differently.
    try
        plt_set(gcf(), "position", [100, 100, width_px, height_px])
    catch e
        println("Figure size setting skipped: " * string(e))
    end
end

function q1_style_axes()
    grid("on")
    ax = gca()
    try
        plt_set(ax, "fontsize", 10)
    catch
    end
end

function q1_save_figure(basepath)
    mkpath(dirname(basepath))
    png_path = basepath * ".png"
    fig_path = basepath * ".syslabfig"
    try
        saveas(gcf(), png_path)
        println("Figure written: " * png_path)
    catch e
        println("PNG export failed for " * png_path)
        println(string(e))
    end
    try
        savefig(gcf(), fig_path)
        println("Syslab figure written: " * fig_path)
    catch e
        println("Syslab figure export failed for " * fig_path)
        println(string(e))
    end
end

function q1_plot_dispatch(source_data, interval_data, plan_a, plan_b)
    x = collect(1:Q1_INTERVAL_COUNT)
    figdir = joinpath(q1_output_dir(), "figures")

    figure()
    q1_set_figure_size(1200, 1500)
    subplot(4, 1, 1)
    plot(x, interval_data["load_kw"] ./ 1000.0; color=Q1_COLOR_BLUE, linewidth=1.4)
    hold("on")
    plot(x, interval_data["pv_kw"] ./ 1000.0; color=Q1_COLOR_GREEN, linewidth=1.4)
    hold("off")
    ylabel("MW")
    title("Load and PV Forecast")
    legend(["Load", "PV forecast"], loc="northeast")
    q1_style_axes()

    subplot(4, 1, 2)
    plot(x, interval_data["price"]; color=Q1_COLOR_AMBER, linewidth=1.4)
    ylabel("yuan/kWh")
    title("Electricity Price")
    q1_style_axes()

    subplot(4, 1, 3)
    plot(x, plan_a["charge_kwh"] ./ 1000.0; color=Q1_COLOR_GREEN, linewidth=1.2)
    hold("on")
    plot(x, -plan_a["discharge_kwh"] ./ 1000.0; color=Q1_COLOR_RED, linewidth=1.2)
    hold("off")
    ylabel("MWh")
    title("Plan A Charge (+) and Discharge (-)")
    legend(["Charge", "Discharge"], loc="northeast")
    q1_style_axes()

    subplot(4, 1, 4)
    plot(x, plan_a["soc_kwh"] ./ 1000.0; color=Q1_COLOR_PURPLE, linewidth=1.4)
    hold("on")
    plot(x, plan_a["grid_kwh"] ./ 1000.0; color=Q1_COLOR_GRAY, linewidth=1.1)
    hold("off")
    xlabel("10-minute interval index")
    ylabel("MWh")
    title("Plan A SOC and Grid Purchase")
    legend(["SOC", "Grid purchase"], loc="northeast")
    q1_style_axes()
    tightlayout()
    q1_save_figure(joinpath(figdir, "q1_dispatch_overview"))

    figure()
    q1_set_figure_size(1600, 600)
    plot(x, plan_b["grid_kwh"] .- plan_a["grid_kwh"]; color=Q1_COLOR_BLUE, linewidth=1.3)
    hold("on")
    plot(x, plan_b["soc_kwh"] .- plan_a["soc_kwh"]; color=Q1_COLOR_PURPLE, linewidth=1.3)
    hold("off")
    xlabel("10-minute interval index")
    ylabel("kWh")
    title("Plan B minus Plan A")
    legend(["Grid purchase difference", "SOC difference"], loc="northeast")
    q1_style_axes()
    tightlayout()
    q1_save_figure(joinpath(figdir, "q1_plan_difference"))
end

function q1_plot_costs(baseline, plan_a, plan_b)
    figdir = joinpath(q1_output_dir(), "figures")
    costs = [baseline["cost"]; plan_a["cost"]; plan_b["cost"]]

    figure()
    bar(costs)
    title("Purchase Cost Comparison")
    ylabel("yuan")
    xlabel("1 = no storage, 2 = plan A, 3 = plan B")
    q1_style_axes()
    tightlayout()
    q1_save_figure(joinpath(figdir, "q1_cost_comparison"))
end

function q1_plot_all(source_data, interval_data, baseline, plan_a, plan_b)
    q1_plot_dispatch(source_data, interval_data, plan_a, plan_b)
    q1_plot_costs(baseline, plan_a, plan_b)
end
