"""
PDF Graphics Extractor
Extracts images, charts, and diagrams from PDF technical manuals
"""
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
import pdfplumber
from PIL import Image
import io
from utils.logger import logger


@dataclass
class PDFImage:
    """Represents an image extracted from PDF"""
    filename: str
    page: int
    width: int
    height: int
    format: str
    image_data: bytes
    pdf_source: str


class PDFGraphicsExtractor:
    """Extracts graphics from PDF manuals"""
    
    def __init__(self):
        """Initialize graphics extractor"""
        self.output_dir = Path("assets/pdf_graphics")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("PDFGraphicsExtractor initialized")
    
    def extract_images_from_pdf(self, pdf_path: Path) -> List[PDFImage]:
        """
        Extract all images from a PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PDFImage objects
        """
        images = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract images from page
                    if hasattr(page, 'images') and page.images:
                        for img_index, img in enumerate(page.images):
                            try:
                                # Get image properties
                                x0, y0, x1, y1 = img['x0'], img['top'], img['x1'], img['bottom']
                                width = int(x1 - x0)
                                height = int(y1 - y0)
                                
                                # Skip very small images (likely decorative)
                                if width < 100 or height < 100:
                                    continue
                                
                                # Extract image using pdfplumber
                                im = page.within_bbox((x0, y0, x1, y1)).to_image(resolution=150)
                                
                                # Convert to PIL Image
                                img_bytes = io.BytesIO()
                                im.original.save(img_bytes, format='PNG')
                                img_bytes.seek(0)
                                
                                # Create PDFImage object
                                filename = f"{pdf_path.stem}_page{page_num}_img{img_index+1}.png"
                                
                                pdf_image = PDFImage(
                                    filename=filename,
                                    page=page_num,
                                    width=width,
                                    height=height,
                                    format='PNG',
                                    image_data=img_bytes.getvalue(),
                                    pdf_source=pdf_path.name
                                )
                                
                                images.append(pdf_image)
                                logger.debug(f"Extracted image: {filename} ({width}x{height})")
                                
                            except Exception as e:
                                logger.warning(f"Failed to extract image {img_index} from page {page_num}: {e}")
                                continue
            
            logger.success(f"Extracted {len(images)} images from {pdf_path.name}")
            
        except Exception as e:
            logger.error(f"Error extracting images from {pdf_path}: {e}")
        
        return images
    
    def save_images(self, images: List[PDFImage], aircraft_family: str) -> List[Path]:
        """
        Save extracted images to disk
        
        Args:
            images: List of PDFImage objects
            aircraft_family: Aircraft family code
            
        Returns:
            List of paths to saved images
        """
        saved_paths = []
        family_dir = self.output_dir / aircraft_family.lower()
        family_dir.mkdir(parents=True, exist_ok=True)
        
        for image in images:
            try:
                output_path = family_dir / image.filename
                
                # Save image
                with open(output_path, 'wb') as f:
                    f.write(image.image_data)
                
                saved_paths.append(output_path)
                logger.debug(f"Saved image: {output_path}")
                
            except Exception as e:
                logger.error(f"Failed to save image {image.filename}: {e}")
        
        logger.success(f"Saved {len(saved_paths)} images for {aircraft_family}")
        return saved_paths
    
    def extract_all_graphics(self, aircraft_family: str) -> Dict[str, List[Path]]:
        """
        Extract all graphics for an aircraft family
        
        Args:
            aircraft_family: Aircraft family code (E145, E1, E2, E170)
            
        Returns:
            Dictionary mapping PDF names to lists of image paths
        """
        results = {}
        docs_dir = Path("docs/pdfs") / aircraft_family.lower()
        
        if not docs_dir.exists():
            logger.warning(f"PDF directory not found: {docs_dir}")
            return results
        
        for pdf_file in docs_dir.glob("*.pdf"):
            logger.info(f"Processing {pdf_file.name}...")
            
            # Extract images
            images = self.extract_images_from_pdf(pdf_file)
            
            # Save images
            if images:
                saved_paths = self.save_images(images, aircraft_family)
                results[pdf_file.name] = saved_paths
        
        total_images = sum(len(paths) for paths in results.values())
        logger.success(f"Extracted {total_images} total graphics for {aircraft_family}")
        
        return results
    
    def create_graphics_index(self, aircraft_family: str) -> str:
        """
        Create an index of extracted graphics
        
        Args:
            aircraft_family: Aircraft family code
            
        Returns:
            Markdown index content
        """
        graphics = self.extract_all_graphics(aircraft_family)
        
        index = f"# Graphics Index - {aircraft_family}\n\n"
        index += f"Total PDFs processed: {len(graphics)}\n"
        index += f"Total graphics extracted: {sum(len(paths) for paths in graphics.values())}\n\n"
        
        for pdf_name, image_paths in sorted(graphics.items()):
            index += f"## {pdf_name}\n\n"
            index += f"Images: {len(image_paths)}\n\n"
            
            for img_path in image_paths:
                index += f"- `{img_path.name}`\n"
            
            index += "\n"
        
        return index
    
    def filter_technical_diagrams(self, images: List[PDFImage], min_width: int = 300, min_height: int = 200) -> List[PDFImage]:
        """
        Filter images to keep only technical diagrams
        
        Args:
            images: List of PDFImage objects
            min_width: Minimum width for diagrams
            min_height: Minimum height for diagrams
            
        Returns:
            Filtered list of PDFImage objects
        """
        diagrams = []
        
        for image in images:
            # Filter by size (technical diagrams are usually larger)
            if image.width >= min_width and image.height >= min_height:
                diagrams.append(image)
        
        logger.info(f"Filtered {len(diagrams)} technical diagrams from {len(images)} total images")
        return diagrams
