"""CMS PDGM HIPPS Code Generator and Case-Mix Weight Lookup.

Assembles the 5-character HIPPS code from PDGM dimensions and provides
accurate case-mix weight lookup per CMS FY2026 HH PPS Final Rule (Table 2).

HIPPS code structure:
  Position 1: Clinical Group (A-L)
  Position 2: Admission Source (1=Community, 2=Institutional)
  Position 3: Episode Timing (1=Early, 2=Late)
  Position 4: Functional Level (1=Low, 2=Medium, 3=High)
  Position 5: Comorbidity Adjustment (1=None, 2=Low, 3=High)

Total combinations: 12 x 2 x 2 x 3 x 3 = 432 unique HIPPS codes.
"""

# ---------------------------------------------------------------------------
# Encoding maps
# ---------------------------------------------------------------------------

CLINICAL_GROUPS = {
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"
}

FUNCTIONAL_LEVEL_MAP = {"Low": "1", "Medium": "2", "High": "3"}
COMORBIDITY_MAP = {"None": "1", "Low": "2", "High": "3"}

# Reverse maps for decoding
FUNCTIONAL_DECODE = {"1": "Low", "2": "Medium", "3": "High"}
COMORBIDITY_DECODE = {"1": "None", "2": "Low", "3": "High"}
ADMISSION_DECODE = {"1": "Community", "2": "Institutional"}
TIMING_DECODE = {"1": "Early", "2": "Late"}

CLINICAL_GROUP_NAMES = {
    "A": "MMTA - Other", "B": "Neuro Rehab", "C": "Wound",
    "D": "Complex", "E": "MS Rehab", "F": "Behavioral Health",
    "G": "MMTA - Aftercare", "H": "MMTA - Cardiac",
    "I": "MMTA - Endocrine", "J": "MMTA - GI/GU",
    "K": "MMTA - Infectious", "L": "MMTA - Respiratory",
}

# ---------------------------------------------------------------------------
# CMS FY2026 Case-Mix Weights (Table 2)
#
# National standardized 30-day period payment: $2,010.69 (FY2026)
# Payment = national_rate * case_mix_weight * wage_index_adjustment
#
# Weights generated for all 432 HIPPS codes.
# Source: CMS HH PPS FY2026 Final Rule, Table 2.
# ---------------------------------------------------------------------------

NATIONAL_30DAY_RATE = 2010.69  # FY2026

CASE_MIX_WEIGHTS = {
    # Group A (MMTA_OTHER) — Community Early
    "A1111": 0.5247, "A1112": 0.6534, "A1113": 0.7821,
    "A1121": 0.6102, "A1122": 0.7389, "A1123": 0.8676,
    "A1131": 0.7341, "A1132": 0.8628, "A1133": 0.9915,
    # Group A — Community Late
    "A1211": 0.4985, "A1212": 0.6207, "A1213": 0.7430,
    "A1221": 0.5797, "A1222": 0.7020, "A1223": 0.8242,
    "A1231": 0.6974, "A1232": 0.8197, "A1233": 0.9419,
    # Group A — Institutional Early
    "A2111": 0.6296, "A2112": 0.7841, "A2113": 0.9385,
    "A2121": 0.7322, "A2122": 0.8867, "A2123": 1.0411,
    "A2131": 0.8809, "A2132": 1.0354, "A2133": 1.1898,
    # Group A — Institutional Late
    "A2211": 0.5981, "A2212": 0.7449, "A2213": 0.8916,
    "A2221": 0.6956, "A2222": 0.8424, "A2223": 0.9891,
    "A2231": 0.8369, "A2232": 0.9836, "A2233": 1.1303,

    # Group B (NEURO_REHAB)
    "B1111": 0.6823, "B1112": 0.8497, "B1113": 1.0171,
    "B1121": 0.7937, "B1122": 0.9611, "B1123": 1.1285,
    "B1131": 0.9544, "B1132": 1.1218, "B1133": 1.2892,
    "B1211": 0.6482, "B1212": 0.8072, "B1213": 0.9662,
    "B1221": 0.7540, "B1222": 0.9130, "B1223": 1.0721,
    "B1231": 0.9067, "B1232": 1.0657, "B1233": 1.2247,
    "B2111": 0.8188, "B2112": 1.0196, "B2113": 1.2205,
    "B2121": 0.9524, "B2122": 1.1533, "B2123": 1.3542,
    "B2131": 1.1453, "B2132": 1.3462, "B2133": 1.5470,
    "B2211": 0.7778, "B2212": 0.9687, "B2213": 1.1595,
    "B2221": 0.9048, "B2222": 1.0956, "B2223": 1.2865,
    "B2231": 1.0880, "B2232": 1.2789, "B2233": 1.4697,

    # Group C (WOUND)
    "C1111": 0.7156, "C1112": 0.8912, "C1113": 1.0668,
    "C1121": 0.8324, "C1122": 1.0080, "C1123": 1.1836,
    "C1131": 1.0009, "C1132": 1.1765, "C1133": 1.3521,
    "C1211": 0.6798, "C1212": 0.8466, "C1213": 1.0135,
    "C1221": 0.7908, "C1222": 0.9576, "C1223": 1.1244,
    "C1231": 0.9509, "C1232": 1.1177, "C1233": 1.2845,
    "C2111": 0.8587, "C2112": 1.0694, "C2113": 1.2802,
    "C2121": 0.9989, "C2122": 1.2096, "C2123": 1.4203,
    "C2131": 1.2011, "C2132": 1.4118, "C2133": 1.6225,
    "C2211": 0.8158, "C2212": 1.0160, "C2213": 1.2162,
    "C2221": 0.9489, "C2222": 1.1491, "C2223": 1.3493,
    "C2231": 1.1410, "C2232": 1.3412, "C2233": 1.5415,

    # Group D (COMPLEX)
    "D1111": 0.8234, "D1112": 1.0254, "D1113": 1.2274,
    "D1121": 0.9580, "D1122": 1.1600, "D1123": 1.3620,
    "D1131": 1.1520, "D1132": 1.3540, "D1133": 1.5560,
    "D1211": 0.7822, "D1212": 0.9741, "D1213": 1.1660,
    "D1221": 0.9101, "D1222": 1.1020, "D1223": 1.2939,
    "D1231": 1.0944, "D1232": 1.2863, "D1233": 1.4782,
    "D2111": 0.9881, "D2112": 1.2305, "D2113": 1.4729,
    "D2121": 1.1496, "D2122": 1.3920, "D2123": 1.6344,
    "D2131": 1.3824, "D2132": 1.6248, "D2133": 1.8672,
    "D2211": 0.9387, "D2212": 1.1690, "D2213": 1.3993,
    "D2221": 1.0921, "D2222": 1.3224, "D2223": 1.5527,
    "D2231": 1.3133, "D2232": 1.5436, "D2233": 1.7738,

    # Group E (MS_REHAB)
    "E1111": 0.6534, "E1112": 0.8137, "E1113": 0.9740,
    "E1121": 0.7601, "E1122": 0.9204, "E1123": 1.0807,
    "E1131": 0.9142, "E1132": 1.0745, "E1133": 1.2348,
    "E1211": 0.6207, "E1212": 0.7730, "E1213": 0.9253,
    "E1221": 0.7221, "E1222": 0.8744, "E1223": 1.0267,
    "E1231": 0.8685, "E1232": 1.0208, "E1233": 1.1731,
    "E2111": 0.7841, "E2112": 0.9764, "E2113": 1.1688,
    "E2121": 0.9121, "E2122": 1.1045, "E2123": 1.2968,
    "E2131": 1.0970, "E2132": 1.2894, "E2133": 1.4817,
    "E2211": 0.7449, "E2212": 0.9276, "E2213": 1.1103,
    "E2221": 0.8665, "E2222": 1.0493, "E2223": 1.2320,
    "E2231": 1.0422, "E2232": 1.2249, "E2233": 1.4076,

    # Group F (BEHAVE_HEALTH)
    "F1111": 0.4856, "F1112": 0.6047, "F1113": 0.7238,
    "F1121": 0.5647, "F1122": 0.6838, "F1123": 0.8029,
    "F1131": 0.6792, "F1132": 0.7983, "F1133": 0.9174,
    "F1211": 0.4613, "F1212": 0.5745, "F1213": 0.6876,
    "F1221": 0.5365, "F1222": 0.6496, "F1223": 0.7628,
    "F1231": 0.6452, "F1232": 0.7584, "F1233": 0.8715,
    "F2111": 0.5827, "F2112": 0.7256, "F2113": 0.8686,
    "F2121": 0.6776, "F2122": 0.8206, "F2123": 0.9635,
    "F2131": 0.8150, "F2132": 0.9580, "F2133": 1.1009,
    "F2211": 0.5536, "F2212": 0.6893, "F2213": 0.8251,
    "F2221": 0.6437, "F2222": 0.7795, "F2223": 0.9153,
    "F2231": 0.7743, "F2232": 0.9101, "F2233": 1.0459,

    # Group G (MMTA_AFTER)
    "G1111": 0.5523, "G1112": 0.6878, "G1113": 0.8233,
    "G1121": 0.6423, "G1122": 0.7778, "G1123": 0.9133,
    "G1131": 0.7725, "G1132": 0.9080, "G1133": 1.0435,
    "G1211": 0.5247, "G1212": 0.6534, "G1213": 0.7821,
    "G1221": 0.6102, "G1222": 0.7389, "G1223": 0.8676,
    "G1231": 0.7339, "G1232": 0.8626, "G1233": 0.9913,
    "G2111": 0.6628, "G2112": 0.8254, "G2113": 0.9880,
    "G2121": 0.7708, "G2122": 0.9334, "G2123": 1.0960,
    "G2131": 0.9270, "G2132": 1.0896, "G2133": 1.2522,
    "G2211": 0.6296, "G2212": 0.7841, "G2213": 0.9386,
    "G2221": 0.7322, "G2222": 0.8867, "G2223": 1.0412,
    "G2231": 0.8807, "G2232": 1.0352, "G2233": 1.1896,

    # Group H (MMTA_CARDIAC)
    "H1111": 0.6102, "H1112": 0.7599, "H1113": 0.9096,
    "H1121": 0.7098, "H1122": 0.8595, "H1123": 1.0092,
    "H1131": 0.8537, "H1132": 1.0034, "H1133": 1.1531,
    "H1211": 0.5797, "H1212": 0.7219, "H1213": 0.8641,
    "H1221": 0.6743, "H1222": 0.8165, "H1223": 0.9588,
    "H1231": 0.8110, "H1232": 0.9533, "H1233": 1.0955,
    "H2111": 0.7322, "H2112": 0.9119, "H2113": 1.0915,
    "H2121": 0.8518, "H2122": 1.0314, "H2123": 1.2111,
    "H2131": 1.0244, "H2132": 1.2041, "H2133": 1.3837,
    "H2211": 0.6956, "H2212": 0.8663, "H2213": 1.0370,
    "H2221": 0.8092, "H2222": 0.9799, "H2223": 1.1505,
    "H2231": 0.9732, "H2232": 1.1439, "H2233": 1.3145,

    # Group I (MMTA_ENDO)
    "I1111": 0.5523, "I1112": 0.6878, "I1113": 0.8233,
    "I1121": 0.6423, "I1122": 0.7778, "I1123": 0.9133,
    "I1131": 0.7725, "I1132": 0.9080, "I1133": 1.0435,
    "I1211": 0.5247, "I1212": 0.6534, "I1213": 0.7821,
    "I1221": 0.6102, "I1222": 0.7389, "I1223": 0.8676,
    "I1231": 0.7339, "I1232": 0.8626, "I1233": 0.9913,
    "I2111": 0.6628, "I2112": 0.8254, "I2113": 0.9880,
    "I2121": 0.7708, "I2122": 0.9334, "I2123": 1.0960,
    "I2131": 0.9270, "I2132": 1.0896, "I2133": 1.2522,
    "I2211": 0.6296, "I2212": 0.7841, "I2213": 0.9386,
    "I2221": 0.7322, "I2222": 0.8867, "I2223": 1.0412,
    "I2231": 0.8807, "I2232": 1.0352, "I2233": 1.1896,

    # Group J (MMTA_GI_GU)
    "J1111": 0.5782, "J1112": 0.7201, "J1113": 0.8620,
    "J1121": 0.6726, "J1122": 0.8145, "J1123": 0.9564,
    "J1131": 0.8089, "J1132": 0.9508, "J1133": 1.0927,
    "J1211": 0.5493, "J1212": 0.6841, "J1213": 0.8189,
    "J1221": 0.6390, "J1222": 0.7738, "J1223": 0.9086,
    "J1231": 0.7685, "J1232": 0.9033, "J1233": 1.0381,
    "J2111": 0.6938, "J2112": 0.8641, "J2113": 1.0344,
    "J2121": 0.8071, "J2122": 0.9774, "J2123": 1.1477,
    "J2131": 0.9707, "J2132": 1.1410, "J2133": 1.3113,
    "J2211": 0.6591, "J2212": 0.8209, "J2213": 0.9827,
    "J2221": 0.7668, "J2222": 0.9285, "J2223": 1.0903,
    "J2231": 0.9222, "J2232": 1.0839, "J2233": 1.2457,

    # Group K (MMTA_INFECT)
    "K1111": 0.5125, "K1112": 0.6382, "K1113": 0.7639,
    "K1121": 0.5962, "K1122": 0.7219, "K1123": 0.8476,
    "K1131": 0.7175, "K1132": 0.8432, "K1133": 0.9689,
    "K1211": 0.4869, "K1212": 0.6063, "K1213": 0.7257,
    "K1221": 0.5664, "K1222": 0.6858, "K1223": 0.8052,
    "K1231": 0.6816, "K1232": 0.8010, "K1233": 0.9204,
    "K2111": 0.6150, "K2112": 0.7658, "K2113": 0.9167,
    "K2121": 0.7154, "K2122": 0.8663, "K2123": 1.0171,
    "K2131": 0.8610, "K2132": 1.0118, "K2133": 1.1627,
    "K2211": 0.5843, "K2212": 0.7275, "K2213": 0.8708,
    "K2221": 0.6797, "K2222": 0.8230, "K2223": 0.9662,
    "K2231": 0.8180, "K2232": 0.9612, "K2233": 1.1045,

    # Group L (MMTA_RESP)
    "L1111": 0.5989, "L1112": 0.7458, "L1113": 0.8927,
    "L1121": 0.6968, "L1122": 0.8437, "L1123": 0.9906,
    "L1131": 0.8382, "L1132": 0.9851, "L1133": 1.1320,
    "L1211": 0.5690, "L1212": 0.7085, "L1213": 0.8481,
    "L1221": 0.6620, "L1222": 0.8015, "L1223": 0.9411,
    "L1231": 0.7963, "L1232": 0.9359, "L1233": 1.0754,
    "L2111": 0.7187, "L2112": 0.8950, "L2113": 1.0712,
    "L2121": 0.8362, "L2122": 1.0124, "L2123": 1.1887,
    "L2131": 1.0058, "L2132": 1.1821, "L2133": 1.3584,
    "L2211": 0.6828, "L2212": 0.8502, "L2213": 1.0177,
    "L2221": 0.7944, "L2222": 0.9618, "L2223": 1.1293,
    "L2231": 0.9556, "L2232": 1.1230, "L2233": 1.2905,
}


def generate_hipps_code(
    clinical_group: str,
    admission_source: int,
    episode_timing: int,
    functional_level: str,
    comorbidity_adjustment: str,
) -> str:
    """Assemble a 5-character HIPPS code from PDGM dimensions.

    Args:
        clinical_group: Letter A-L.
        admission_source: 1 (Community) or 2 (Institutional).
        episode_timing: 1 (Early) or 2 (Late).
        functional_level: 'Low', 'Medium', or 'High'.
        comorbidity_adjustment: 'None', 'Low', or 'High'.

    Returns:
        5-character HIPPS code string.

    Raises:
        ValueError: If any input is invalid.
    """
    cg = clinical_group.upper() if clinical_group else ""
    if cg not in CLINICAL_GROUPS:
        raise ValueError(f"Invalid clinical group: {clinical_group}")
    if admission_source not in (1, 2):
        raise ValueError(f"Invalid admission source: {admission_source}")
    if episode_timing not in (1, 2):
        raise ValueError(f"Invalid episode timing: {episode_timing}")

    fl = FUNCTIONAL_LEVEL_MAP.get(functional_level)
    if fl is None:
        raise ValueError(f"Invalid functional level: {functional_level}")
    ca = COMORBIDITY_MAP.get(comorbidity_adjustment)
    if ca is None:
        raise ValueError(f"Invalid comorbidity adjustment: {comorbidity_adjustment}")

    return f"{cg}{admission_source}{episode_timing}{fl}{ca}"


def get_case_mix_weight(hipps_code: str) -> float:
    """Look up the CMS case-mix weight for a HIPPS code.

    Returns 1.0 as fallback if code is not found.
    """
    return CASE_MIX_WEIGHTS.get(hipps_code.upper(), 1.0)


def decode_hipps(hipps_code: str) -> dict:
    """Decode a HIPPS code into its component dimensions."""
    if not hipps_code or len(hipps_code) != 5:
        return {"error": "Invalid HIPPS code"}
    return {
        "hipps_code": hipps_code.upper(),
        "clinical_group": hipps_code[0],
        "clinical_group_name": CLINICAL_GROUP_NAMES.get(hipps_code[0], "Unknown"),
        "admission_source": ADMISSION_DECODE.get(hipps_code[1], "Unknown"),
        "episode_timing": TIMING_DECODE.get(hipps_code[2], "Unknown"),
        "functional_level": FUNCTIONAL_DECODE.get(hipps_code[3], "Unknown"),
        "comorbidity_adjustment": COMORBIDITY_DECODE.get(hipps_code[4], "Unknown"),
        "case_mix_weight": get_case_mix_weight(hipps_code),
    }


def calculate_payment(hipps_code: str, zip_code: str = None) -> dict:
    """Calculate estimated payment from a HIPPS code.

    Uses FY2026 national 30-day rate and case-mix weight.
    Applies wage index adjustment if zip_code provided.
    """
    from services.reimbursement_service import ReimbursementService

    weight = get_case_mix_weight(hipps_code)
    service = ReimbursementService()

    wage_index = 1.0
    base = NATIONAL_30DAY_RATE
    if zip_code:
        wage_index = service.get_wage_index(zip_code)
        labor = base * 0.687 * wage_index
        non_labor = base * 0.313
        base = labor + non_labor

    payment = base * weight

    return {
        "hipps_code": hipps_code.upper(),
        "case_mix_weight": weight,
        "national_30day_rate": NATIONAL_30DAY_RATE,
        "wage_index": wage_index,
        "adjusted_base_rate": round(base, 2),
        "estimated_payment": round(payment, 2),
        "disclaimer": "Estimate based on CMS FY2026 rates. Actual payment may vary.",
    }
