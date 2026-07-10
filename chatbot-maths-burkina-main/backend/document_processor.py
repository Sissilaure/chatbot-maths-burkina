"""Document Processor for math curriculum documents"""
import os
from pathlib import Path
from typing import Optional, List, Dict


class DocumentProcessor:
    """Process math curriculum documents for the knowledge base"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        
    def process_pdf(self, file_path: str, metadata: dict) -> Optional[dict]:
        """Extract text from a PDF file"""
        try:
            import PyPDF2
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            return {
                "text": text,
                "metadata": {
                    "source": file_path,
                    "type": "pdf",
                    **metadata
                }
            }
        except ImportError:
            print("PyPDF2 not installed, trying pypdf...")
            try:
                from pypdf import PdfReader
                text = ""
                with open(file_path, 'rb') as f:
                    reader = PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                
                return {
                    "text": text,
                    "metadata": {
                        "source": file_path,
                        "type": "pdf",
                        **metadata
                    }
                }
            except ImportError:
                print("No PDF library available")
                return None
        except Exception as e:
            print(f"Error processing PDF {file_path}: {e}")
            return None
    
    def process_docx(self, file_path: str, metadata: dict) -> Optional[dict]:
        """Extract text from a DOCX file"""
        try:
            import docx
            doc = docx.Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            
            return {
                "text": text,
                "metadata": {
                    "source": file_path,
                    "type": "docx",
                    **metadata
                }
            }
        except Exception as e:
            print(f"Error processing DOCX {file_path}: {e}")
            return None
    
    def process_txt(self, file_path: str, metadata: dict) -> Optional[dict]:
        """Extract text from a TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            return {
                "text": text,
                "metadata": {
                    "source": file_path,
                    "type": "txt",
                    **metadata
                }
            }
        except Exception as e:
            print(f"Error processing TXT {file_path}: {e}")
            return None
    
    def create_sample_documents(self) -> List[dict]:
        """Create sample curriculum documents"""
        samples = [
            {
                "text": """Le théorème de Pythagore est un résultat fondamental en géométrie.
                
Dans un triangle rectangle, le carré de la longueur de l'hypoténuse est égal à la somme des carrés des longueurs des deux autres côtés.

Si ABC est un triangle rectangle en A, alors BC² = AB² + AC²

Exemple : Si AB = 3 cm et AC = 4 cm, alors BC² = 3² + 4² = 9 + 16 = 25, donc BC = 5 cm.

Ce théorème permet de calculer la longueur d'un côté d'un triangle rectangle quand on connaît les deux autres.""",
                "metadata": {"type": "sample", "chapter": "Théorème de Pythagore", "class": "5ème"}
            },
            {
                "text": """Le théorème de Thalès permet de calculer des longueurs dans des configurations de triangles emboîtés ou coupés par une parallèle.

Si deux droites parallèles coupent deux sécantes, alors elles déterminent sur ces sécantes des segments proportionnels.

Dans un triangle ABC, si une droite parallèle à BC coupe AB en D et AC en E, alors :
AD/AB = AE/AC = DE/BC

Exemple : Si AD = 2 cm, AB = 6 cm et DE = 3 cm, trouver BC.""",
                "metadata": {"type": "sample", "chapter": "Théorème de Thalès", "class": "4ème"}
            },
            {
                "text": """Les fractions représentent une partie d'un tout.

Une fraction a/b représente a parts égales d'un tout divisé en b parts.

Opérations :
- Addition/Soustraction : Il faut le même dénominateur
- Multiplication : (a/b) × (c/d) = (a×c)/(b×d)
- Division : (a/b) ÷ (c/d) = (a×d)/(b×c)

Simplification : Diviser le numérateur et le dénominateur par leur PGCD.""",
                "metadata": {"type": "sample", "chapter": "Fractions", "class": "6ème"}
            }
        ]
        return samples