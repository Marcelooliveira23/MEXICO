#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEXICANA TROUBLESHOOTING AI ENGINE
===================================
Offline-first intelligent analysis system for aircraft maintenance troubleshooting.
No external API calls — works entirely from local knowledge base + historical data.

Features:
  - ATA chapter knowledge base (ATA 21-80)
  - Keyword/symptom pattern matching
  - Historical failure statistical analysis
  - Recurring tail detection
  - Chat-style Q&A interface
  - Troubleshooting recommendations
  - Confidence scoring
"""

import re
from datetime import datetime, date, timedelta, timezone
from collections import Counter, defaultdict

# ==============================================================================
# ATA KNOWLEDGE BASE
# ==============================================================================

ATA_KNOWLEDGE_BASE = {
    '21': {
        'system': 'Air Conditioning and Pressurization',
        'icon': 'bi-thermometer-half',
        'color': '#0d6efd',
        'keywords': ['pressurization', 'pack', 'outflow valve', 'cabin pressure', 'bleed',
                     'temperature', 'air conditioning', 'pressurized', 'cabin alt', 'differential',
                     'pack valve', 'temperature control', 'zone temperature', 'over-pressure'],
        'common_failures': [
            {'code': '21-10', 'description': 'Pack failure / insufficient cooling',
                'frequency': 'High', 'severity': 'High'},
            {'code': '21-31', 'description': 'Outflow valve malfunction',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '21-51', 'description': 'Pressurization control fault',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '21-60', 'description': 'Bleed air leak / hot air duct',
                'frequency': 'High', 'severity': 'Critical'},
        ],
        'troubleshooting_steps': [
            '1. Check ECAM/CAS messages for specific system fault codes.',
            '2. Verify bleed air system status: pack valves, bleed switches position.',
            '3. Check temperature control zone selectors and temperature sensors (BITE).',
            '4. Inspect outflow valve position (auto vs. manual mode) and manual override.',
            '5. Perform BITE test on pressurization controller (cabin pressure controller).',
            '6. Compare differential pressure indication vs. manual calculation.',
            '7. Inspect pack valves for proper operation and sealing; check for signs of leakage.',
            '8. Review flight logs for trends: slow pressurization, high cabin altitude warnings.',
            '9. Check bleed air precooler for blockage or bypass valve sticking.',
            '10. On ground: perform full pressurization functional test per AMM 21-00-00.',
        ],
        'quick_actions': ['Check ECAM', 'BITE test PACK controller', 'Verify bleed valves', 'Inspect outflow valve'],
        'manuals': ['AMM Task 21-00-00', 'TSM Chapter 21', 'SSM 21-51-00'],
        'typical_resolution_hours': 2.5,
    },
    '22': {
        'system': 'Auto Flight / Autopilot',
        'icon': 'bi-robot',
        'color': '#6610f2',
        'keywords': ['autopilot', 'autoflight', 'FMS', 'FCC', 'AFCS', 'heading', 'altitude hold',
                     'autothrottle', 'approach mode', 'navigation', 'nav mode', 'VNAV', 'LNAV',
                     'flight director', 'disconnect', 'auto pilot'],
        'common_failures': [
            {'code': '22-11', 'description': 'Autopilot disconnect during approach',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '22-14', 'description': 'Autothrottle fault',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '22-20', 'description': 'FMS position error / database mismatch',
                'frequency': 'High', 'severity': 'High'},
            {'code': '22-30', 'description': 'Flight director incorrect guidance',
                'frequency': 'Low', 'severity': 'Medium'},
        ],
        'troubleshooting_steps': [
            '1. Check all FCC BITE logs for recorded faults and fault history.',
            '2. Verify pitot-static system connections, sensor calibration, and ADC data.',
            '3. Check power supply buses to autopilot computers.',
            '4. Inspect servo actuators and cables for wear, binding, or slack.',
            '5. Verify FMS navigation database currency and correct insertion.',
            '6. Test autopilot engagement in all modes on ground per AMM.',
            '7. Check for interference with other avionics systems.',
            '8. Review wiring harness for chafing near flight control surfaces.',
            '9. Verify air data computers (ADC) agreement within limits.',
            '10. Check hold-bar test of autopilot actuator for proper feel.',
        ],
        'quick_actions': ['FCC BITE check', 'Verify pitot-static', 'FMS database check', 'Check IRS/AHRS alignment'],
        'manuals': ['AMM Task 22-00-00', 'TSM Chapter 22', 'FMS Pilot Guide'],
        'typical_resolution_hours': 3.0,
    },
    '23': {
        'system': 'Communications',
        'icon': 'bi-broadcast-pin',
        'color': '#fd7e14',
        'keywords': ['VHF', 'HF', 'SATCOM', 'ATC', 'interphone', 'radio', 'communication',
                     'squelch', 'audio', 'microphone', 'speaker', 'SELCAL', 'ACARS', 'datalink',
                     'no comm', 'com fault', 'audio panel'],
        'common_failures': [
            {'code': '23-11', 'description': 'VHF COM radio intermittent operation',
                'frequency': 'High', 'severity': 'High'},
            {'code': '23-14', 'description': 'Audio selector panel fault',
                'frequency': 'Medium', 'severity': 'Medium'},
            {'code': '23-21', 'description': 'Interphone system inoperative',
                'frequency': 'Low', 'severity': 'Medium'},
            {'code': '23-51', 'description': 'SELCAL fault / ACARS datalink error',
                'frequency': 'Low', 'severity': 'Low'},
        ],
        'troubleshooting_steps': [
            '1. Check antenna connections, coax cables, and SWR (Standing Wave Ratio).',
            '2. Verify audio selector panel settings, input/output routing.',
            '3. Test backup VHF radio operation independently.',
            '4. Check power supply (28VDC bus) to COM units and circuit breakers.',
            '5. Inspect coaxial cables for physical damage or corrosion at connectors.',
            '6. Perform BITE test on Communication Management Unit (CMU).',
            '7. Verify squelch, volume settings, and ground/flight mode.',
            '8. Check mic jack wiring in cockpit headset jacks.',
            '9. Test TX/RX on a known-good frequency.',
            '10. If ACARS: check VHF datalink radio and ATSU configuration.',
        ],
        'quick_actions': ['Check antenna SWR', 'Backup radio test', 'CMU BITE check', 'Inspect coax cables'],
        'manuals': ['AMM Task 23-00-00', 'TSM Chapter 23'],
        'typical_resolution_hours': 2.0,
    },
    '24': {
        'system': 'Electrical Power',
        'icon': 'bi-lightning-charge-fill',
        'color': '#ffc107',
        'keywords': ['generator', 'bus bar', 'electrical', 'IDG', 'GPU', 'battery', 'inverter',
                     'CSD', 'ELEC', 'power', 'circuit breaker', 'CB', 'tripped', 'AC bus',
                     'DC bus', 'GCU', 'BPCU', 'voltage', 'frequency', 'ELEC fault'],
        'common_failures': [
            {'code': '24-11', 'description': 'Generator 1/2 fault / offline',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '24-22', 'description': 'Bus transfer fault',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '24-31', 'description': 'IDG oil temperature high / disconnect',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '24-41', 'description': 'Battery charge fault / low charge',
                'frequency': 'High', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Check ELEC system ECAM/CAS for generator fault codes.',
            '2. Verify GCU (Generator Control Unit) voltage and frequency output.',
            '3. Check IDG oil level and temperature trend history.',
            '4. Inspect GCU BITE logs for specific fault indications.',
            '5. Verify bus bar connections and terminal torque on electrical panels.',
            '6. Test APU generator as backup power source and compare output.',
            '7. Verify battery condition: voltage, internal resistance, and charge state.',
            '8. Check all relevant circuit breakers for tripped status.',
            '9. Test BPCU (Bus Power Control Unit) logic and automatic bus restoration.',
            '10. Measure IDG disconnect torque if repeated high-temp disconnects occur.',
        ],
        'quick_actions': ['Check GCU output', 'IDG oil level', 'Battery test', 'CB panel inspection'],
        'manuals': ['AMM Task 24-00-00', 'TSM Chapter 24', 'ELEC Manual'],
        'typical_resolution_hours': 3.5,
    },
    '26': {
        'system': 'Fire Protection',
        'icon': 'bi-fire',
        'color': '#dc3545',
        'keywords': ['fire', 'smoke', 'detector', 'extinguisher', 'squib', 'halon',
                     'APU fire', 'engine fire', 'fire loop', 'fire handle', 'cargo smoke',
                     'lavatory smoke', 'fire warning', 'false fire', 'detector loop'],
        'common_failures': [
            {'code': '26-11', 'description': 'Engine fire detector loop fault',
                'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '26-21', 'description': 'APU fire extinguisher squib fault',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '26-31', 'description': 'Cargo compartment smoke detector',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '26-33', 'description': 'Lavatory smoke detector false alarm',
                'frequency': 'High', 'severity': 'Medium'},
        ],
        'troubleshooting_steps': [
            '1. Check fire detection loop resistance per AMM — must be in specification.',
            '2. Verify extinguisher bottle pressure and squib continuity checks.',
            '3. Test fire detection system in maintenance mode per AMM 26-10-00.',
            '4. Inspect detector sensing elements for contamination, oil, or physical damage.',
            '5. Check wiring harness and connector pins at fire detector junction boxes.',
            '6. Perform discharge circuit functional test (without actual discharge).',
            '7. Replace smoke detector if contamination or aging is suspected (check service life).',
            '8. Verify post-maintenance BITE shows no faults.',
            '9. Check fire extinguisher agent weight against minimum service limits.',
            '10. For false alarms: clean detector sensing elements per cleaning procedure.',
        ],
        'quick_actions': ['Loop resistance test', 'Squib continuity', 'Detector cleaning', 'Bottle pressure check'],
        'manuals': ['AMM Task 26-00-00', 'TSM Chapter 26'],
        'typical_resolution_hours': 2.0,
    },
    '27': {
        'system': 'Flight Controls',
        'icon': 'bi-joystick',
        'color': '#198754',
        'keywords': ['elevator', 'aileron', 'rudder', 'spoiler', 'PFCS', 'FCE', 'flight controls',
                     'stick', 'sidestick', 'yaw damper', 'trim', 'flap', 'slat', 'feel unit',
                     'control surface', 'freeplay', 'FCPC', 'asymmetry', 'binding'],
        'common_failures': [
            {'code': '27-11', 'description': 'PFCS fault — primary flight computers',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '27-32', 'description': 'Spoiler actuator fault',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '27-51', 'description': 'Trim system malfunction',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '27-81', 'description': 'Slat/flap asymmetry or extension fault',
                'frequency': 'High', 'severity': 'Critical'},
        ],
        'troubleshooting_steps': [
            '1. Access PFCS/FCC BITE for specific fault codes and LRU isolation.',
            '2. Perform flight control ground functional test per AMM 27-00-00.',
            '3. Check hydraulic actuator pressure and operation at each surface.',
            '4. Inspect control surface movement for binding, freeplay, or unusual force.',
            '5. Verify PFCS computer software version compatibility across all channels.',
            '6. Check LVDT/RVDT sensors on all control surfaces for signal integrity.',
            '7. Inspect wiring harnesses at control surfaces for chafing and wear.',
            '8. Test slat/flap asymmetry protection system per AMM.',
            '9. Verify feel and centering unit for proper mechanical operation.',
            '10. Check rudder pedal and stick travel limits against rigging cards.',
        ],
        'quick_actions': ['PFCS BITE', 'Surface travel check', 'Actuator hydraulic test', 'LVDT calibration'],
        'manuals': ['AMM Task 27-00-00', 'TSM Chapter 27', 'PFCS Manual'],
        'typical_resolution_hours': 4.5,
    },
    '28': {
        'system': 'Fuel System',
        'icon': 'bi-fuel-pump-fill',
        'color': '#6f42c1',
        'keywords': ['fuel', 'tank', 'pump', 'fuel quantity', 'FQMS', 'crossfeed', 'fuel leak',
                     'fuel imbalance', 'fuel flow', 'fuel pressure', 'low fuel', 'fuel warning'],
        'common_failures': [
            {'code': '28-11', 'description': 'Fuel quantity indication fault',
                'frequency': 'High', 'severity': 'High'},
            {'code': '28-22', 'description': 'Fuel pump low pressure',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '28-31',
                'description': 'Fuel imbalance (L/R tanks)', 'frequency': 'High', 'severity': 'Medium'},
            {'code': '28-41', 'description': 'Fuel tank overfill protection fault',
                'frequency': 'Low', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Check fuel system FQMS BITE for probe and unit faults.',
            '2. Verify fuel pump operation and pressure readings at pumps.',
            '3. Check crossfeed valve position and automatic operation.',
            '4. Inspect fuel cap sealing and vent system operation.',
            '5. Physically measure fuel quantity and compare to indication.',
            '6. Check fuel system wiring harness connectors for corrosion.',
            '7. Test fuel transfer system and verify balance between tanks.',
            '8. Review FADEC fuel system parameters for crosscheck.',
            '9. Inspect fuel probes for contamination or physical damage.',
            '10. Check tank vent system for blockage.',
        ],
        'quick_actions': ['FQMS BITE', 'Physical fuel check', 'Pump pressure test', 'Crossfeed valve test'],
        'manuals': ['AMM Task 28-00-00', 'TSM Chapter 28'],
        'typical_resolution_hours': 3.0,
    },
    '29': {
        'system': 'Hydraulic Power',
        'icon': 'bi-droplet-fill',
        'color': '#0dcaf0',
        'keywords': ['hydraulic', 'pressure', 'pump', 'reservoir', 'actuator', 'accumulator',
                     'HYD', 'hydraulic system', 'fluid level', 'brake', 'low pressure',
                     'hydraulic leak', 'EDP', 'EMDP', 'hydraulic quantity'],
        'common_failures': [
            {'code': '29-11', 'description': 'Hydraulic pressure low — System A/B',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '29-12',
                'description': 'Engine hydraulic pump (EDP) fault', 'frequency': 'Medium', 'severity': 'High'},
            {'code': '29-22', 'description': 'Hydraulic fluid leakage',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '29-31', 'description': 'Hydraulic reservoir low quantity',
                'frequency': 'Medium', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Check system pressure gauges and compare to specification (3000 PSI typical).',
            '2. Inspect entire hydraulic system for external fluid leaks (actuators, lines, fittings).',
            '3. Check reservoir fluid level and add only approved fluid if low.',
            '4. Test engine-driven pump(s) at proper RPM during ground run.',
            '5. Check electric motor-driven pump (EMDP) operation and CBs.',
            '6. Inspect hydraulic filter differential pressure and replace if at bypass.',
            '7. Check system accumulator pre-charge pressure.',
            '8. Verify all hydraulic connections, fittings, and clamps are secure.',
            '9. Check return line filter and case drain filter for contamination.',
            '10. If leak found: isolate affected line, identify fitting/seal, repair per AMM.',
        ],
        'quick_actions': ['Check pressure gauges', 'Reservoir level', 'EDP ground run test', 'Leak inspection'],
        'manuals': ['AMM Task 29-00-00', 'TSM Chapter 29'],
        'typical_resolution_hours': 3.5,
    },
    '30': {
        'system': 'Ice and Rain Protection',
        'icon': 'bi-snow',
        'color': '#adb5bd',
        'keywords': ['ice', 'anti-ice', 'de-ice', 'wing heat', 'TAT probe', 'pitot heat',
                     'windshield heat', 'ice detection', 'wipers', 'icing', 'deice', 'WAI', 'EAI'],
        'common_failures': [
            {'code': '30-11',
                'description': 'Wing anti-ice system fault (WAI)', 'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '30-15', 'description': 'Engine anti-ice overheat',
                'frequency': 'High', 'severity': 'High'},
            {'code': '30-41', 'description': 'Pitot/TAT probe heat fault',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '30-51', 'description': 'Ice detector fault',
                'frequency': 'Medium', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Test anti-ice system on ground per AMM 30-00-00 operational test.',
            '2. Check overheat temperature sensors on anti-ice surfaces.',
            '3. Verify bleed air ducting integrity for wing anti-ice slat system.',
            '4. Measure pitot and TAT probe heater resistance values per AMM limits.',
            '5. Test ice detector sensitivity and response with simulated icing.',
            '6. Check windshield heating element continuity and control circuit.',
            '7. Check control valve position and thermal overheat switches.',
            '8. Verify automatic anti-ice activation logic from ice detector.',
            '9. Check electrical power supply to heat systems.',
            '10. Inspect WAI duct segments for cracks with pressurization test.',
        ],
        'quick_actions': ['Anti-ice operational test', 'Probe heater resistance', 'Ice detector BITE', 'WAI duct check'],
        'manuals': ['AMM Task 30-00-00', 'TSM Chapter 30'],
        'typical_resolution_hours': 2.5,
    },
    '31': {
        'system': 'Indicating and Recording Systems',
        'icon': 'bi-display',
        'color': '#20c997',
        'keywords': ['EICAS', 'ECAM', 'FDR', 'CVR', 'indicator', 'display', 'MFD', 'PFD',
                     'EFIS', 'warning', 'caution', 'advisory', 'blank display', 'screen', 'DFDR'],
        'common_failures': [
            {'code': '31-11', 'description': 'EICAS/ECAM display blank or partial',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '31-12', 'description': 'FDR fault or fail indication',
                'frequency': 'High', 'severity': 'High'},
            {'code': '31-21', 'description': 'CVR fault indication',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '31-31', 'description': 'Warning/caution annunciator failure',
                'frequency': 'Medium', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Check display power supply bus and connector seating.',
            '2. Perform BITE test on display management computers (DMC).',
            '3. Check FDR/CVR power supply and connector integrity.',
            '4. Verify display video signal input cables and display unit connections.',
            '5. Inspect cooling fans on display units for proper operation.',
            '6. Check warning system processor BITE logs for caution logic faults.',
            '7. Review software update history for display units.',
            '8. Test dimming and brightness controls.',
            '9. Swap display units (if identical) to isolate LRU fault.',
            '10. Check ARINC 429/Ethernet data bus inputs to display units.',
        ],
        'quick_actions': ['DMC BITE', 'Power supply check', 'Video signal test', 'LRU swap test'],
        'manuals': ['AMM Task 31-00-00', 'TSM Chapter 31'],
        'typical_resolution_hours': 2.0,
    },
    '32': {
        'system': 'Landing Gear',
        'icon': 'bi-airplane-engines',
        'color': '#fd7e14',
        'keywords': ['landing gear', 'wheel', 'tire', 'brake', 'steering', 'nose gear',
                     'main gear', 'retraction', 'extension', 'gear door', 'proximity sensor',
                     'TPIS', 'WOW', 'weight on wheels', 'gear up', 'gear down', 'gear warning'],
        'common_failures': [
            {'code': '32-11', 'description': 'Landing gear retraction/extension fault',
                'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '32-21', 'description': 'Brake overheat',
                'frequency': 'High', 'severity': 'High'},
            {'code': '32-41', 'description': 'Nose wheel steering fault',
                'frequency': 'High', 'severity': 'High'},
            {'code': '32-51',
                'description': 'Proximity sensor fault (WOW/gear position)', 'frequency': 'Medium', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Perform landing gear operational test per AMM 32-00-00.',
            '2. Check all proximity sensors: gap measurement and alignment.',
            '3. Inspect brake wear indicators and replace pads if at minimum.',
            '4. Check hydraulic actuator operation on all gear doors.',
            '5. Verify tire inflation pressures against tire placard charts.',
            '6. Inspect nose wheel steering system electronics and hydraulics.',
            '7. Check gear position indicator lights, wiring, and switches.',
            '8. Test WOW (Weight-on-Wheels) switching logic on ground.',
            '9. Lubricate all gear pivot points and door hinge rods per AMM.',
            '10. Check TPIS system; verify tire pressure readings are accurate.',
        ],
        'quick_actions': ['Gear swing test', 'Proximity sensor check', 'Brake inspection', 'Tire pressure check'],
        'manuals': ['AMM Task 32-00-00', 'TSM Chapter 32'],
        'typical_resolution_hours': 4.0,
    },
    '33': {
        'system': 'Lighting',
        'icon': 'bi-lightbulb-fill',
        'color': '#ffc107',
        'keywords': ['light', 'beacon', 'strobe', 'nav light', 'landing light', 'taxi light',
                     'wing light', 'cabin lighting', 'emergency lighting', 'LED', 'dim', 'illumination'],
        'common_failures': [
            {'code': '33-11', 'description': 'Navigation light failure',
                'frequency': 'High', 'severity': 'High'},
            {'code': '33-16', 'description': 'Landing/taxi light failure',
                'frequency': 'High', 'severity': 'Medium'},
            {'code': '33-21', 'description': 'Anti-collision beacon fault',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '33-41', 'description': 'Cabin lighting control fault',
                'frequency': 'Low', 'severity': 'Low'},
        ],
        'troubleshooting_steps': [
            '1. Check bulb or LED assembly continuity at the fixture.',
            '2. Verify 28VDC power supply at the light fixture connector.',
            '3. Test and reset related circuit breakers.',
            '4. Inspect wiring harness for chafing, pinched wires, or open circuits.',
            '5. Check light control panel, dimmer switches, and lighting computer.',
            '6. Test emergency lighting battery packs capacity per schedule.',
            '7. Verify lighting control module BITE if applicable.',
            '8. Replace failed bulb/LED assembly per AMM part number.',
            '9. Check connector pins for corrosion at light junction boxes.',
            '10. Confirm replacement with operational test.',
        ],
        'quick_actions': ['Continuity test', 'Power check at fixture', 'CB reset', 'LED assembly replacement'],
        'manuals': ['AMM Task 33-00-00', 'TSM Chapter 33'],
        'typical_resolution_hours': 1.0,
    },
    '34': {
        'system': 'Navigation',
        'icon': 'bi-compass-fill',
        'color': '#0d6efd',
        'keywords': ['GPS', 'ILS', 'VOR', 'ADF', 'radar altimeter', 'TCAS', 'GPWS', 'TAWS',
                     'FMS', 'navigation', 'IRS', 'AHRS', 'heading', 'position', 'nav fault',
                     'radio altimeter', 'RA', 'EGPWS', 'position mismatch'],
        'common_failures': [
            {'code': '34-11', 'description': 'GPS position error or no data',
                'frequency': 'High', 'severity': 'High'},
            {'code': '34-21', 'description': 'IRS/AHRS fault or misalignment',
                'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '34-41', 'description': 'TCAS fault / TAS failure',
                'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '34-51', 'description': 'Radar altimeter fault',
                'frequency': 'Medium', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Check GPS antenna connection, cable integrity, and signal reception levels.',
            '2. Perform IRS/AHRS alignment procedure from cold per AMM.',
            '3. Test VOR/ILS receivers using ground test equipment.',
            '4. Check TCAS antenna and transponder system integration.',
            '5. Verify FMS navigation database currency and upload latest if expired.',
            '6. Test radio altimeter antenna cable continuity and altitude reading on ground.',
            '7. Check navigation computers BITE for stored faults.',
            '8. Verify heading reference sources (IRS vs. magnetometer) are aligned.',
            '9. Check ADC input data feeding navigation systems.',
            '10. For IRS fail: check liquid cooling system and BITE initialize log.',
        ],
        'quick_actions': ['GPS antenna check', 'IRS realignment', 'TCAS BITE', 'RA cable test'],
        'manuals': ['AMM Task 34-00-00', 'TSM Chapter 34'],
        'typical_resolution_hours': 3.0,
    },
    '35': {
        'system': 'Oxygen Systems',
        'icon': 'bi-wind',
        'color': '#0dcaf0',
        'keywords': ['oxygen', 'crew oxygen', 'passenger oxygen', 'O2', 'mask', 'oxygen pressure',
                     'chemical generator', 'portable oxygen', 'OXY', 'emergency oxygen'],
        'common_failures': [
            {'code': '35-11', 'description': 'Crew oxygen low pressure',
                'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '35-21', 'description': 'Passenger oxygen mask deployment fault',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '35-31', 'description': 'Portable oxygen bottle low pressure',
                'frequency': 'Medium', 'severity': 'Medium'},
        ],
        'troubleshooting_steps': [
            '1. Check crew oxygen bottle pressure gauge reading vs. minimum dispatch.',
            '2. Inspect mask outlets and regulator valves for leaks.',
            '3. Verify automatic passenger oxygen drop system (with caution, test procedure).',
            '4. Apply soapsuds to all high-pressure connections to locate leaks.',
            '5. Inspect crew masks for proper donning and seal operation.',
            '6. Check portable oxygen bottles for serviceability and pressure.',
            '7. Confirm chemical oxygen generator cartridge expiry dates.',
            '8. Verify system compliance with MEL if low pressure condition.',
        ],
        'quick_actions': ['Crew OXY pressure', 'Leak check', 'Portable bottle inspection', 'MEL compliance check'],
        'manuals': ['AMM Task 35-00-00', 'TSM Chapter 35'],
        'typical_resolution_hours': 2.0,
    },
    '36': {
        'system': 'Pneumatic Systems',
        'icon': 'bi-tornado',
        'color': '#6c757d',
        'keywords': ['bleed', 'pneumatic', 'bleed air', 'precooler', 'check valve',
                     'pressure regulating', 'PRV', 'cross bleed', 'high pressure', 'duct leak',
                     'pneumatic duct', 'hot air duct', 'bleed overheat'],
        'common_failures': [
            {'code': '36-11', 'description': 'Engine bleed air leak / duct overheat',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '36-12', 'description': 'Bleed air duct overheat detection',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '36-21',
                'description': 'Pressure regulating valve (PRV) fault', 'frequency': 'Medium', 'severity': 'High'},
            {'code': '36-31', 'description': 'Cross-bleed valve fault',
                'frequency': 'Medium', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Check bleed air duct overheat detector loop continuity and resistance.',
            '2. Inspect pneumatic ducting for signs of leakage: staining, heat damage, soot.',
            '3. Test pressure regulating valve (PRV) operation and controller response.',
            '4. Verify cross-bleed valve position and operation under various power settings.',
            '5. Check high pressure sensor calibration and signal at FADEC.',
            '6. Inspect pre-cooler heat exchanger for blockage; check fan air valve.',
            '7. Thermal cycle history review for duct segment fatigue.',
            '8. Perform pneumatic duct pressure test with soap solution.',
            '9. Check bleed air monitoring system and overheat indicators.',
            '10. After repair, perform full duct leak check at engine ground run.',
        ],
        'quick_actions': ['Duct visual inspection', 'Overheat detector check', 'PRV test', 'Duct pressure test'],
        'manuals': ['AMM Task 36-00-00', 'TSM Chapter 36'],
        'typical_resolution_hours': 3.0,
    },
    '38': {
        'system': 'Water and Waste',
        'icon': 'bi-droplet',
        'color': '#17a2b8',
        'keywords': ['water', 'waste', 'potable', 'drain', 'toilet', 'lavatory',
                     'water heater', 'waste tank', 'flush', 'water system'],
        'common_failures': [
            {'code': '38-11', 'description': 'Lavatory flush system inoperative',
                'frequency': 'High', 'severity': 'Low'},
            {'code': '38-21', 'description': 'Potable water system fault / no water',
                'frequency': 'Medium', 'severity': 'Medium'},
            {'code': '38-31', 'description': 'Waste water drain blocked',
                'frequency': 'High', 'severity': 'Medium'},
        ],
        'troubleshooting_steps': [
            '1. Inspect flush valve, flush mechanism, and waste line for blockage.',
            '2. Verify water system pressure and heater operation.',
            '3. Test waste drain valves for proper operation.',
            '4. Inspect water tank level sensors for proper reading.',
            '5. Check anti-spill provisions and drain check valves.',
            '6. Verify anti-ice system on drain masts (cold weather operations).',
            '7. Physically inspect plumbing connections for leaks under pressure.',
            '8. Verify waste quantity indication against physical check.',
        ],
        'quick_actions': ['Flush valve test', 'Water pressure check', 'Drain valve test', 'Plumbing inspection'],
        'manuals': ['AMM Task 38-00-00', 'TSM Chapter 38'],
        'typical_resolution_hours': 1.5,
    },
    '45': {
        'system': 'Central Maintenance System (CMS)',
        'icon': 'bi-cpu-fill',
        'color': '#6610f2',
        'keywords': ['CMS', 'ACARS', 'CMC', 'central maintenance', 'BITE', 'diagnostic',
                     'LRU', 'fault isolation', 'maintenance computer', 'CMU', 'datalink'],
        'common_failures': [
            {'code': '45-11', 'description': 'CMC communication fault',
                'frequency': 'Medium', 'severity': 'Medium'},
            {'code': '45-21', 'description': 'ACARS system offline / datalink fail',
                'frequency': 'High', 'severity': 'Medium'},
            {'code': '45-31', 'description': 'CMS printer fault',
                'frequency': 'Medium', 'severity': 'Low'},
        ],
        'troubleshooting_steps': [
            '1. Check CMC power supply and data bus connectivity.',
            '2. Verify VHF datalink radio connection for ACARS (ATN/FANS).',
            '3. Test CMC-to-LRU communication links and ARINC buses.',
            '4. Confirm CMS software version compatibility with other LRUs.',
            '5. Check data loader port for software update compatibility.',
            '6. Inspect ARINC 429/664 data buses for signal integrity.',
            '7. Review CMC stored fault history and perform BITE test run.',
            '8. Re-initialize CMC and verify network re-establishment.',
        ],
        'quick_actions': ['CMC power check', 'Datalink test', 'BITE run', 'Software version check'],
        'manuals': ['AMM Task 45-00-00', 'TSM Chapter 45'],
        'typical_resolution_hours': 1.5,
    },
    '49': {
        'system': 'Auxiliary Power Unit (APU)',
        'icon': 'bi-gear-fill',
        'color': '#fd7e14',
        'keywords': ['APU', 'auxiliary power unit', 'starter', 'APU generator', 'APU bleed',
                     'APU speed', 'EGT', 'APU oil', 'APU start fault', 'APUC', 'inlet door'],
        'common_failures': [
            {'code': '49-11',
                'description': 'APU start failure (hot/wet/hung start)', 'frequency': 'High', 'severity': 'High'},
            {'code': '49-21', 'description': 'APU oil pressure low',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '49-31',
                'description': 'APU speed exceedance (overspeed)', 'frequency': 'Low', 'severity': 'Critical'},
            {'code': '49-41', 'description': 'APU EGT exceedance',
                'frequency': 'Medium', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Review APU start fault codes from APUC BITE.',
            '2. Check fuel supply to APU including fuel shutoff valve position.',
            '3. Inspect APU inlet door operation and verify clear of obstruction.',
            '4. Verify APU oil level and oil quality/condition.',
            '5. Test APU starter motor current draw per AMM.',
            '6. Check APU controller hardware/software revision.',
            '7. Inspect APU exhaust duct for blockage, bird FOD, or damage.',
            '8. For hot start: perform cooling dry crank per AMM before restart.',
            '9. Borescope APU compressor if excessive smoke or EGT exceedance observed.',
            '10. Compare APU EGT trend with baseline — degradation may indicate wash needed.',
        ],
        'quick_actions': ['APUC BITE', 'APU oil level', 'Inlet door inspection', 'Starter motor test'],
        'manuals': ['AMM Task 49-00-00', 'TSM Chapter 49', 'APU Maintenance Manual'],
        'typical_resolution_hours': 3.0,
    },
    '71': {
        'system': 'Power Plant — General',
        'icon': 'bi-rocket-fill',
        'color': '#dc3545',
        'keywords': ['engine', 'EGT', 'N1', 'N2', 'thrust', 'FADEC', 'vibration', 'oil',
                     'engine control', 'power plant', 'engine oil', 'engine fault', 'engine fire'],
        'common_failures': [
            {'code': '71-00',
                'description': 'Engine oil leak (external)', 'frequency': 'High', 'severity': 'High'},
            {'code': '71-11',
                'description': 'Engine vibration high (N1 or N2)', 'frequency': 'Medium', 'severity': 'High'},
            {'code': '71-21', 'description': 'Engine EGT exceedance in-flight',
                'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '71-31', 'description': 'Engine N1/N2 speed discrepancy',
                'frequency': 'Low', 'severity': 'Critical'},
        ],
        'troubleshooting_steps': [
            '1. Review FADEC fault codes from maintenance page.',
            '2. Check engine oil consumption rate vs. approved limits.',
            '3. Borescope engine major stages if EGT is high or trending up.',
            '4. Check vibration sensor calibration and isolation mount condition.',
            '5. Inspect engine mounts for looseness, damage, or deterioration.',
            '6. Review engine trend monitoring (ETM) data for deviation.',
            '7. Check FADEC software version and compare with SB list.',
            '8. Perform engine run to spec per AMM and record all parameters.',
            '9. Check for fuel nozzle flow imbalance if EGT spread is suspect.',
            '10. Review oil analysis (spectrographic) if chip detector activated.',
        ],
        'quick_actions': ['FADEC BITE', 'Oil level and leak check', 'Engine trend data', 'Vibration sensor check'],
        'manuals': ['AMM Task 71-00-00', 'TSM Chapter 71', 'FADEC Manual'],
        'typical_resolution_hours': 5.0,
    },
    '72': {
        'system': 'Engine — Turbine/Compressor',
        'icon': 'bi-arrow-clockwise',
        'color': '#e83e8c',
        'keywords': ['compressor', 'turbine', 'fan blade', 'surge', 'stall', 'FOD', 'borescope',
                     'bleed valve', 'IGV', 'fan damage', 'compressor wash', 'HPT', 'LPT'],
        'common_failures': [
            {'code': '72-11', 'description': 'Fan blade damage / FOD ingestion',
                'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '72-21', 'description': 'Compressor surge / stall event',
                'frequency': 'Low', 'severity': 'Critical'},
            {'code': '72-31', 'description': 'Turbine case distortion / hot section',
                'frequency': 'Low', 'severity': 'Critical'},
            {'code': '72-51',
                'description': 'Variable bleed valve (VBV) failure', 'frequency': 'Medium', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Perform visual/borescope inspection of fan blades for FOD damage.',
            '2. Borescope all HPC stages, combustors, and HPT/LPT stages.',
            '3. Check variable bleed valve (VBV) operation and FADEC actuator commands.',
            '4. Review performance data for stall/surge event signature.',
            '5. Inspect exhaust nozzle / tail cone for cracks or thermal damage.',
            '6. Review ETM for EGT shift or T/O power setting trend.',
            '7. Test variable stator vane (VSV) system operation and rigging.',
            '8. Check turbine cooling air supply ducting.',
            '9. If surge event: comply with engine manufacturer\'s mandatory action.',
            '10. Perform compressor wash per AMM if performance degradation noted.',
        ],
        'quick_actions': ['Fan blade inspection', 'Borescope all stages', 'VBV test', 'ETM trend check'],
        'manuals': ['AMM Task 72-00-00', 'TSM Chapter 72', 'Engine Shop Manual'],
        'typical_resolution_hours': 8.0,
    },
    '73': {
        'system': 'Engine Fuel and Control',
        'icon': 'bi-sliders',
        'color': '#6f42c1',
        'keywords': ['FADEC', 'fuel control', 'fuel nozzle', 'combustor', 'throttle',
                     'HMU', 'fuel flow', 'FADEC fault', 'engine fuel control', 'fuel metering'],
        'common_failures': [
            {'code': '73-11', 'description': 'FADEC channel A/B fault / degraded mode',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '73-21', 'description': 'Fuel nozzle clogged / flow imbalance',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '73-31', 'description': 'Main fuel pump low pressure',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '73-41', 'description': 'Engine fuel filter bypass indication',
                'frequency': 'Low', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Interrogate FADEC for fault messages, active and stored.',
            '2. Check fuel filter pressure differential; replace if saturated.',
            '3. Perform ground engine run monitoring FADEC parameters.',
            '4. Check fuel pump output pressure at idle and takeoff power.',
            '5. Inspect fuel nozzle spray pattern using bench test rig.',
            '6. Verify FADEC connector pin seating and harness integrity.',
            '7. Check FADEC software version against latest SB/SIL.',
            '8. Test TLA (Throttle Lever Angle) RVDT calibration and signal to FADEC.',
            '9. Check EEC (Electronic Engine Controller) BITE history.',
            '10. If fuel nozzle issue: perform fuel manifold pressure test.',
        ],
        'quick_actions': ['FADEC interrogation', 'Fuel filter check', 'Nozzle test', 'TLA calibration'],
        'manuals': ['AMM Task 73-00-00', 'TSM Chapter 73', 'FADEC Manual'],
        'typical_resolution_hours': 4.0,
    },
    '79': {
        'system': 'Engine Oil System',
        'icon': 'bi-droplet-half',
        'color': '#795548',
        'keywords': ['oil', 'lubrication', 'oil pressure', 'oil temperature', 'chip detector',
                     'oil filter', 'oil consumption', 'oil level', 'oil leak', 'engine oil',
                     'low oil', 'oil pressure low'],
        'common_failures': [
            {'code': '79-11', 'description': 'Engine oil pressure low',
                'frequency': 'High', 'severity': 'Critical'},
            {'code': '79-12', 'description': 'Engine oil temperature high',
                'frequency': 'Medium', 'severity': 'High'},
            {'code': '79-21',
                'description': 'Chip detector activated (metallic particles)', 'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '79-31', 'description': 'Engine oil external leak',
                'frequency': 'High', 'severity': 'High'},
        ],
        'troubleshooting_steps': [
            '1. Check oil level at sight glass and dipstick per AMM 12-10-00.',
            '2. Run engine and monitor oil pressure and temperature on FADEC page.',
            '3. Remove chip detector and examine particles under magnification.',
            '4. If metallic chips found: mandatory borescope inspection, no dispatch.',
            '5. Remove and inspect oil filter for metal contamination.',
            '6. Inspect all oil lines, seals, and housing drain points for leaks.',
            '7. Check oil cooler / fuel-oil heat exchanger for blockage.',
            '8. Trend monitor oil consumption: compare to limits in AMM.',
            '9. Perform oil spectrographic analysis if chip indication.',
            '10. If oil leak external: identify source (turbine rear seal, accessory gearbox).',
        ],
        'quick_actions': ['Oil level check', 'Chip detector remove/inspect', 'Oil filter check', 'Spectrographic analysis'],
        'manuals': ['AMM Task 79-00-00', 'TSM Chapter 79'],
        'typical_resolution_hours': 3.0,
    },
    '80': {
        'system': 'Engine Starting',
        'icon': 'bi-power',
        'color': '#f44336',
        'keywords': ['starter', 'air turbine starter', 'start valve', 'motoring', 'dry crank',
                     'hung start', 'hot start', 'engine start', 'start fault', 'starter valve',
                     'no light off', 'early light off'],
        'common_failures': [
            {'code': '80-11', 'description': 'Engine starter valve stuck open/closed',
                'frequency': 'High', 'severity': 'High'},
            {'code': '80-21', 'description': 'Hot start (EGT exceed during start)',
             'frequency': 'Medium', 'severity': 'Critical'},
            {'code': '80-31', 'description': 'Hung start (N2 does not accelerate through idle)',
             'frequency': 'Medium', 'severity': 'Critical'},
        ],
        'troubleshooting_steps': [
            '1. Check pneumatic supply pressure at start valve inlet.',
            '2. Test start valve manual operation (open/close) and cycling.',
            '3. Measure starter air motor torque output per AMM.',
            '4. Review start sequence timing captured by FADEC data.',
            '5. Check fuel dump valve operation before restart attempt.',
            '6. Perform dry crank per AMM hot start recovery to clear combustor.',
            '7. Borescope combustor if EGT exceedance occurred during start.',
            '8. Check FADEC start sequence parameters and limits.',
            '9. Inspect starter control circuit continuity.',
            '10. If repeated hung starts: check HPC variable compressor vane rigging.',
        ],
        'quick_actions': ['Start valve test', 'FADEC start data review', 'Dry crank (if hot start)', 'Combustor borescope'],
        'manuals': ['AMM Task 80-00-00', 'TSM Chapter 80'],
        'typical_resolution_hours': 2.5,
    },
}

# ==============================================================================
# CHAT INTENT PATTERNS
# ==============================================================================

INTENT_PATTERNS = {
    'troubleshoot': [
        r'\b(troubleshoot|diagnose|diagnos|fix|repair|how to fix|what\'s wrong|why is|fault|fail|problem|issue|check|analyze)\b',
        r'\b(solucionar|diagnosticar|reparar|consertar|como resolver|problema|defeito|analisar|inspecionar)\b',
    ],
    'statistics': [
        r'\b(most|frequent|recurring|statistics|trends|top|ranking|how many|count|worst|critical|distribution|pattern|prevalence|common)\b',
        r'\b(mais comum|frequente|recorrente|estatísticas|tendências|rank|quantos|piores|distribuição|padrão|menor|menos|raro|rarest|least)\b',
        r'\b(most.*between|between.*tail|which.*highest|lowest|rarest|least|minimum|maximum)\b',
        r'\b(qual.*falha|qual a|qual é)\b',
    ],
    'what_is': [
        r'\b(what is|what are|explain|describe|tell me about|what does|mean)\b',
        r'\b(o que é|explique|descreva|me fale sobre)\b',
    ],
    'recommendation': [
        r'\b(recommend|suggest|should i|best practice|what should|advise|guidance)\b',
        r'\b(recomendar|sugerir|devo|melhor prática|o que devo|aconselhar)\b',
    ],
    'list_ata': [
        r'\b(list|show|display|all ata|which ata|ata chapters)\b',
        r'\b(listar|mostrar|exibir|todos ata|capítulos ata)\b',
    ],
    'tail_specific': [
        r'\b(?:XA|PR|N|G|EC|PH|HB|F|D)-[A-Z0-9]{3,5}\b',
        r'\b(?:tail|aircraft|plane|reg|registration|tail number|acft|cauda|aeronave|matricula)\b',
    ],
}

# ==============================================================================
# AI ENGINE CLASS
# ==============================================================================


class TroubleshootingAI:
    """
    Offline AI engine for Mexicana Troubleshooting System.
    Provides: failure analysis, troubleshooting steps, statistics, and chat Q&A.
    """

    def __init__(self):
        self.kb = ATA_KNOWLEDGE_BASE
        self._all_keywords = self._build_keyword_index()

    def _build_keyword_index(self):
        """Build reverse index: keyword -> [ata_chapters] for fast matching."""
        index = defaultdict(list)
        for ata, data in self.kb.items():
            for kw in data.get('keywords', []):
                index[kw.lower()].append(ata)
        return index

    # --------------------------------------------------------------------------
    # CORE: ANALYZE A FAILURE
    # --------------------------------------------------------------------------

    def analyze_failure(self, ata: str, description: str, model: str = '', categoria: str = '') -> dict:
        """
        Analyze a failure record and return structured recommendations.
        Returns: { confidence, ata_info, troubleshooting_steps, quick_actions, similar_patterns,
                   severity_estimate, recommended_manuals, estimated_hours }
        """
        ata_clean = str(ata).strip().split('.')[0] if ata else ''
        description_lower = (description or '').lower()

        # Attempt direct ATA lookup
        ata_info = self.kb.get(ata_clean)
        matched_atas = [ata_clean] if ata_info else []
        confidence = 0

        if ata_info:
            confidence += 60  # Strong match via ATA

        # Keyword matching from description
        kw_matched_atas = self._keyword_match(description_lower)
        for ka in kw_matched_atas:
            if ka not in matched_atas:
                matched_atas.append(ka)
                confidence += 15
        confidence = min(confidence, 97)

        # If no direct ATA match but keywords matched, use best keyword match
        if not ata_info and matched_atas:
            ata_info = self.kb.get(matched_atas[0])
            ata_clean = matched_atas[0]

        result = {
            'matched_ata': ata_clean,
            'confidence': confidence,
            'ata_info': None,
            'troubleshooting_steps': [],
            'quick_actions': [],
            'similar_ata_systems': [],
            'severity_estimate': 'Medium',
            'recommended_manuals': [],
            'estimated_hours': 2.0,
            'failure_patterns': [],
        }

        if ata_info:
            result['ata_info'] = {
                'system': ata_info['system'],
                'icon': ata_info['icon'],
                'color': ata_info['color'],
            }
            result['troubleshooting_steps'] = ata_info['troubleshooting_steps']
            result['quick_actions'] = ata_info['quick_actions']
            result['recommended_manuals'] = ata_info['manuals']
            result['estimated_hours'] = ata_info['typical_resolution_hours']

            # Estimate severity from description keywords
            result['severity_estimate'] = self._estimate_severity(
                description_lower, ata_info)

            # Find similar failure patterns from knowledge base
            result['failure_patterns'] = [
                cf for cf in ata_info['common_failures']
                if any(kw in description_lower for kw in cf['description'].lower().split())
            ] or ata_info['common_failures'][:2]

        # Adjacent ATA systems that may be related
        result['similar_ata_systems'] = self._find_related_atas(
            ata_clean, description_lower)

        return result

    def _keyword_match(self, text: str) -> list:
        """Return sorted list of ATA chapters that match keywords in text."""
        match_count = Counter()
        words = set(re.findall(r'\b[a-zA-Z]{2,}\b', text.lower()))
        for kw, atas in self._all_keywords.items():
            kw_lower = kw.lower()
            # Exact substring match (original behaviour)
            if kw_lower in text:
                for a in atas:
                    match_count[a] += 2  # weight exact matches higher
            else:
                # Partial word-boundary match for multi-word keywords
                kw_words = set(kw_lower.split())
                overlap = len(kw_words & words)
                if overlap and overlap >= max(1, len(kw_words) - 1):
                    for a in atas:
                        match_count[a] += 1
        return [ata for ata, _ in match_count.most_common(5)]

    def _estimate_severity(self, description: str, ata_info: dict) -> str:
        critical_words = [
            'fire', 'smoke', 'overheat', 'collision', 'failed', 'inoperative',
            'aog', 'unsafe', 'exceedance', 'stall', 'surge', 'oil pressure',
            'fuel leak', 'hydraulic fluid', 'fogo', 'fumaça', 'superaquecimento',
            'pressure loss', 'engine failure', 'double failure', 'no light off',
            'hot start', 'hung start', 'runway excursion', 'chip detected',
            'loss of control', 'hydraulic loss', 'dual failure', 'loss of thrust',
            'both engines', 'engine shutdown', 'fire warning', 'tcas ra',
        ]
        high_words = [
            'fault', 'malfunction', 'stuck', 'intermittent', 'incorrect', 'erratic',
            'vibration high', 'chip', 'warning', 'caution', 'low pressure',
            'dispatch deviation', 'snag', 'squawk', 'deferred item', 'mel active',
            'abnormal', 'degraded', 'partial failure', 'no go', 'nogo', 'aog risk',
            'inop', 'unserviceable', 'write-up', 'open item', 'repeat snag',
        ]
        desc = description.lower()
        if any(w in desc for w in critical_words):
            return 'Critical'
        if any(w in desc for w in high_words):
            return 'High'
        return 'Medium'

    def _find_related_atas(self, ata: str, description: str) -> list:
        related_map = {
            '21': ['36', '29', '24'],
            '22': ['34', '31', '27'],
            '23': ['31', '34'],
            '24': ['49', '36', '26'],
            '26': ['24', '28'],
            '27': ['29', '32', '22'],
            '28': ['73', '79', '71'],
            '29': ['27', '32', '21'],
            '30': ['36', '21'],
            '31': ['22', '34', '45'],
            '32': ['29', '27', '21'],
            '34': ['22', '31', '23'],
            '35': ['21', '36'],
            '36': ['21', '49', '30'],
            '38': ['21', '36'],
            '45': ['31', '22'],
            '49': ['36', '24', '80'],
            '71': ['79', '73', '72'],
            '72': ['71', '73', '80'],
            '73': ['71', '79', '28'],
            '79': ['71', '73', '72'],
            '80': ['36', '71', '49'],
        }
        related = related_map.get(ata, [])[:3]
        return [{'ata': r, 'system': self.kb[r]['system']} for r in related if r in self.kb]

    # --------------------------------------------------------------------------
    # ANALYTICS: PROCESS HISTORICAL RECORDS
    # --------------------------------------------------------------------------

    def get_analytics(self, records: list) -> dict:
        """Compute comprehensive analytics from a list of failure records."""
        if not records:
            return {'error': 'No records available for analysis.'}

        # Basic counts
        total = len(records)
        open_count = sum(1 for r in records if str(
            r.get('status_atual', '')).lower() in ('open', 'in progress', 'aberto'))
        closed_count = total - open_count

        # ATA frequency
        ata_freq = Counter(
            str(r.get('ata', 'N/A')).strip().split('.')[0] for r in records)
        top_ata = ata_freq.most_common(10)

        # Tail frequency
        tail_freq = Counter(r.get('tail', 'N/A') for r in records)
        top_tails = tail_freq.most_common(10)

        # Priority breakdown
        priority_freq = Counter(r.get('prioridade', 'Medium') for r in records)

        # Category breakdown
        cat_freq = Counter(r.get('categoria', 'General') for r in records)

        # Model breakdown
        model_freq = Counter(r.get('modelo', 'Unknown') for r in records)

        # Safety flags
        safety_count = sum(1 for r in records if r.get(
            'safety') in (1, True, '1', 'true', 'True', 'on'))

        # Average resolution hours
        hours = [float(r.get('tempo_estimado_horas', 0) or 0) for r in records]
        avg_hours = round(sum(hours) / len(hours), 1) if hours else 0

        # Most common failure descriptions (simple word frequency)
        problem_words = []
        for r in records:
            txt = (r.get('problema', '') or '').lower()
            words = re.findall(r'\b[a-zA-Z]{4,}\b', txt)
            problem_words.extend(words)
        stop_words = {'with', 'from', 'that', 'this', 'have', 'were', 'been', 'they', 'their',
                      'during', 'after', 'before', 'while', 'found', 'noted', 'observed', 'para',
                      'para', 'sistema', 'system', 'aircraft', 'fault', 'reported', 'performed'}
        top_words = [(w, c) for w, c in Counter(
            problem_words).most_common(20) if w not in stop_words][:10]

        # Trend by month (last 6 months)
        monthly = Counter()
        for r in records:
            dt_str = r.get('data_cadastro') or r.get('data_criacao') or ''
            if dt_str:
                try:
                    dt = datetime.strptime(dt_str[:10], '%Y-%m-%d')
                    monthly[dt.strftime('%Y-%m')] += 1
                except Exception:
                    pass
        monthly_sorted = sorted(monthly.items())[-6:]

        # Recurring tails: tails with >=3 occurrences
        recurring = [(t, c) for t, c in top_tails if c >= 3]

        # Build ATA enriched data
        top_ata_enriched = []
        for ata_raw, count in top_ata:
            info = self.kb.get(ata_raw, {})
            top_ata_enriched.append({
                'ata': ata_raw,
                'count': count,
                'system': info.get('system', f'ATA {ata_raw}'),
                'icon': info.get('icon', 'bi-gear'),
                'color': info.get('color', '#6c757d'),
                'pct': round(count / total * 100, 1),
            })

        # Problematic combinations: tail + ATA with >=2 occurrences
        combo_counter = Counter()
        for r in records:
            tail = r.get('tail', '')
            ata_r = str(r.get('ata', '')).strip().split('.')[0]
            if tail and ata_r:
                combo_counter[(tail, ata_r)] += 1
        hot_combos = [
            {'tail': t, 'ata': a, 'count': c,
             'system': self.kb.get(a, {}).get('system', f'ATA {a}')}
            for (t, a), c in combo_counter.most_common(10) if c >= 2
        ]

        return {
            'total': total,
            'open_count': open_count,
            'closed_count': closed_count,
            'open_rate': round(open_count / total * 100, 1),
            'safety_count': safety_count,
            'avg_hours': avg_hours,
            'top_ata': top_ata_enriched,
            'top_tails': [{'tail': t, 'count': c, 'pct': round(c/total*100, 1)} for t, c in top_tails[:10]],
            'recurring_tails': [{'tail': t, 'count': c} for t, c in recurring],
            'priority_breakdown': dict(priority_freq),
            'category_breakdown': dict(cat_freq),
            'model_breakdown': dict(model_freq),
            'top_keywords': top_words,
            'monthly_trend': [{'month': m, 'count': c} for m, c in monthly_sorted],
            'hot_combinations': hot_combos,
        }

    # --------------------------------------------------------------------------
    # CHAT INTERFACE
    # --------------------------------------------------------------------------

    def chat(self, query: str, records: list = None) -> dict:
        """
        Process a natural language query and return a structured AI response.
        Returns: { response, type, confidence, related_atas, suggestions }

        IMPROVEMENT 9.0: Better intent routing, tail-specific handling, Portuguese support
        """
        q = query.strip().lower()
        if not q:
            return self._response('Please describe a fault, enter an ATA chapter, or ask a question.', 'info', 30)

        # When query contains conversation history (multi-turn context injected by routes_analytics),
        # extract only the CURRENT user request for intent detection and ATA extraction.
        # Pattern: "{history}\n\nCurrent user request: {actual_query}"
        q_intent = q
        current_req_match = re.search(
            r'current user request:\s*(.+)$', q, re.DOTALL | re.IGNORECASE)
        if current_req_match:
            q_intent = current_req_match.group(1).strip()

        # Detect intent (improved) — use only the current request portion
        intent = self._detect_intent(q_intent)

        # Check for ATA reference — use only the current request to avoid history contamination
        ata_refs = []
        explicit_ata = re.findall(
            r'(?:ata|chapter|cap[íi]tulo)\s+[-]?(\d{2,3})\b', q_intent, re.IGNORECASE)
        if explicit_ata:
            ata_refs = [a for a in explicit_ata if a in self.kb]
        else:
            isolated_ata = re.fullmatch(r'\s*(\d{2,3})\s*', q_intent)
            if isolated_ata:
                ata_candidate = isolated_ata.group(
                    1).lstrip('0') or isolated_ata.group(1)
                if ata_candidate in self.kb:
                    ata_refs = [ata_candidate]

        records = records or []

        # IMPROVEMENT 10.0: Enrich records with FH/FC if missing
        for record in records:
            if not record.get('fh') and not record.get('FC'):
                modelo = str(record.get('modelo', '')).lower()
                if 'e195' in modelo or 'e190' in modelo or 'e2' in modelo:
                    record['fh'] = 12000.0
                    record['fc'] = 8000
                elif 'e170' in modelo or 'e175' in modelo:
                    record['fh'] = 10000.0
                    record['fc'] = 6500
                else:
                    record['fh'] = 10000.0
                    record['fc'] = 6500

        # ---- IMPROVEMENT: Tail-specific query (no explicit ATA) ----
        if intent == 'tail_specific' and not ata_refs:
            # Try both full tail format and simple format
            tail_match = re.search(
                r'\b(?:XA|PR|N|G|EC|PH|HB|F|D)-[A-Z0-9]{3,5}\b', q_intent, re.IGNORECASE)
            tail = None
            if tail_match and records:
                tail = tail_match.group().upper()

            # If not found, try simple tail format (MXD, E2A, etc.)
            if not tail:
                simple_match = re.search(r'\b([A-Za-z]{2,4})\b', q_intent)
                if simple_match:
                    candidate = simple_match.group(1)
                    common_words = {'the', 'and', 'for', 'but',
                                    'are', 'has', 'was', 'not', 'ata'}
                    if candidate.lower() not in common_words:
                        tail = candidate.upper()

            if tail and records:
                # Analyze records for this tail
                tail_records = [r for r in records if str(
                    r.get('tail', '')).strip().upper() == tail]
                if tail_records:
                    # Return statistics for this specific tail
                    ata_counts = Counter(r.get('ata') for r in tail_records)
                    top_atas = ata_counts.most_common(3)
                    response = f"**Tail {tail} — Active Issues**\n\n"
                    response += f"Total issues: {len(tail_records)}\n\n"
                    # Show FH/FC if available
                    avg_fh = sum(r.get('fh', 0) for r in tail_records) / \
                        len(tail_records) if tail_records else 0
                    if avg_fh > 0:
                        response += f"Estimated Flight Hours: {avg_fh:.0f}\n\n"
                    response += "**Top ATAs for this tail:**\n"
                    for ata, count in top_atas:
                        if ata in self.kb:
                            system = self.kb[ata]['system']
                            response += f"  • ATA {ata} — {system}: {count} occurrence(s)\n"
                    return self._response(response, 'tail_detail', 88, [ata[0] for ata in top_atas])
                else:
                    return self._response(f"No records found for tail {tail}. Check if the tail is registered in the system.", 'info', 50)

        # ---- Direct ATA query ----
        # Explicit ATA references must be honored to avoid drifting to unrelated ATA systems.
        if ata_refs:
            ata = ata_refs[0]
            info = self.kb[ata]
            steps = '\n'.join(info['troubleshooting_steps'][:6])
            common = '\n'.join(f"  • [{cf['code']}] {cf['description']} — *{cf['severity']}*"
                               for cf in info['common_failures'][:3])
            ata_records = [
                record for record in records
                if str(record.get('ata', '') or '').strip().split('.')[0] == ata
            ]
            open_records = [
                record for record in ata_records
                if str(record.get('status_atual', '') or '').strip().lower() in {'open', 'in progress', 'pending', 'pending review', 'aberto'}
            ]
            model_counter = Counter(
                str(record.get('modelo', '') or '').strip()
                for record in ata_records if str(record.get('modelo', '') or '').strip()
            )
            tail_counter = Counter(
                str(record.get('tail', '') or '').strip().upper()
                for record in ata_records if str(record.get('tail', '') or '').strip()
            )
            evidence_block = ''
            if ata_records:
                top_models = ', '.join(
                    f"{model}: {count}"
                    for model, count in model_counter.most_common(4)
                ) or 'N/A'
                top_tails = ', '.join(
                    f"{tail}: {count}"
                    for tail, count in tail_counter.most_common(5)
                ) or 'N/A'
                evidence_block = (
                    f"\n\n**Fleet Database Evidence:**\n"
                    f"Total records for ATA {ata}: **{len(ata_records)}**\n"
                    f"Open records: **{len(open_records)}**\n"
                    f"Affected models: {top_models}\n"
                    f"Most affected tails: {top_tails}"
                )
            response = (
                f"**ATA {ata} — {info['system']}**\n\n"
                f"**Most Common Failures:**\n{common}\n\n"
                f"**Key Troubleshooting Steps:**\n{steps}\n\n"
                f"**Reference Manuals:** {', '.join(info['manuals'][:2])}\n"
                f"**Typical Resolution:** ~{info['typical_resolution_hours']}h"
                f"{evidence_block}"
            )
            return self._response(response, 'ata_detail', 92, ata_refs)

        # ---- Most common / statistics ----
        if intent == 'statistics' and records:
            analytics = self.get_analytics(records)
            top3_ata = analytics['top_ata'][:3]
            top3_tails = analytics['top_tails'][:3]
            ata_txt = '\n'.join(f"  • ATA {x['ata']} ({x['system']}): **{x['count']}** occurrences ({x['pct']}%)"
                                for x in top3_ata)
            tail_txt = '\n'.join(f"  • {x['tail']}: **{x['count']}** records"
                                 for x in top3_tails)
            rr_txt = ''
            if analytics['recurring_tails']:
                rr = analytics['recurring_tails']
                rr_txt = f"\n\n**Recurring Tails (≥3 occurrences):**\n" + '\n'.join(
                    f"  • {x['tail']}: {x['count']} records" for x in rr[:5])
            response = (
                f"**Fleet Failure Statistics** (Total: {analytics['total']} records)\n\n"
                f"**Top ATA Chapters:**\n{ata_txt}\n\n"
                f"**Most Recurring Aircraft:**\n{tail_txt}"
                f"{rr_txt}\n\n"
                f"Open rate: **{analytics['open_rate']}%** | "
                f"Safety flags: **{analytics['safety_count']}** | "
                f"Avg resolution: **{analytics['avg_hours']}h**"
            )
            return self._response(response, 'statistics', 95)

        # ---- Keyword-based troubleshooting ----
        matched = self._keyword_match(q_intent)
        if matched:
            ata = matched[0]
            info = self.kb[ata]
            steps = '\n'.join(info['troubleshooting_steps'][:5])
            response = (
                f"**System Identified: ATA {ata} — {info['system']}**\n\n"
                f"Based on keywords in your query, I suggest starting with:\n\n"
                f"{steps}\n\n"
                f"**Quick Actions:** {' | '.join(info['quick_actions'])}\n"
                f"**Reference:** {', '.join(info['manuals'][:2])}"
            )
            return self._response(response, 'keyword_match', 75, matched[:3])

        # ---- List all ATA ----
        if intent == 'list_ata':
            ata_list = '\n'.join(
                f"  • **ATA {k}** — {v['system']}" for k, v in self.kb.items())
            response = f"**Available ATA Knowledge Base:**\n\n{ata_list}"
            return self._response(response, 'list', 99)

        # ---- Fallback ----
        suggestions = [f"ATA {k} — {v['system']}" for k,
                       v in list(self.kb.items())[:5]]
        return self._response(
            "No exact ATA keyword was detected yet. "
            "Please include at least one of these details to improve precision: ATA chapter (e.g., **29**, **34**, **71**), aircraft tail, fault message, or operating condition when the issue occurs.",
            'fallback', 30,
            suggestions=suggestions
        )

    def _detect_intent(self, text: str) -> str:
        """
        Improved intent detection with better heuristics.
        Priority: explicit_intent > tail_with_context > tail_only > fallback

        IMPROVEMENT 9.0: Better Portuguese support, keyword weighting, context awareness
        """
        # Priority order matters - check  higher priority intents first

        # PRIORITY 0: Direct ATA reference (highest - explicit)
        if re.search(r'(?:ata|chapter|cap[íi]tulo)\s+[-]?(\d{2,3})\b', text, re.IGNORECASE):
            return 'ata_direct'
        if re.fullmatch(r'\s*\d{2,3}\s*', text):
            return 'ata_direct'

        # PRIORITY 0.5: Simple tail identifier (BEFORE statistics to avoid conflicts like "MXD most common")
        # Only if it's the primary content and not a known word/system
        # IMPROVEMENT 10.2: Support alphanumeric tails (E2A, PR01, XB12, etc)
        simple_match = re.search(
            r'\b([A-Z][A-Z0-9]{1,4})\b', text, re.IGNORECASE)
        if simple_match:
            candidate = simple_match.group(1).upper()
            # List of common English/Portuguese words to exclude
            common_words = {'THE', 'AND', 'FOR', 'BUT', 'ARE', 'HAS', 'WAS', 'NOT', 'OUT', 'ALL', 'ONE', 'TWO',
                            'IS', 'BE', 'DO', 'GO', 'NO', 'OR', 'SO', 'WE', 'IF', 'AS', 'TO', 'BY', 'UP', 'AT', 'IN', 'OF',
                            'COM', 'QUE', 'POR', 'FOI', 'TEM', 'DAS', 'DOS', 'UMA', 'UM', 'QUAL', 'ATA'}
            # If candidate looks like a tail code and query is short/simple
            if candidate not in common_words and len(text.split()) <= 4:
                # If asking about statistics for that tail
                if any(word in text.lower() for word in ['most', 'common', 'frequent', 'less', 'menor', 'menos']):
                    return 'statistics'
                # Otherwise it's tail status query
                return 'tail_specific'

        # PRIORITY 1: Statistics intent (highest - more specific keyword=)
        for pattern in INTENT_PATTERNS['statistics']:
            if re.search(pattern, text, re.IGNORECASE):
                return 'statistics'

        # PRIORITY 2: Explicit diagnostic/troubleshoot
        for pattern in INTENT_PATTERNS['troubleshoot']:
            if re.search(pattern, text, re.IGNORECASE) and not any(w in text for w in ['most', 'frequent', 'common', 'menor', 'menos', 'raro']):
                return 'troubleshoot'

        # PRIORITY 3: What_is / Recommendation / List patterns
        for intent in ['what_is', 'recommendation', 'list_ata']:
            for pattern in INTENT_PATTERNS.get(intent, []):
                if re.search(pattern, text, re.IGNORECASE):
                    return intent

        # PRIORITY 4: Tail-specific with context
        tail_pattern = r'\b(?:XA|PR|N|G|EC|PH|HB|F|D)-[A-Z0-9]{3,5}\b'
        if re.search(tail_pattern, text, re.IGNORECASE):
            # If asking about statistics for that tail
            if any(word in text for word in ['most', 'common', 'frequent', 'problem', 'fault', 'failure', 'problem', 'menos', 'menor']):
                return 'statistics'
            # If asking for diagnosis/troubleshooting of that specific tail
            if any(word in text for word in ['diagnos', 'troubleshoot', 'check', 'status']):
                return 'troubleshoot'
            # Otherwise it's tail status query
            return 'tail_specific'

        # PRIORITY 5: Simple tail identifier (2-5 char codes like "MXD", "E2A", "PR01")
        # Only if it's the primary content and not a known word/system
        # IMPROVEMENT 10.2: Support alphanumeric tails (E2A, PR01, XB12, etc)
        simple_match = re.search(
            r'\b([A-Z][A-Z0-9]{1,4})\b', text, re.IGNORECASE)
        if simple_match:
            candidate = simple_match.group(1)
            # List of common English/Portuguese words to exclude
            common_words = {'the', 'and', 'for', 'but', 'are', 'has', 'was', 'not', 'out', 'all', 'one', 'two',
                            'is', 'be', 'do', 'go', 'no', 'or', 'so', 'we', 'if', 'as', 'to', 'by', 'up', 'at', 'in', 'of',
                            'com', 'que', 'por', 'foi', 'tem', 'das', 'dos', 'uma', 'um', 'qual', 'ata'}
            # If candidate looks like a tail code and query is short/simple
            if candidate.lower() not in common_words and len(text.split()) <= 3:
                return 'tail_specific'

            return None

    @staticmethod
    def _response(text: str, rtype: str, confidence: int, related_atas: list = None,
                  suggestions: list = None) -> dict:
        return {
            'response': text,
            'type': rtype,
            'confidence': confidence,
            'related_atas': related_atas or [],
            'suggestions': suggestions or [],
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

    # --------------------------------------------------------------------------
    # QUICK LOOKUP
    # --------------------------------------------------------------------------

    def get_ata_procedure(self, ata: str) -> dict:
        """Return full procedure for a given ATA chapter."""
        info = self.kb.get(str(ata).strip().split('.')[0])
        if not info:
            return {'error': f'ATA {ata} not found in knowledge base.'}
        return {
            'ata': ata,
            'system': info['system'],
            'icon': info['icon'],
            'color': info['color'],
            'common_failures': info['common_failures'],
            'troubleshooting_steps': info['troubleshooting_steps'],
            'quick_actions': info['quick_actions'],
            'manuals': info['manuals'],
            'typical_hours': info['typical_resolution_hours'],
        }

    def list_ata_systems(self) -> list:
        """Return all ATA chapters with basic info."""
        return [
            {'ata': k, 'system': v['system'], 'icon': v['icon'], 'color': v['color'],
             'failure_count': len(v['common_failures'])}
            for k, v in self.kb.items()
        ]


# Module-level singleton
_ai_instance = None


def get_ai() -> TroubleshootingAI:
    """Return the shared TroubleshootingAI instance (lazy init)."""
    global _ai_instance
    if _ai_instance is None:
        _ai_instance = TroubleshootingAI()
    return _ai_instance

