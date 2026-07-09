"""
E1 Aircraft Technical Specifications - Strict PDF-Based Rules
Based on Mexicana E-Jets E1 Family (E170/E175/E190/E195) Technical Manuals
"""

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class TechnicalLimit:
    """Technical limit from aircraft manual"""
    parameter: str
    limit_value: float
    unit: str
    condition: str = ""
    reference: str = ""
    inspection_required: bool = True


class E1TechnicalSpecifications:
    """E1 Family (E170/E175/E190/E195) Technical Specifications"""
    
    # ==================== HARD LANDING SPECIFICATIONS ====================
    # Based on AMM 05-51-00 Landing Gear - Structural Inspection
    
    HARD_LANDING_LIMITS = {
        "vertical_acceleration": [
            TechnicalLimit(
                parameter="vertical_acceleration",
                limit_value=2.0,
                unit="G",
                condition="Normal landing - maximum acceptable",
                reference="AMM 05-51-00 - Landing Gear Inspection",
                inspection_required=True
            ),
            TechnicalLimit(
                parameter="vertical_acceleration",
                limit_value=2.6,
                unit="G",
                condition="Hard landing - detailed inspection required",
                reference="AMM 05-51-00 - Hard Landing Inspection",
                inspection_required=True
            ),
            TechnicalLimit(
                parameter="vertical_acceleration",
                limit_value=2.8,
                unit="G",
                condition="Very hard landing - extensive inspection",
                reference="AMM 05-51-00 - Structural Damage Assessment",
                inspection_required=True
            )
        ],
        "descent_rate": [
            TechnicalLimit(
                parameter="descent_rate",
                limit_value=600,
                unit="ft/min",
                condition="Normal landing descent rate",
                reference="FCOM - Normal Procedures",
                inspection_required=False
            ),
            TechnicalLimit(
                parameter="descent_rate",
                limit_value=1000,
                unit="ft/min",
                condition="Hard landing descent rate threshold",
                reference="AMM 05-51-00",
                inspection_required=True
            )
        ]
    }
    
    # ==================== LANDING GEAR OVERSPEED ====================
    # Based on AMM 32-10-00 Landing Gear Operation Limits
    
    LANDING_GEAR_LIMITS = {
        "vle": TechnicalLimit(
            parameter="airspeed",
            limit_value=250,
            unit="KIAS",
            condition="VLE - Maximum speed with gear extended",
            reference="AFM Limitations - Landing Gear Extended Speed",
            inspection_required=True
        ),
        "vlo_extension": TechnicalLimit(
            parameter="airspeed",
            limit_value=250,
            unit="KIAS",
            condition="VLO - Maximum speed for gear extension",
            reference="AFM Limitations - Landing Gear Operating Speed",
            inspection_required=True
        ),
        "vlo_retraction": TechnicalLimit(
            parameter="airspeed",
            limit_value=220,
            unit="KIAS",
            condition="VLO - Maximum speed for gear retraction",
            reference="AFM Limitations - Landing Gear Operating Speed",
            inspection_required=True
        ),
        "overspeed_tolerance": TechnicalLimit(
            parameter="airspeed",
            limit_value=10,
            unit="KIAS",
            condition="Allowable overspeed exceedance for inspection",
            reference="AMM 32-10-00 - Gear Overspeed Inspection",
            inspection_required=True
        )
    }
    
    # ==================== TEMPERATURE ENVELOPE ====================
    # Based on AMM 71-00-00 Powerplant - Temperature Limits
    
    TEMPERATURE_LIMITS = {
        "egt_takeoff": TechnicalLimit(
            parameter="egt",
            limit_value=950,
            unit="°C",
            condition="EGT - Maximum for takeoff (5 minutes)",
            reference="AMM 71-00-00 - Engine Limitations",
            inspection_required=True
        ),
        "egt_continuous": TechnicalLimit(
            parameter="egt",
            limit_value=915,
            unit="°C",
            condition="EGT - Maximum continuous",
            reference="AMM 71-00-00 - Engine Limitations",
            inspection_required=True
        ),
        "egt_start": TechnicalLimit(
            parameter="egt",
            limit_value=725,
            unit="°C",
            condition="EGT - Maximum during start (2 seconds)",
            reference="AMM 71-00-00 - Engine Start Limitations",
            inspection_required=True
        ),
        "tat_maximum": TechnicalLimit(
            parameter="temperature",
            limit_value=54,
            unit="°C",
            condition="TAT - Maximum Total Air Temperature (ISA+35)",
            reference="AFM Limitations - Temperature Envelope",
            inspection_required=False
        ),
        "tat_minimum": TechnicalLimit(
            parameter="temperature",
            limit_value=-54,
            unit="°C",
            condition="TAT - Minimum Total Air Temperature",
            reference="AFM Limitations - Temperature Envelope",
            inspection_required=False
        )
    }
    
    # ==================== MAXIMUM OPERATING SPEED ====================
    # Based on AFM Limitations Section - Operating Speeds
    
    MAX_SPEED_LIMITS = {
        "vmo": TechnicalLimit(
            parameter="airspeed",
            limit_value=320,
            unit="KIAS",
            condition="VMO - Maximum Operating Speed (below 8000 ft)",
            reference="AFM Limitations - Maximum Speeds",
            inspection_required=True
        ),
        "mmo": TechnicalLimit(
            parameter="mach",
            limit_value=0.82,
            unit="Mach",
            condition="MMO - Maximum Operating Mach Number",
            reference="AFM Limitations - Maximum Speeds",
            inspection_required=True
        ),
        "overspeed_inspection": TechnicalLimit(
            parameter="airspeed",
            limit_value=330,
            unit="KIAS",
            condition="VMO+10 - Inspection required",
            reference="AMM 05-00-00 - Overspeed Inspection",
            inspection_required=True
        )
    }
    
    # ==================== FLAP OVERSPEED ====================
    # Based on AFM Limitations - Flap Operating Speeds
    
    FLAP_LIMITS = {
        "flap_1": TechnicalLimit(
            parameter="airspeed",
            limit_value=250,
            unit="KIAS",
            condition="Flap 1 - Maximum speed",
            reference="AFM Limitations - Flap Speeds",
            inspection_required=True
        ),
        "flap_2": TechnicalLimit(
            parameter="airspeed",
            limit_value=230,
            unit="KIAS",
            condition="Flap 2 - Maximum speed",
            reference="AFM Limitations - Flap Speeds",
            inspection_required=True
        ),
        "flap_3": TechnicalLimit(
            parameter="airspeed",
            limit_value=210,
            unit="KIAS",
            condition="Flap 3 - Maximum speed",
            reference="AFM Limitations - Flap Speeds",
            inspection_required=True
        ),
        "flap_4": TechnicalLimit(
            parameter="airspeed",
            limit_value=200,
            unit="KIAS",
            condition="Flap 4 - Maximum speed",
            reference="AFM Limitations - Flap Speeds",
            inspection_required=True
        ),
        "flap_full": TechnicalLimit(
            parameter="airspeed",
            limit_value=180,
            unit="KIAS",
            condition="Flap FULL - Maximum speed",
            reference="AFM Limitations - Flap Speeds",
            inspection_required=True
        )
    }
    
    # ==================== OVERWEIGHT LANDING ====================
    # Based on AFM Limitations - Weight Limits
    
    WEIGHT_LIMITS = {
        "e170": {
            "mtow": TechnicalLimit(
                parameter="gross_weight",
                limit_value=79244,
                unit="lbs",
                condition="E170 - Maximum Takeoff Weight",
                reference="AFM Limitations - E170 Weights",
                inspection_required=False
            ),
            "mlw": TechnicalLimit(
                parameter="gross_weight",
                limit_value=69224,
                unit="lbs",
                condition="E170 - Maximum Landing Weight",
                reference="AFM Limitations - E170 Weights",
                inspection_required=True
            )
        },
        "e175": {
            "mtow": TechnicalLimit(
                parameter="gross_weight",
                limit_value=85517,
                unit="lbs",
                condition="E175 - Maximum Takeoff Weight",
                reference="AFM Limitations - E175 Weights",
                inspection_required=False
            ),
            "mlw": TechnicalLimit(
                parameter="gross_weight",
                limit_value=75000,
                unit="lbs",
                condition="E175 - Maximum Landing Weight",
                reference="AFM Limitations - E175 Weights",
                inspection_required=True
            )
        },
        "e190": {
            "mtow": TechnicalLimit(
                parameter="gross_weight",
                limit_value=110231,
                unit="lbs",
                condition="E190 - Maximum Takeoff Weight",
                reference="AFM Limitations - E190 Weights",
                inspection_required=False
            ),
            "mlw": TechnicalLimit(
                parameter="gross_weight",
                limit_value=97000,
                unit="lbs",
                condition="E190 - Maximum Landing Weight",
                reference="AFM Limitations - E190 Weights",
                inspection_required=True
            )
        },
        "e195": {
            "mtow": TechnicalLimit(
                parameter="gross_weight",
                limit_value=115741,
                unit="lbs",
                condition="E195 - Maximum Takeoff Weight",
                reference="AFM Limitations - E195 Weights",
                inspection_required=False
            ),
            "mlw": TechnicalLimit(
                parameter="gross_weight",
                limit_value=100309,
                unit="lbs",
                condition="E195 - Maximum Landing Weight",
                reference="AFM Limitations - E195 Weights",
                inspection_required=True
            )
        }
    }
    
    @classmethod
    def get_limits_for_event(cls, event_type: str, aircraft_model: str = "e170") -> Dict:
        """Get technical limits for specific event type"""
        limits_map = {
            "hard_landing": cls.HARD_LANDING_LIMITS,
            "gear_overspeed": cls.LANDING_GEAR_LIMITS,
            "temp_envelope": cls.TEMPERATURE_LIMITS,
            "max_speed": cls.MAX_SPEED_LIMITS,
            "flap_overspeed": cls.FLAP_LIMITS,
            "overweight": cls.WEIGHT_LIMITS.get(aircraft_model.lower(), cls.WEIGHT_LIMITS["e170"])
        }
        return limits_map.get(event_type, {})
    
    @classmethod
    def get_inspection_requirements(cls, event_type: str, exceedance_value: float, 
                                   parameter: str) -> List[str]:
        """Get inspection requirements based on exceedance severity"""
        requirements = []
        
        if event_type == "hard_landing":
            if exceedance_value >= 2.8:
                requirements = [
                    "Visual inspection of landing gear structure",
                    "Torque check of all landing gear attachment bolts",
                    "Functional test of landing gear retraction system",
                    "Inspection of wing-to-fuselage attach points",
                    "Check for fuselage skin wrinkles near landing gear",
                    "Inspection of floor beams and seat tracks",
                    "Non-destructive testing (NDT) of critical areas"
                ]
            elif exceedance_value >= 2.6:
                requirements = [
                    "Visual inspection of landing gear structure",
                    "Torque check of landing gear attachment bolts",
                    "Functional test of landing gear retraction system",
                    "Visual inspection of wing-to-fuselage attachments"
                ]
            elif exceedance_value >= 2.0:
                requirements = [
                    "Visual inspection of landing gear structure",
                    "Functional test of landing gear operation"
                ]
        
        elif event_type == "gear_overspeed":
            requirements = [
                "Visual inspection of landing gear doors",
                "Check landing gear door actuators and hinges",
                "Inspection of gear door seals",
                "Functional test of landing gear extension/retraction",
                "Check for excessive wear on gear door components"
            ]
        
        elif event_type == "temp_envelope":
            if parameter == "egt" and exceedance_value >= 950:
                requirements = [
                    "Borescope inspection of turbine section",
                    "Check turbine blade condition",
                    "Inspection of combustion chamber",
                    "Review engine trend monitoring data",
                    "Check for signs of thermal distress"
                ]
        
        elif event_type == "max_speed":
            requirements = [
                "Inspection of flight control surfaces",
                "Check for structural damage or deformation",
                "Inspection of wing and empennage attachments",
                "Review aircraft flight history for flutter",
                "Functional test of flight controls"
            ]
        
        elif event_type == "flap_overspeed":
            requirements = [
                "Visual inspection of flap surfaces",
                "Check flap actuator attachment points",
                "Inspection of flap tracks and rollers",
                "Functional test of flap extension/retraction",
                "Check for deformation or damage to flap structure"
            ]
        
        elif event_type == "overweight":
            requirements = [
                "Inspection of landing gear structure",
                "Check landing gear shock struts",
                "Inspection of main landing gear attachments",
                "Review weight and balance documentation",
                "Functional test of landing gear system"
            ]
        
        return requirements


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    print("=" * 70)
    print("E1 TECHNICAL SPECIFICATIONS - STRICT PDF-BASED RULES")
    print("=" * 70)
    
    # Hard Landing Example
    print("\n📋 HARD LANDING LIMITS:")
    for param, limits in E1TechnicalSpecifications.HARD_LANDING_LIMITS.items():
        print(f"\n   Parameter: {param}")
        for limit in limits:
            print(f"   ├─ {limit.limit_value} {limit.unit}")
            print(f"   ├─ Condition: {limit.condition}")
            print(f"   └─ Reference: {limit.reference}")
    
    # Landing Gear Limits
    print("\n📋 LANDING GEAR SPEED LIMITS:")
    for key, limit in E1TechnicalSpecifications.LANDING_GEAR_LIMITS.items():
        print(f"   {key.upper()}: {limit.limit_value} {limit.unit}")
        print(f"   └─ {limit.condition}")
    
    # Weight Limits by Aircraft
    print("\n📋 MAXIMUM LANDING WEIGHTS:")
    for aircraft, limits in E1TechnicalSpecifications.WEIGHT_LIMITS.items():
        print(f"   {aircraft.upper()}: {limits['mlw'].limit_value} lbs")
    
    # Inspection Requirements Example
    print("\n📋 INSPECTION REQUIREMENTS (Hard Landing @ 2.8G):")
    reqs = E1TechnicalSpecifications.get_inspection_requirements(
        "hard_landing", 2.8, "vertical_acceleration"
    )
    for i, req in enumerate(reqs, 1):
        print(f"   {i}. {req}")
    
    print("\n" + "=" * 70)
    print("✅ Technical specifications loaded successfully")
    print("=" * 70)

