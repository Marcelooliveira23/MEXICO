"""
PDF Rules Extractor
Extracts specific technical rules and limits from PDF manuals
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import pdfplumber
from utils.logger import logger
from utils import AppConfig
from services.pdf_mapper import PDFMapper


@dataclass
class TechnicalLimit:
    """Technical limit extracted from PDF"""
    parameter: str
    value: float
    unit: str
    condition: Optional[str] = None
    page: Optional[int] = None
    source: Optional[str] = None


@dataclass
class InspectionRule:
    """Inspection rule extracted from PDF"""
    event_type: str
    aircraft_family: str
    limits: List[TechnicalLimit]
    procedures: List[str]
    references: List[str]


class PDFRulesExtractor:
    """Extracts technical rules from PDF manuals"""
    
    def __init__(self):
        """Initialize PDF rules extractor"""
        self.docs_dir = AppConfig.BASE_DIR
        logger.info("PDFRulesExtractor initialized")
    
    def extract_numeric_values(self, text: str) -> List[Tuple[float, str]]:
        """
        Extract numeric values with units from text
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (value, unit) tuples
        """
        # Patterns for numeric values with units
        patterns = [
            r'(\d+\.?\d*)\s*(G|g)',  # G-forces
            r'(\d+\.?\d*)\s*(kt|kts|KIAS|knots)',  # Speed in knots
            r'(\d+\.?\d*)\s*(ft/min|fpm)',  # Vertical speed
            r'(\d+\.?\d*)\s*(°C|deg C|degrees C)',  # Temperature
            r'(\d+\.?\d*)\s*(kg|lbs|pounds)',  # Weight
            r'(\d+\.?\d*)\s*(ft|feet)',  # Altitude/distance
            r'(\d+\.?\d*)\s*(deg|degrees|°)',  # Angles
        ]
        
        results = []
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value = float(match.group(1))
                    unit = match.group(2)
                    results.append((value, unit))
                except ValueError:
                    continue
        
        return results
    
    def extract_hard_landing_rules(self, pdf_path: Path, aircraft_family: str) -> InspectionRule:
        """
        Extract hard landing rules from PDF
        
        Args:
            pdf_path: Path to PDF file
            aircraft_family: Aircraft family (E145, E170, E1, E2)
            
        Returns:
            InspectionRule object
        """
        limits = []
        procedures = []
        references = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    
                    # Extract vertical acceleration limits
                    if any(keyword in text.lower() for keyword in ['vertical acceleration', 'accel', 'g-force']):
                        numeric_values = self.extract_numeric_values(text)
                        for value, unit in numeric_values:
                            if unit.upper() == 'G' and 1.0 <= value <= 5.0:
                                limits.append(TechnicalLimit(
                                    parameter="vertical_acceleration",
                                    value=value,
                                    unit="G",
                                    condition="maximum",
                                    page=page_num,
                                    source=pdf_path.name
                                ))
                    
                    # Extract descent rate limits
                    if any(keyword in text.lower() for keyword in ['descent rate', 'vertical speed', 'sink rate']):
                        numeric_values = self.extract_numeric_values(text)
                        for value, unit in numeric_values:
                            if 'ft/min' in unit.lower() or 'fpm' in unit.lower():
                                if 200 <= value <= 2000:
                                    limits.append(TechnicalLimit(
                                        parameter="descent_rate",
                                        value=value,
                                        unit="ft/min",
                                        condition="maximum",
                                        page=page_num,
                                        source=pdf_path.name
                                    ))
                    
                    # Extract procedures
                    if any(keyword in text.lower() for keyword in ['inspect', 'check', 'examine', 'verify']):
                        lines = text.split('\n')
                        for line in lines:
                            if any(keyword in line.lower() for keyword in ['inspect', 'check', 'examine']):
                                if len(line) < 200:  # Reasonable procedure length
                                    procedures.append(line.strip())
                    
                    # Extract AMM references
                    amm_matches = re.finditer(r'AMM\s+(\d{2}-\d{2}-\d{2})', text, re.IGNORECASE)
                    for match in amm_matches:
                        ref = f"AMM {match.group(1)}"
                        if ref not in references:
                            references.append(ref)
            
            logger.success(f"Extracted hard landing rules from {pdf_path.name}: {len(limits)} limits, {len(procedures)} procedures")
            
        except Exception as e:
            logger.error(f"Error extracting hard landing rules from {pdf_path}: {e}")
        
        return InspectionRule(
            event_type="HARD_LANDING",
            aircraft_family=aircraft_family,
            limits=limits,
            procedures=procedures[:10],  # Limit to top 10
            references=references
        )
    
    def extract_gear_overspeed_rules(self, pdf_path: Path, aircraft_family: str) -> InspectionRule:
        """Extract landing gear overspeed rules from PDF"""
        limits = []
        procedures = []
        references = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    
                    # Extract speed limits (VLE, VLO)
                    if any(keyword in text.lower() for keyword in ['vle', 'vlo', 'gear speed', 'landing gear']):
                        numeric_values = self.extract_numeric_values(text)
                        for value, unit in numeric_values:
                            if any(speed_unit in unit.lower() for speed_unit in ['kt', 'kts', 'kias', 'knots']):
                                if 100 <= value <= 350:
                                    # Determine if VLE or VLO based on context
                                    param_name = "vle"
                                    if 'vlo' in text.lower():
                                        param_name = "vlo"
                                    
                                    limits.append(TechnicalLimit(
                                        parameter=param_name,
                                        value=value,
                                        unit="KIAS",
                                        condition="maximum",
                                        page=page_num,
                                        source=pdf_path.name
                                    ))
                    
                    # Extract procedures
                    if any(keyword in text.lower() for keyword in ['inspect', 'examine', 'landing gear']):
                        lines = text.split('\n')
                        for line in lines:
                            if any(keyword in line.lower() for keyword in ['gear', 'inspect', 'check']):
                                if len(line) < 200:
                                    procedures.append(line.strip())
                    
                    # Extract references
                    refs = re.finditer(r'(AMM|SRM|CMM)\s+(\d{2}-\d{2}-\d{2})', text, re.IGNORECASE)
                    for match in refs:
                        ref = f"{match.group(1).upper()} {match.group(2)}"
                        if ref not in references:
                            references.append(ref)
            
            logger.success(f"Extracted gear overspeed rules from {pdf_path.name}: {len(limits)} limits")
            
        except Exception as e:
            logger.error(f"Error extracting gear overspeed rules from {pdf_path}: {e}")
        
        return InspectionRule(
            event_type="GEAR_OVERSPEED",
            aircraft_family=aircraft_family,
            limits=limits,
            procedures=procedures[:10],
            references=references
        )
    
    def extract_temperature_rules(self, pdf_path: Path, aircraft_family: str) -> InspectionRule:
        """Extract temperature envelope rules from PDF"""
        limits = []
        procedures = []
        references = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    
                    # Extract temperature limits
                    if any(keyword in text.lower() for keyword in ['temperature', 'tat', 'sat', 'envelope']):
                        numeric_values = self.extract_numeric_values(text)
                        for value, unit in numeric_values:
                            if '°c' in unit.lower() or 'deg' in unit.lower():
                                if -70 <= value <= 60:
                                    limits.append(TechnicalLimit(
                                        parameter="temperature",
                                        value=value,
                                        unit="°C",
                                        condition="limit",
                                        page=page_num,
                                        source=pdf_path.name
                                    ))
                    
                    # Extract procedures
                    if 'temperature' in text.lower() and 'exceed' in text.lower():
                        lines = text.split('\n')
                        for line in lines:
                            if any(keyword in line.lower() for keyword in ['inspect', 'check', 'monitor']):
                                if len(line) < 200:
                                    procedures.append(line.strip())
            
            logger.success(f"Extracted temperature rules from {pdf_path.name}: {len(limits)} limits")
            
        except Exception as e:
            logger.error(f"Error extracting temperature rules from {pdf_path}: {e}")
        
        return InspectionRule(
            event_type="TEMPERATURE",
            aircraft_family=aircraft_family,
            limits=limits,
            procedures=procedures[:10],
            references=references
        )
    
    def extract_speed_rules(self, pdf_path: Path, aircraft_family: str) -> InspectionRule:
        """Extract maximum operating speed rules from PDF"""
        limits = []
        procedures = []
        references = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    
                    # Extract VMO/MMO limits
                    if any(keyword in text.lower() for keyword in ['vmo', 'mmo', 'maximum speed', 'operating speed']):
                        numeric_values = self.extract_numeric_values(text)
                        for value, unit in numeric_values:
                            if any(speed_unit in unit.lower() for speed_unit in ['kt', 'kts', 'kias', 'knots']):
                                if 200 <= value <= 400:
                                    limits.append(TechnicalLimit(
                                        parameter="vmo",
                                        value=value,
                                        unit="KIAS",
                                        condition="maximum",
                                        page=page_num,
                                        source=pdf_path.name
                                    ))
            
            logger.success(f"Extracted speed rules from {pdf_path.name}: {len(limits)} limits")
            
        except Exception as e:
            logger.error(f"Error extracting speed rules from {pdf_path}: {e}")
        
        return InspectionRule(
            event_type="SPEED",
            aircraft_family=aircraft_family,
            limits=limits,
            procedures=procedures,
            references=references
        )

    def extract_turbulence_rules(self, pdf_path: Path, aircraft_family: str) -> InspectionRule:
        """Extract turbulence encounter rules from PDF"""
        limits = []
        procedures = []
        references = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    text_lower = text.lower()

                    if any(keyword in text_lower for keyword in ['turbulence', 'gust', 'encounter']):
                        # Extract G-limits (allow signed values)
                        g_matches = re.finditer(r'([+-]?\d+\.?\d*)\s*(G|g)', text)
                        for match in g_matches:
                            try:
                                value = float(match.group(1))
                            except ValueError:
                                continue

                            if value >= 0:
                                limits.append(TechnicalLimit(
                                    parameter="max_positive_g",
                                    value=value,
                                    unit="G",
                                    condition="maximum",
                                    page=page_num,
                                    source=pdf_path.name
                                ))
                            else:
                                limits.append(TechnicalLimit(
                                    parameter="max_negative_g",
                                    value=value,
                                    unit="G",
                                    condition="minimum",
                                    page=page_num,
                                    source=pdf_path.name
                                ))

                        # Extract turbulence speed limits (if mentioned)
                        if 'speed' in text_lower or 'kias' in text_lower or 'kt' in text_lower:
                            numeric_values = self.extract_numeric_values(text)
                            for value, unit in numeric_values:
                                if any(speed_unit in unit.lower() for speed_unit in ['kt', 'kts', 'kias', 'knots']):
                                    if 100 <= value <= 400:
                                        limits.append(TechnicalLimit(
                                            parameter="max_turbulence_speed",
                                            value=value,
                                            unit="KIAS",
                                            condition="maximum",
                                            page=page_num,
                                            source=pdf_path.name
                                        ))

                    # Extract procedures and references
                    if any(keyword in text_lower for keyword in ['inspect', 'check', 'examine', 'verify']):
                        lines = text.split('\n')
                        for line in lines:
                            if any(keyword in line.lower() for keyword in ['turbulence', 'gust', 'inspect', 'check']):
                                if len(line) < 200:
                                    procedures.append(line.strip())

                    refs = re.finditer(r'(AMM|SRM|CMM)\s+(\d{2}-\d{2}-\d{2})', text, re.IGNORECASE)
                    for match in refs:
                        ref = f"{match.group(1).upper()} {match.group(2)}"
                        if ref not in references:
                            references.append(ref)

            logger.success(f"Extracted turbulence rules from {pdf_path.name}: {len(limits)} limits")

        except Exception as e:
            logger.error(f"Error extracting turbulence rules from {pdf_path}: {e}")

        return InspectionRule(
            event_type="TURBULENCE",
            aircraft_family=aircraft_family,
            limits=limits,
            procedures=procedures[:10],
            references=references
        )

    def extract_over_g_rules(self, pdf_path: Path, aircraft_family: str) -> InspectionRule:
        """Extract over-G maneuver rules from PDF"""
        limits = []
        procedures = []
        references = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    text_lower = text.lower()

                    if any(keyword in text_lower for keyword in ['over-g', 'over g', 'g-load', 'g load', 'g limit']):
                        g_matches = re.finditer(r'([+-]?\d+\.?\d*)\s*(G|g)', text)
                        for match in g_matches:
                            try:
                                value = float(match.group(1))
                            except ValueError:
                                continue

                            if value >= 0:
                                limits.append(TechnicalLimit(
                                    parameter="max_positive_g",
                                    value=value,
                                    unit="G",
                                    condition="maximum",
                                    page=page_num,
                                    source=pdf_path.name
                                ))
                            else:
                                limits.append(TechnicalLimit(
                                    parameter="max_negative_g",
                                    value=value,
                                    unit="G",
                                    condition="minimum",
                                    page=page_num,
                                    source=pdf_path.name
                                ))

                    if any(keyword in text_lower for keyword in ['inspect', 'check', 'examine', 'verify']):
                        lines = text.split('\n')
                        for line in lines:
                            if any(keyword in line.lower() for keyword in ['over-g', 'over g', 'g-load', 'g load']):
                                if len(line) < 200:
                                    procedures.append(line.strip())

                    refs = re.finditer(r'(AMM|SRM|CMM)\s+(\d{2}-\d{2}-\d{2})', text, re.IGNORECASE)
                    for match in refs:
                        ref = f"{match.group(1).upper()} {match.group(2)}"
                        if ref not in references:
                            references.append(ref)

            logger.success(f"Extracted over-G rules from {pdf_path.name}: {len(limits)} limits")

        except Exception as e:
            logger.error(f"Error extracting over-G rules from {pdf_path}: {e}")

        return InspectionRule(
            event_type="OVER_G",
            aircraft_family=aircraft_family,
            limits=limits,
            procedures=procedures[:10],
            references=references
        )

    def extract_high_bank_angle_rules(self, pdf_path: Path, aircraft_family: str) -> InspectionRule:
        """Extract high bank angle rules from PDF"""
        limits = []
        procedures = []
        references = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    text_lower = text.lower()

                    if any(keyword in text_lower for keyword in ['bank angle', 'bank', 'roll angle']):
                        lines = text.split('\n')
                        for line in lines:
                            line_lower = line.lower()
                            if not any(keyword in line_lower for keyword in ['bank angle', 'bank', 'roll angle']):
                                continue

                            numeric_values = self.extract_numeric_values(line)
                            for value, unit in numeric_values:
                                if not any(angle_unit in unit.lower() for angle_unit in ['deg', 'degrees', '°']):
                                    continue
                                if not 30 <= value <= 90:
                                    continue

                                if any(keyword in line_lower for keyword in ['emergency', 'upset']):
                                    parameter = "emergency"
                                elif any(keyword in line_lower for keyword in ['normal', 'standard', 'routine']):
                                    parameter = "normal"
                                else:
                                    parameter = "emergency" if value >= 65 else "normal"

                                limits.append(TechnicalLimit(
                                    parameter=parameter,
                                    value=value,
                                    unit="deg",
                                    condition="maximum",
                                    page=page_num,
                                    source=pdf_path.name
                                ))

                    if any(keyword in text_lower for keyword in ['inspect', 'check', 'examine', 'verify']):
                        lines = text.split('\n')
                        for line in lines:
                            if any(keyword in line.lower() for keyword in ['bank', 'roll', 'inspect', 'check']):
                                if len(line) < 200:
                                    procedures.append(line.strip())

                    refs = re.finditer(r'(AMM|SRM|CMM)\s+(\d{2}-\d{2}-\d{2})', text, re.IGNORECASE)
                    for match in refs:
                        ref = f"{match.group(1).upper()} {match.group(2)}"
                        if ref not in references:
                            references.append(ref)

            logger.success(f"Extracted high bank angle rules from {pdf_path.name}: {len(limits)} limits")

        except Exception as e:
            logger.error(f"Error extracting high bank angle rules from {pdf_path}: {e}")

        return InspectionRule(
            event_type="HIGH_BANK_ANGLE",
            aircraft_family=aircraft_family,
            limits=limits,
            procedures=procedures[:10],
            references=references
        )
    
    def extract_all_rules(self, aircraft_family: str) -> Dict[str, InspectionRule]:
        """
        Extract all rules for an aircraft family
        
        Args:
            aircraft_family: Aircraft family code (E145, E170, E1, E2)
            
        Returns:
            Dictionary mapping event types to InspectionRule objects
        """
        rules = {}
        family_key = (aircraft_family or "").lower()
        family_folder_map = {
            "e145": "E145",
            "e170": "E170",
            "e1": "E1",
            "e2": "E2",
        }
        family_folder = family_folder_map.get(family_key, aircraft_family)
        family_dir = self.docs_dir / family_folder
        
        if not family_dir.exists():
            logger.warning(f"PDF directory not found: {family_dir}")
            return rules
        
        # Map PDF files to event types
        category_map = {
            "hard_landing": "HARD_LANDING",
            "gear_overspeed": "GEAR_OVERSPEED",
            "temp_envelope": "TEMPERATURE",
            "max_speed": "SPEED",
            "flap_overspeed": "FLAP_SPEED",
            "overweight_landing": "OVERWEIGHT",
            "turbulence": "TURBULENCE",
            "over_g": "OVER_G",
            "high_bank_angle": "HIGH_BANK_ANGLE",
        }
        event_mappings = {
            'hard_landing': 'HARD_LANDING',
            '05-50-02': 'HARD_LANDING',
            '05-50-03': 'HARD_LANDING',
            'gear': 'GEAR_OVERSPEED',
            '05-50-13': 'GEAR_OVERSPEED',
            '05-50-27': 'GEAR_OVERSPEED',
            'temperature': 'TEMPERATURE',
            'speed': 'SPEED',
            'overspeed': 'SPEED',
            '05-50-04': 'SPEED',
            '05-50-06': 'SPEED',
            'flap': 'FLAP_SPEED',
            'slat': 'FLAP_SPEED',
            '05-50-07': 'FLAP_SPEED',
            'overweight': 'OVERWEIGHT',
            '05-50-09': 'OVERWEIGHT',
            '05-50-25': 'OVERWEIGHT',
            'turbulence': 'TURBULENCE',
            'gust': 'TURBULENCE',
            '05-50-28': 'TURBULENCE',
            'over-g': 'OVER_G',
            'over_g': 'OVER_G',
            'g-load': 'OVER_G',
            '05-57-00': 'HIGH_BANK_ANGLE',
            'bank': 'HIGH_BANK_ANGLE'
        }
        
        pdf_files = list(family_dir.glob("*.pdf")) + list(family_dir.glob("*.PDF"))
        for pdf_file in dict.fromkeys(pdf_files):
            filename_lower = pdf_file.stem.lower()
            
            # Determine event type using structured mapping first
            event_type = None
            try:
                pdf_doc = PDFMapper.map_pdf(pdf_file)
                event_type = category_map.get(pdf_doc.event_category)
            except Exception as e:
                logger.warning(f"PDF mapping fallback for {pdf_file.name}: {e}")

            if not event_type:
                for keyword, evt_type in event_mappings.items():
                    if keyword in filename_lower:
                        event_type = evt_type
                        break
            
            if not event_type:
                continue
            
            # Extract rules based on event type
            if event_type == 'HARD_LANDING':
                rule = self.extract_hard_landing_rules(pdf_file, aircraft_family)
            elif event_type == 'GEAR_OVERSPEED':
                rule = self.extract_gear_overspeed_rules(pdf_file, aircraft_family)
            elif event_type == 'TEMPERATURE':
                rule = self.extract_temperature_rules(pdf_file, aircraft_family)
            elif event_type == 'SPEED':
                rule = self.extract_speed_rules(pdf_file, aircraft_family)
            elif event_type == 'TURBULENCE':
                rule = self.extract_turbulence_rules(pdf_file, aircraft_family)
            elif event_type == 'OVER_G':
                rule = self.extract_over_g_rules(pdf_file, aircraft_family)
            elif event_type == 'HIGH_BANK_ANGLE':
                rule = self.extract_high_bank_angle_rules(pdf_file, aircraft_family)
            else:
                continue
            
            # Merge with existing rules
            if event_type in rules:
                rules[event_type].limits.extend(rule.limits)
                rules[event_type].procedures.extend(rule.procedures)
                rules[event_type].references.extend(rule.references)
            else:
                rules[event_type] = rule
        
        logger.info(f"Extracted {len(rules)} rule sets for {aircraft_family}")
        return rules
    
    def generate_rules_summary(self, aircraft_family: str) -> str:
        """
        Generate a summary of extracted rules
        
        Args:
            aircraft_family: Aircraft family code
            
        Returns:
            Formatted summary string
        """
        rules = self.extract_all_rules(aircraft_family)
        
        summary = f"# Technical Rules Summary - {aircraft_family}\n\n"
        
        for event_type, rule in rules.items():
            summary += f"## {event_type}\n\n"
            
            if rule.limits:
                summary += "### Limits:\n"
                for limit in rule.limits:
                    summary += f"- {limit.parameter}: {limit.value} {limit.unit}"
                    if limit.condition:
                        summary += f" ({limit.condition})"
                    if limit.page:
                        summary += f" [Page {limit.page}]"
                    summary += "\n"
                summary += "\n"
            
            if rule.procedures:
                summary += "### Procedures:\n"
                for proc in rule.procedures[:5]:  # Top 5
                    summary += f"- {proc}\n"
                summary += "\n"
            
            if rule.references:
                summary += "### References:\n"
                for ref in rule.references:
                    summary += f"- {ref}\n"
                summary += "\n"
            
            summary += "---\n\n"
        
        return summary
