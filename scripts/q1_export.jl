# Question 1 output helpers.

using PyCall

function q1_csv_cell(value)
    if value isa AbstractFloat
        s = string(round(value, digits=10))
    else
        s = string(value)
    end
    s = replace(s, "\"" => "\"\"")
    return "\"" * s * "\""
end

function q1_write_csv(path, data)
    mkpath(dirname(path))
    open(path, "w") do io
        # UTF-8 BOM helps Chinese headers open correctly in many Excel setups.
        print(io, "\ufeff")
        for r in 1:size(data, 1)
            cells = [q1_csv_cell(data[r, c]) for c in 1:size(data, 2)]
            println(io, join(cells, ","))
        end
    end
end

function q1_schedule_table(source_data, interval_data, plan_a, plan_b)
    headers = [
        "index",
        "source_time",
        "interval",
        "price_yuan_per_kwh",
        "load_kw",
        "pv_forecast_kw",
        "load_kwh",
        "pv_forecast_kwh",
        "grid_A_kwh",
        "charge_A_kwh",
        "discharge_A_kwh",
        "curtail_A_kwh",
        "soc_A_kwh",
        "grid_B_kwh",
        "charge_B_kwh",
        "discharge_B_kwh",
        "curtail_B_kwh",
        "soc_B_kwh",
        "diff_grid_B_minus_A_kwh",
        "diff_soc_B_minus_A_kwh",
    ]

    table = Matrix{Any}(undef, Q1_INTERVAL_COUNT + 1, length(headers))
    table[1, :] = headers
    for t in 1:Q1_INTERVAL_COUNT
        table[t + 1, :] = Any[
            t,
            source_data["source_time"][t],
            source_data["interval"][t],
            interval_data["price"][t],
            interval_data["load_kw"][t],
            interval_data["pv_kw"][t],
            interval_data["load_kwh"][t],
            interval_data["pv_kwh"][t],
            plan_a["grid_kwh"][t],
            plan_a["charge_kwh"][t],
            plan_a["discharge_kwh"][t],
            plan_a["curtail_kwh"][t],
            plan_a["soc_kwh"][t],
            plan_b["grid_kwh"][t],
            plan_b["charge_kwh"][t],
            plan_b["discharge_kwh"][t],
            plan_b["curtail_kwh"][t],
            plan_b["soc_kwh"][t],
            plan_b["grid_kwh"][t] - plan_a["grid_kwh"][t],
            plan_b["soc_kwh"][t] - plan_a["soc_kwh"][t],
        ]
    end
    return table
end

function q1_summary_table(baseline, plan_a, plan_b, checks)
    rows = Any[
        "no_storage_cost_yuan" baseline["cost"];
        "no_storage_grid_kwh" baseline["total_grid_kwh"];
        "plan_A_cost_yuan" plan_a["cost"];
        "plan_A_grid_kwh" plan_a["total_grid_kwh"];
        "plan_A_charge_kwh" plan_a["total_charge_kwh"];
        "plan_A_discharge_kwh" plan_a["total_discharge_kwh"];
        "plan_A_curtail_kwh" plan_a["total_curtail_kwh"];
        "plan_A_target_index" plan_a["target_index"];
        "plan_A_target_grid_kwh" plan_a["target_grid_kwh"];
        "plan_A_max_balance_residual" checks["plan_a"]["max_balance_residual"];
        "plan_B_cost_yuan" plan_b["cost"];
        "plan_B_grid_kwh" plan_b["total_grid_kwh"];
        "plan_B_charge_kwh" plan_b["total_charge_kwh"];
        "plan_B_discharge_kwh" plan_b["total_discharge_kwh"];
        "plan_B_curtail_kwh" plan_b["total_curtail_kwh"];
        "plan_B_target_index" plan_b["target_index"];
        "plan_B_target_grid_kwh" plan_b["target_grid_kwh"];
        "plan_B_max_balance_residual" checks["plan_b"]["max_balance_residual"];
        "cost_saving_A_vs_no_storage_yuan" baseline["cost"] - plan_a["cost"];
        "cost_saving_B_vs_no_storage_yuan" baseline["cost"] - plan_b["cost"];
        "max_abs_grid_difference_B_minus_A_kwh" maximum(abs.(plan_b["grid_kwh"] .- plan_a["grid_kwh"]));
        "model_note" "same optimal purchase cost, different interval-level purchase schedules";
    ]

    table = Matrix{Any}(undef, size(rows, 1) + 1, 2)
    table[1, :] = Any["metric", "value"]
    table[2:end, :] = rows
    return table
end

function q1_four_hour_table(plan_a, plan_b)
    labels = ["00:00-04:00", "04:00-08:00", "08:00-12:00", "12:00-16:00", "16:00-20:00", "20:00-24:00"]
    table = Matrix{Any}(undef, 7, 7)
    table[1, :] = Any[
        "interval",
        "charge_A_kwh",
        "discharge_A_kwh",
        "grid_A_kwh",
        "charge_B_kwh",
        "discharge_B_kwh",
        "grid_B_kwh",
    ]
    for k in 1:6
        idx = ((k - 1) * 24 + 1):(k * 24)
        table[k + 1, :] = Any[
            labels[k],
            sum(plan_a["charge_kwh"][idx]),
            sum(plan_a["discharge_kwh"][idx]),
            sum(plan_a["grid_kwh"][idx]),
            sum(plan_b["charge_kwh"][idx]),
            sum(plan_b["discharge_kwh"][idx]),
            sum(plan_b["grid_kwh"][idx]),
        ]
    end
    return table
end

function q1_target_purchase_table(source_data, plan_a, plan_b)
    targets = ["10:00-10:10", "12:00-12:10", "14:00-14:10", "16:00-16:10", "18:00-18:10", "20:00-20:10"]
    table = Matrix{Any}(undef, length(targets) + 1, 4)
    table[1, :] = Any["interval", "index", "grid_A_kwh", "grid_B_kwh"]
    for i in 1:length(targets)
        idx = findfirst(x -> x == targets[i], source_data["interval"])
        if isnothing(idx)
            error("target interval not found: " * targets[i])
        end
        table[i + 1, :] = Any[targets[i], idx, plan_a["grid_kwh"][idx], plan_b["grid_kwh"][idx]]
    end
    return table
end

function q1_excel_session(; visible=false)
    if !Sys.iswindows()
        error("Excel COM export only works on Windows.")
    end
    win32 = PyCall.pyimport("win32com.client")
    excel = win32.Dispatch("Excel.Application")
    excel.Visible = visible
    excel.DisplayAlerts = false
    return excel
end

function q1_excel_write_sheet(workbook, sheet_index, sheet_name, data)
    sheets = workbook.Worksheets
    while sheets.Count < sheet_index
        sheets.Add(; Before=PyCall.pybuiltin("None"), After=sheets.Item(sheets.Count))
    end
    ws = sheets.Item(sheet_index)
    ws.Name = sheet_name
    ws.Cells.Clear()

    rows = size(data, 1)
    cols = size(data, 2)
    start_cell = ws.Cells.Item(1, 1)
    end_cell = ws.Cells.Item(rows, cols)
    ws.Range(start_cell, end_cell)."Value" = reshape(data, rows, cols)
    ws.Columns.AutoFit()
end

function q1_write_excel(path, sheets)
    excel = q1_excel_session(visible=false)
    workbook = excel.Workbooks.Add()
    try
        for i in 1:length(sheets)
            q1_excel_write_sheet(workbook, i, sheets[i][1], sheets[i][2])
        end
        if isfile(path)
            rm(path)
        end
        workbook.SaveAs(abspath(path))
        workbook.Close(false)
    catch e
        try
            workbook.Close(false)
        catch
        end
        excel.Quit()
        rethrow(e)
    end
    excel.Quit()
end

function q1_export_all(source_data, interval_data, baseline, plan_a, plan_b, checks)
    outdir = q1_output_dir()
    mkpath(outdir)

    schedule = q1_schedule_table(source_data, interval_data, plan_a, plan_b)
    summary = q1_summary_table(baseline, plan_a, plan_b, checks)
    four_hour = q1_four_hour_table(plan_a, plan_b)
    target_purchase = q1_target_purchase_table(source_data, plan_a, plan_b)

    q1_write_csv(joinpath(outdir, "q1_schedule.csv"), schedule)
    q1_write_csv(joinpath(outdir, "q1_summary.csv"), summary)
    q1_write_csv(joinpath(outdir, "q1_four_hour_summary.csv"), four_hour)
    q1_write_csv(joinpath(outdir, "q1_target_purchase.csv"), target_purchase)

    workbook_path = joinpath(outdir, "q1_results.xlsx")
    try
        q1_write_excel(workbook_path, [
            ("schedule", schedule),
            ("summary", summary),
            ("four_hour", four_hour),
            ("target_purchase", target_purchase),
        ])
        println("Excel workbook written: " * workbook_path)
    catch e
        println("Excel workbook export failed; CSV files were still written.")
        println(string(e))
    end

    return Dict(
        "schedule_csv" => joinpath(outdir, "q1_schedule.csv"),
        "summary_csv" => joinpath(outdir, "q1_summary.csv"),
        "four_hour_csv" => joinpath(outdir, "q1_four_hour_summary.csv"),
        "target_purchase_csv" => joinpath(outdir, "q1_target_purchase.csv"),
        "workbook" => workbook_path,
    )
end
