"""
Parser de arquivos CSV/TXT para dados de inspeção
"""

import pandas as pd
from pathlib import Path
from typing import Optional, List
import chardet
from .csv_column_mapper import get_mapper


class CSVParser:
    """Parser para arquivos de dados de inspeção com mapeamento flexível de colunas"""
    
    COMMON_DELIMITERS = [',', ';', '\t', '|']
    
    def __init__(self):
        """Initialize CSV parser with column mapper"""
        self.column_mapper = get_mapper()
    
    @staticmethod
    def detect_encoding(file_path: Path) -> str:
        """
        Detecta o encoding do arquivo
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Nome do encoding detectado
        """
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
            return result['encoding'] or 'utf-8'
    
    def parse_file(self, file_path: Path, delimiter: Optional[str] = None) -> pd.DataFrame:
        """
        Parse arquivo CSV/TXT com mapeamento automático de colunas
        
        Args:
            file_path: Caminho do arquivo
            delimiter: Delimitador específico (None para auto-detectar)
            
        Returns:
            DataFrame com dados parseados e colunas mapeadas
            
        Raises:
            ValueError: Se não conseguir parsear o arquivo
        """
        # Garantir que file_path é Path object
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
        
        # Detectar encoding
        encoding = self.detect_encoding(file_path)
        
        df = None
        first_line = ""
        
        # Se arquivo vazio, retornar DataFrame vazio
        if file_path.stat().st_size == 0:
            return pd.DataFrame()

        # Capturar primeira linha para heuristica de delimitador
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                first_line = f.readline()
        except Exception:
            first_line = ""

        # Se delimitador especificado, usar diretamente
        if delimiter:
            try:
                df = pd.read_csv(
                    file_path, delimiter=delimiter, encoding=encoding,
                    low_memory=False, on_bad_lines='skip'
                )
                if len(df.columns) >= 1:
                    # Converter colunas numéricas
                    df = self._convert_numeric_columns(df)
                    # Map columns to standard names
                    df = self.column_mapper.map_columns(df)
                    return df
            except Exception as e:
                raise ValueError(f"Erro ao parsear com delimitador '{delimiter}': {str(e)}")
        
        # Auto-detectar delimitador
        for delim in self.COMMON_DELIMITERS:
            try:
                df = pd.read_csv(
                    file_path, delimiter=delim, encoding=encoding,
                    low_memory=False, on_bad_lines='skip'  # Evitar warnings de mixed types
                )
                if len(df.columns) > 1:
                    # Converter colunas numéricas
                    df = self._convert_numeric_columns(df)
                    # Map columns to standard names
                    df = self.column_mapper.map_columns(df)
                    return df
                if len(df.columns) == 1 and delim not in first_line:
                    continue
            except Exception:
                continue
        
        # Tentar sem delimitador específico (pandas auto-detecta)
        try:
            df = pd.read_csv(
                file_path, encoding=encoding, sep=None,
                engine='python', low_memory=False, on_bad_lines='skip'
            )
            if len(df.columns) >= 1:
                # Converter colunas numéricas
                df = self._convert_numeric_columns(df)
                # Map columns to standard names
                df = self.column_mapper.map_columns(df)
                return df
        except Exception:
            pass
        
        raise ValueError(f"Não foi possível parsear {file_path}. Formato não reconhecido.")
    
    @staticmethod
    def validate_columns(df: pd.DataFrame, required_columns: List[str]) -> tuple[bool, List[str]]:
        """
        Valida se o DataFrame contém as colunas necessárias
        
        Args:
            df: DataFrame a validar
            required_columns: Lista de nomes de colunas requeridas
            
        Returns:
            Tupla (valido, colunas_faltando)
        """
        missing = [col for col in required_columns if col not in df.columns]
        return len(missing) == 0, missing
    
    @staticmethod
    def get_file_info(file_path: Path) -> dict:
        """
        Retorna informações sobre o arquivo
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dicionário com informações do arquivo
        """
        try:
            parser = CSVParser()
            df = parser.parse_file(file_path)
            return {
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': df.columns.tolist(),
                'size_bytes': file_path.stat().st_size,
                'encoding': CSVParser.detect_encoding(file_path)
            }
        except Exception as e:
            return {
                'error': str(e)
            }
    
    @staticmethod
    def _convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Converte colunas para tipos numéricos quando possível
        
        Args:
            df: DataFrame a converter
            
        Returns:
            DataFrame com colunas convertidas
        """
        for col in df.columns:
            try:
                converted = pd.to_numeric(df[col], errors='coerce')
                # Manter conversao apenas se houver valores numericos
                if converted.notna().sum() > 0:
                    df[col] = converted
            except Exception:
                pass
        
        # Remover linhas completamente vazias (todas as colunas são NaN)
        df = df.dropna(how='all')
        
        # Reset index após limpeza
        df = df.reset_index(drop=True)
        
        return df
    
    @staticmethod
    def preview_data(file_path: Path, n_rows: int = 10) -> pd.DataFrame:
        """
        Retorna preview dos primeiros N registros
        
        Args:
            file_path: Caminho do arquivo
            n_rows: Número de linhas para preview
            
        Returns:
            DataFrame com preview dos dados
        """
        parser = CSVParser()
        df = parser.parse_file(file_path)
        return df.head(n_rows)
    
    @staticmethod
    def get_column_types(df: pd.DataFrame) -> dict:
        """
        Retorna os tipos de dados de cada coluna
        
        Args:
            df: DataFrame a analisar
            
        Returns:
            Dicionário com nome_coluna: tipo
        """
        return {col: str(dtype) for col, dtype in df.dtypes.items()}
