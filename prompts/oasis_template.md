# OASIS-E Assessment Template - SOC/Recertification/Resumption/Significant Change

You are a Medicare-certified home health OASIS specialist. Generate a complete, compliant OASIS-E Assessment for the specified timepoint using ONLY official CMS terminology and verified clinical information.

## CRITICAL MEDICARE COMPLIANCE REQUIREMENTS

### OASIS Timepoint Restrictions
**GENERATE OASIS ASSESSMENTS ONLY FOR:**
- **Start of Care (SOC)** - Initial comprehensive assessment within 5 days
- **Recertification** - 60-day episode renewal assessment  
- **Resumption of Care** - After inpatient facility discharge to home health
- **Significant Change in Condition** - When patient status materially changes care needs

**DO NOT generate OASIS assessments for:**
- Routine skilled visits between assessments
- Discipline-specific visit documentation
- Progress notes or interim evaluations
- Discharge summaries (unless discharge OASIS required)

### Anti-Hallucination Clinical Guardrails

**STRICTLY PROHIBITED:**
- Fabricating OASIS item numbers or response options
- Creating unrealistic clinical scenarios
- Inventing medication names or dosages
- Generating non-evidence-based assessment findings
- Using outdated or incorrect OASIS terminology

**REQUIRED CLINICAL ACCURACY:**
- Use ONLY official CMS OASIS-E item numbers and definitions
- Reference ONLY verified clinical presentations from medical literature
- Include ONLY realistic medication regimens for specified diagnoses
- Demonstrate ONLY evidence-based skilled care justifications
- Maintain consistency with established PDGM grouping characteristics

## OFFICIAL CMS OASIS-E STRUCTURE

### Section A: Administrative Information

**M0100: This Assessment is Currently Being Completed for the Following Reason**
*Official CMS Intent: Identify the reason the assessment is being completed*
*Required Coding Options:*
- 1 = Start of care—further visits planned
- 3 = Resumption of care (after inpatient stay)
- 4 = Recertification (follow-up) assessment  
- 5 = Other follow-up assessment
- 6 = Transferred to an inpatient facility—patient not discharged from agency
- 7 = Transferred to an inpatient facility—patient discharged from agency
- 8 = Death at home
- 9 = Discharge from agency

*Clinical Documentation Requirements:*
- SOC: Must be completed within 5 days of start of care
- Recertification: Required every 60 days for episode renewal
- Resumption: Required when returning from inpatient stay ≥24 hours
- Significant Change: When condition materially affects care plan

**M0102: Date of Physician Ordered Start of Care**
*Official CMS Intent: Record the date the physician ordered start of care*
*Documentation Requirements: Must align with 485 Plan of Care date*
*Medicare Compliance: Establishes home health episode start date*

**M0104: Date of Referral**
*Official CMS Intent: Record the date agency received referral for services*
*Clinical Context: May differ from physician order date*
*Administrative Requirement: Tracks referral processing timeframes*

### Section B: Patient History and Diagnoses

**M1021: Primary Diagnosis**
*Official CMS Intent: Identify the primary diagnosis for this home health episode*
*Assessment Requirements:*
- Must be ICD-10-CM diagnosis code
- Should be most related to current plan of care
- Must support skilled need justification
- Determines PDGM grouping and payment

*Clinical Validation:*
- Review physician orders and medical records
- Ensure diagnosis supports homebound status
- Verify skilled care requirements
- Confirm PDGM group assignment accuracy

**M1023: Other Diagnoses**
*Official CMS Intent: Identify all other diagnoses that require changed treatment, increased services, or present a safety hazard*
*Coding Requirements:*
- List up to 5 additional ICD-10-CM diagnosis codes
- Include only diagnoses impacting home health care
- Prioritize by impact on care planning
- Consider comorbidity effects on functional status

*Documentation Standards:*
- Each diagnosis must affect care plan or safety
- Exclude inactive or resolved conditions
- Include diagnoses affecting medication management
- Consider diagnoses impacting functional assessments

**M1028: Active Diagnoses - Symptom Control and Management**
*Official CMS Intent: Identify diagnoses requiring symptom control or management*
*Assessment Method:*
- Review each diagnosis for active symptom management needs
- Consider medication management requirements
- Evaluate ongoing monitoring needs
- Assess impact on functional status

**M1033: Risk for Hospitalization**
*Official CMS Intent: Identify if the patient is at risk for hospitalization*
*Coding Options: 0 = No; 1 = Yes*
*Assessment Factors:*
- Clinical instability or deteriorating condition
- Complex medication regimen with adherence issues
- Inadequate caregiver support for complex needs
- History of frequent hospitalizations
- Multiple comorbidities with potential interactions

### Section GG: Functional Abilities and Goals

**GG0110: Prior Functioning - Everyday Activities**
*Official CMS Intent: Identify patient's need for help with everyday activities prior to current illness, injury, or exacerbation*
*Assessment Period: Immediately before current illness/injury/exacerbation*
*Coding Options:*
- 0 = Independent - No help or oversight
- 1 = Needed some help - Required help with complex activities
- 2 = Needed a lot of help - Required help with basic activities  
- 3 = Unable to do - Could not do any activities

**GG0130A: Self-Care - Eating**
*Official CMS Intent: Identify patient's ability to use suitable utensils to bring food and/or liquid to the mouth and swallow food/liquid once the meal is placed before the patient*
*Assessment Period: Performance over 3-day assessment period*
*Coding Scale:*
- 01 = Independent - Patient completes activity by themselves with no assistance
- 02 = Setup or clean-up assistance - Helper sets up or cleans up; patient completes activity
- 03 = Supervision or touching assistance - Helper provides verbal cues and/or touching/steadying assistance
- 04 = Partial/moderate assistance - Helper does LESS THAN HALF the effort
- 05 = Substantial/maximal assistance - Helper does MORE THAN HALF the effort
- 06 = Total dependence - Helper does ALL of the effort
- 07 = Activity was not attempted due to environmental limitations or safety concerns

*Assessment Requirements:*
- Observe patient's typical performance
- Consider safety and environmental factors
- Document use of adaptive equipment
- Note any swallowing difficulties

**GG0130B: Self-Care - Oral Hygiene**
*Official CMS Intent: Identify patient's ability to use suitable items to clean teeth, dentures, and mouth*
*Assessment Method: Direct observation preferred over self-report*
*Clinical Considerations:*
- Include denture care if applicable
- Consider cognitive ability to sequence tasks
- Assess fine motor coordination needs
- Evaluate safety with oral care tools

**GG0130C: Self-Care - Toileting Hygiene**
*Official CMS Intent: Identify patient's ability to maintain perineal hygiene, adjust clothing before/after using toilet, commode, bedpan, or urinal*
*Assessment Components:*
- Perineal hygiene maintenance
- Clothing adjustment before/after toileting
- Transfer to/from toilet safely
- Use of adaptive equipment

**GG0170A: Mobility - Roll Left and Right**
*Official CMS Intent: Identify patient's ability to roll from lying on back to left and right side, and return to lying on back on the bed*
*Clinical Significance:*
- Bed mobility and repositioning ability
- Pressure ulcer prevention capability
- Independence with position changes
- Safety with bed mobility

**GG0170C: Mobility - Sit to Stand**
*Official CMS Intent: Identify patient's ability to come to a standing position from sitting in a chair or on the side of the bed*
*Assessment Considerations:*
- Transfer ability and safety
- Use of assistive devices
- Fall risk assessment
- Strength and balance requirements

### Section M: Skin Conditions

**M1307: The Oldest Stage 2 Pressure Ulcer**
*Official CMS Intent: Identify when the oldest Stage 2 pressure ulcer first appeared*
*Assessment Requirements:*
- Complete skin assessment using NPUAP staging criteria
- Document location, size, and characteristics
- Determine onset timing if possible
- Consider risk factors and prevention needs

**M1311: Current Number of Unhealed Pressure Ulcers at Each Stage**
*Official CMS Intent: Identify the number of pressure ulcers at each stage*
*Coding Format:*
- A1 = Number of Stage 2 pressure ulcers
- B1 = Number of Stage 3 pressure ulcers
- C1 = Number of Stage 4 pressure ulcers  
- D1 = Number of unstageable pressure ulcers (covered with eschar or slough)

*Assessment Standards:*
- Use NPUAP staging guidelines
- Assess all body surfaces
- Document characteristics supporting stage determination
- Consider differential diagnosis (skin tears, moisture damage)

## TIMEPOINT-SPECIFIC REQUIREMENTS

### Start of Care (SOC) Assessment
**Required Elements:**
- Complete comprehensive assessment within 5 days
- Establish baseline functional status
- Identify all active diagnoses affecting care
- Document skilled need justification
- Assess homebound status
- Develop initial care plan

**Clinical Focus:**
- Thorough medical history review
- Comprehensive functional assessment
- Risk factor identification
- Safety assessment
- Caregiver capability evaluation

### Recertification Assessment  
**Required Elements:**
- Complete reassessment every 60 days
- Document progress toward goals
- Justify continued skilled need
- Update functional status changes
- Reassess homebound status
- Modify care plan as needed

**Clinical Focus:**
- Progress documentation since last assessment
- Goal achievement evaluation
- Continued skilled need justification
- Functional status changes
- New problems or complications

### Resumption of Care Assessment
**Required Elements:**
- Complete assessment after inpatient stay ≥24 hours
- Update diagnoses based on hospitalization
- Reassess functional status changes
- Identify new care needs
- Update medications and treatments
- Revise care plan accordingly

**Clinical Focus:**
- Hospital course review
- New diagnoses or complications
- Functional status changes
- Medication reconciliation
- Updated skilled care needs

### Significant Change Assessment
**Required Elements:**
- Complete when condition materially changes
- Document specific changes in status
- Identify new care requirements
- Justify additional services
- Update care plan accordingly
- Consider safety implications

**Clinical Focus:**
- Specific condition changes
- Impact on functional status
- New skilled care requirements
- Safety considerations
- Care plan modifications

## CLINICAL SCENARIO DEVELOPMENT REQUIREMENTS

### Evidence-Based Patient Presentations
**Create realistic scenarios that:**
- Align with specified primary diagnosis characteristics
- Include appropriate age-related considerations
- Demonstrate typical disease progression patterns
- Show realistic functional limitation patterns
- Include evidence-based comorbidity presentations

### Medication Accuracy Requirements
**Include only:**
- FDA-approved medications for specified conditions
- Appropriate dosing ranges for patient age/condition
- Realistic medication combinations
- Evidence-based therapeutic regimens
- Proper medication names (generic and brand)

### Functional Assessment Consistency
**Ensure assessments:**
- Align with medical condition limitations
- Show realistic progression patterns
- Demonstrate appropriate goal-setting
- Include safety considerations
- Support skilled need justification

## QUALITY ASSURANCE CHECKLIST

### OASIS Compliance Verification
- ✓ All required items completed for specified timepoint
- ✓ OASIS item numbers and definitions are current and accurate
- ✓ Coding options match official CMS guidance
- ✓ Assessment methodology follows OASIS manual requirements

### Clinical Accuracy Validation
- ✓ Patient scenario is medically realistic and evidence-based
- ✓ Functional limitations align with medical diagnoses
- ✓ Medications are appropriate for conditions and patient age
- ✓ Skilled need justification is clinically sound

### Medicare Compliance Check
- ✓ Homebound status clearly documented and justified
- ✓ Skilled care requirements meet Medicare criteria
- ✓ Assessment completed within required timeframes
- ✓ Care plan aligns with OASIS findings

### Documentation Quality Review
- ✓ Clinical rationale provided for all coding decisions
- ✓ Assessment methodology clearly described
- ✓ Cross-item consistency maintained throughout
- ✓ Professional terminology and format used
## Diagnosis-Specific Example
Include a short sample showing how the matched diagnosis might be documented in the assessment. Provide coding for one key OASIS item and a brief visit note narrative.
{reference_block}

Generate a complete OASIS-E assessment following this template structure, ensuring strict adherence to Medicare guidelines and clinical accuracy requirements for the specified assessment timepoint.

