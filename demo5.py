import os
import re
import shutil
import asyncio
import platform
from pathlib import Path
from typing import Optional, Tuple, List
import psutil

import pandas as pd
from nicegui import ui, app

# DXF处理模块
try:
    import ezdxf
    from ezdxf import zoom
    DXF_AVAILABLE = True
except ImportError:
    DXF_AVAILABLE = False


class DXFProcessor:
    """DXF文件处理器"""
    
    @staticmethod
    def process_dxf_file(file_path: Path, num: int, output_dir: Path) -> Tuple[bool, str]:
        """处理DXF文件：复制图层0中的模型指定次数"""
        if not DXF_AVAILABLE:
            return False, "❌ 未安装ezdxf库，请运行: pip install ezdxf"
        
        try:
            # 读取DXF文件
            doc = ezdxf.readfile(str(file_path))
            msp = doc.modelspace()
            
            # 检查图层0
            if '0' not in doc.layers:
                return False, "❌ 文件中不存在图层0"
            
            # 隐藏其他图层
            hidden_count = 0
            for layer in doc.layers:
                if layer.dxf.name != '0':
                    layer.off()
                    hidden_count += 1
            
            # 获取图层0实体
            layer_0_entities = [e for e in msp if e.dxf.layer == '0']
            if not layer_0_entities:
                return False, "❌ 图层0中没有实体"
            
            # 复制实体
            copy_count = 0
            base_offset = 100
            
            for i in range(1, num + 1):
                offset_x = i * base_offset
                offset_y = i * base_offset
                
                for entity in layer_0_entities:
                    try:
                        if entity.dxftype() == 'LINE':
                            msp.add_line(
                                start=(entity.dxf.start[0] + offset_x, entity.dxf.start[1] + offset_y),
                                end=(entity.dxf.end[0] + offset_x, entity.dxf.end[1] + offset_y),
                                dxfattribs={'layer': '0'}
                            )
                        elif entity.dxftype() == 'CIRCLE':
                            msp.add_circle(
                                center=(entity.dxf.center[0] + offset_x, entity.dxf.center[1] + offset_y),
                                radius=entity.dxf.radius,
                                dxfattribs={'layer': '0'}
                            )
                        elif entity.dxftype() == 'LWPOLYLINE':
                            points = [(p[0] + offset_x, p[1] + offset_y) for p in entity.get_points()]
                            msp.add_lwpolyline(points, dxfattribs={'layer': '0'})
                        elif entity.dxftype() == 'TEXT':
                            msp.add_text(
                                entity.dxf.text,
                                dxfattribs={
                                    'layer': '0',
                                    'insert': (entity.dxf.insert[0] + offset_x, entity.dxf.insert[1] + offset_y),
                                    'height': entity.dxf.height
                                }
                            )
                        else:
                            new_entity = entity.copy()
                            if hasattr(new_entity.dxf, 'insert'):
                                new_entity.dxf.insert = (
                                    new_entity.dxf.insert[0] + offset_x,
                                    new_entity.dxf.insert[1] + offset_y
                                )
                            msp.add_entity(new_entity)
                        
                        copy_count += 1
                    except Exception as e:
                        continue
            
            # 保存文件
            zoom.extents(msp)
            output_file = output_dir / f"processed_{file_path.name}"
            doc.saveas(str(output_file))
            
            return True, f"✅ 成功处理 | 复制{copy_count}个实体 | 保存至: {output_file.name}"
            
        except Exception as e:
            return False, f"❌ 处理失败: {str(e)}"


class BOMClassifier:
    def __init__(self):
        self.base_path = Path(os.getcwd())
        self.bom_dir = self.base_path / "1_放入BOM表"
        self.src_dir = self.base_path / "2_放入源文件"
        self.out_dir = self.base_path / "3_分类结果输出"
        self.dxf_dir = self.base_path / "4_DXF处理结果"
        
        self.df = None
        self.headers = []
        self.bom_file = None
        self.header_row = 0
        
    def init_folders(self):
        """创建基础目录"""
        for d in [self.bom_dir, self.src_dir, self.out_dir, self.dxf_dir]:
            d.mkdir(exist_ok=True)
        
        readme = self.base_path / "使用说明.txt"
        if not readme.exists():
            readme.write_text(
                """
=========================
BOM智能分类工具使用指南
=========================
1. 将BOM Excel表放入 '1_放入BOM表' 文件夹
2. 将所有源文件放入 '2_放入源文件' 文件夹
3. 分类结果将输出到 '3_分类结果输出' 文件夹
4. DXF处理结果将输出到 '4_DXF处理结果' 文件夹

# 注意事项：
- BOM表的材料列需包含类似 'A3板 T=10' 的格式
- 源文件名需与BOM表中的零件名称匹配
- DXF文件将根据BOM表中的数量自动复制
                """,
                encoding='utf-8'
            )
        
        ui.notify("✅ 工作目录已创建", type='positive')
        self._open_folder(self.base_path)
    
    def _open_folder(self, path: Path):
        """跨平台打开文件夹"""
        import subprocess
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(path) # type: ignore
            elif system == 'Darwin':
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            ui.notify(f"无法打开文件夹: {e}", type='warning')
    
    def detect_header_row(self, file_path: Path, max_rows: int = 20) -> Tuple[int, List[str]]:
        """智能检测表头所在行"""
        try:
            df_preview = pd.read_excel(file_path, header=None, nrows=max_rows)
            best_row = 0
            best_score = 0
            
            for i in range(min(max_rows, len(df_preview))):
                row = df_preview.iloc[i]
                score = 0
                valid_cols = []
                
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
            headers = [h for h in df.columns if not str(h).startswith('Unnamed')]
            return best_row, headers
            
        except Exception as e:
            raise Exception(f"表头检测失败: {str(e)}")
    
    def load_bom_headers(self):
        """读取BOM并智能检测表头"""
        files = list(self.bom_dir.glob("*.xlsx")) + list(self.bom_dir.glob("*.xls"))
        if not files:
            ui.notify("⚠️ 未找到Excel文件", type='warning')
            return False
        
        try:
            self.bom_file = files[0]
            self.header_row, self.headers = self.detect_header_row(self.bom_file)
            
            if not self.headers:
                ui.notify("⚠️ 未能识别有效表头", type='warning')
                return False
            
            ui.notify(
                f"✅ 成功加载: {self.bom_file.name} (表头在第 {self.header_row + 1} 行)",
                type='positive'
            )
            return True
            
        except Exception as e:
            ui.notify(f"❌ 读取失败: {e}", type='negative')
            return False
    
    def parse_material(self, material_str: str) -> Tuple[Optional[str], Optional[str]]:
        """解析材料字符串"""
        if not material_str or pd.isna(material_str):
            return None, None
        
        material_str = str(material_str).strip()
        pattern = r'(.+?板)\s*T=(\d+(?:\.\d+)?)'
        match = re.search(pattern, material_str)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None, None
    
    async def run_classification(self, config, progress, log):
        """执行分类任务"""
        if not self.bom_file:
            ui.notify("❌ 请先加载BOM表头", type='negative')
            return
        
        required_fields = ['part', 'mat', 'qty']
        missing = [f for f in required_fields if not config.get(f)]
        if missing:
            ui.notify(f"⚠️ 请配置必填列", type='warning')
            return
        
        log.clear()
        log.push("🚀 开始执行分类任务...")
        progress.set_value(0)
        
        try:
            df = pd.read_excel(self.bom_file, header=self.header_row).fillna('')
            df = df.dropna(how='all')
            
            source_files = {f.name: f for f in self.src_dir.rglob('*') if f.is_file()}
            log.push(f"📁 源文件数量: {len(source_files)}")
            
            if not source_files:
                ui.notify("⚠️ 源文件目录为空", type='warning')
                return
            
            success_count = 0
            total_rows = len(df)
            
            for idx in range(total_rows):
                row = df.iloc[idx]
                part_name = str(row.get(config['part'], '')).strip()
                material_raw = str(row.get(config['mat'], '')).strip()
                quantity = str(row.get(config['qty'], '1')).strip()
                
                if not part_name or part_name == 'nan':
                    continue
                
                material, thickness = self.parse_material(material_raw)
                if not material:
                    material = material_raw if material_raw != 'nan' else "未分类材质"
                if not thickness:
                    thickness = "未知厚度"
                
                found_file = None
                for filename, filepath in source_files.items():
                    if part_name in filename:
                        found_file = filepath
                        break
                
                if found_file:
                    try:
                        dest_dir = self.out_dir / material / thickness
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        
                        qty_prefix = quantity if quantity != 'nan' else '1'
                        new_name = f"({qty_prefix}){found_file.name}"
                        dest_file = dest_dir / new_name
                        
                        shutil.copy2(found_file, dest_file)
                        success_count += 1
                        log.push(f"✅ [{success_count}] {part_name} → {material}/{thickness}/")
                        
                    except Exception as e:
                        log.push(f"❌ {part_name} - 复制失败: {str(e)}")
                
                progress.set_value((idx + 1) / total_rows)
                if idx % 5 == 0:
                    await asyncio.sleep(0.01)
            
            log.push("\n" + "=" * 60)
            log.push(f"🎉 分类完成！成功归档: {success_count} 个文件")
            log.push("=" * 60)
            
            ui.notify(f"🎉 分类完成！", type='positive')
            self._open_folder(self.out_dir)
                
        except Exception as e:
            log.push(f"\n💥 执行出错: {str(e)}")
            ui.notify(f"❌ 执行失败", type='negative')
    
    async def process_dxf_files(self, config, progress, log):
        """处理DXF文件（第四步）"""
        if not DXF_AVAILABLE:
            ui.notify("❌ 请先安装ezdxf: pip install ezdxf", type='negative')
            return
        
        if not self.bom_file:
            ui.notify("❌ 请先加载BOM表", type='negative')
            return
        
        log.clear()
        log.push("🎨 开始处理DXF文件...")
        progress.set_value(0)
        
        try:
            df = pd.read_excel(self.bom_file, header=self.header_row).fillna('')
            df = df.dropna(how='all')
            
            # 清空并重建输出目录
            if self.dxf_dir.exists():
                shutil.rmtree(self.dxf_dir)
            self.dxf_dir.mkdir()
            
            dxf_files = list(self.out_dir.rglob("*.dxf"))
            log.push(f"📐 找到 {len(dxf_files)} 个DXF文件")
            
            if not dxf_files:
                ui.notify("⚠️ 未找到DXF文件", type='warning')
                return
            
            success_count = 0
            processor = DXFProcessor()
            
            for idx, dxf_file in enumerate(dxf_files):
                # 从文件名提取数量 (2)filename.dxf
                match = re.search(r'\((\d+)\)', dxf_file.name)
                quantity = int(match.group(1)) if match else 1
                
                log.push(f"\n处理: {dxf_file.name} (数量: {quantity})")
                
                # 创建对应的输出目录
                rel_path = dxf_file.parent.relative_to(self.out_dir)
                output_dir = self.dxf_dir / rel_path
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # 处理DXF
                success, msg = processor.process_dxf_file(dxf_file, quantity, output_dir)
                log.push(msg)
                
                if success:
                    success_count += 1
                
                progress.set_value((idx + 1) / len(dxf_files))
                await asyncio.sleep(0.01)
            
            log.push("\n" + "=" * 60)
            log.push(f"🎉 DXF处理完成！成功: {success_count}/{len(dxf_files)}")
            log.push(f"📂 结果保存在: {self.dxf_dir.name}")
            log.push("=" * 60)
            
            ui.notify("🎉 DXF处理完成！", type='positive')
            self._open_folder(self.dxf_dir)
            
        except Exception as e:
            log.push(f"\n💥 处理出错: {str(e)}")
            ui.notify(f"❌ 处理失败", type='negative')


classifier = BOMClassifier()


@ui.page('/')
def main_page():
    ui.query('body').style('background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)')
    config = {'part': '', 'mat': '', 'mat_backup': '', 'thk': '', 'qty': ''}
    
    with ui.column().classes('w-full max-w-5xl mx-auto p-8 gap-6'):
        # 标题
        with ui.card().classes('w-full p-6 bg-white shadow-2xl'):
            ui.label('🎯 BOM智能分类助手 + DXF处理器').classes('text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600')
            ui.label('自动分类 · 智能复制DXF · 一站式工程文件管理').classes('text-gray-600 text-lg mt-2')
        
        # 第一步：初始化
        with ui.card().classes('w-full p-6 bg-white shadow-xl'):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('folder_open', size='2.5rem').classes('text-blue-600')
                ui.label('第一步：准备工作目录').classes('text-2xl font-bold')
            
            ui.button(
                '生成工作目录并打开',
                on_click=classifier.init_folders,
                icon='create_new_folder'
            ).props('size=lg color=blue-6').classes('w-full')
        
        # 第二步：配置列映射
        with ui.card().classes('w-full p-6 bg-white shadow-xl'):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('settings', size='2.5rem').classes('text-orange-600')
                ui.label('第二步：智能识别表头').classes('text-2xl font-bold')
            
            def update_headers():
                if classifier.load_bom_headers():
                    header_info.text = f"✨ 检测到表头在第 {classifier.header_row + 1} 行"
                    sel_part.options = classifier.headers
                    sel_mat.options = classifier.headers
                    sel_qty.options = classifier.headers
                    
                    for h in classifier.headers:
                        h_lower = h.lower()
                        if any(kw in h_lower for kw in ['物料', '零件', '名称', 'part']):
                            sel_part.value = h
                            config['part'] = h
                        if any(kw in h_lower for kw in ['材料', '材质', 'material']):
                            sel_mat.value = h
                            config['mat'] = h
                        if any(kw in h_lower for kw in ['数量', 'qty', 'quantity']):
                            sel_qty.value = h
                            config['qty'] = h
            
            ui.button('🔍 智能加载BOM表头', on_click=update_headers, icon='refresh').props('size=md color=orange-6').classes('w-full')
            header_info = ui.label('').classes('text-sm text-gray-500')
            
            ui.separator().classes('my-4')
            with ui.grid(columns=3).classes('w-full gap-4'):
                sel_part = ui.select(label='📋 零件号列 *', options=[]).classes('w-full').bind_value(config, 'part')
                sel_mat = ui.select(label='🔧 材质列 *', options=[]).classes('w-full').bind_value(config, 'mat')
                sel_qty = ui.select(label='🔢 数量列 *', options=[]).classes('w-full').bind_value(config, 'qty')
        
        # 第三步：执行分类
        with ui.card().classes('w-full p-6 bg-white shadow-xl'):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('folder_copy', size='2.5rem').classes('text-green-600')
                ui.label('第三步：文件分类归档').classes('text-2xl font-bold')
            
            ui.button(
                '🚀 开始文件分类',
                on_click=lambda: classifier.run_classification(config, progress1, log1),
                icon='play_arrow'
            ).props('size=xl color=green-6').classes('w-full h-16 text-xl')
            
            progress1 = ui.linear_progress(value=0).classes('w-full mt-4')
            log1 = ui.log(max_lines=200).classes('w-full h-64 bg-gray-900 text-green-400 font-mono p-4')
        
        # 第四步：DXF处理
        with ui.card().classes('w-full p-6 bg-white shadow-xl border-t-4 border-purple-500'):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('architecture', size='2.5rem').classes('text-purple-600')
                ui.label('第四步：DXF智能复制').classes('text-2xl font-bold')
            
            if not DXF_AVAILABLE:
                ui.label('⚠️ 未安装ezdxf库，请运行: pip install ezdxf').classes('text-red-600 mb-2')
            
            ui.markdown(
                """
**功能说明：**
- 自动扫描第三步输出的所有DXF文件
- 根据BOM表中的数量进行智能复制
- 文件名中的数量标记 `(2)` 将决定复制次数
- 保持原有的文件夹结构
                """
            ).classes('text-sm text-gray-600 mb-4')
            
            ui.button(
                '🎨 开始处理DXF文件',
                on_click=lambda: classifier.process_dxf_files(config, progress2, log2),
                icon='content_copy'
            ).props('size=xl color=purple-6').classes('w-full h-16 text-xl')
            
            progress2 = ui.linear_progress(value=0).classes('w-full mt-4')
            log2 = ui.log(max_lines=200).classes('w-full h-64 bg-gray-900 text-purple-400 font-mono p-4')


def handle_shutdown():
    current_os = platform.system()
    if current_os == 'Windows':
        try:
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)
            for child in children:
                child.terminate()
            psutil.wait_procs(children, timeout=3)
            os._exit(0)
        except:
            os._exit(0)

app.on_shutdown(handle_shutdown)

ui.run(
    title='BOM智能分类助手 + DXF处理器',
    native=True,
    window_size=(1000, 900),
    favicon='🎯',
    port=8765,
    reload=False,
    show=False
)