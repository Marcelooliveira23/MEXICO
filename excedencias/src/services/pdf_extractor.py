"""
Extrator de conteúdo e gráficos de PDFs técnicos
"""

import pdfplumber
try:
    import pypdf as PyPDF2
except ImportError:
    import PyPDF2
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image
import io


class PDFExtractor:
    """Extrai texto, tabelas e imagens de PDFs técnicos"""
    
    @staticmethod
    def extract_text(pdf_path: Path) -> str:
        """
        Extrai todo o texto do PDF
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            Texto completo do PDF
        """
        text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
        except Exception as e:
            print(f"Erro ao extrair texto de {pdf_path}: {e}")
        
        return text
    
    @staticmethod
    def extract_tables(pdf_path: Path) -> List[List[List[str]]]:
        """
        Extrai tabelas do PDF
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            Lista de tabelas, onde cada tabela é uma lista de linhas
        """
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
        except Exception as e:
            print(f"Erro ao extrair tabelas de {pdf_path}: {e}")
        
        return tables
    
    @staticmethod
    def extract_images(pdf_path: Path, output_dir: Optional[Path] = None) -> List[Path]:
        """
        Extrai imagens/gráficos do PDF
        
        Args:
            pdf_path: Caminho do PDF
            output_dir: Diretório para salvar imagens (None = não salvar)
            
        Returns:
            Lista de caminhos das imagens extraídas
        """
        images = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    
                    # Extrair imagens da página
                    if '/XObject' in page['/Resources']:
                        x_object = page['/Resources']['/XObject'].get_object()
                        
                        for obj_name in x_object:
                            obj = x_object[obj_name]
                            
                            if obj['/Subtype'] == '/Image':
                                # Extrair dados da imagem
                                if '/Filter' in obj:
                                    filter_type = obj['/Filter']
                                    
                                    if filter_type == '/DCTDecode':  # JPEG
                                        image_data = obj._data
                                        
                                        if output_dir:
                                            # Salvar imagem
                                            image_name = f"{pdf_path.stem}_page{page_num+1}_{obj_name[1:]}.jpg"
                                            image_path = output_dir / image_name
                                            
                                            with open(image_path, 'wb') as img_file:
                                                img_file.write(image_data)
                                            
                                            images.append(image_path)
                                    
                                    elif filter_type == '/FlateDecode':  # PNG
                                        try:
                                            # Converter para imagem
                                            size = (obj['/Width'], obj['/Height'])
                                            data = obj._data
                                            
                                            if '/ColorSpace' in obj:
                                                color_space = obj['/ColorSpace']
                                                
                                                if color_space == '/DeviceRGB':
                                                    mode = "RGB"
                                                elif color_space == '/DeviceGray':
                                                    mode = "L"
                                                else:
                                                    mode = "RGB"
                                                
                                                img = Image.frombytes(mode, size, data)
                                                
                                                if output_dir:
                                                    image_name = f"{pdf_path.stem}_page{page_num+1}_{obj_name[1:]}.png"
                                                    image_path = output_dir / image_name
                                                    img.save(image_path)
                                                    images.append(image_path)
                                        except Exception as e:
                                            print(f"Erro ao processar imagem FlateDecode: {e}")
                                            
        except Exception as e:
            print(f"Erro ao extrair imagens de {pdf_path}: {e}")
        
        return images
    
    @staticmethod
    def extract_rules_and_limits(pdf_path: Path) -> Dict[str, any]:
        """
        Extrai regras, limites e tolerâncias do PDF
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            Dicionário com regras extraídas
        """
        rules = {
            'limits': {},
            'tolerances': {},
            'conditions': [],
            'inspection_criteria': [],
            'raw_text': ''
        }
        
        try:
            text = PDFExtractor.extract_text(pdf_path)
            rules['raw_text'] = text
            
            # Procurar por padrões comuns em documentos técnicos
            lines = text.split('\n')
            
            for line in lines:
                line_lower = line.lower().strip()
                
                # Procurar limites numéricos
                if any(keyword in line_lower for keyword in ['limit', 'maximum', 'minimum', 'threshold']):
                    # Extrair números da linha
                    import re
                    numbers = re.findall(r'-?\d+\.?\d*', line)
                    if numbers:
                        rules['limits'][line.strip()] = numbers
                
                # Procurar tolerâncias
                if any(keyword in line_lower for keyword in ['tolerance', 'allowable', 'acceptable']):
                    rules['tolerances'][line.strip()] = line.strip()
                
                # Procurar condições
                if any(keyword in line_lower for keyword in ['if', 'when', 'condition', 'case']):
                    if len(line.strip()) > 10:  # Evitar linhas muito curtas
                        rules['conditions'].append(line.strip())
                
                # Procurar critérios de inspeção
                if any(keyword in line_lower for keyword in ['inspect', 'check', 'verify', 'examine']):
                    if len(line.strip()) > 10:
                        rules['inspection_criteria'].append(line.strip())
            
            # Extrair tabelas (podem conter regras estruturadas)
            tables = PDFExtractor.extract_tables(pdf_path)
            if tables:
                rules['tables'] = tables
            
        except Exception as e:
            print(f"Erro ao extrair regras de {pdf_path}: {e}")
        
        return rules
    
    @staticmethod
    def get_pdf_info(pdf_path: Path) -> Dict[str, any]:
        """
        Retorna informações gerais sobre o PDF
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            Dicionário com informações do PDF
        """
        info = {
            'filename': pdf_path.name,
            'size_bytes': pdf_path.stat().st_size,
            'size_kb': pdf_path.stat().st_size / 1024,
            'pages': 0,
            'has_images': False,
            'has_tables': False
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                info['pages'] = len(pdf.pages)
            
            # Verificar se há tabelas
            tables = PDFExtractor.extract_tables(pdf_path)
            info['has_tables'] = len(tables) > 0
            
            # Verificar se há imagens (simplificado)
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    if '/XObject' in page.get('/Resources', {}):
                        info['has_images'] = True
                        break
                        
        except Exception as e:
            print(f"Erro ao obter info de {pdf_path}: {e}")
        
        return info
    
    @staticmethod
    def create_summary(pdf_path: Path) -> str:
        """
        Cria um resumo do conteúdo do PDF
        
        Args:
            pdf_path: Caminho do PDF
            
        Returns:
            String com resumo
        """
        info = PDFExtractor.get_pdf_info(pdf_path)
        rules = PDFExtractor.extract_rules_and_limits(pdf_path)
        
        summary = f"""
📄 Documento: {info['filename']}
📊 Páginas: {info['pages']}
💾 Tamanho: {info['size_kb']:.1f} KB
🖼️ Contém imagens: {'Sim' if info['has_images'] else 'Não'}
📋 Contém tabelas: {'Sim' if info['has_tables'] else 'Não'}

📏 Limites encontrados: {len(rules['limits'])}
⚙️ Tolerâncias encontradas: {len(rules['tolerances'])}
✅ Condições encontradas: {len(rules['conditions'])}
🔍 Critérios de inspeção: {len(rules['inspection_criteria'])}
"""
        
        return summary.strip()
