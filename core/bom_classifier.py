# core/bom_classifier.py

import re
import platform
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List
import pandas as pd


class BOMClassifier:
    """BOM分类器"""
    
    def __init__(self):
        self.project_dir: Optional[Path] = None
        self.bom_file: Optional[Path] = None
        self.result_dir: Optional[Path] = None
        self.classified_dir: Optional[Path] = None
        self.processed_dxf_dir: Optional[Path] = None
        self.merged_dir: Optional[Path] = None
        
        self.df: Optional[pd.DataFrame] = None
        self.headers: List[str] = []
        self.header_row: int = 0
    
    def set_project_dir(self, dir_path: str) -> bool:
        """设置项目目录（包含BOM表和SLDDRW文件）"""
        self.project_dir = Path(dir_path)
        if self.project_dir.exists():
            # 在项目目录下创建result目录
            self.result_dir = self.project_dir / "result"
            self.classified_dir = self.result_dir / "1_分类结果"
            self.processed_dxf_dir = self.result_dir / "2_DXF处理结果"
            self.merged_dir = self.result_dir / "3_合并文件"
            
            # 创建所有目录
            for directory in [self.result_dir, self.classified_dir, 
                            self.processed_dxf_dir, self.merged_dir]:
                directory.mkdir(exist_ok=True)
            
            return True
        return False
    
    def find_bom_files(self) -> List[Path]:
        """在项目目录中查找所有Excel文件"""
        if not self.project_dir:
            return []
        
        excel_files = []
        for ext in ['*.xlsx', '*.xls']:
            excel_files.extend(self.project_dir.glob(ext))
        
        return sorted(excel_files)
    
    def find_slddrw_files(self) -> List[Path]:
        """在项目目录中查找所有SLDDRW文件"""
        if not self.project_dir:
            return []
        
        slddrw_files = []
        for ext in ['*.SLDDRW', '*.slddrw']:
            slddrw_files.extend(self.project_dir.glob(ext))
        
        return sorted(slddrw_files)
    
    def set_bom_file(self, file_path: str) -> bool:
        """设置BOM文件"""
        self.bom_file = Path(file_path)
        return self.bom_file.exists()
    
    def detect_header_row(self, file_path: Path, max_rows: int = 20) -> Tuple[int, List[str]]:
        """智能检测表头所在行"""
        df_preview = pd.read_excel(file_path, header=None, nrows=max_rows)
        best_row = 0
        best_score = 0
        
        for i in range(min(max_rows, len(df_preview))):
            row = df_preview.iloc[i]
            score = 0
            valid_cols: List[str] = []
            
            for val in row:
                if pd.notna(val) and str(val).strip():
                    val_str = str(val).strip()
                    if not val_str.replace('.', '').replace('-', '').isdigit():
                        score += 1
                        valid_cols.append(val_str)
                    
                    keywords = ['名称', '材料', '材质', '厚度', '数量', '零件', '图号']
                    if any(kw in val_str.lower() for kw in keywords):
                        score += 5
            
            if score > best_score and len(valid_cols) >= 3:
                best_score = score
                best_row = i
        
        df = pd.read_excel(file_path, header=best_row, nrows=1)
        headers = [str(h) for h in df.columns if not str(h).startswith('Unnamed')]
        return best_row, headers
    
    def load_bom_headers(self) -> Tuple[bool, str]:
        """读取BOM并智能检测表头"""
        if not self.bom_file:
            return False, "请先选择BOM文件"
        
        try:
            self.header_row, self.headers = self.detect_header_row(self.bom_file)
            
            if not self.headers:
                return False, "未能识别有效表头"
            
            return True, f"成功加载: {self.bom_file.name} (表头在第 {self.header_row + 1} 行)"
        except Exception as e:
            return False, f"读取失败: {e}"
    
    def parse_material(self, material_str: str) -> Tuple[Optional[str], Optional[str]]:
        """解析材料字符串
        
        Args:
            material_str: 材料字符串，格式如 "铝板 T=2.0"
        
        Returns:
            (材料名称, 厚度) 或 (None, None)
        """
        if not material_str or pd.isna(material_str):
            return None, None
        
        material_str = str(material_str).strip()
        pattern = r'(.+?板)\s*T=(\d+(?:\.\d+)?)'
        match = re.search(pattern, material_str)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None, None
    
    def open_folder(self, path: Path) -> None:
        """跨平台打开文件夹"""
        system = platform.system()
        try:
            if system == 'Windows':
                import os
                os.startfile(str(path))
            elif system == 'Darwin':
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            print(f"无法打开文件夹: {e}")