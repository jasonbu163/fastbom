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
from ezdxf import zoom, addons
from ezdxf.filemanagement import readfile, new
from ezdxf.bbox import extents
from ezdxf.math import Vec3


class DXFProcessor:
    """DXF文件处理器"""
    
    @staticmethod
    def process_dxf_file(file_path: Path, num: int, output_dir: Path) -> Tuple[bool, str]:
        """处理DXF文件：复制图层0中的模型指定次数"""
        
        try:
            # 读取DXF文件
            doc = readfile(str(file_path))
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
            
            # 插入文件名
            try:
                # 1. 获取当前所有实体的包围盒（Bounding Box），以确定插入位置
                # 如果不需要动态位置，可以直接设置固定坐标，如 (0, 0)
                from ezdxf.bbox import extents
                entity_extent = extents(layer_0_entities)
                
                if entity_extent.has_data:
                    # 获取左上角坐标 (min_x, max_y) 并向上偏移一点
                    insert_pos = (entity_extent.extmin.x, entity_extent.extmax.y + 10) 
                    text_height = 50 # 根据图纸比例调整文字高度
                else:
                    insert_pos = (0, 0)
                    text_height = 100

                # 2. 在图层 0 插入文件名
                file_name_to_insert = file_path.stem  # 获取不带后缀的文件名
                
                msp.add_text(
                    file_name_to_insert,
                    dxfattribs={
                        'layer': '0',
                        'height': text_height,
                        'color': 7,  # 白色/黑色
                    }
                ).set_placement(insert_pos) # 设置插入点

            except Exception as text_err:
                print(f"插入文字提示: {text_err}") # 插入文字失败不应中断主流程
            
            # 保存文件
            zoom.extents(msp)
            output_file = output_dir / f"processed_{file_path.name}"
            doc.saveas(str(output_file))
            
            # return True, f"✅ 成功处理 | 复制{copy_count}个实体 | 保存至: {output_file.name}"
            return True, f"✅ 成功处理 | 保存至: {output_file.name}"
            
        except Exception as e:
            return False, f"❌ 处理失败: {str(e)}"

    @staticmethod
    def merge_directory_to_dxf(input_dir: str):
        input_path = Path(input_dir)
        if not input_path.is_dir():
            print(f"❌ 错误: {input_dir} 不是有效的目录")
            return

        # 1. 创建新的目标 DXF 文件
        merged_doc = new()
        merged_msp = merged_doc.modelspace()
        
        # 获取目录下所有 dxf 文件
        dxf_files = list(input_path.glob("*.dxf"))
        if not dxf_files:
            print(f"⚠️ 文件夹内没有 DXF 文件")
            return

        current_x_offset = 0
        spacing = 50  # 每个模型之间的间距
        
        print(f"🚀 开始合并目录: {input_path.name}，共 {len(dxf_files)} 个文件")

        for dxf_file in dxf_files:
            try:
                # 2. 读取源文件
                source_doc = readfile(str(dxf_file))
                source_msp = source_doc.modelspace()
                
                # 3. 计算源文件的包围盒（确定大小）
                # 只获取图层 '0' 的实体，或根据需要修改
                entities = source_msp.query('*') 
                if not entities:
                    continue
                    
                bbox = extents(entities)
                if not bbox.has_data:
                    continue

                # 计算偏移量：将模型左下角对齐到 (current_x_offset, 0)
                offset = Vec3(current_x_offset - bbox.extmin.x, -bbox.extmin.y, 0)
                
                # 4. 插入文件名标注
                file_label = dxf_file.stem
                text_height = max((bbox.extmax.y - bbox.extmin.y) * 0.05, 5.0) # 动态字号
                merged_msp.add_text(
                    file_label, 
                    dxfattribs={'height': text_height, 'layer': '0'}
                ).set_placement((current_x_offset, bbox.extmax.y - bbox.extmin.y + text_height))

                # 5. 将实体复制并移动到新文件
                # importer 负责处理不同文件间的资源（如图层、线型）合并
                importer = addons.importer.Importer(source_doc, merged_doc)
                importer.import_entities(entities)
                
                # 移动刚刚导入的实体
                for entity in entities:
                    # 注意：importer 会保持原始引用，我们需要对导入后的实体进行位移
                    # 这里的逻辑简写了，实际上 ezdxf 的 importer 会返回新生成的实体
                    pass 
                
                # 更稳妥的办法：直接对目标位置进行矩阵变换
                for entity in merged_msp.query('*'):
                    # 这里需要区分哪些是刚进来的，建议用下面的简易版逻辑或 Block 形式
                    pass

                # --- 核心逻辑：使用矩阵平移整个模型 ---
                # 为了简单起见，我们直接在读取时处理或使用“块”
                # 以下是更推荐的“块插入”写法，能完美解决重叠和移动问题：
                
                block_name = dxf_file.stem.replace(" ", "_")
                new_block = merged_doc.blocks.new(name=block_name)
                importer.import_entities(entities, target_layout=new_block)
                importer.finalize()

                # 将块插入到指定位置
                merged_msp.add_blockref(block_name, (current_x_offset, 0))
                
                # 更新下一个模型的 X 轴偏移量
                current_x_offset += (bbox.extmax.x - bbox.extmin.x) + spacing

                print(f"✅ 已加入: {dxf_file.name}")

            except Exception as e:
                print(f"❌ 处理 {dxf_file.name} 失败: {e}")

        # 6. 保存最终文件
        output_file = input_path.parent / f"{input_path.name}.dxf"
        merged_doc.saveas(str(output_file))
        print(f"\n✨ 完成！合并后的文件保存在: {output_file}")


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
    
    async def run_classification(self, config: dict, progress: ui.linear_progress, log: ui.log):
        """执行分类任务 - 优化版：复制所有同名不同后缀的文件"""
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
            
            # 构建源文件字典：按文件名(不含扩展名)分组
            source_files_dict = {}
            for f in self.src_dir.rglob('*'):
                if f.is_file():
                    stem = f.stem  # 文件名（不含扩展名）
                    if stem not in source_files_dict:
                        source_files_dict[stem] = []
                    source_files_dict[stem].append(f)
            
            log.push(f"📁 源文件组数量: {len(source_files_dict)}")
            log.push(f"📁 总文件数量: {sum(len(files) for files in source_files_dict.values())}")
            
            if not source_files_dict:
                ui.notify("⚠️ 源文件目录为空", type='warning')
                return
            
            success_count = 0
            file_copy_count = 0
            skipped_count = 0
            total_rows = len(df)
            
            for idx in range(total_rows):
                row = df.iloc[idx]
                part_name = str(row.get(config['part'], '')).strip()
                material_raw = str(row.get(config['mat'], '')).strip()
                quantity = str(row.get(config['qty'], '1')).strip()
                
                # 跳过空行
                if not part_name or part_name == 'nan':
                    continue
                
                # 解析材料和厚度
                material, thickness = self.parse_material(material_raw)
                if not material or not thickness:
                    skipped_count += 1
                    log.push(f"⏭️ 跳过 [{part_name}] - 材料格式不符合要求")
                    continue
                
                # 查找匹配的文件（支持部分匹配）
                found_files = []
                for file_stem, file_list in source_files_dict.items():
                    if part_name in file_stem or file_stem in part_name:
                        found_files.extend(file_list)
                        break
                
                if found_files:
                    try:
                        dest_dir = self.out_dir / material / thickness
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        
                        qty_prefix = quantity if quantity != 'nan' else '1'
                        
                        # 复制所有同名不同后缀的文件
                        copied_files = []
                        for found_file in found_files:
                            new_name = f"({qty_prefix}){found_file.name}"
                            dest_file = dest_dir / new_name
                            
                            shutil.copy2(found_file, dest_file)
                            copied_files.append(found_file.name)
                            file_copy_count += 1
                        
                        success_count += 1
                        files_str = ", ".join(copied_files)
                        log.push(f"✅ [{success_count}] {part_name} → {material}/{thickness}/ ({len(copied_files)}个文件)")
                        log.push(f"    文件: {files_str}")
                        
                    except Exception as e:
                        log.push(f"❌ {part_name} - 复制失败: {str(e)}")
                else:
                    log.push(f"⚠️ 未找到文件: {part_name}")
                
                progress.set_value((idx + 1) / total_rows)
                if idx % 5 == 0:
                    await asyncio.sleep(0.01)
            
            log.push("\n" + "=" * 60)
            log.push(f"🎉 分类完成！")
            log.push(f"   ✅ 成功归档: {success_count} 组文件 (共 {file_copy_count} 个文件)")
            log.push(f"   ⏭️ 跳过: {skipped_count} 行 (材料格式不符)")
            log.push("=" * 60)
            
            ui.notify(f"🎉 分类完成！归档 {success_count} 组 {file_copy_count} 个文件", type='positive')
            self._open_folder(self.out_dir)
                
        except Exception as e:
            log.push(f"\n💥 执行出错: {str(e)}")
            ui.notify(f"❌ 执行失败", type='negative')
    
    async def process_dxf_files(self, config: dict, progress: ui.linear_progress, log: ui.log):
        """处理DXF文件（第四步）"""
        
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
                    config['part'] = '图号'
                    config['mat'] = '材料'
                    config['qty'] = '总数量'

            update_headers()

            with ui.grid(columns=3).classes('w-full gap-4'):
                ui.label(f'📋 零件号列 * {config['part']}').classes('w-full')
                ui.label(f'🔧 材质列 * {config['mat']}').classes('w-full')
                ui.label(f'🔢 数量列 * {config['qty']}').classes('w-full')
        
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

# ui.run(
#     title='BOM智能分类助手 + DXF处理器',
#     native=True,
#     window_size=(1000, 900),
#     favicon='🎯',
#     port=8765,
#     reload=False,
#     show=False
# )