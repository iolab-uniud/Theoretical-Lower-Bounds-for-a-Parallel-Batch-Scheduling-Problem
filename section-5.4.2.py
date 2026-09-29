import os
import argparse
import pandas as pd

import evaluate_results as evaluate_results

METHOD_FAMILIES = {
    "gurobi": ["mzn-gurobi", "mzn-gurobi-LB-noUB"],
    "gurobiWS": ["mzn-gurobi-WS", "mzn-gurobiWS-LB-noUB"],
    "opl": ["opl-reprjob", "opl-reprjob-LB-noUB"],
    "oplWS": ["opl-reprjob-WS", "opl-reprjob-LB-WS-noUB"],
}
METHODS_WITHOUT_BOUNDS = ["mzn-gurobi", "mzn-gurobi-WS", "opl-reprjob", "opl-reprjob-WS"]


def build_all_tables(input_csv, out_dir, sep=";"):
    os.makedirs(out_dir, exist_ok=True)
    results = pd.read_csv(input_csv, sep=sep)

    present_methods = set(results["solution_method"].unique())
    all_solution_methods = [m for fam in METHOD_FAMILIES.values() for m in fam]
    missing = [m for m in all_solution_methods if m not in present_methods]
    if missing:
        print(f"[INFO] questi solution_method non sono nel file e verranno saltati: {missing}")
    all_solution_methods = [m for m in all_solution_methods if m in present_methods]

    tables = {}

    # 1) tabella complessiva, riferimento = primo metodo della lista
    reference_method = all_solution_methods[0]
    print(f"[INFO] tabella complessiva - riferimento: {reference_method}")
    overall_stats = evaluate_results.query_statistics_per_solution_method_new(
        results, {}, all_solution_methods, reference_method
    )
    tables["overall_stats"] = overall_stats

    # 2) tabelle per famiglia (con/senza LB), usando come "migliore assoluto"
    #    quello calcolato su TUTTI i metodi 
    best_results_all_methods = evaluate_results.query_best_results_per_instance(
        results, all_solution_methods
    )
    for family_name, methods in METHOD_FAMILIES.items():
        methods = [m for m in methods if m in present_methods]
        if len(methods) < 2:
            print(f"[INFO] famiglia '{family_name}': meno di 2 metodi presenti, la salto ({methods}).")
            continue
        stats = evaluate_results.query_statistics_per_solution_method_new(
            results, best_results_all_methods, methods, methods[0]
        )
        tables[f"stats_{family_name}"] = stats

    # 3) confronto best-con-bound vs best-senza-bound
    methods_without_bounds = [m for m in METHODS_WITHOUT_BOUNDS if m in present_methods]
    methods_with_bounds = [m for m in all_solution_methods if m not in methods_without_bounds]
    if methods_without_bounds and methods_with_bounds:
        best_without = evaluate_results.query_best_results_per_instance(results, methods_without_bounds)
        best_without_df = pd.concat([best_without['min'], best_without['max']['int_objective_bound']], axis=1)
        best_without_df['solution_method'] = "best without bounds"

        best_with = evaluate_results.query_best_results_per_instance(results, methods_with_bounds)
        best_with_df = pd.concat([best_with['min'], best_with['max']['int_objective_bound']], axis=1)
        best_with_df['solution_method'] = "best with bounds"

        combined = pd.concat([best_with_df, best_without_df], ignore_index=True)
        comparison = evaluate_results.query_statistics_per_solution_method_new(
            combined, {}, ["best with bounds", "best without bounds"], "best without bounds"
        )
        tables["comparison_with_vs_without_bounds"] = comparison
    else:
        print("[INFO] non ho trovato sia metodi 'con bound' che 'senza bound' nel file: salto il confronto aggregato.")

    # scrittura csv + latex
    for name, df in tables.items():
        csv_path = os.path.join(out_dir, f"{name}.csv")
        tex_path = os.path.join(out_dir, f"{name}.tex")
        df.to_csv(csv_path, index=False, sep=';')
        with open(tex_path, "w") as f:
            f.write(df.to_latex(index=False))
        print(f"[INFO] '{name}': {csv_path} + {tex_path}")

    return tables


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", default="data/all-complete.csv")
    parser.add_argument("--out-dir", default="summary_tables")
    parser.add_argument("--sep", default=";")
    args = parser.parse_args()

    tables = build_all_tables(args.input_csv, args.out_dir, args.sep)
    for name, df in tables.items():
        print(f"\n=== {name} ===")
        print(df.to_string(index=False))
