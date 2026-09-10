# Question 1 verification helpers.

const Q1_VERIFY_TOL = 1.0e-6

function q1_purchase_cost(price, grid_kwh)
    return sum(price .* grid_kwh)
end

function q1_assert_soc_bounds(soc)
    if minimum(soc) < Q1_SOC_MIN_KWH - Q1_VERIFY_TOL
        error("SOC lower bound violated")
    end
    if maximum(soc) > Q1_SOC_MAX_KWH + Q1_VERIFY_TOL
        error("SOC upper bound violated")
    end
    if abs(soc[end] - Q1_SOC_TERMINAL_KWH) > Q1_VERIFY_TOL
        error("terminal SOC violated")
    end
end

function q1_assert_power_limits(charge_kwh, discharge_kwh)
    limit_kwh = Q1_POWER_LIMIT_KW * Q1_DELTA_HOUR
    if maximum(charge_kwh) > limit_kwh + Q1_VERIFY_TOL
        error("charge power limit violated")
    end
    if maximum(discharge_kwh) > limit_kwh + Q1_VERIFY_TOL
        error("discharge power limit violated")
    end
end

function q1_assert_curtailment(curtail_kwh, pv_kwh)
    if minimum(curtail_kwh) < -Q1_VERIFY_TOL
        error("negative PV curtailment detected")
    end
    if maximum(curtail_kwh .- pv_kwh) > Q1_VERIFY_TOL
        error("PV curtailment exceeds available PV")
    end
end

function q1_assert_nonnegative_grid(grid_kwh)
    if minimum(grid_kwh) < -Q1_VERIFY_TOL
        error("negative grid purchase detected")
    end
end

function q1_max_balance_residual(interval_data, solution)
    residual = solution["grid_kwh"] .+ interval_data["pv_kwh"] .-
               solution["curtail_kwh"] .+ solution["discharge_kwh"] .-
               interval_data["load_kwh"] .- solution["charge_kwh"]
    return maximum(abs.(residual))
end

function q1_verify_solution(interval_data, solution)
    q1_assert_nonnegative_grid(solution["grid_kwh"])
    q1_assert_soc_bounds(solution["soc_kwh"])
    q1_assert_power_limits(solution["charge_kwh"], solution["discharge_kwh"])
    q1_assert_curtailment(solution["curtail_kwh"], interval_data["pv_kwh"])

    residual = q1_max_balance_residual(interval_data, solution)
    if residual > 1.0e-5
        error("energy balance residual too large: " * string(residual))
    end

    return Dict(
        "name" => solution["name"],
        "cost" => q1_purchase_cost(interval_data["price"], solution["grid_kwh"]),
        "max_balance_residual" => residual,
        "min_soc" => minimum(solution["soc_kwh"]),
        "max_soc" => maximum(solution["soc_kwh"]),
        "terminal_soc" => solution["soc_kwh"][end],
        "max_charge_kwh" => maximum(solution["charge_kwh"]),
        "max_discharge_kwh" => maximum(solution["discharge_kwh"]),
        "min_curtail_kwh" => minimum(solution["curtail_kwh"]),
    )
end

function q1_assert_equal_optimal_cost(cost_a, cost_b)
    if abs(cost_a - cost_b) > Q1_VERIFY_TOL
        error("two schedules do not have equal optimal cost")
    end
end

function q1_assert_different_purchase_schedule(grid_a, grid_b)
    if maximum(abs.(grid_a .- grid_b)) <= Q1_VERIFY_TOL
        error("purchase schedules are not meaningfully different")
    end
end

function q1_verify_pair(interval_data, plan_a, plan_b)
    check_a = q1_verify_solution(interval_data, plan_a)
    check_b = q1_verify_solution(interval_data, plan_b)
    q1_assert_equal_optimal_cost(plan_a["cost"], plan_b["cost"])
    q1_assert_different_purchase_schedule(plan_a["grid_kwh"], plan_b["grid_kwh"])
    return Dict("plan_a" => check_a, "plan_b" => check_b)
end
