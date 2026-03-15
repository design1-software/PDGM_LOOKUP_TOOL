from datetime import datetime


class ReimbursementService:
    def __init__(self):
        self.base_rates = self.load_base_rates()
        self.pdgm_multipliers = self.load_pdgm_multipliers()
        self.zip_adjustments = {}

    def load_base_rates(self):
        """Load CMS base payment rates"""
        return {
            'national_base': 1901.12,
            'rural_adjustment': 1.03,
            'wage_index_floor': 0.60,
        }

    def load_pdgm_multipliers(self):
        """Load PDGM case-mix multipliers.

        The mapping contains a very small subset of actual HIPPS case-mix
        weights. It now also includes single letter clinical group codes (A-L)
        used by the CSV so tests can estimate payments without a full dataset.
        """
        return {
            # Example HIPPS codes
            'MMTA01': 0.9523, 'MMTA02': 1.0477, 'MMTA03': 1.1431,
            'MMTA04': 0.9523, 'MMTA05': 1.0477, 'MMTA06': 1.1431,
            'MMTA07': 0.9523, 'MMTA08': 1.0477, 'MMTA09': 1.1431,
            'MMTA10': 0.9523, 'MMTA11': 1.0477, 'MMTA12': 1.1431,
            'SURG01': 0.8569, 'SURG02': 0.9523, 'SURG03': 1.0477,
            'SURG04': 0.8569, 'SURG05': 0.9523, 'SURG06': 1.0477,
            'BEHAV01': 0.9523, 'BEHAV02': 1.0477,
            'COMPLEX01': 1.1431, 'COMPLEX02': 1.2385,

            # Letter based clinical group codes
            'A': 1.00, 'MMTA_OTHER': 1.00,
            'B': 1.05, 'NEURO_REHAB': 1.05,
            'C': 0.98, 'WOUND': 0.98,
            'D': 1.10, 'COMPLEX': 1.10,
            'E': 1.02, 'MS_REHAB': 1.02,
            'F': 0.97, 'BEHAVE_HEALTH': 0.97,
            'G': 1.00, 'MMTA_AFTER': 1.00,
            'H': 1.03, 'MMTA_CARDIAC': 1.03,
            'I': 1.00, 'MMTA_ENDO': 1.00,
            'J': 1.01, 'MMTA_GI_GU': 1.01,
            'K': 0.95, 'MMTA_INFECT': 0.95,
            'L': 1.04, 'MMTA_RESP': 1.04,

            'DEFAULT': 1.0000,
        }

    def get_wage_index(self, zip_code):
        """Get wage index for ZIP code"""
        if zip_code in self.zip_adjustments:
            return self.zip_adjustments[zip_code]
        state_estimates = {
            '10': 1.15, '11': 1.12, '20': 1.08, '21': 1.08,
            '90': 1.20, '91': 1.18, '92': 1.16, '93': 1.14,
            '02': 1.10, '03': 1.08,
            '30': 1.02, '33': 1.01, '60': 1.05, '77': 1.03,
            '35': 0.85, '38': 0.82, '40': 0.88, '50': 0.90,
        }
        prefix = zip_code[:2] if len(zip_code) >= 2 else '00'
        wage_index = state_estimates.get(prefix, 0.95)
        self.zip_adjustments[zip_code] = wage_index
        return wage_index

    def calculate_payment(self, pdgm_code, zip_code=None, visit_count=None, episode_timing='early'):
        """Calculate estimated payment amount"""
        try:
            base_rate = self.base_rates['national_base']
            wage_index = 1.0
            if zip_code:
                wage_index = self.get_wage_index(zip_code)
                labor = base_rate * 0.687 * wage_index
                non_labor = base_rate * 0.313
                base_rate = labor + non_labor
            multiplier = self.pdgm_multipliers.get(pdgm_code, self.pdgm_multipliers['DEFAULT'])
            payment = base_rate * multiplier
            if episode_timing == 'late':
                payment *= 0.95
            lupa_threshold = self.get_lupa_threshold(pdgm_code)
            is_lupa = bool(visit_count) and visit_count < lupa_threshold
            if is_lupa and visit_count is not None:
                per_visit_rate = self.get_per_visit_rate(pdgm_code)
                payment = per_visit_rate * visit_count
            return {
                'estimated_payment': round(payment, 2),
                'base_rate': round(base_rate, 2),
                'pdgm_multiplier': multiplier,
                'wage_index': wage_index,
                'is_lupa': is_lupa,
                'lupa_threshold': lupa_threshold,
                'episode_timing': episode_timing,
                'calculation_date': datetime.now().strftime('%Y-%m-%d'),
                'disclaimer': 'Estimate only. Actual payment may vary based on specific circumstances.'
            }
        except Exception as e:
            return {'error': f'Payment calculation failed: {str(e)}', 'estimated_payment': None}

    def get_lupa_threshold(self, pdgm_code):
        """Get LUPA threshold for PDGM code"""
        thresholds = {'MMTA': 4, 'SURG': 2, 'BEHAV': 7, 'COMPLEX': 6}
        if pdgm_code.startswith('MMTA'):
            return thresholds['MMTA']
        if pdgm_code.startswith('SURG'):
            return thresholds['SURG']
        if pdgm_code.startswith('BEHAV'):
            return thresholds['BEHAV']
        if pdgm_code.startswith('COMPLEX'):
            return thresholds['COMPLEX']
        return 4

    def get_per_visit_rate(self, pdgm_code):
        """Get per-visit rate for LUPA calculations"""
        rates = {
            'MMTA': 150.00,
            'SURG': 160.00,
            'BEHAV': 140.00,
            'COMPLEX': 170.00,
        }
        for prefix, rate in rates.items():
            if pdgm_code.startswith(prefix):
                return rate
        return 145.00


def extract_pdgm_code_from_response(ai_response):
    """Extract PDGM code from AI response"""
    import re
    # Match explicit HIPPS codes (e.g. MMTA01) or single clinical group
    # letters (A-L) that appear in the mapping CSV.
    group_names = (
        'BEHAVE_HEALTH|COMPLEX|MMTA_AFTER|MMTA_CARDIAC|MMTA_ENDO|MMTA_GI_GU|'
        'MMTA_INFECT|MMTA_OTHER|MMTA_RESP|MS_REHAB|NEURO_REHAB|WOUND'
    )
    pattern = rf'(MMTA\d{{2}}|SURG\d{{2}}|BEHAV\d{{2}}|COMPLEX\d{{2}}|\b[A-L]\b|{group_names})'
    match = re.search(pattern, ai_response)
    return match.group(1) if match else None


def ai_map_phrase_to_code_with_payment(ai_map_func, phrase, zip_code=None, visit_count=None):
    """Call AI mapping function and append reimbursement estimate."""
    ai_response = ai_map_func(phrase)
    pdgm_code = extract_pdgm_code_from_response(ai_response)
    if pdgm_code and zip_code:
        service = ReimbursementService()
        payment_info = service.calculate_payment(pdgm_code, zip_code, visit_count)
        if payment_info.get('estimated_payment'):
            payment_text = f"\n\nESTIMATED REIMBURSEMENT:\n" \
                          f"Payment Amount: ${payment_info['estimated_payment']:,.2f}\n" \
                          f"Base Rate: ${payment_info['base_rate']:,.2f}\n" \
                          f"PDGM Multiplier: {payment_info['pdgm_multiplier']}\n" \
                          f"Wage Index: {payment_info['wage_index']:.3f}\n"
            if payment_info['is_lupa']:
                payment_text += f"⚠️ LUPA Alert: Visit count ({visit_count}) below threshold ({payment_info['lupa_threshold']})\n"
            payment_text += f"\n{payment_info['disclaimer']}"
            ai_response += payment_text
    return ai_response
