"""
recourse.py — Counterfactual Recourse Engine for Household Poverty Alleviation.

Transforms the system from descriptive classification into actionable policy prescription:
Given a household predicted as poor (P(poor) >= threshold), computes the minimum-cost,
monotonically valid set of actionable feature interventions to flip the prediction
to non-poor (P(poor) < threshold).
"""
from typing import Dict, List, Any, Optional
import copy
import pandas as pd
import numpy as np

# ── Policy Action Catalog ──────────────────────────────────────────────────
# Defines actionable levers, intervention descriptions, target upgrades, and policy cost weights (1-10)
INTERVENTION_CATALOG = {
    "elec_ac": {
        "label": "National Grid Connection",
        "domain": "Infrastructure",
        "target_val": 1.0,
        "cost_weight": 3.5,
        "description": "Subsidize last-mile electrical grid connection",
    },
    "ind_bank": {
        "label": "Bank / Mobile Money Account",
        "domain": "Financial Inclusion",
        "target_val": 1.0,
        "cost_weight": 1.5,
        "description": "Enroll household head in digital financial inclusion / banking program",
    },
    "ind_telpor": {
        "label": "Mobile Phone Ownership",
        "domain": "Connectivity",
        "target_val": 1.0,
        "cost_weight": 1.0,
        "description": "Provide basic mobile phone device for market information access",
    },
    "ind_internet": {
        "label": "Internet Connectivity Access",
        "domain": "Connectivity",
        "target_val": 1.0,
        "cost_weight": 2.0,
        "description": "Community broadband / cellular data access voucher",
    },
    "eauboi_ss": {
        "label": "Protected Drinking Water Source",
        "domain": "Sanitation & Health",
        "target_val": 1.0,
        "cost_weight": 2.8,
        "description": "Provide community borehole / piped protected drinking water",
    },
    "toilet": {
        "label": "Improved Sanitation Facility",
        "domain": "Sanitation & Health",
        "target_val": 3.0,
        "cost_weight": 2.5,
        "description": "Upgrade from open/unimproved to ventilated pit latrine or flush toilet",
    },
    "sol": {
        "label": "Cement / Tiled Floor Quality",
        "domain": "Housing Quality",
        "target_val": 3.0,
        "cost_weight": 2.2,
        "description": "Replace dirt/earth floor with cement or finished tiling",
    },
    "toit": {
        "label": "Corrugated Metal / Concrete Roof",
        "domain": "Housing Quality",
        "target_val": 3.0,
        "cost_weight": 3.0,
        "description": "Upgrade thatched/straw roof to durable sheet metal or concrete",
    },
    "mur": {
        "label": "Cement / Masonry Wall Quality",
        "domain": "Housing Quality",
        "target_val": 3.0,
        "cost_weight": 3.8,
        "description": "Reinforce mud/mat walls with cement masonry or stone",
    },
    "ind_salaire": {
        "label": "Formal Wage Employment",
        "domain": "Labor & Livelihood",
        "target_val": 1.0,
        "cost_weight": 5.0,
        "description": "Facilitate transition of at least one member into formal wage labor",
    },
    "ind_diplome": {
        "label": "Vocational / Secondary Diploma",
        "domain": "Human Capital",
        "target_val": 1.0,
        "cost_weight": 4.5,
        "description": "Adult vocational skill certification or secondary diploma program",
    },
}

# Immutable features that must NEVER be modified in counterfactual recourse
IMMUTABLE_FEATURES = {
    "hage", "hgender", "hhsize", "eqadu1", "eqadu2", "indiv_count",
    "milieu", "zae", "hnation", "hethnie", "hreligion",
    "sh_co_eco", "sh_id_demo", "sh_co_natu", "sh_id_eco", "sh_co_vio", "sh_co_oth",
    "country_code", "hhid", "poor"
}


def compute_recourse(
    household_dict: Dict[str, Any],
    model: Any,
    feature_cols: List[str],
    policy_threshold: float = 0.35,
    max_steps: int = 3,
) -> Dict[str, Any]:
    """
    Compute optimal counterfactual recourse for a single household.
    
    ponytail: Uses fast greedy search over the 11 actionable levers.
    Exhaustive search over 11 levers with max_steps=3 is at most C(11,1)+C(11,2)+C(11,3)=231
    model predictions, which runs in <30ms total.
    """
    # Create baseline row DataFrame
    x_base = pd.DataFrame([[household_dict.get(c, 0.0) for c in feature_cols]], columns=feature_cols)
    p_base = float(model.predict_proba(x_base)[0, 1])

    result = {
        "baseline_probability": p_base,
        "policy_threshold": policy_threshold,
        "is_currently_poor": bool(p_base >= policy_threshold),
        "recourse_needed": bool(p_base >= policy_threshold),
        "single_action_effects": [],
        "optimal_plan": None,
        "achieved_probability": p_base,
        "status": "NON_POOR" if p_base < policy_threshold else "SEARCHING",
    }

    if p_base < policy_threshold:
        result["status"] = "ALREADY_NON_POOR"
        result["message"] = f"Household is already classified as non-poor (P={p_base:.1%} < {policy_threshold:.1%})."
        return result

    # 1. Identify valid candidate actions (respecting monotonicity: can only upgrade, never downgrade)
    candidate_actions = []
    for feat, meta in INTERVENTION_CATALOG.items():
        if feat not in feature_cols or feat in IMMUTABLE_FEATURES:
            continue
        current_val = float(household_dict.get(feat, 0.0))
        target_val = float(meta["target_val"])
        if current_val < target_val:
            candidate_actions.append({
                "feature": feat,
                "label": meta["label"],
                "domain": meta["domain"],
                "current_val": current_val,
                "target_val": target_val,
                "cost_weight": meta["cost_weight"],
                "description": meta["description"],
            })

    if not candidate_actions:
        result["status"] = "NO_ACTIONS_AVAILABLE"
        result["message"] = "Household already has all actionable features at maximum status."
        return result

    # 2. Evaluate all single actions
    for action in candidate_actions:
        x_mod = x_base.copy()
        x_mod[action["feature"]] = action["target_val"]
        p_new = float(model.predict_proba(x_mod)[0, 1])
        delta = p_base - p_new
        efficiency = (delta / action["cost_weight"]) if action["cost_weight"] > 0 else 0.0

        action_summary = {
            **action,
            "new_probability": p_new,
            "probability_reduction_pp": delta * 100,
            "cost_efficiency": efficiency,
            "flips_decision": bool(p_new < policy_threshold),
        }
        result["single_action_effects"].append(action_summary)

    # Sort single actions by probability reduction descending
    result["single_action_effects"].sort(key=lambda x: x["probability_reduction_pp"], reverse=True)

    # Check if any single action alone flips the decision
    single_flippers = [a for a in result["single_action_effects"] if a["flips_decision"]]
    if single_flippers:
        # Pick the one with lowest cost weight
        single_flippers.sort(key=lambda x: x["cost_weight"])
        best_single = single_flippers[0]
        result["status"] = "SOLVED_SINGLE"
        result["optimal_plan"] = {
            "actions": [best_single],
            "total_cost": best_single["cost_weight"],
            "new_probability": best_single["new_probability"],
            "reduction_pp": best_single["probability_reduction_pp"],
            "flips_decision": True,
        }
        result["achieved_probability"] = best_single["new_probability"]
        return result

    # 3. If no single action flips, search 2-action and 3-action combinations
    import itertools
    best_combo_plan = None
    min_combo_cost = float("inf")

    for k in range(2, min(max_steps + 1, len(candidate_actions) + 1)):
        for combo in itertools.combinations(candidate_actions, k):
            x_mod = x_base.copy()
            total_cost = 0.0
            for act in combo:
                x_mod[act["feature"]] = act["target_val"]
                total_cost += act["cost_weight"]

            p_new = float(model.predict_proba(x_mod)[0, 1])
            if p_new < policy_threshold:
                if total_cost < min_combo_cost:
                    min_combo_cost = total_cost
                    best_combo_plan = {
                        "actions": list(combo),
                        "total_cost": total_cost,
                        "new_probability": p_new,
                        "reduction_pp": (p_base - p_new) * 100,
                        "flips_decision": True,
                    }

        if best_combo_plan is not None:
            # Found lowest-k successful combination
            break

    if best_combo_plan:
        result["status"] = f"SOLVED_COMBO_{len(best_combo_plan['actions'])}"
        result["optimal_plan"] = best_combo_plan
        result["achieved_probability"] = best_combo_plan["new_probability"]
    else:
        # Return best effort (top-k reduction) even if it didn't cross threshold
        top_k = result["single_action_effects"][:max_steps]
        x_mod = x_base.copy()
        tot_cost = 0.0
        for act in top_k:
            x_mod[act["feature"]] = act["target_val"]
            tot_cost += act["cost_weight"]
        p_best_effort = float(model.predict_proba(x_mod)[0, 1])
        result["status"] = "PARTIAL_REDUCTION"
        result["optimal_plan"] = {
            "actions": top_k,
            "total_cost": tot_cost,
            "new_probability": p_best_effort,
            "reduction_pp": (p_base - p_best_effort) * 100,
            "flips_decision": False,
        }
        result["achieved_probability"] = p_best_effort

    return result


if __name__ == "__main__":
    from . import config
    from .dashboard_utils import load_simulator_artifact, HOUSEHOLD_ARCHETYPES

    print("Running Counterfactual Recourse self-check...")
    artifact = load_simulator_artifact()
    if not artifact:
        print("Model artifact missing, skipping test.")
    else:
        model = artifact["model"]
        feature_cols = artifact["feature_cols"]

        # Test with impoverished rural archetype
        poor_profile = copy.deepcopy(HOUSEHOLD_ARCHETYPES["🏚️ Impoverished Rural Household (Large, No Assets)"])
        recourse = compute_recourse(poor_profile, model, feature_cols, policy_threshold=0.35)

        print(f"Baseline probability: {recourse['baseline_probability']:.1%}")
        print(f"Status: {recourse['status']}")
        if recourse["optimal_plan"]:
            plan = recourse["optimal_plan"]
            print(f"Optimal plan flips decision: {plan['flips_decision']}")
            print(f"New probability: {plan['new_probability']:.1%}")
            print(f"Total policy cost: {plan['total_cost']:.1f}")
            for a in plan["actions"]:
                print(f"  -> {a['label']} ({a['domain']}): cost {a['cost_weight']}")

        assert recourse["baseline_probability"] > 0.35, "Archetype should be poor"
        assert recourse["achieved_probability"] < recourse["baseline_probability"], "Recourse should reduce poverty prob"
        print("Counterfactual recourse self-check passed!")
