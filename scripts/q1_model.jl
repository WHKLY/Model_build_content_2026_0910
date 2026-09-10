# Question 1 model construction and LP solving.

using TyOptimization
using TyMath
using TyBase

const Q1_INTERVAL_COUNT = 144
const Q1_DELTA_HOUR = 1.0 / 6.0

const Q1_BATTERY_CAPACITY_KWH = 12000.0
const Q1_SOC_MIN_KWH = 1200.0
const Q1_SOC_MAX_KWH = 10800.0
const Q1_SOC_INITIAL_KWH = 6000.0
const Q1_SOC_TERMINAL_KWH = 6000.0

const Q1_CHARGE_EFFICIENCY = 0.9
const Q1_DISCHARGE_EFFICIENCY = 0.9
const Q1_POWER_LIMIT_KW = 5000.0

function q1_energy_from_power_kw(power_kw)
    return power_kw .* Q1_DELTA_HOUR
end

function q1_charge_energy_limit_kwh()
    return Q1_POWER_LIMIT_KW * Q1_DELTA_HOUR * Q1_CHARGE_EFFICIENCY
end

function q1_discharge_internal_limit_kwh()
    return Q1_POWER_LIMIT_KW * Q1_DELTA_HOUR / Q1_DISCHARGE_EFFICIENCY
end

function q1_index_grid(t)
    return t
end

function q1_index_soc(t)
    return Q1_INTERVAL_COUNT + t
end

function q1_variable_count()
    return 2 * Q1_INTERVAL_COUNT
end

function q1_validate_input_lengths(price, load_kw, pv_kw)
    if length(price) != Q1_INTERVAL_COUNT
        error("price length must be 144")
    end
    if length(load_kw) != Q1_INTERVAL_COUNT
        error("load_kw length must be 144")
    end
    if length(pv_kw) != Q1_INTERVAL_COUNT
        error("pv_kw length must be 144")
    end
end

function q1_prepare_interval_data(price, load_kw, pv_kw)
    q1_validate_input_lengths(price, load_kw, pv_kw)

    load_kwh = q1_energy_from_power_kw(load_kw)
    pv_kwh = q1_energy_from_power_kw(pv_kw)
    net_kwh = load_kwh .- pv_kwh

    return Dict(
        "price" => price,
        "load_kw" => load_kw,
        "pv_kw" => pv_kw,
        "load_kwh" => load_kwh,
        "pv_kwh" => pv_kwh,
        "net_kwh" => net_kwh,
    )
end

function q1_objective(price)
    f = zeros(q1_variable_count())
    for t in 1:Q1_INTERVAL_COUNT
        f[q1_index_grid(t)] = price[t]
    end
    return f
end

function q1_build_lp(interval_data)
    price = interval_data["price"]
    load_kwh = interval_data["load_kwh"]
    net_kwh = interval_data["net_kwh"]
    nvars = q1_variable_count()

    # Four inequalities per interval:
    # two epigraph constraints and two internal-energy increment bounds.
    A = zeros(4 * Q1_INTERVAL_COUNT, nvars)
    b = zeros(4 * Q1_INTERVAL_COUNT)

    row = 0
    charge_upper = q1_charge_energy_limit_kwh()
    ac_discharge_limit = Q1_POWER_LIMIT_KW * Q1_DELTA_HOUR

    for t in 1:Q1_INTERVAL_COUNT
        g = q1_index_grid(t)
        s = q1_index_soc(t)
        s_prev = t == 1 ? 0 : q1_index_soc(t - 1)

        # g_t >= n_t + x_t / eta_c
        row += 1
        A[row, g] = -1.0
        A[row, s] = 1.0 / Q1_CHARGE_EFFICIENCY
        if t == 1
            b[row] = -net_kwh[t] + Q1_SOC_INITIAL_KWH / Q1_CHARGE_EFFICIENCY
        else
            A[row, s_prev] = -1.0 / Q1_CHARGE_EFFICIENCY
            b[row] = -net_kwh[t]
        end

        # g_t >= n_t + eta_d * x_t
        row += 1
        A[row, g] = -1.0
        A[row, s] = Q1_DISCHARGE_EFFICIENCY
        if t == 1
            b[row] = -net_kwh[t] + Q1_DISCHARGE_EFFICIENCY * Q1_SOC_INITIAL_KWH
        else
            A[row, s_prev] = -Q1_DISCHARGE_EFFICIENCY
            b[row] = -net_kwh[t]
        end

        # x_t <= eta_c * Pmax * dt
        row += 1
        A[row, s] = 1.0
        if t == 1
            b[row] = charge_upper + Q1_SOC_INITIAL_KWH
        else
            A[row, s_prev] = -1.0
            b[row] = charge_upper
        end

        # x_t >= -min(Pmax*dt, load_t) / eta_d
        discharge_lower = -min(ac_discharge_limit, load_kwh[t]) / Q1_DISCHARGE_EFFICIENCY
        row += 1
        A[row, s] = -1.0
        if t == 1
            b[row] = -discharge_lower - Q1_SOC_INITIAL_KWH
        else
            A[row, s_prev] = 1.0
            b[row] = -discharge_lower
        end
    end

    Aeq = zeros(1, nvars)
    Aeq[1, q1_index_soc(Q1_INTERVAL_COUNT)] = 1.0
    beq = [Q1_SOC_TERMINAL_KWH]

    lb = zeros(nvars)
    ub = fill(Inf, nvars)
    for t in 1:Q1_INTERVAL_COUNT
        s = q1_index_soc(t)
        lb[s] = Q1_SOC_MIN_KWH
        ub[s] = Q1_SOC_MAX_KWH
    end

    return Dict(
        "f" => q1_objective(price),
        "A" => A,
        "b" => b,
        "Aeq" => Aeq,
        "beq" => beq,
        "lb" => lb,
        "ub" => ub,
    )
end

function q1_recover_solution(z, interval_data; name="solution")
    grid_kwh = vec(z[1:Q1_INTERVAL_COUNT])
    soc_kwh = vec(z[(Q1_INTERVAL_COUNT + 1):end])

    previous_soc = vcat([Q1_SOC_INITIAL_KWH], soc_kwh[1:end-1])
    internal_delta = soc_kwh .- previous_soc
    charge_kwh = max.(internal_delta, 0.0) ./ Q1_CHARGE_EFFICIENCY
    discharge_kwh = Q1_DISCHARGE_EFFICIENCY .* max.(-internal_delta, 0.0)
    curtail_kwh = grid_kwh .+ interval_data["pv_kwh"] .+ discharge_kwh .-
                  interval_data["load_kwh"] .- charge_kwh

    return Dict(
        "name" => name,
        "z" => z,
        "grid_kwh" => grid_kwh,
        "soc_kwh" => soc_kwh,
        "internal_delta_kwh" => internal_delta,
        "charge_kwh" => charge_kwh,
        "discharge_kwh" => discharge_kwh,
        "curtail_kwh" => curtail_kwh,
        "cost" => sum(interval_data["price"] .* grid_kwh),
        "total_grid_kwh" => sum(grid_kwh),
        "total_charge_kwh" => sum(charge_kwh),
        "total_discharge_kwh" => sum(discharge_kwh),
        "total_curtail_kwh" => sum(curtail_kwh),
    )
end

function q1_solve_lp(lp; objective=nothing, Aeq=nothing, beq=nothing, name="solution")
    f = isnothing(objective) ? lp["f"] : objective
    local_Aeq = isnothing(Aeq) ? lp["Aeq"] : Aeq
    local_beq = isnothing(beq) ? lp["beq"] : beq

    options = optimoptions(:linprog, Display = "off")
    z, fval, exitflag, output = linprog(
        vec(f),
        lp["A"],
        lp["b"],
        local_Aeq,
        local_beq,
        vec(lp["lb"]),
        vec(lp["ub"]),
        options,
    )

    if exitflag <= 0
        error("linprog failed for " * name * ", exitflag = " * string(exitflag))
    end

    return z, fval, exitflag, output
end

function q1_solve_primary(interval_data)
    lp = q1_build_lp(interval_data)
    z, fval, exitflag, output = q1_solve_lp(lp, name="primary-cost")
    solution = q1_recover_solution(z, interval_data, name="primary-cost")
    solution["reported_fval"] = fval
    solution["exitflag"] = exitflag
    return solution, lp
end

function q1_solve_at_same_cost(interval_data, lp, optimal_cost; target_index=140, sense="min")
    nvars = q1_variable_count()
    f2 = zeros(nvars)
    f2[q1_index_grid(target_index)] = sense == "max" ? -1.0 : 1.0

    cost_row = reshape(lp["f"], 1, nvars)
    Aeq2 = vcat(lp["Aeq"], cost_row)
    beq2 = vcat(lp["beq"], [optimal_cost])

    z, fval, exitflag, output = q1_solve_lp(
        lp,
        objective=f2,
        Aeq=Aeq2,
        beq=beq2,
        name=sense * "-g" * string(target_index),
    )

    solname = sense == "max" ? "plan_B_max_g$(target_index)" : "plan_A_min_g$(target_index)"
    solution = q1_recover_solution(z, interval_data, name=solname)
    solution["reported_fval"] = fval
    solution["exitflag"] = exitflag
    solution["target_index"] = target_index
    solution["target_grid_kwh"] = solution["grid_kwh"][target_index]
    return solution
end

function q1_no_storage_baseline(interval_data)
    grid_kwh = max.(interval_data["net_kwh"], 0.0)
    curtail_kwh = max.(-interval_data["net_kwh"], 0.0)
    return Dict(
        "name" => "no_storage",
        "grid_kwh" => grid_kwh,
        "cost" => sum(interval_data["price"] .* grid_kwh),
        "total_grid_kwh" => sum(grid_kwh),
        "total_curtail_kwh" => sum(curtail_kwh),
    )
end
