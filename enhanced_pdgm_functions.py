"""
Enhanced PDGM Functions with Medical Synonym Mapping and Improved Follow-up Logic
"""

import re
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Set

# Medical synonym mapping for common abbreviations and terms
MEDICAL_SYNONYMS = {
    # --- Original entries ---
    'CHF': ['heart failure', 'congestive heart failure', 'cardiac failure'],
    'DM': ['diabetes mellitus', 'diabetes'],
    'COPD': ['chronic obstructive pulmonary disease', 'chronic obstructive lung disease'],
    'MI': ['myocardial infarction', 'heart attack'],
    'CVA': ['cerebrovascular accident', 'stroke'],
    'UTI': ['urinary tract infection', 'bladder infection'],
    'DVT': ['deep vein thrombosis', 'deep venous thrombosis'],
    'PE': ['pulmonary embolism', 'pulmonary embolus'],
    'GERD': ['gastroesophageal reflux disease', 'acid reflux'],
    'HTN': ['hypertension', 'high blood pressure'],
    'CAD': ['coronary artery disease', 'coronary heart disease'],
    'CKD': ['chronic kidney disease', 'chronic renal disease'],
    'ESRD': ['end stage renal disease', 'end stage kidney disease'],
    'AFIB': ['atrial fibrillation'],
    'PVD': ['peripheral vascular disease', 'peripheral artery disease'],
    'TIA': ['transient ischemic attack', 'mini stroke'],
    'PTSD': ['post traumatic stress disorder'],
    'OCD': ['obsessive compulsive disorder'],
    'ADHD': ['attention deficit hyperactivity disorder'],
    'HIV': ['human immunodeficiency virus'],
    'AIDS': ['acquired immunodeficiency syndrome'],
    'MRSA': ['methicillin resistant staphylococcus aureus'],
    'C DIFF': ['clostridium difficile', 'clostridioides difficile'],
    'PNEUMONIA': ['lung infection', 'respiratory infection'],
    'SEPSIS': ['blood infection', 'systemic infection'],
    'CELLULITIS': ['skin infection', 'soft tissue infection'],

    # --- Cardiac (~20) ---
    'A FIB': ['atrial fibrillation', 'afib', 'a-fib'],
    'SVT': ['supraventricular tachycardia'],
    'VT': ['ventricular tachycardia', 'v tach'],
    'ENDOCARDITIS': ['infective endocarditis', 'bacterial endocarditis', 'heart valve infection'],
    'PERICARDITIS': ['pericardial inflammation', 'inflammation of pericardium'],
    'CARDIOMYOPATHY': ['heart muscle disease', 'dilated cardiomyopathy', 'hypertrophic cardiomyopathy'],
    'VALVE REPLACEMENT': ['heart valve replacement', 'prosthetic heart valve', 'mechanical valve', 'bioprosthetic valve'],
    'PACEMAKER': ['cardiac pacemaker', 'pacemaker insertion', 'pacemaker placement'],
    'AICD': ['automatic implantable cardioverter defibrillator', 'icd', 'implantable cardioverter defibrillator', 'defibrillator implant'],
    'ICD': ['implantable cardioverter defibrillator', 'aicd', 'automatic implantable cardioverter defibrillator'],
    'ANGINA': ['chest pain', 'angina pectoris', 'stable angina', 'unstable angina'],
    'AORTIC STENOSIS': ['aortic valve stenosis', 'as', 'narrowing of aortic valve'],
    'MITRAL REGURGITATION': ['mitral valve regurgitation', 'mr', 'mitral insufficiency', 'mitral valve incompetence'],
    'BRADYCARDIA': ['slow heart rate', 'low heart rate', 'sinus bradycardia'],
    'TACHYCARDIA': ['fast heart rate', 'rapid heart rate', 'sinus tachycardia'],
    'CARDIAC ARREST': ['heart stopped', 'asystole', 'cardiopulmonary arrest', 'code blue'],
    'STENT': ['cardiac stent', 'coronary stent', 'stent placement', 'percutaneous coronary intervention', 'pci'],
    'CABG': ['coronary artery bypass graft', 'bypass surgery', 'heart bypass', 'coronary bypass'],
    'CORONARY ARTERY DISEASE': ['cad', 'coronary heart disease', 'ischemic heart disease', 'atherosclerotic heart disease', 'ashd'],

    # --- Respiratory (~15) ---
    'ASTHMA': ['reactive airway disease', 'bronchial asthma', 'asthmatic bronchitis'],
    'BRONCHIECTASIS': ['dilated bronchi', 'chronic bronchiectasis'],
    'TRACHEOSTOMY': ['trach', 'tracheotomy', 'trach tube', 'tracheostomy tube'],
    'VENTILATOR DEPENDENT': ['ventilator dependence', 'vent dependent', 'mechanical ventilation', 'on ventilator'],
    'O2 DEPENDENT': ['oxygen dependent', 'supplemental oxygen', 'home oxygen', 'chronic oxygen therapy'],
    'PLEURAL EFFUSION': ['fluid around lung', 'fluid in pleural space', 'pleural fluid'],
    'PNEUMOTHORAX': ['collapsed lung', 'air in pleural space', 'lung collapse'],
    'PULMONARY FIBROSIS': ['lung fibrosis', 'interstitial lung disease', 'ild', 'idiopathic pulmonary fibrosis', 'ipf'],
    'PULMONARY HYPERTENSION': ['pulmonary arterial hypertension', 'pah', 'elevated pulmonary pressure'],
    'RSV': ['respiratory syncytial virus'],
    'CROUP': ['laryngotracheobronchitis', 'viral croup'],
    'BRONCHIOLITIS': ['viral bronchiolitis', 'acute bronchiolitis'],
    'SLEEP APNEA': ['obstructive sleep apnea', 'osa', 'central sleep apnea', 'sleep disordered breathing'],
    'RESPIRATORY FAILURE': ['acute respiratory failure', 'chronic respiratory failure', 'respiratory insufficiency'],
    'LUNG CANCER': ['pulmonary neoplasm', 'bronchogenic carcinoma', 'lung neoplasm', 'lung malignancy'],

    # --- Wound (~15) ---
    'PRESSURE INJURY': ['pressure ulcer', 'decubitus ulcer', 'decubitus', 'bedsore', 'bed sore', 'pressure sore'],
    'PRESSURE ULCER STAGE 1': ['stage 1 pressure injury', 'stage i pressure ulcer', 'non blanchable erythema'],
    'PRESSURE ULCER STAGE 2': ['stage 2 pressure injury', 'stage ii pressure ulcer', 'partial thickness skin loss'],
    'PRESSURE ULCER STAGE 3': ['stage 3 pressure injury', 'stage iii pressure ulcer', 'full thickness skin loss'],
    'PRESSURE ULCER STAGE 4': ['stage 4 pressure injury', 'stage iv pressure ulcer', 'full thickness tissue loss'],
    'UNSTAGEABLE PRESSURE ULCER': ['unstageable pressure injury', 'eschar covered wound'],
    'SURGICAL WOUND DEHISCENCE': ['wound dehiscence', 'incision dehiscence', 'wound separation', 'surgical wound complication'],
    'VENOUS STASIS ULCER': ['venous ulcer', 'venous insufficiency ulcer', 'stasis ulcer', 'venous leg ulcer'],
    'ARTERIAL ULCER': ['arterial insufficiency ulcer', 'ischemic ulcer'],
    'NEUROPATHIC ULCER': ['diabetic foot ulcer', 'diabetic ulcer', 'neuropathic foot ulcer'],
    'SKIN TEAR': ['skin laceration', 'skin avulsion', 'traumatic skin tear'],
    'BURN': ['thermal burn', 'burn wound', 'burn injury', 'chemical burn'],
    'SKIN GRAFT': ['skin graft site', 'graft site', 'split thickness skin graft', 'stsg', 'full thickness skin graft'],
    'WOUND VAC': ['negative pressure wound therapy', 'npwt', 'vac therapy', 'wound vacuum'],
    'ABSCESS': ['skin abscess', 'subcutaneous abscess', 'cutaneous abscess'],
    'GANGRENE': ['gangrenous', 'necrosis', 'tissue necrosis', 'dry gangrene', 'wet gangrene', 'gas gangrene'],

    # --- Neuro (~20) ---
    'PARKINSONS': ['parkinson disease', 'parkinsonism', 'pd'],
    'PD': ['parkinson disease', 'parkinsons', 'parkinsonism'],
    'MS': ['multiple sclerosis', 'demyelinating disease'],
    'MULTIPLE SCLEROSIS': ['ms', 'demyelinating disease'],
    'ALS': ['amyotrophic lateral sclerosis', 'lou gehrig disease', 'motor neuron disease'],
    'ALZHEIMERS': ['alzheimer disease', 'alzheimer dementia', 'senile dementia alzheimer type'],
    'DEMENTIA': ['cognitive impairment', 'memory loss', 'neurocognitive disorder', 'senile dementia'],
    'TBI': ['traumatic brain injury', 'brain injury', 'head injury', 'closed head injury'],
    'SCI': ['spinal cord injury', 'spinal injury'],
    'SPINAL CORD INJURY': ['sci', 'spinal injury', 'paralysis from spinal injury'],
    'HEMIPLEGIA': ['one sided paralysis', 'hemiparesis', 'half body paralysis'],
    'HEMIPARESIS': ['one sided weakness', 'hemiplegia', 'half body weakness'],
    'APHASIA': ['speech impairment', 'language impairment', 'expressive aphasia', 'receptive aphasia'],
    'DYSPHAGIA': ['swallowing difficulty', 'difficulty swallowing', 'swallowing disorder', 'swallowing dysfunction'],
    'SEIZURE': ['epilepsy', 'convulsion', 'seizure disorder'],
    'EPILEPSY': ['seizure disorder', 'recurrent seizures', 'seizure'],
    'NEUROPATHY': ['peripheral neuropathy', 'nerve damage', 'diabetic neuropathy', 'polyneuropathy'],
    'VERTIGO': ['dizziness', 'benign positional vertigo', 'bppv', 'vestibular disorder'],
    'BELL PALSY': ['bells palsy', 'facial nerve palsy', 'facial paralysis'],
    'GUILLAIN BARRE': ['guillain barre syndrome', 'gbs', 'acute inflammatory demyelinating polyneuropathy'],
    'MYASTHENIA GRAVIS': ['mg', 'neuromuscular junction disorder', 'myasthenia'],
    'ENCEPHALOPATHY': ['brain dysfunction', 'metabolic encephalopathy', 'hepatic encephalopathy', 'toxic encephalopathy'],
    'MENINGITIS': ['brain infection', 'meningeal infection', 'bacterial meningitis', 'viral meningitis'],

    # --- Musculoskeletal (~20) ---
    'THR': ['total hip replacement', 'total hip arthroplasty', 'hip replacement'],
    'TOTAL HIP REPLACEMENT': ['thr', 'total hip arthroplasty', 'hip replacement', 'hip arthroplasty'],
    'TKR': ['total knee replacement', 'total knee arthroplasty', 'knee replacement'],
    'TOTAL KNEE REPLACEMENT': ['tkr', 'total knee arthroplasty', 'knee replacement', 'knee arthroplasty'],
    'ARTHROPLASTY': ['joint replacement', 'joint replacement surgery'],
    'ORIF': ['open reduction internal fixation', 'fracture repair', 'surgical fracture fixation'],
    'ROTATOR CUFF': ['rotator cuff tear', 'rotator cuff repair', 'rotator cuff injury', 'shoulder repair'],
    'LAMINECTOMY': ['spinal decompression', 'laminotomy', 'lumbar laminectomy'],
    'SPINAL FUSION': ['spine fusion', 'vertebral fusion', 'lumbar fusion', 'cervical fusion', 'arthrodesis'],
    'AMPUTATION': ['limb amputation', 'surgical amputation'],
    'BKA': ['below knee amputation', 'transtibial amputation', 'lower leg amputation'],
    'AKA': ['above knee amputation', 'transfemoral amputation', 'upper leg amputation'],
    'OSTEOARTHRITIS': ['oa', 'degenerative joint disease', 'djd', 'wear and tear arthritis'],
    'OA': ['osteoarthritis', 'degenerative joint disease', 'djd'],
    'RHEUMATOID ARTHRITIS': ['ra', 'rheumatoid disease', 'inflammatory arthritis'],
    'RA': ['rheumatoid arthritis', 'rheumatoid disease'],
    'GOUT': ['gouty arthritis', 'crystal arthropathy', 'uric acid arthritis'],
    'OSTEOPOROSIS': ['bone loss', 'decreased bone density', 'brittle bones', 'low bone mass'],
    'HIP FRACTURE': ['fractured hip', 'femoral neck fracture', 'intertrochanteric fracture', 'broken hip'],
    'VERTEBRAL FRACTURE': ['spinal fracture', 'compression fracture', 'vertebral compression fracture'],
    'WRIST FRACTURE': ['colles fracture', 'distal radius fracture', 'broken wrist'],
    'JOINT REPLACEMENT': ['arthroplasty', 'prosthetic joint', 'joint prosthesis'],
    'TENDONITIS': ['tendinitis', 'tendon inflammation', 'tendinopathy'],
    'BURSITIS': ['bursa inflammation', 'joint inflammation'],
    'SCIATICA': ['sciatic nerve pain', 'lumbar radiculopathy', 'radiculopathy'],

    # --- Endocrine (~10) ---
    'HYPOTHYROID': ['hypothyroidism', 'underactive thyroid', 'low thyroid'],
    'HYPERTHYROID': ['hyperthyroidism', 'overactive thyroid', 'thyrotoxicosis', 'graves disease'],
    'ADDISONS': ['addison disease', 'adrenal insufficiency', 'primary adrenal insufficiency'],
    'CUSHINGS': ['cushing syndrome', 'cushing disease', 'hypercortisolism'],
    'DKA': ['diabetic ketoacidosis', 'ketoacidosis'],
    'HYPERGLYCEMIA': ['high blood sugar', 'elevated blood glucose', 'elevated glucose'],
    'HYPOGLYCEMIA': ['low blood sugar', 'low blood glucose', 'insulin reaction'],
    'INSULIN PUMP': ['continuous subcutaneous insulin infusion', 'csii', 'insulin pump therapy'],
    'THYROIDECTOMY': ['thyroid removal', 'thyroid surgery', 'total thyroidectomy', 'partial thyroidectomy'],
    'OBESITY': ['morbid obesity', 'severe obesity', 'class iii obesity', 'bmi greater than 40'],
    'MORBID OBESITY': ['obesity', 'severe obesity', 'class iii obesity'],

    # --- GI/GU (~16) ---
    'COLOSTOMY': ['colostomy care', 'colostomy bag', 'stoma care'],
    'ILEOSTOMY': ['ileostomy care', 'ileostomy bag', 'small bowel stoma'],
    'FOLEY': ['foley catheter', 'indwelling catheter', 'urinary catheter', 'bladder catheter'],
    'CATHETER': ['urinary catheter', 'foley catheter', 'indwelling catheter'],
    'SUPRAPUBIC CATHETER': ['suprapubic tube', 'sp catheter', 'suprapubic cystostomy'],
    'NEPHROSTOMY': ['nephrostomy tube', 'percutaneous nephrostomy', 'kidney drain'],
    'PEG TUBE': ['percutaneous endoscopic gastrostomy', 'g tube', 'gastrostomy tube', 'feeding tube'],
    'G TUBE': ['gastrostomy tube', 'peg tube', 'percutaneous endoscopic gastrostomy', 'feeding tube'],
    'TPN': ['total parenteral nutrition', 'parenteral nutrition', 'iv nutrition'],
    'BOWEL OBSTRUCTION': ['intestinal obstruction', 'small bowel obstruction', 'sbo', 'large bowel obstruction', 'ileus'],
    'CROHNS': ['crohn disease', 'regional enteritis', 'inflammatory bowel disease'],
    'UC': ['ulcerative colitis', 'inflammatory bowel disease'],
    'ULCERATIVE COLITIS': ['uc', 'inflammatory bowel disease', 'colitis'],
    'DIVERTICULITIS': ['diverticular disease', 'inflamed diverticulum', 'diverticular abscess'],
    'GI BLEED': ['gastrointestinal hemorrhage', 'gastrointestinal bleeding', 'upper gi bleed', 'lower gi bleed', 'melena', 'hematemesis'],
    'CIRRHOSIS': ['liver cirrhosis', 'hepatic cirrhosis', 'chronic liver disease', 'end stage liver disease'],
    'HEPATITIS': ['liver inflammation', 'hepatitis a', 'hepatitis b', 'hepatitis c', 'viral hepatitis'],
    'PANCREATITIS': ['pancreatic inflammation', 'acute pancreatitis', 'chronic pancreatitis'],
    'KIDNEY STONES': ['nephrolithiasis', 'renal calculi', 'urolithiasis', 'renal stones'],

    # --- Infectious (~10) ---
    'OSTEOMYELITIS': ['bone infection', 'infected bone', 'chronic osteomyelitis', 'acute osteomyelitis'],
    'PICC LINE': ['peripherally inserted central catheter', 'picc', 'central line'],
    'IV ANTIBIOTICS': ['intravenous antibiotics', 'iv abx', 'parenteral antibiotics'],
    'WOUND INFECTION': ['infected wound', 'surgical wound infection', 'wound sepsis'],
    'SURGICAL SITE INFECTION': ['ssi', 'postoperative wound infection', 'post surgical infection'],
    'C DIFFICILE': ['clostridium difficile', 'clostridioides difficile', 'c diff', 'cdiff'],
    'VRE': ['vancomycin resistant enterococcus', 'vancomycin resistant enterococci'],
    'BACTEREMIA': ['bloodstream infection', 'blood infection', 'positive blood cultures'],
    'FUNGAL INFECTION': ['mycosis', 'candidiasis', 'fungal disease', 'yeast infection'],
    'TB': ['tuberculosis', 'mycobacterium tuberculosis', 'pulmonary tuberculosis'],
    'TUBERCULOSIS': ['tb', 'mycobacterium tuberculosis', 'pulmonary tb'],

    # --- Behavioral (~11) ---
    'DEPRESSION': ['major depressive disorder', 'mdd', 'depressive episode', 'clinical depression'],
    'MDD': ['major depressive disorder', 'depression', 'clinical depression'],
    'ANXIETY': ['generalized anxiety disorder', 'gad', 'anxiety disorder', 'anxious'],
    'GAD': ['generalized anxiety disorder', 'anxiety', 'anxiety disorder'],
    'BIPOLAR': ['bipolar disorder', 'manic depressive', 'bipolar affective disorder'],
    'SCHIZOPHRENIA': ['schizoaffective disorder', 'psychotic disorder', 'psychosis'],
    'SUBSTANCE ABUSE': ['substance use disorder', 'drug abuse', 'drug dependence', 'addiction'],
    'ALCOHOL DEPENDENCE': ['alcoholism', 'alcohol use disorder', 'alcohol abuse', 'aud'],
    'COGNITIVE DECLINE': ['cognitive impairment', 'mild cognitive impairment', 'mci', 'memory impairment'],
    'DELIRIUM': ['acute confusion', 'altered mental status', 'ams', 'acute confusional state'],
    'INSOMNIA': ['sleep disorder', 'sleeplessness', 'difficulty sleeping', 'sleep disturbance'],
    'EATING DISORDER': ['anorexia nervosa', 'bulimia nervosa', 'binge eating disorder'],
    'PANIC DISORDER': ['panic attacks', 'panic attack', 'anxiety with panic'],

    # --- Complex care (~10) ---
    'TRANSPLANT': ['organ transplant', 'transplant recipient', 'post transplant', 'graft'],
    'CHEMO': ['chemotherapy', 'cancer treatment', 'antineoplastic therapy'],
    'CHEMOTHERAPY': ['chemo', 'cancer treatment', 'antineoplastic therapy'],
    'RADIATION': ['radiation therapy', 'radiotherapy', 'radiation treatment', 'xrt'],
    'PALLIATIVE CARE': ['comfort care', 'supportive care', 'end of life care', 'hospice transition'],
    'TRACHEOSTOMY CARE': ['trach care', 'tracheostomy management', 'trach tube care'],
    'VENTILATOR WEANING': ['vent weaning', 'weaning from ventilator', 'liberation from ventilator'],
    'COMPLEX WOUND CARE': ['wound management', 'advanced wound care', 'wound treatment'],
    'IV THERAPY': ['intravenous therapy', 'infusion therapy', 'iv infusion'],
    'BLOOD TRANSFUSION': ['transfusion', 'packed red blood cells', 'prbc', 'blood products'],
    'DIALYSIS': ['hemodialysis', 'peritoneal dialysis', 'renal dialysis', 'kidney dialysis', 'hd'],

    # --- Additional cardiac ---
    'HEART MURMUR': ['cardiac murmur', 'heart sound abnormality'],
    'AORTIC ANEURYSM': ['aaa', 'abdominal aortic aneurysm', 'thoracic aortic aneurysm'],
    'CONDUCTION DISORDER': ['heart block', 'bundle branch block', 'av block'],

    # --- Additional respiratory ---
    'EMPHYSEMA': ['pulmonary emphysema', 'chronic emphysema'],
    'CHRONIC BRONCHITIS': ['chronic bronchial inflammation', 'bronchitis chronic'],
    'ACUTE BRONCHITIS': ['bronchitis', 'chest cold', 'acute bronchial infection'],

    # --- Additional neuro ---
    'CEREBRAL PALSY': ['cp', 'spastic cerebral palsy'],
    'HYDROCEPHALUS': ['hydrocephalus', 'normal pressure hydrocephalus', 'nph'],
    'TRIGEMINAL NEURALGIA': ['tic douloureux', 'facial pain syndrome'],

    # --- Additional musculoskeletal ---
    'FROZEN SHOULDER': ['adhesive capsulitis', 'shoulder stiffness'],
    'CARPAL TUNNEL': ['carpal tunnel syndrome', 'cts', 'median nerve entrapment'],
    'PLANTAR FASCIITIS': ['heel pain', 'plantar fasciopathy'],
    'SCOLIOSIS': ['spinal curvature', 'lateral spinal curvature'],

    # --- Additional GI ---
    'GASTRITIS': ['stomach inflammation', 'gastric inflammation'],
    'GASTROPARESIS': ['delayed gastric emptying', 'stomach paralysis'],
    'HEMORRHOIDS': ['piles', 'rectal hemorrhoids', 'internal hemorrhoids', 'external hemorrhoids'],
}

# Context keywords that suggest specific variants
CONTEXT_KEYWORDS = {
    'exacerbation': ['acute', 'acute on chronic', 'with exacerbation'],
    'acute': ['acute', 'sudden onset'],
    'chronic': ['chronic', 'long term', 'persistent'],
    'with complications': ['with complications', 'complicated'],
    'unspecified': ['unspecified', 'not otherwise specified', 'NOS'],
    'type 1': ['type 1', 'type I', 'insulin dependent'],
    'type 2': ['type 2', 'type II', 'non insulin dependent'],
    'systolic': ['systolic', 'left ventricular'],
    'diastolic': ['diastolic', 'right ventricular'],
    'bilateral': ['bilateral', 'both sides'],
    'unilateral': ['unilateral', 'one side'],
    'primary': ['primary', 'essential'],
    'secondary': ['secondary', 'due to']
}

# Predefined follow-up suggestions for common conditions
PREDEFINED_FOLLOWUPS = {
    # --- Original entries ---
    'heart failure': "Would you like to specify: acute exacerbation, chronic systolic, chronic diastolic, or combined systolic/diastolic?",
    'diabetes': "Please specify: Type 1, Type 2, with complications (neuropathy, nephropathy, retinopathy), or gestational?",
    'COPD': "Is this: acute exacerbation, with acute bronchitis, or chronic obstructive asthma?",
    'hypertension': "Please specify: essential hypertension, hypertensive heart disease, or hypertensive kidney disease?",
    'pneumonia': "Would you like to specify: bacterial, viral, aspiration, or organism-specific pneumonia?",
    'diabetes mellitus': "Please specify: Type 1, Type 2, with complications (neuropathy, nephropathy, retinopathy), or gestational?",
    'stroke': "Please specify: ischemic stroke, hemorrhagic stroke, or transient ischemic attack (TIA)?",
    'kidney disease': "Would you like to specify: acute kidney injury, chronic kidney disease stage, or end-stage renal disease?",
    'infection': "Please specify the site: urinary tract, respiratory, skin/soft tissue, or bloodstream infection?",
    'fracture': "Please specify: location (hip, wrist, spine), type (closed, open), or healing status?",
    'wound': "Please specify: pressure ulcer with stage, diabetic ulcer, or surgical wound complication?",
    'pain': "Please specify: location (back, joint, neuropathic), chronic vs acute, or pain syndrome type?",

    # --- Cardiac ---
    'atrial fibrillation': "Please specify: paroxysmal, persistent, or chronic/permanent AFib? With or without rapid ventricular response?",
    'afib': "Please specify: paroxysmal, persistent, or chronic/permanent AFib? With or without rapid ventricular response?",
    'cardiomyopathy': "Would you like to specify: dilated, hypertrophic, ischemic, or restrictive cardiomyopathy?",
    'angina': "Please specify: stable angina, unstable angina, or variant (Prinzmetal) angina?",
    'valve': "Please specify: which valve (aortic, mitral, tricuspid, pulmonic) and the condition (stenosis, regurgitation, replacement)?",
    'pacemaker': "Please specify: new implant, generator replacement, lead revision, or pacemaker malfunction?",
    'stent': "Please specify: new stent placement, in-stent restenosis, or post-stent management?",
    'coronary artery disease': "Would you like to specify: stable CAD, acute coronary syndrome, or post-CABG/stent status?",

    # --- Respiratory ---
    'asthma': "Please specify: mild intermittent, mild persistent, moderate persistent, or severe persistent asthma? With or without acute exacerbation?",
    'respiratory failure': "Please specify: acute or chronic respiratory failure? Hypoxic (Type I) or hypercapnic (Type II)?",
    'tracheostomy': "Please specify: new tracheostomy, tracheostomy care/management, or ventilator weaning via trach?",
    'pleural effusion': "Please specify: malignant or non-malignant effusion? Does it require thoracentesis?",
    'pulmonary fibrosis': "Would you like to specify: idiopathic pulmonary fibrosis, or secondary to a known cause (e.g., medication, autoimmune)?",
    'sleep apnea': "Please specify: obstructive sleep apnea, central sleep apnea, or mixed? On CPAP/BiPAP?",
    'lung cancer': "Please specify: primary or metastatic? Small cell or non-small cell? Currently on treatment?",

    # --- Wound ---
    'pressure ulcer': "Please specify: stage (1, 2, 3, 4, unstageable, or deep tissue injury) and anatomic location (sacrum, heel, ischium)?",
    'pressure injury': "Please specify: stage (1, 2, 3, 4, unstageable, or deep tissue injury) and anatomic location (sacrum, heel, ischium)?",
    'decubitus': "Please specify: stage (1, 2, 3, 4, unstageable, or deep tissue injury) and anatomic location (sacrum, heel, ischium)?",
    'ulcer': "Please specify: pressure ulcer (with stage), venous stasis ulcer, arterial ulcer, or diabetic/neuropathic ulcer?",
    'surgical wound': "Please specify: clean healing incision, wound dehiscence, surgical site infection, or wound complication?",
    'skin graft': "Please specify: split-thickness or full-thickness graft? Donor site or graft site care?",
    'wound vac': "Is this for: pressure injury, surgical wound, diabetic ulcer, or traumatic wound? Please include wound location.",
    'gangrene': "Please specify: dry gangrene, wet gangrene, or gas gangrene? What is the location and underlying cause?",

    # --- Neuro ---
    'parkinson': "Please specify: early or advanced stage Parkinson disease? Any current complications (falls, dysphagia, dementia)?",
    'multiple sclerosis': "Please specify: relapsing-remitting, secondary progressive, or primary progressive MS?",
    'als': "Please specify: current functional status and any complications (respiratory failure, dysphagia, mobility)?",
    'alzheimer': "Please specify: early onset or late onset? Mild, moderate, or severe stage? With or without behavioral disturbance?",
    'dementia': "Please specify: type (Alzheimer, vascular, Lewy body, frontotemporal) and severity (mild, moderate, severe)?",
    'brain injury': "Please specify: traumatic or non-traumatic? Acute, subacute, or chronic phase? Any residual deficits?",
    'spinal cord injury': "Please specify: level (cervical, thoracic, lumbar) and completeness (complete vs incomplete)?",
    'seizure': "Please specify: new onset or known epilepsy? Type (generalized, focal/partial)? Controlled or uncontrolled?",
    'neuropathy': "Please specify: diabetic, alcoholic, idiopathic, or other cause? Sensory, motor, or mixed?",
    'dysphagia': "Please specify: oropharyngeal or esophageal dysphagia? Current diet texture level?",

    # --- Musculoskeletal ---
    'hip replacement': "Please specify: primary or revision total hip arthroplasty? Right, left, or bilateral? Any complications (dislocation, infection)?",
    'knee replacement': "Please specify: primary or revision total knee arthroplasty? Right, left, or bilateral? Any complications?",
    'arthroplasty': "Please specify: which joint (hip, knee, shoulder) and whether primary or revision surgery?",
    'amputation': "Please specify: level (toe, BKA, AKA, upper extremity), side, and whether traumatic or surgical?",
    'spinal fusion': "Please specify: cervical or lumbar fusion? How many levels? Any complications (hardware failure, pseudarthrosis)?",
    'osteoarthritis': "Please specify: which joint(s) involved and severity? Any plans for surgical intervention?",
    'rheumatoid arthritis': "Please specify: disease activity (active flare or stable), affected joints, and current treatment?",
    'gout': "Please specify: acute gout flare or chronic tophaceous gout? Which joint(s)?",
    'osteoporosis': "Please specify: with or without pathological fracture? Location of fracture if applicable?",

    # --- Endocrine ---
    'thyroid': "Please specify: hypothyroidism or hyperthyroidism? Primary or secondary? Post-thyroidectomy?",
    'dka': "Is this a current DKA episode or history of DKA? Type 1 or Type 2 diabetes?",
    'hyperglycemia': "Please specify: related to Type 1 or Type 2 diabetes? With or without ketoacidosis?",
    'hypoglycemia': "Please specify: cause (insulin, oral medications, other) and frequency of episodes?",
    'obesity': "Please specify: BMI range, and whether related to a surgical procedure (bariatric) or contributing to another condition?",

    # --- GI/GU ---
    'colostomy': "Please specify: new colostomy (teaching needed), established colostomy (routine care), or colostomy complication?",
    'catheter': "Please specify: Foley/indwelling, suprapubic, or intermittent catheterization? New placement or ongoing management?",
    'feeding tube': "Please specify: PEG/G-tube or NG tube? New placement teaching or ongoing management? Bolus or continuous feeds?",
    'peg tube': "Please specify: new PEG placement (teaching needed), routine management, or complication (dislodgment, infection)?",
    'bowel obstruction': "Please specify: small bowel or large bowel obstruction? Partial or complete? Surgical or conservative management?",
    'crohn': "Please specify: location (ileal, colonic, ileocolonic), current flare or remission, any fistulas or strictures?",
    'ulcerative colitis': "Please specify: extent (proctitis, left-sided, pancolitis), active flare or remission?",
    'cirrhosis': "Please specify: compensated or decompensated? Etiology (alcohol, hepatitis, NASH)? Any complications (ascites, varices)?",
    'hepatitis': "Please specify: type (A, B, C), acute or chronic, and treatment status?",

    # --- Behavioral ---
    'depression': "Please specify: single episode or recurrent? Mild, moderate, or severe? With or without psychotic features?",
    'anxiety': "Please specify: generalized anxiety disorder, social anxiety, PTSD-related, or panic disorder?",
    'bipolar': "Please specify: Bipolar I or II? Current episode (manic, depressive, mixed)? Stable or unstable?",
    'schizophrenia': "Please specify: paranoid, disorganized, or undifferentiated type? Stable on medication or active symptoms?",
    'substance abuse': "Please specify: substance type (alcohol, opioid, stimulant), current use or in recovery, and any withdrawal concerns?",
    'delirium': "Please specify: hyperactive, hypoactive, or mixed type? Known underlying cause (infection, medication, metabolic)?",
    'cognitive decline': "Please specify: mild cognitive impairment or dementia? Known etiology? Any behavioral disturbances?",
}

def expand_with_medical_synonyms(phrase: str) -> List[str]:
    """Expand a medical phrase with known synonyms and abbreviations."""
    expanded_terms = [phrase.lower()]
    phrase_lower = phrase.lower()
    
    # Check for exact abbreviation matches
    for abbrev, synonyms in MEDICAL_SYNONYMS.items():
        if abbrev.lower() in phrase_lower:
            for synonym in synonyms:
                # Replace abbreviation with synonym
                expanded_phrase = phrase_lower.replace(abbrev.lower(), synonym)
                expanded_terms.append(expanded_phrase)
                expanded_terms.extend(synonyms)
    
    # Check for partial matches in synonyms
    for abbrev, synonyms in MEDICAL_SYNONYMS.items():
        for synonym in synonyms:
            if any(word in phrase_lower for word in synonym.split()):
                expanded_terms.extend(synonyms)
                expanded_terms.append(abbrev.lower())
                break
    
    return list(set(expanded_terms))  # Remove duplicates

def extract_context_keywords(phrase: str) -> List[str]:
    """Extract context keywords that suggest specific code variants."""
    phrase_lower = phrase.lower()
    found_contexts = []
    
    for keyword, variants in CONTEXT_KEYWORDS.items():
        if keyword in phrase_lower:
            found_contexts.extend(variants)
    
    return found_contexts

def get_candidate_codes_enhanced(phrase: str, icd10_data: Dict, limit: int = 15) -> List[Dict]:
    """Enhanced candidate code matching with medical synonyms and context awareness."""
    
    # Expand phrase with medical synonyms
    expanded_terms = expand_with_medical_synonyms(phrase)
    context_keywords = extract_context_keywords(phrase)
    
    # Combine all search terms
    all_search_terms = expanded_terms + context_keywords
    
    # Score all codes against all search terms
    code_scores = {}
    
    for row in icd10_data.values():
        desc = row.get('description', '')
        if not desc:
            continue
            
        desc_lower = desc.lower()
        max_score = 0
        
        # Test against all expanded terms
        for term in all_search_terms:
            # Exact phrase match gets highest score
            if term in desc_lower:
                score = 1.0
            else:
                # Fuzzy matching for partial matches
                score = SequenceMatcher(None, term, desc_lower).ratio()
            
            # Boost score for context matches
            if any(ctx in desc_lower for ctx in context_keywords):
                score *= 1.5
            
            max_score = max(max_score, score)
        
        # Only include codes with reasonable similarity
        if max_score > 0.3:
            code_scores[row['icd10_code']] = (max_score, row)
    
    # Sort by score and return top candidates
    sorted_codes = sorted(code_scores.values(), key=lambda x: x[0], reverse=True)
    return [row for _, row in sorted_codes[:limit]]

def get_fallback_followup(phrase: str) -> str:
    """Generate fallback follow-up suggestions when AI returns None."""
    phrase_lower = phrase.lower()
    
    # Check for predefined follow-ups
    for condition, followup in PREDEFINED_FOLLOWUPS.items():
        if condition in phrase_lower:
            return followup
    
    # Check for common medical terms that need specification
    if any(term in phrase_lower for term in ['diabetes', 'dm']):
        return PREDEFINED_FOLLOWUPS['diabetes']
    elif any(term in phrase_lower for term in ['heart failure', 'chf']):
        return PREDEFINED_FOLLOWUPS['heart failure']
    elif any(term in phrase_lower for term in ['copd', 'chronic obstructive']):
        return PREDEFINED_FOLLOWUPS['COPD']
    elif any(term in phrase_lower for term in ['hypertension', 'htn', 'high blood pressure']):
        return PREDEFINED_FOLLOWUPS['hypertension']
    elif any(term in phrase_lower for term in ['pneumonia', 'lung infection']):
        return PREDEFINED_FOLLOWUPS['pneumonia']
    elif any(term in phrase_lower for term in ['stroke', 'cva']):
        return PREDEFINED_FOLLOWUPS['stroke']
    elif any(term in phrase_lower for term in ['kidney', 'renal']):
        return PREDEFINED_FOLLOWUPS['kidney disease']
    elif any(term in phrase_lower for term in ['infection', 'uti', 'sepsis']):
        return PREDEFINED_FOLLOWUPS['infection']
    elif any(term in phrase_lower for term in ['fracture', 'break', 'broken']):
        return PREDEFINED_FOLLOWUPS['fracture']
    elif any(term in phrase_lower for term in ['wound', 'ulcer', 'sore']):
        return PREDEFINED_FOLLOWUPS['wound']
    elif any(term in phrase_lower for term in ['pain', 'ache']):
        return PREDEFINED_FOLLOWUPS['pain']
    # Cardiac
    elif any(term in phrase_lower for term in ['afib', 'a-fib', 'atrial fibrillation']):
        return PREDEFINED_FOLLOWUPS['atrial fibrillation']
    elif any(term in phrase_lower for term in ['cardiomyopathy']):
        return PREDEFINED_FOLLOWUPS['cardiomyopathy']
    elif any(term in phrase_lower for term in ['angina', 'chest pain']):
        return PREDEFINED_FOLLOWUPS['angina']
    elif any(term in phrase_lower for term in ['valve', 'stenosis', 'regurgitation']):
        return PREDEFINED_FOLLOWUPS['valve']
    elif any(term in phrase_lower for term in ['pacemaker', 'aicd', 'icd']):
        return PREDEFINED_FOLLOWUPS['pacemaker']
    elif any(term in phrase_lower for term in ['stent', 'pci']):
        return PREDEFINED_FOLLOWUPS['stent']
    # Respiratory
    elif any(term in phrase_lower for term in ['asthma', 'reactive airway']):
        return PREDEFINED_FOLLOWUPS['asthma']
    elif any(term in phrase_lower for term in ['respiratory failure']):
        return PREDEFINED_FOLLOWUPS['respiratory failure']
    elif any(term in phrase_lower for term in ['trach', 'tracheostomy']):
        return PREDEFINED_FOLLOWUPS['tracheostomy']
    elif any(term in phrase_lower for term in ['pleural effusion']):
        return PREDEFINED_FOLLOWUPS['pleural effusion']
    elif any(term in phrase_lower for term in ['sleep apnea', 'osa']):
        return PREDEFINED_FOLLOWUPS['sleep apnea']
    elif any(term in phrase_lower for term in ['lung cancer', 'pulmonary neoplasm']):
        return PREDEFINED_FOLLOWUPS['lung cancer']
    # Wound
    elif any(term in phrase_lower for term in ['pressure injury', 'pressure ulcer', 'decubitus', 'bedsore']):
        return PREDEFINED_FOLLOWUPS['pressure ulcer']
    elif any(term in phrase_lower for term in ['surgical wound', 'dehiscence']):
        return PREDEFINED_FOLLOWUPS['surgical wound']
    elif any(term in phrase_lower for term in ['skin graft', 'graft site']):
        return PREDEFINED_FOLLOWUPS['skin graft']
    elif any(term in phrase_lower for term in ['wound vac', 'npwt']):
        return PREDEFINED_FOLLOWUPS['wound vac']
    elif any(term in phrase_lower for term in ['gangrene', 'necrosis']):
        return PREDEFINED_FOLLOWUPS['gangrene']
    # Neuro
    elif any(term in phrase_lower for term in ['parkinson', 'parkinsons']):
        return PREDEFINED_FOLLOWUPS['parkinson']
    elif any(term in phrase_lower for term in ['multiple sclerosis', ' ms ']):
        return PREDEFINED_FOLLOWUPS['multiple sclerosis']
    elif any(term in phrase_lower for term in ['als', 'amyotrophic']):
        return PREDEFINED_FOLLOWUPS['als']
    elif any(term in phrase_lower for term in ['alzheimer']):
        return PREDEFINED_FOLLOWUPS['alzheimer']
    elif any(term in phrase_lower for term in ['dementia', 'cognitive impairment']):
        return PREDEFINED_FOLLOWUPS['dementia']
    elif any(term in phrase_lower for term in ['brain injury', 'tbi']):
        return PREDEFINED_FOLLOWUPS['brain injury']
    elif any(term in phrase_lower for term in ['spinal cord injury', 'sci', 'paralysis']):
        return PREDEFINED_FOLLOWUPS['spinal cord injury']
    elif any(term in phrase_lower for term in ['seizure', 'epilepsy', 'convulsion']):
        return PREDEFINED_FOLLOWUPS['seizure']
    elif any(term in phrase_lower for term in ['neuropathy', 'nerve damage']):
        return PREDEFINED_FOLLOWUPS['neuropathy']
    elif any(term in phrase_lower for term in ['dysphagia', 'swallowing']):
        return PREDEFINED_FOLLOWUPS['dysphagia']
    # Musculoskeletal
    elif any(term in phrase_lower for term in ['hip replacement', 'total hip', 'thr']):
        return PREDEFINED_FOLLOWUPS['hip replacement']
    elif any(term in phrase_lower for term in ['knee replacement', 'total knee', 'tkr']):
        return PREDEFINED_FOLLOWUPS['knee replacement']
    elif any(term in phrase_lower for term in ['arthroplasty', 'joint replacement']):
        return PREDEFINED_FOLLOWUPS['arthroplasty']
    elif any(term in phrase_lower for term in ['amputation', 'bka', 'aka']):
        return PREDEFINED_FOLLOWUPS['amputation']
    elif any(term in phrase_lower for term in ['spinal fusion', 'spine fusion']):
        return PREDEFINED_FOLLOWUPS['spinal fusion']
    elif any(term in phrase_lower for term in ['osteoarthritis', 'degenerative joint']):
        return PREDEFINED_FOLLOWUPS['osteoarthritis']
    elif any(term in phrase_lower for term in ['rheumatoid', 'ra ']):
        return PREDEFINED_FOLLOWUPS['rheumatoid arthritis']
    elif any(term in phrase_lower for term in ['gout', 'gouty']):
        return PREDEFINED_FOLLOWUPS['gout']
    elif any(term in phrase_lower for term in ['osteoporosis', 'bone loss']):
        return PREDEFINED_FOLLOWUPS['osteoporosis']
    # Endocrine
    elif any(term in phrase_lower for term in ['thyroid', 'hypothyroid', 'hyperthyroid']):
        return PREDEFINED_FOLLOWUPS['thyroid']
    elif any(term in phrase_lower for term in ['dka', 'ketoacidosis']):
        return PREDEFINED_FOLLOWUPS['dka']
    elif any(term in phrase_lower for term in ['hyperglycemia', 'high blood sugar']):
        return PREDEFINED_FOLLOWUPS['hyperglycemia']
    elif any(term in phrase_lower for term in ['hypoglycemia', 'low blood sugar']):
        return PREDEFINED_FOLLOWUPS['hypoglycemia']
    elif any(term in phrase_lower for term in ['obesity', 'morbid obesity']):
        return PREDEFINED_FOLLOWUPS['obesity']
    # GI/GU
    elif any(term in phrase_lower for term in ['colostomy', 'stoma']):
        return PREDEFINED_FOLLOWUPS['colostomy']
    elif any(term in phrase_lower for term in ['catheter', 'foley', 'suprapubic']):
        return PREDEFINED_FOLLOWUPS['catheter']
    elif any(term in phrase_lower for term in ['peg tube', 'g tube', 'feeding tube', 'gastrostomy']):
        return PREDEFINED_FOLLOWUPS['peg tube']
    elif any(term in phrase_lower for term in ['bowel obstruction', 'ileus', 'sbo']):
        return PREDEFINED_FOLLOWUPS['bowel obstruction']
    elif any(term in phrase_lower for term in ['crohn', 'crohns']):
        return PREDEFINED_FOLLOWUPS['crohn']
    elif any(term in phrase_lower for term in ['ulcerative colitis']):
        return PREDEFINED_FOLLOWUPS['ulcerative colitis']
    elif any(term in phrase_lower for term in ['cirrhosis', 'liver disease']):
        return PREDEFINED_FOLLOWUPS['cirrhosis']
    elif any(term in phrase_lower for term in ['hepatitis']):
        return PREDEFINED_FOLLOWUPS['hepatitis']
    # Behavioral
    elif any(term in phrase_lower for term in ['depression', 'depressive', 'mdd']):
        return PREDEFINED_FOLLOWUPS['depression']
    elif any(term in phrase_lower for term in ['anxiety', 'gad', 'anxious']):
        return PREDEFINED_FOLLOWUPS['anxiety']
    elif any(term in phrase_lower for term in ['bipolar', 'manic']):
        return PREDEFINED_FOLLOWUPS['bipolar']
    elif any(term in phrase_lower for term in ['schizophrenia', 'psychosis']):
        return PREDEFINED_FOLLOWUPS['schizophrenia']
    elif any(term in phrase_lower for term in ['substance abuse', 'addiction', 'drug abuse']):
        return PREDEFINED_FOLLOWUPS['substance abuse']
    elif any(term in phrase_lower for term in ['delirium', 'acute confusion']):
        return PREDEFINED_FOLLOWUPS['delirium']
    elif any(term in phrase_lower for term in ['cognitive decline', 'mci']):
        return PREDEFINED_FOLLOWUPS['cognitive decline']

    # Generic fallback for broad terms
    return "Could you provide more specific details about the condition, such as: acute vs chronic, location, severity, or any complications?"

def ai_followup_question_enhanced(phrase: str, pdgm_response: str = "") -> str:
    """Enhanced follow-up question generation with fallback logic."""
    
    # If PDGM response is empty or indicates no match, use fallback
    if not pdgm_response or any(indicator in pdgm_response.lower() for indicator in 
                               ['no matching codes', 'error', 'not found', 'openai error']):
        return get_fallback_followup(phrase)
    
    # Check for predefined follow-ups first (faster and more reliable)
    fallback = get_fallback_followup(phrase)
    if fallback != "Could you provide more specific details about the condition, such as: acute vs chronic, location, severity, or any complications?":
        return fallback
    
    # If we have a good PDGM response, we can still try AI for more specific follow-ups
    # But we'll return the fallback if AI fails or returns "None"
    return fallback

def validate_pdgm_response(response: str) -> bool:
    """Validate that a PDGM response contains proper structure."""
    if not response:
        return False
    
    # Check for required PDGM response elements
    required_elements = ['Focus of Care:', 'ICD-10:', 'PDGM Group:']
    return any(element in response for element in required_elements)

# Test function to verify the enhancements work
def test_enhanced_functions():
    """Test the enhanced functions with CHF exacerbation."""
    
    # Test synonym expansion
    expanded = expand_with_medical_synonyms("CHF exacerbation")
    print("Expanded terms for 'CHF exacerbation':")
    for term in expanded:
        print(f"  - {term}")
    
    # Test context extraction
    contexts = extract_context_keywords("CHF exacerbation")
    print(f"\nContext keywords: {contexts}")
    
    # Test fallback follow-up
    followup = get_fallback_followup("CHF exacerbation")
    print(f"\nFallback follow-up: {followup}")

if __name__ == "__main__":
    test_enhanced_functions()

