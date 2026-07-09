"""
Mapeamento de PDFs técnicos por família e categoria de evento
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PDFDocument:
    """Representa um documento PDF técnico"""
    filename: str
    family: str  # e145, e1, e2, e170
    event_category: str  # hard_landing, gear_overspeed, etc.
    task_number: str  # Número da task (ex: 05-50-02)
    description: str
    

class PDFMapper:
    """Mapeia PDFs para famílias e categorias de eventos"""
    
    # Mapeamento de códigos de task para categorias de eventos
    TASK_TO_EVENT = {
        # Hard Landing
        '05-50-02': 'hard_landing',           # Hard Landing
        '05-50-03': 'hard_landing',           # Hard Landing (variação)

        # Maximum Operating Speed (VMO/MMO)
        '05-50-04': 'max_speed',              # Maximum Operating Speed
        '05-50-06': 'max_speed',              # Maximum Operating Speed

        # Flap/Slat Extended Speed
        '05-50-07': 'flap_overspeed',         # Flap/Slat Overspeed

        # Overweight Landing
        '05-50-09': 'overweight_landing',     # Overweight Landing
        '05-50-25': 'overweight_landing',     # Overweight Landing (variação)

        # Turbulence / Buffeting
        '05-50-10': 'turbulence',             # Severe Turbulence
        '05-50-28': 'turbulence',             # Turbulence / Maneuver

        # Landing Gear Overspeed
        '05-50-13': 'gear_overspeed',         # Landing Gear Down Overspeed
        '05-50-27': 'gear_overspeed',         # Landing Gear Overspeed

        # High Bank Angle
        '05-57-00': 'high_bank_angle',        # High Bank Angle
    }

    KEYWORD_TO_EVENT = {
        'hard landing': 'hard_landing',
        'hard_landing': 'hard_landing',
        'over g': 'over_g',
        'over-g': 'over_g',
        'overg': 'over_g',
        'turbulence': 'turbulence',
        'gust': 'turbulence',
        'maneuver': 'turbulence',
        'manoeuv': 'turbulence',
        'bank angle': 'high_bank_angle',
        'bank': 'high_bank_angle',
        'vmo': 'max_speed',
        'mmo': 'max_speed',
        'speed': 'max_speed',
        'flap': 'flap_overspeed',
        'slat': 'flap_overspeed',
        'overweight': 'overweight_landing',
        'gear': 'gear_overspeed',
    }
    
    # Descrições legíveis
    EVENT_DESCRIPTIONS = {
        'hard_landing': 'Hard Landing',
        'gear_overspeed': 'Landing Gear Down Overspeed',
        'temp_envelope': 'Off-Temperature Envelope Flight',
        'max_speed': 'Maximum Operating Speed (VMO/MMO)',
        'flap_overspeed': 'Maximum Flap/Slat Extended Speed',
        'overweight_landing': 'Overweight Landing',
        'turbulence': 'Turbulence Encounter',
        'over_g': 'Over-G Maneuver',
        'high_bank_angle': 'High Bank Angle',
    }

    EXPECTED_TASKS_BY_FAMILY = {
        'e145': {
            'hard_landing': ['05-50-02'],
            'flap_overspeed': ['05-50-07'],
            'gear_overspeed': ['05-50-13', '05-50-27'],
            'overweight_landing': ['05-50-25'],
            'max_speed': ['05-50-04', '05-50-06'],
            'turbulence': [],
        },
        'e170': {
            'hard_landing': ['05-50-03'],
            'flap_overspeed': ['05-50-07'],
            'gear_overspeed': ['05-50-13', '05-50-27'],
            'overweight_landing': ['05-50-09'],
            'max_speed': ['05-50-06'],
            'turbulence': ['05-50-28'],
        },
        'e1': {
            'hard_landing': ['05-50-03'],
            'flap_overspeed': ['05-50-07'],
            'gear_overspeed': ['05-50-13', '05-50-27'],
            'overweight_landing': ['05-50-09'],
            'max_speed': ['05-50-06'],
            'turbulence': ['05-50-28'],
        },
        'e2': {
            'hard_landing': ['05-50-03'],
            'flap_overspeed': ['05-50-07'],
            'gear_overspeed': ['05-50-13', '05-50-27'],
            'overweight_landing': ['05-50-09'],
            'max_speed': ['05-50-06'],
            'turbulence': ['05-50-10'],
        },
    }
    
    @staticmethod
    def get_family_from_path(pdf_path: Path) -> str:
        """Extrai família do caminho do PDF"""
        path_parts = pdf_path.parts
        for part in path_parts:
            part_lower = part.lower()
            if 'e145' in part_lower:
                return 'e145'
            elif part_lower == 'e1':
                return 'e1'
            elif part_lower == 'e2':
                return 'e2'
            elif 'e170' in part_lower:
                return 'e170'
        return 'unknown'
    
    @staticmethod
    def extract_task_number(filename: str) -> str:
        """Extrai número da task do nome do arquivo"""
        # Formato: MPP####_05-50-XX-...
        parts = filename.split('_')
        if len(parts) > 1:
            task_part = parts[1]
            # Pegar primeiros 3 segmentos (05-50-XX)
            task_segments = task_part.split('-')[:3]
            return '-'.join(task_segments)
        return 'unknown'
    
    @staticmethod
    def get_event_category(task_number: str) -> str:
        """Retorna categoria de evento baseada no número da task"""
        return PDFMapper.TASK_TO_EVENT.get(task_number, 'unknown')
    
    @staticmethod
    def map_pdf(pdf_path: Path) -> PDFDocument:
        """Mapeia um PDF para seu documento estruturado"""
        family = PDFMapper.get_family_from_path(pdf_path)
        filename = pdf_path.name
        task_number = PDFMapper.extract_task_number(filename)
        event_category = PDFMapper.get_event_category(task_number)
        if event_category == 'unknown':
            filename_lower = pdf_path.stem.lower()
            for keyword, mapped_event in PDFMapper.KEYWORD_TO_EVENT.items():
                if keyword in filename_lower:
                    event_category = mapped_event
                    break
        description = PDFMapper.EVENT_DESCRIPTIONS.get(
            event_category,
            f"Task {task_number}"
        )
        
        return PDFDocument(
            filename=filename,
            family=family,
            event_category=event_category,
            task_number=task_number,
            description=description
        )
    
    @staticmethod
    def scan_all_pdfs(base_path: Path) -> Dict[str, List[PDFDocument]]:
        """
        Escaneia todos os PDFs e organiza por família
        
        Returns:
            Dicionário com estrutura: {family: [PDFDocuments]}
        """
        pdfs_by_family = {
            'e145': [],
            'e1': [],
            'e2': [],
            'e170': []
        }
        
        # Escanear cada pasta de família
        for family_folder in ['E145', 'E1', 'E2', 'E170']:
            family_path = base_path / family_folder
            if family_path.exists():
                pdf_files = list(family_path.glob('*.PDF')) + list(family_path.glob('*.pdf'))
                for pdf_file in dict.fromkeys(pdf_files):
                    pdf_doc = PDFMapper.map_pdf(pdf_file)
                    family_key = pdf_doc.family
                    if family_key in pdfs_by_family:
                        pdfs_by_family[family_key].append(pdf_doc)
        
        return pdfs_by_family
    
    @staticmethod
    def get_pdfs_for_event(
        family: str,
        event_category: str,
        base_path: Path
    ) -> List[Path]:
        """
        Retorna lista de PDFs para uma família e categoria de evento
        específicas
        
        Args:
            family: ID da família (e145, e1, e2, e170)
            event_category: Categoria do evento
            base_path: Caminho base onde estão as pastas
            
        Returns:
            Lista de caminhos de PDFs relevantes
        """
        family_folder_map = {
            'e145': 'E145',
            'e1': 'E1',
            'e2': 'E2',
            'e170': 'E170'
        }
        
        folder_name = family_folder_map.get(family, '')
        if not folder_name:
            return []
        
        family_path = base_path / folder_name
        if not family_path.exists():
            return []
        
        matching_pdfs = []
        pdf_files = list(family_path.glob('*.PDF')) + list(family_path.glob('*.pdf'))
        for pdf_file in dict.fromkeys(pdf_files):
            pdf_doc = PDFMapper.map_pdf(pdf_file)
            if pdf_doc.event_category == event_category:
                matching_pdfs.append(pdf_file)
        
        return matching_pdfs

    @staticmethod
    def get_expected_tasks(family: str, event_category: str) -> List[str]:
        family_key = (family or "").lower()
        return PDFMapper.EXPECTED_TASKS_BY_FAMILY.get(family_key, {}).get(event_category, [])

    @staticmethod
    def get_missing_expected_tasks(
        family: str,
        event_category: str,
        base_path: Path
    ) -> List[str]:
        expected = PDFMapper.get_expected_tasks(family, event_category)
        if not expected:
            return []

        pdf_paths = PDFMapper.get_pdfs_for_event(family, event_category, base_path)
        found = {PDFMapper.extract_task_number(p.name) for p in pdf_paths}
        return [task for task in expected if task not in found]
