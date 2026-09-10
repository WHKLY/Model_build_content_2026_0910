# Question 1 entry point.

include("project_paths.jl")
include("q1_data.jl")
include("q1_model.jl")
include("q1_verify.jl")
include("q1_export.jl")
include("q1_plot.jl")

function main()
    ensure_output_dirs()

    data = q1_source_data()
    interval_data = q1_prepare_interval_data(
        data["price"],
        data["load_kw"],
        data["pv_kw"],
    )

    primary_solution, lp = q1_solve_primary(interval_data)
    plan_a = q1_solve_at_same_cost(
        interval_data,
        lp,
        primary_solution["cost"],
        target_index=140,
        sense="min",
    )
    plan_b = q1_solve_at_same_cost(
        interval_data,
        lp,
        primary_solution["cost"],
        target_index=140,
        sense="max",
    )
    baseline = q1_no_storage_baseline(interval_data)

    checks = q1_verify_pair(interval_data, plan_a, plan_b)

    exported = q1_export_all(data, interval_data, baseline, plan_a, plan_b, checks)
    q1_plot_all(data, interval_data, baseline, plan_a, plan_b)

    println("")
    println("Question 1 completed.")
    println("No-storage cost: " * string(baseline["cost"]))
    println("Plan A cost: " * string(plan_a["cost"]))
    println("Plan B cost: " * string(plan_b["cost"]))
    println("Plan A g140: " * string(plan_a["target_grid_kwh"]))
    println("Plan B g140: " * string(plan_b["target_grid_kwh"]))
    println("Schedule CSV: " * exported["schedule_csv"])
    println("Summary CSV: " * exported["summary_csv"])
    println("Workbook path: " * exported["workbook"])

    return Dict(
        "baseline" => baseline,
        "plan_a" => plan_a,
        "plan_b" => plan_b,
        "checks" => checks,
        "exported" => exported,
    )
end

main()
