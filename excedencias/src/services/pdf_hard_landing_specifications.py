"""
Hard Landing Thresholds - Extracted from PDF MPP8725_05-50-03-200-801-A Rev 15
CONFORMIDADE AMM 05-50-03 FOR E190-E2 AND E195-E2
"""

from dataclasses import dataclass
from typing import List, Tuple

# ============================================================================
# E190-E2 SPECIFICATIONS
# ============================================================================

# Figure 605: E190-E2 Hard Landing - Roll Rate ≤ 8 DEG/S
# Source: Page 22 of MPP8725_05-50-03-06
VERT_ACCEL_THRESHOLD_E190E2_FIGURE605 = [
    # (Aircraft Mass in kg, NZ Threshold in G)
    # Based on table data extracted from PDF
    # Note: Exact values from visual table, may need OCR verification
    (34700, 2.30),   # From PDF extraction
    (40000, 2.30),   # From PDF extraction  
    (47000, 2.30),   # Interpolated
    (51850, 2.19),   # From PDF extraction
    (54000, 2.15),   # Interpolated from graph
]

# Figure 606: E190-E2 Hard Landing - Roll Rate > 8 DEG/S
# Source: Page 23 of MPP8725_05-50-03-06
VERT_ACCEL_THRESHOLD_E190E2_FIGURE606 = [
    # (Aircraft Mass in kg, NZ Threshold in G)
    # Values extracted from PDF - Roll rate > 8 deg/s condition
    # Full data extraction needed (graph analysis required)
    # Placeholder values pending complete extraction
    (34700, 1.95),   # From PDF text
    # Additional points need extraction from graph
]

# ============================================================================
# E195-E2 SPECIFICATIONS  
# ============================================================================

# Figure 607: E195-E2 Hard Landing - Roll Rate ≤ 2.5 DEG/S
# Source: Page 24 of MPP8725_05-50-03-06
VERT_ACCEL_THRESHOLD_E195E2_FIGURE607 = [
    # (Aircraft Mass in kg, NZ Threshold in G)
    (34700, 3.05),    # From PDF text extraction
    (40000, 2.86),    # From PDF text extraction
    (40900, 2.80),    # From PDF text extraction
    (47000, 2.71),    # From PDF text extraction
    (51850, 2.61),    # From PDF text extraction
    (54000, 2.57),    # From PDF text extraction
    (61500, 2.43),    # From PDF text extraction (61500 kg ≈ 135,579 lbs)
]

# Figure 608: E195-E2 Hard Landing - 2.5 DEG/S < Roll Rate < 7.5 DEG/S
# Source: Page 25 of MPP8725_05-50-03-06
VERT_ACCEL_THRESHOLD_E195E2_FIGURE608 = [
    # (Aircraft Mass in kg, NZ Threshold in G)
    (34700, 2.65),    # From PDF text extraction
    (40000, 2.65),    # From PDF text extraction
    (40900, 2.65),    # From PDF text extraction
    (47000, 2.65),    # From PDF text extraction
    (51850, 2.52),    # From PDF text extraction
    (54000, 2.42),    # From PDF text extraction
    (61500, 2.19),    # From PDF text extraction
]

# Figure 609: E195-E2 Hard Landing - Roll Rate > 7.5 DEG/S
# Source: Page 26 of MPP8725_05-50-03-06
VERT_ACCEL_THRESHOLD_E195E2_FIGURE609 = [
    # (Aircraft Mass in kg, NZ Threshold in G)
    (34700, 2.44),    # From PDF text extraction
    (40000, 2.38),    # From PDF text extraction
    (40900, 2.38),    # From PDF text extraction
    (47000, 2.31),    # From PDF text extraction
    (51850, 2.17),    # From PDF text extraction
    (54000, 2.10),    # From PDF text extraction
    (61500, 1.91),    # From PDF text extraction
]

# ============================================================================
# DATA COMPLETENESS STATUS
# ============================================================================

PDF_DATA_STATUS = {
    'E190-E2': {
        'Figure605_Roll<=8': {
            'status': 'INCOMPLETE',  # Only 5 points extracted, may have more
            'points_extracted': 5,
            'needs_validation': True,
            'notes': 'Values from table; graph area has additional interpolation points'
        },
        'Figure606_Roll>8': {
            'status': 'INCOMPLETE',  # Only 1 value extracted
            'points_extracted': 1,
            'needs_validation': True,
            'notes': 'Requires graph analysis for intermediate weight points'
        }
    },
    'E195-E2': {
        'Figure607_Roll<=2.5': {
            'status': 'COMPLETE',
            'points_extracted': 7,
            'needs_validation': False,
            'notes': 'Complete table extracted from PDF'
        },
        'Figure608_Roll2.5-7.5': {
            'status': 'COMPLETE', 
            'points_extracted': 7,
            'needs_validation': False,
            'notes': 'Complete table extracted from PDF'
        },
        'Figure609_Roll>7.5': {
            'status': 'COMPLETE',
            'points_extracted': 7,
            'needs_validation': False,
            'notes': 'Complete table extracted from PDF'
        }
    }
}

# ============================================================================
# COMPARISON: PDF vs CODE
# ============================================================================

"""
CURRENT CODE IMPLEMENTATION (hard_landing_analyzer.py lines 52-77):

VERT_ACCEL_THRESHOLDS = {
    'low': [
        (38000, 1.800), (40000, 1.850), (42000, 1.900),
        (44000, 1.950), (46000, 2.000), (48000, 2.050),
        (50000, 2.100), (52000, 2.150), (54000, 2.200)
    ],
    'high': [
        (38000, 2.100), (40000, 2.150), (42000, 2.200),
        (44000, 2.250), (46000, 2.300), (48000, 2.350),
        (50000, 2.400), (52000, 2.450), (54000, 2.500)
    ],
    'engine': [
        (38000, 2.400), (40000, 2.450), (42000, 2.500),
        (44000, 2.550), (46000, 2.600), (48000, 2.650),
        (50000, 2.700), (52000, 2.750), (54000, 2.800)
    ]
}

PROBLEMS IDENTIFIED:

1. WEIGHT UNITS: Code uses LBS (38000-54000 lbs), PDF uses KG (34700-61500 kg)
   - 38000 lbs ≈ 17,236 kg (CODE OUT OF RANGE)
   - 54000 lbs ≈ 24,494 kg (CODE OUT OF RANGE)
   - PDF range: 34.7k - 61.5k kg (much wider and different)

2. ROLL RATE DEPENDENCY: Code doesn't use roll rate, PDF requires it
   - PDF: Different thresholds for different roll rate ranges
   - Code: Only uses one 'low'/'high'/'engine' regardless of roll rate
   
3. THRESHOLD VALUES: For comparable weight, values differ significantly
   - Example at ~54 kg:
     * Code 'low': 2.200 G
     * Code 'high': 2.500 G
     * PDF E195-E2 Figure607 (Roll<=2.5): 2.57 G
     * PDF E195-E2 Figure609 (Roll>7.5): 2.10 G

4. NUMBER OF POINTS: Code has 9 points, PDF has 5-7 points
   - This suggests CODE might be using generic data, not PDF data

CONCLUSION: Code implementation is FUNDAMENTALLY INCORRECT for E190/E195
"""
