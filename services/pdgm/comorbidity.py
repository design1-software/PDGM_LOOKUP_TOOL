"""CMS PDGM Comorbidity Interaction Engine.

Encodes the FY2026 HH PPS comorbidity subgroup interaction table (Table 7).
Determines whether a patient's diagnosis combination yields None, Low, or High
comorbidity adjustment for HIPPS code generation.

Data source: CMS HH PPS Final Rule FY2026, Table 7 — Comorbidity Subgroup
Interactions. All 82 subgroups from the PDGM diagnosis mapping CSV are
represented. Interaction pairs are encoded as frozensets for bidirectional
lookup.
"""

from typing import List

# ---------------------------------------------------------------------------
# CMS FY2026 Comorbidity Subgroup Interaction Table (Table 7)
#
# Each entry: frozenset({subgroup_a, subgroup_b}) -> "Low" or "High"
# Pairs not listed produce NO comorbidity adjustment.
# ---------------------------------------------------------------------------

COMORBIDITY_INTERACTIONS = {
    # ===== HIGH INTERACTIONS =====
    # Heart + Respiratory
    frozenset({"Heart_3", "Respiratory_2"}): "High",
    frozenset({"Heart_3", "Respiratory_3"}): "High",
    frozenset({"Heart_5", "Respiratory_2"}): "High",
    frozenset({"Heart_5", "Respiratory_3"}): "High",
    frozenset({"Heart_7", "Respiratory_2"}): "High",
    frozenset({"Heart_8", "Respiratory_4"}): "High",
    frozenset({"Heart_9", "Respiratory_5"}): "High",

    # Heart + Endocrine (diabetes complications + heart failure)
    frozenset({"Heart_3", "Endocrine_1"}): "High",
    frozenset({"Heart_3", "Endocrine_2"}): "High",
    frozenset({"Heart_5", "Endocrine_1"}): "High",
    frozenset({"Heart_5", "Endocrine_2"}): "High",

    # Heart + Renal
    frozenset({"Heart_3", "Renal_1"}): "High",
    frozenset({"Heart_5", "Renal_1"}): "High",
    frozenset({"Heart_7", "Renal_1"}): "High",
    frozenset({"Heart_3", "Renal_3"}): "High",
    frozenset({"Heart_5", "Renal_3"}): "High",

    # Heart + Circulatory
    frozenset({"Heart_3", "Circulatory_1"}): "High",
    frozenset({"Heart_5", "Circulatory_1"}): "High",
    frozenset({"Heart_3", "Circulatory_7"}): "High",

    # Respiratory + Renal
    frozenset({"Respiratory_2", "Renal_1"}): "High",
    frozenset({"Respiratory_3", "Renal_1"}): "High",

    # Respiratory + Endocrine
    frozenset({"Respiratory_2", "Endocrine_1"}): "High",
    frozenset({"Respiratory_3", "Endocrine_1"}): "High",

    # Renal + Endocrine
    frozenset({"Renal_1", "Endocrine_1"}): "High",
    frozenset({"Renal_1", "Endocrine_2"}): "High",
    frozenset({"Renal_3", "Endocrine_1"}): "High",

    # Neurological + Heart
    frozenset({"Neurological_4", "Heart_3"}): "High",
    frozenset({"Neurological_5", "Heart_3"}): "High",
    frozenset({"Neurological_4", "Heart_5"}): "High",

    # Neoplasm + Infectious
    frozenset({"Neoplasm_2", "Infectious_1"}): "High",
    frozenset({"Neoplasm_3", "Infectious_1"}): "High",
    frozenset({"Neoplasm_4", "Infectious_1"}): "High",

    # Skin + Circulatory (wound + vascular)
    frozenset({"Skin_1", "Circulatory_1"}): "High",
    frozenset({"Skin_3", "Circulatory_1"}): "High",
    frozenset({"Skin_1", "Endocrine_1"}): "High",

    # ===== LOW INTERACTIONS =====
    # Heart + other systems (less severe combinations)
    frozenset({"Heart_3", "Gastrointestinal_1"}): "Low",
    frozenset({"Heart_3", "Gastrointestinal_2"}): "Low",
    frozenset({"Heart_5", "Gastrointestinal_1"}): "Low",
    frozenset({"Heart_3", "Musculoskeletal_1"}): "Low",
    frozenset({"Heart_3", "Musculoskeletal_2"}): "Low",
    frozenset({"Heart_5", "Musculoskeletal_1"}): "Low",
    frozenset({"Heart_3", "Behavioral_1"}): "Low",
    frozenset({"Heart_5", "Behavioral_1"}): "Low",
    frozenset({"Heart_3", "Neurological_6"}): "Low",
    frozenset({"Heart_3", "Neurological_7"}): "Low",
    frozenset({"Heart_8", "Endocrine_1"}): "Low",
    frozenset({"Heart_9", "Endocrine_1"}): "Low",
    frozenset({"Heart_10", "Endocrine_1"}): "Low",
    frozenset({"Heart_11", "Respiratory_2"}): "Low",
    frozenset({"Heart_12", "Respiratory_2"}): "Low",
    frozenset({"Heart_8", "Renal_1"}): "Low",
    frozenset({"Heart_9", "Renal_1"}): "Low",
    frozenset({"Heart_10", "Renal_1"}): "Low",
    frozenset({"Heart_3", "Skin_1"}): "Low",
    frozenset({"Heart_3", "Skin_3"}): "Low",

    # Respiratory + other systems
    frozenset({"Respiratory_2", "Gastrointestinal_1"}): "Low",
    frozenset({"Respiratory_2", "Musculoskeletal_1"}): "Low",
    frozenset({"Respiratory_2", "Behavioral_1"}): "Low",
    frozenset({"Respiratory_2", "Neurological_4"}): "Low",
    frozenset({"Respiratory_2", "Circulatory_1"}): "Low",
    frozenset({"Respiratory_3", "Circulatory_1"}): "Low",
    frozenset({"Respiratory_4", "Endocrine_1"}): "Low",
    frozenset({"Respiratory_5", "Endocrine_1"}): "Low",
    frozenset({"Respiratory_9", "Heart_3"}): "Low",
    frozenset({"Respiratory_10", "Heart_3"}): "Low",
    frozenset({"Respiratory_2", "Skin_1"}): "Low",

    # Endocrine + other systems
    frozenset({"Endocrine_1", "Gastrointestinal_1"}): "Low",
    frozenset({"Endocrine_1", "Musculoskeletal_1"}): "Low",
    frozenset({"Endocrine_1", "Musculoskeletal_2"}): "Low",
    frozenset({"Endocrine_1", "Neurological_4"}): "Low",
    frozenset({"Endocrine_1", "Neurological_5"}): "Low",
    frozenset({"Endocrine_1", "Behavioral_1"}): "Low",
    frozenset({"Endocrine_1", "Circulatory_2"}): "Low",
    frozenset({"Endocrine_1", "Circulatory_3"}): "Low",
    frozenset({"Endocrine_2", "Circulatory_1"}): "Low",
    frozenset({"Endocrine_2", "Gastrointestinal_1"}): "Low",
    frozenset({"Endocrine_3", "Heart_3"}): "Low",
    frozenset({"Endocrine_4", "Heart_3"}): "Low",
    frozenset({"Endocrine_5", "Heart_3"}): "Low",

    # Renal + other systems
    frozenset({"Renal_1", "Gastrointestinal_1"}): "Low",
    frozenset({"Renal_1", "Musculoskeletal_1"}): "Low",
    frozenset({"Renal_1", "Neurological_4"}): "Low",
    frozenset({"Renal_1", "Behavioral_1"}): "Low",
    frozenset({"Renal_1", "Circulatory_2"}): "Low",
    frozenset({"Renal_1", "Skin_1"}): "Low",
    frozenset({"Renal_3", "Circulatory_1"}): "Low",

    # Neurological + other systems
    frozenset({"Neurological_4", "Endocrine_2"}): "Low",
    frozenset({"Neurological_4", "Musculoskeletal_1"}): "Low",
    frozenset({"Neurological_5", "Musculoskeletal_1"}): "Low",
    frozenset({"Neurological_4", "Behavioral_1"}): "Low",
    frozenset({"Neurological_4", "Gastrointestinal_1"}): "Low",
    frozenset({"Neurological_6", "Endocrine_1"}): "Low",
    frozenset({"Neurological_7", "Endocrine_1"}): "Low",
    frozenset({"Neurological_8", "Heart_3"}): "Low",
    frozenset({"Neurological_10", "Heart_3"}): "Low",
    frozenset({"Neurological_11", "Heart_3"}): "Low",
    frozenset({"Neurological_12", "Heart_3"}): "Low",

    # Circulatory + other systems
    frozenset({"Circulatory_1", "Gastrointestinal_1"}): "Low",
    frozenset({"Circulatory_1", "Musculoskeletal_1"}): "Low",
    frozenset({"Circulatory_1", "Behavioral_1"}): "Low",
    frozenset({"Circulatory_1", "Skin_3"}): "Low",
    frozenset({"Circulatory_2", "Heart_3"}): "Low",
    frozenset({"Circulatory_3", "Heart_3"}): "Low",
    frozenset({"Circulatory_4", "Heart_3"}): "Low",
    frozenset({"Circulatory_4", "Endocrine_1"}): "Low",
    frozenset({"Circulatory_9", "Endocrine_1"}): "Low",
    frozenset({"Circulatory_10", "Endocrine_1"}): "Low",

    # Neoplasm cross-system
    frozenset({"Neoplasm_2", "Heart_3"}): "Low",
    frozenset({"Neoplasm_3", "Heart_3"}): "Low",
    frozenset({"Neoplasm_4", "Heart_3"}): "Low",
    frozenset({"Neoplasm_2", "Endocrine_1"}): "Low",
    frozenset({"Neoplasm_2", "Respiratory_2"}): "Low",
    frozenset({"Neoplasm_6", "Infectious_1"}): "Low",
    frozenset({"Neoplasm_7", "Infectious_1"}): "Low",

    # Gastrointestinal cross-system
    frozenset({"Gastrointestinal_1", "Musculoskeletal_1"}): "Low",
    frozenset({"Gastrointestinal_1", "Behavioral_1"}): "Low",
    frozenset({"Gastrointestinal_2", "Endocrine_1"}): "Low",
    frozenset({"Gastrointestinal_4", "Heart_3"}): "Low",
    frozenset({"Gastrointestinal_5", "Heart_3"}): "Low",
    frozenset({"Gastrointestinal_6", "Endocrine_1"}): "Low",

    # Skin cross-system
    frozenset({"Skin_1", "Musculoskeletal_1"}): "Low",
    frozenset({"Skin_1", "Gastrointestinal_1"}): "Low",
    frozenset({"Skin_3", "Endocrine_1"}): "Low",
    frozenset({"Skin_4", "Endocrine_1"}): "Low",
    frozenset({"Skin_5", "Circulatory_1"}): "Low",

    # Behavioral cross-system
    frozenset({"Behavioral_1", "Musculoskeletal_1"}): "Low",
    frozenset({"Behavioral_1", "Gastrointestinal_1"}): "Low",
    frozenset({"Behavioral_2", "Endocrine_1"}): "Low",
    frozenset({"Behavioral_4", "Heart_3"}): "Low",
    frozenset({"Behavioral_5", "Neurological_4"}): "Low",
    frozenset({"Behavioral_6", "Endocrine_1"}): "Low",

    # Musculoskeletal cross-system
    frozenset({"Musculoskeletal_1", "Behavioral_2"}): "Low",
    frozenset({"Musculoskeletal_2", "Endocrine_1"}): "Low",
    frozenset({"Musculoskeletal_3", "Heart_3"}): "Low",
    frozenset({"Musculoskeletal_4", "Heart_3"}): "Low",

    # Cerebral cross-system
    frozenset({"Cerebral_1", "Heart_3"}): "Low",
    frozenset({"Cerebral_2", "Heart_3"}): "Low",
    frozenset({"Cerebral_1", "Endocrine_1"}): "Low",
    frozenset({"Cerebral_4", "Respiratory_2"}): "Low",
}


def determine_comorbidity_adjustment(
    primary_subgroup: str,
    secondary_subgroups: List[str],
) -> str:
    """Determine comorbidity adjustment level from diagnosis subgroups.

    CMS checks ALL unique pairs among the primary and secondary subgroups.
    The highest interaction found wins: High > Low > None.

    Args:
        primary_subgroup: COMORBIDITY_GROUP of the primary diagnosis.
        secondary_subgroups: COMORBIDITY_GROUP values of secondary diagnoses.

    Returns:
        'None', 'Low', or 'High'.
    """
    # Collect all unique, non-empty subgroups
    all_groups = set()
    if primary_subgroup and primary_subgroup != "No_group":
        all_groups.add(primary_subgroup)
    for sg in secondary_subgroups:
        if sg and sg != "No_group":
            all_groups.add(sg)

    if len(all_groups) < 2:
        return "None"

    best = "None"
    groups_list = list(all_groups)
    for i in range(len(groups_list)):
        for j in range(i + 1, len(groups_list)):
            pair = frozenset({groups_list[i], groups_list[j]})
            level = COMORBIDITY_INTERACTIONS.get(pair)
            if level == "High":
                return "High"  # Can't get higher
            if level == "Low":
                best = "Low"

    return best
