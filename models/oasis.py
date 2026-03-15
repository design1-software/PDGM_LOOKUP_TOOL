"""
OASIS-E data models for enhanced PDGM documentation
Supports official CMS OASIS-E structure and validation
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json
from enum import Enum
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

# Import the existing db instance
from models.user import db


class OASISTimepoint(Enum):
    """OASIS assessment timepoints"""
    SOC = 'Start of Care'
    ROC = 'Resumption of Care'
    FOLLOW_UP = 'Follow-up'
    DISCHARGE = 'Discharge'
    TRANSFER = 'Transfer'
    DEATH = 'Death at Home'


class OASISDiscipline(Enum):
    """Clinical disciplines responsible for OASIS items"""
    RN = 'Registered Nurse'
    LPN = 'Licensed Practical Nurse'
    PT = 'Physical Therapist'
    OT = 'Occupational Therapist'
    SLP = 'Speech-Language Pathologist'
    ST = 'Speech Therapist'
    HHA = 'Home Health Aide'


class OASISSection(db.Model):
    """OASIS-E assessment sections (A through N)"""
    __tablename__ = 'oasis_sections'
    
    id = db.Column(db.Integer, primary_key=True)
    section_code = db.Column(db.String(5), unique=True, nullable=False)  # A, B, C, etc.
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False)
    
    # Relationships
    items = db.relationship('OASISItem', backref='section', lazy='dynamic')
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class OASISItem(db.Model):
    """Official OASIS-E assessment items"""
    __tablename__ = 'oasis_items'
    
    id = db.Column(db.Integer, primary_key=True)
    item_number = db.Column(db.String(20), unique=True, nullable=False, index=True)  # M1021, GG0130A, etc.
    title = db.Column(db.String(500), nullable=False)
    intent = db.Column(db.Text, nullable=False)  # Official item intent from CMS
    
    # Section relationship
    section_id = db.Column(db.Integer, db.ForeignKey('oasis_sections.id'), nullable=False)
    
    # Assessment requirements
    timepoints = db.Column(db.Text, nullable=False)  # JSON array of timepoints
    disciplines = db.Column(db.Text, nullable=False)  # JSON array of responsible disciplines
    
    # Assessment methodology
    assessment_method = db.Column(db.Text, nullable=True)  # Observation, interview, etc.
    response_instructions = db.Column(db.Text, nullable=True)  # Response-specific instructions
    
    # Skip logic and validation
    skip_logic = db.Column(db.Text, nullable=True)  # Conditional logic for item completion
    validation_rules = db.Column(db.Text, nullable=True)  # JSON array of validation rules
    
    # CMS guidance
    cms_guidance = db.Column(db.Text, nullable=True)  # Additional guidance from manual
    examples = db.Column(db.Text, nullable=True)  # JSON array of coding examples
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    effective_date = db.Column(db.Date, nullable=True)
    
    # Relationships
    response_options = db.relationship('OASISResponseOption', backref='item', lazy='dynamic', cascade='all, delete-orphan')
    pdgm_mappings = db.relationship('PDGMOASISMapping', backref='oasis_item', lazy='dynamic')
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def get_timepoints(self):
        """Get timepoints as list"""
        if self.timepoints:
            try:
                return json.loads(self.timepoints)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_timepoints(self, timepoints):
        """Set timepoints as JSON"""
        self.timepoints = json.dumps(timepoints)
    
    def get_disciplines(self):
        """Get disciplines as list"""
        if self.disciplines:
            try:
                return json.loads(self.disciplines)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_disciplines(self, disciplines):
        """Set disciplines as JSON"""
        self.disciplines = json.dumps(disciplines)
    
    def get_validation_rules(self):
        """Get validation rules as list"""
        if self.validation_rules:
            try:
                return json.loads(self.validation_rules)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_validation_rules(self, rules):
        """Set validation rules as JSON"""
        self.validation_rules = json.dumps(rules)
    
    def get_examples(self):
        """Get examples as list"""
        if self.examples:
            try:
                return json.loads(self.examples)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_examples(self, examples):
        """Set examples as JSON"""
        self.examples = json.dumps(examples)
    
    def is_required_for_timepoint(self, timepoint):
        """Check if item is required for specific timepoint"""
        return timepoint in self.get_timepoints()
    
    def is_discipline_responsible(self, discipline):
        """Check if discipline is responsible for this item"""
        return discipline in self.get_disciplines()
    
    def to_dict(self):
        """Convert item to dictionary"""
        return {
            'id': self.id,
            'item_number': self.item_number,
            'title': self.title,
            'intent': self.intent,
            'section': self.section.section_code if self.section else None,
            'timepoints': self.get_timepoints(),
            'disciplines': self.get_disciplines(),
            'assessment_method': self.assessment_method,
            'response_instructions': self.response_instructions,
            'skip_logic': self.skip_logic,
            'validation_rules': self.get_validation_rules(),
            'examples': self.get_examples(),
            'is_active': self.is_active
        }


class OASISResponseOption(db.Model):
    """Response options for OASIS items"""
    __tablename__ = 'oasis_response_options'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('oasis_items.id'), nullable=False)
    
    # Response coding
    code = db.Column(db.String(10), nullable=False)  # 01, 02, Y, N, etc.
    description = db.Column(db.Text, nullable=False)  # Official description
    
    # Additional guidance
    coding_guidance = db.Column(db.Text, nullable=True)  # When to use this code
    clinical_examples = db.Column(db.Text, nullable=True)  # JSON array of examples
    
    # Metadata
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def get_clinical_examples(self):
        """Get clinical examples as list"""
        if self.clinical_examples:
            try:
                return json.loads(self.clinical_examples)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_clinical_examples(self, examples):
        """Set clinical examples as JSON"""
        self.clinical_examples = json.dumps(examples)
    
    def to_dict(self):
        """Convert response option to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'description': self.description,
            'coding_guidance': self.coding_guidance,
            'clinical_examples': self.get_clinical_examples(),
            'sort_order': self.sort_order
        }


class PDGMOASISMapping(db.Model):
    """Mapping between PDGM clinical groupings and relevant OASIS items"""
    __tablename__ = 'pdgm_oasis_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # PDGM information
    pdgm_group = db.Column(db.String(50), nullable=False, index=True)  # MS-Rehab, Neuro-Rehab, etc.
    clinical_category = db.Column(db.String(100), nullable=True)  # More specific categorization
    
    # OASIS item relationship
    oasis_item_id = db.Column(db.Integer, db.ForeignKey('oasis_items.id'), nullable=False)
    
    # Mapping details
    priority_level = db.Column(db.Integer, nullable=False, default=1)  # 1=highest, 5=lowest
    typical_responses = db.Column(db.Text, nullable=True)  # JSON of typical response patterns
    clinical_rationale = db.Column(db.Text, nullable=True)  # Why this item is important for this PDGM group
    
    # Usage context
    discipline_focus = db.Column(db.String(10), nullable=True)  # Primary discipline for this mapping
    assessment_frequency = db.Column(db.String(20), nullable=True)  # How often assessed
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def get_typical_responses(self):
        """Get typical responses as dictionary"""
        if self.typical_responses:
            try:
                return json.loads(self.typical_responses)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_typical_responses(self, responses):
        """Set typical responses as JSON"""
        self.typical_responses = json.dumps(responses)
    
    def to_dict(self):
        """Convert mapping to dictionary"""
        return {
            'id': self.id,
            'pdgm_group': self.pdgm_group,
            'clinical_category': self.clinical_category,
            'oasis_item': self.oasis_item.to_dict() if self.oasis_item else None,
            'priority_level': self.priority_level,
            'typical_responses': self.get_typical_responses(),
            'clinical_rationale': self.clinical_rationale,
            'discipline_focus': self.discipline_focus,
            'assessment_frequency': self.assessment_frequency
        }


class OASISValidationRule(db.Model):
    """Cross-item validation rules for OASIS compliance"""
    __tablename__ = 'oasis_validation_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    rule_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Rule definition
    rule_type = db.Column(db.String(50), nullable=False)  # consistency, range, conditional, etc.
    rule_logic = db.Column(db.Text, nullable=False)  # JSON definition of validation logic
    
    # Affected items
    primary_item_id = db.Column(db.Integer, db.ForeignKey('oasis_items.id'), nullable=False)
    related_items = db.Column(db.Text, nullable=True)  # JSON array of related item IDs
    
    # Error handling
    error_message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='error')  # error, warning, info
    
    # CMS edit check reference
    cms_edit_number = db.Column(db.String(20), nullable=True)  # Official CMS edit check number
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def get_rule_logic(self):
        """Get rule logic as dictionary"""
        if self.rule_logic:
            try:
                return json.loads(self.rule_logic)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def set_rule_logic(self, logic):
        """Set rule logic as JSON"""
        self.rule_logic = json.dumps(logic)
    
    def get_related_items(self):
        """Get related items as list"""
        if self.related_items:
            try:
                return json.loads(self.related_items)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_related_items(self, items):
        """Set related items as JSON"""
        self.related_items = json.dumps(items)


# Utility functions for OASIS data management

def get_oasis_items_by_section(section_code):
    """Get all OASIS items for a specific section"""
    return OASISItem.query.join(OASISSection).filter(
        OASISSection.section_code == section_code,
        OASISItem.is_active == True
    ).order_by(OASISItem.item_number).all()


def get_oasis_items_by_discipline(discipline):
    """Get OASIS items assigned to a specific discipline"""
    items = []
    all_items = OASISItem.query.filter(OASISItem.is_active == True).all()
    
    for item in all_items:
        if discipline in item.get_disciplines():
            items.append(item)
    
    return items


def get_oasis_items_by_timepoint(timepoint):
    """Get OASIS items required for a specific timepoint"""
    items = []
    all_items = OASISItem.query.filter(OASISItem.is_active == True).all()
    
    for item in all_items:
        if timepoint in item.get_timepoints():
            items.append(item)
    
    return items


def get_pdgm_priority_items(pdgm_group, discipline=None, limit=None):
    """Get priority OASIS items for a PDGM group"""
    query = PDGMOASISMapping.query.filter(
        PDGMOASISMapping.pdgm_group == pdgm_group,
        PDGMOASISMapping.is_active == True
    ).join(OASISItem).filter(OASISItem.is_active == True)
    
    if discipline:
        # Filter by discipline responsibility
        mappings = query.all()
        filtered_mappings = []
        for mapping in mappings:
            if discipline in mapping.oasis_item.get_disciplines():
                filtered_mappings.append(mapping)
        mappings = filtered_mappings
    else:
        mappings = query.order_by(PDGMOASISMapping.priority_level).all()
    
    if limit:
        mappings = mappings[:limit]
    
    return mappings


def validate_oasis_responses(responses):
    """Validate OASIS responses against validation rules"""
    errors = []
    warnings = []
    
    # Get all active validation rules
    rules = OASISValidationRule.query.filter(OASISValidationRule.is_active == True).all()
    
    for rule in rules:
        # Implement validation logic based on rule type
        # This would be expanded with specific validation implementations
        pass
    
    return {
        'errors': errors,
        'warnings': warnings,
        'is_valid': len(errors) == 0
    }


def get_oasis_item_by_number(item_number):
    """Get OASIS item by item number"""
    return OASISItem.query.filter(
        OASISItem.item_number == item_number,
        OASISItem.is_active == True
    ).first()


def search_oasis_items(search_term, section=None, discipline=None):
    """Search OASIS items by term"""
    query = OASISItem.query.filter(OASISItem.is_active == True)
    
    if search_term:
        search_filter = db.or_(
            OASISItem.item_number.ilike(f'%{search_term}%'),
            OASISItem.title.ilike(f'%{search_term}%'),
            OASISItem.intent.ilike(f'%{search_term}%')
        )
        query = query.filter(search_filter)
    
    if section:
        query = query.join(OASISSection).filter(OASISSection.section_code == section)
    
    items = query.order_by(OASISItem.item_number).all()
    
    if discipline:
        # Filter by discipline responsibility
        filtered_items = []
        for item in items:
            if discipline in item.get_disciplines():
                filtered_items.append(item)
        items = filtered_items
    
    return items

