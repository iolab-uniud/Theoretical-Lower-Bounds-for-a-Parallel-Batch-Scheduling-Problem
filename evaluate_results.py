import pandas as pd
import numpy as np

FLOAT_PRECISION = 0.000001


def _lookup_by_instance(df, instance_numbers, col):
    return (df.drop_duplicates(subset='instance_number')
              .set_index('instance_number')[col]
              .reindex(instance_numbers)
              .reset_index(drop=True))


def query_best_results_per_instance(results, solution_methods, out_dir=None):
    combined = pd.concat(
        [results[results['solution_method'] == m] for m in solution_methods
         if len(results[results['solution_method'] == m]) > 0],
        ignore_index=False
    ) if solution_methods else pd.DataFrame()

    best_results = ((combined[['instance_number', 'solutionCosts', 'optimal', 'total_time']]
                     .replace(-1, np.nan).groupby(['instance_number'], as_index=False))
                    .min())

    # per i lower bound ci interessa il valore piu' grande trovato
    max_results = ((combined[['instance_number', 'int_objective_bound']]
                    .replace(-1, np.nan).groupby(['instance_number'], as_index=False))
                   .max())

    if out_dir is not None:
        best_results.to_csv(f"{out_dir}/best_results.csv", index=False, sep=';')
        max_results.to_csv(f"{out_dir}/max_results.csv", index=False, sep=';')

    return {'min': best_results, 'max': max_results}


def query_statistics_per_solution_method_new(results, minmax_results, solution_methods, reference_solution_method):

    best_max = query_best_results_per_instance(results, solution_methods)
    best_results = best_max['min']
    max_results = best_max['max']

    if not minmax_results:
        overall_best_results = best_results
        overall_max_results = max_results
    else:
        overall_best_results = minmax_results['min']
        overall_max_results = minmax_results['max']

    stats_rows = []

    if reference_solution_method != "":
        reference_results = results[results['solution_method'] == reference_solution_method]
    else:
        reference_results = results[results['solution_method'] == solution_methods[0]]
    optimally_solved_by_reference_method = reference_results[reference_results['optimal'] == 1]['instance_number'].tolist()

    ref_grouped_results = reference_results.replace(-1, np.nan).groupby(['instance_number'], as_index=False)
    ref_min_agg_results = ref_grouped_results.min()
    ref_max_agg_results = ref_grouped_results.max()

    ref_instances = ref_min_agg_results['instance_number']
    ov_costs = _lookup_by_instance(overall_best_results, ref_instances, 'solutionCosts')
    ov_optimal = _lookup_by_instance(overall_best_results, ref_instances, 'optimal')
    ref_opt_count = int((
        (ref_min_agg_results['solutionCosts'].reset_index(drop=True) >= 0)
        & (ref_min_agg_results['solutionCosts'].reset_index(drop=True) <= FLOAT_PRECISION + ov_costs)
        & (ref_min_agg_results['solutionCosts'].reset_index(drop=True) >= -FLOAT_PRECISION + ov_costs)
        & (ov_optimal > 0)
    ).sum())
    ref_proven_count = len(ref_min_agg_results[ref_min_agg_results['optimal'] > 0])
    ref_solved_count = len(ref_min_agg_results[ref_min_agg_results['solutionCosts'] >= 0])

    bst_costs = _lookup_by_instance(best_results, ref_instances, 'solutionCosts')
    ref_best_count = int((
        (ref_min_agg_results['solutionCosts'].reset_index(drop=True) >= 0)
        & (ref_min_agg_results['solutionCosts'].reset_index(drop=True) <= FLOAT_PRECISION + bst_costs)
        & (ref_min_agg_results['solutionCosts'].reset_index(drop=True) >= -FLOAT_PRECISION + bst_costs)
    ).sum())

    ref_max_instances = ref_max_agg_results['instance_number']
    mx_bound = _lookup_by_instance(max_results, ref_max_instances, 'int_objective_bound')
    ref_best_lower_bound_count = int((
        (ref_max_agg_results['int_objective_bound'].reset_index(drop=True) >= 0)
        & (ref_max_agg_results['int_objective_bound'].reset_index(drop=True) == mx_bound)
    ).sum())

    avg_rt = ref_min_agg_results[ref_min_agg_results['instance_number'].isin(optimally_solved_by_reference_method)
                                  ]['total_time'].mean()
    avg_rt = round(avg_rt, 1)
    std_rt = ref_min_agg_results[ref_min_agg_results['instance_number'].isin(optimally_solved_by_reference_method)
                                  ]['total_time'].std()
    std_rt = round(std_rt, 1)

    stats_rows.append({'solution_method': reference_solution_method,
                        "#optimal": ref_opt_count,
                        "#solved": ref_solved_count,
                        "#proven opt": ref_proven_count,
                        "#best": ref_best_count,
                        "#best lower bound": ref_best_lower_bound_count,
                        "avg rt": avg_rt,
                        "std rt": std_rt})

    for solution_method in solution_methods:
        solver_results = results[results['solution_method'] == solution_method]

        if len(solver_results) == 0 or solution_method == reference_solution_method:
            continue

        grouped_results = solver_results.replace(-1, np.nan).groupby(['instance_number'], as_index=False)
        min_agg_results = grouped_results.min()
        max_agg_results = grouped_results.max()

        instances = min_agg_results['instance_number']
        ov_costs = _lookup_by_instance(overall_best_results, instances, 'solutionCosts')
        ov_optimal = _lookup_by_instance(overall_best_results, instances, 'optimal')
        opt_count = int((
            (min_agg_results['solutionCosts'].reset_index(drop=True) >= 0)
            & (min_agg_results['solutionCosts'].reset_index(drop=True) <= FLOAT_PRECISION + ov_costs)
            & (min_agg_results['solutionCosts'].reset_index(drop=True) >= -FLOAT_PRECISION + ov_costs)
            & (ov_optimal > 0)
        ).sum())
        delta_opt_count = opt_count - ref_opt_count

        proven_count = len(min_agg_results[min_agg_results['optimal'] > 0])
        delta_proven_count = proven_count - ref_proven_count
        solved_count = len(min_agg_results[min_agg_results['solutionCosts'] >= 0])
        delta_solved_count = solved_count - ref_solved_count

        bst_costs = _lookup_by_instance(best_results, instances, 'solutionCosts')
        best_count = int((
            (min_agg_results['solutionCosts'].reset_index(drop=True) >= 0)
            & (min_agg_results['solutionCosts'].reset_index(drop=True) <= FLOAT_PRECISION + bst_costs)
            & (min_agg_results['solutionCosts'].reset_index(drop=True) >= -FLOAT_PRECISION + bst_costs)
        ).sum())
        delta_best_count = best_count - ref_best_count

        max_instances = max_agg_results['instance_number']
        mx_bound = _lookup_by_instance(max_results, max_instances, 'int_objective_bound')
        best_lower_bound_count = int((
            (max_agg_results['int_objective_bound'].reset_index(drop=True) >= 0)
            & (max_agg_results['int_objective_bound'].reset_index(drop=True) == mx_bound)
        ).sum())
        delta_best_lower_bound_count = best_lower_bound_count - ref_best_lower_bound_count

        avg_rt = min_agg_results[min_agg_results['instance_number'].isin(optimally_solved_by_reference_method)
                                 ]['total_time'].mean()
        avg_rt = round(avg_rt, 1)
        std_rt = min_agg_results[min_agg_results['instance_number'].isin(optimally_solved_by_reference_method)
                                 ]['total_time'].std()
        std_rt = round(std_rt, 1)

        stats_rows.append({'solution_method': solution_method,
                            "#optimal": f"{opt_count} ({delta_opt_count:+d})",
                            "#solved": f"{solved_count} ({delta_solved_count:+d})",
                            "#proven opt": f"{proven_count} ({delta_proven_count:+d})",
                            "#best": f"{best_count} ({delta_best_count:+d})",
                            "#best lower bound": f"{best_lower_bound_count} ({delta_best_lower_bound_count:+d})",
                            "avg rt": avg_rt,
                            "std rt": std_rt})

    return pd.DataFrame(stats_rows)