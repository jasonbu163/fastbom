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


class BOMClassifier:
    def __init__(self):
        self.base_path = Path(os.getcwd())
        self.bom_dir = self.base_path / "1_放入BOM表"
        self.src_dir = self.base_path / "2_放入源文件"
        self.out_dir = self.base_path / "3_分类结果输出"
        
        self.df = None
        self.headers = []
        self.bom_file = None
        self.header_row = 0  # 表头所在行号
        
    def init_folders(self):
        """创建基础目录并打开"""
        for d in [self.bom_dir, self.src_dir, self.out_dir]:
            d.mkdir(exist_ok=True)
        
        # 创建说明文件
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
                
                # 注意事项：
                - BOM表的材料列需包含类似 'A3板 T=10' 的格式
                - 源文件名需与BOM表中的零件名称匹配
                - 支持模糊匹配，只要文件名包含零件名即可
                - 表头不在第一行？工具会自动识别！
                """,
                encoding='utf-8'
            )
        
        ui.notify("✅ 工作目录已创建", type='positive')
        
        # 打开文件夹（跨平台）
        self._open_folder(self.base_path)
    
    def _open_folder(self, path: Path):
        """跨平台打开文件夹"""
        import platform
        import subprocess
        
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(path)  # type: ignore
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', str(path)])
            else:  # Linux
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            ui.notify(f"无法打开文件夹: {e}", type='warning')
    
    def detect_header_row(self, file_path: Path, max_rows: int = 20) -> Tuple[int, List[str]]:
        """
        智能检测表头所在行
        策略：找到第一行包含多个有效列名（非空、非纯数字）的行
        """
        try:
            # 读取前N行来寻找表头
            df_preview = pd.read_excel(file_path, header=None, nrows=max_rows)
            
            best_row = 0
            best_score = 0
            
            for i in range(min(max_rows, len(df_preview))):
                row = df_preview.iloc[i]
                
                # 计算该行作为表头的得分
                score = 0
                valid_cols = []
                
                for val in row:
                    if pd.notna(val) and str(val).strip():
                        val_str = str(val).strip()
                        
                        # 不是纯数字
                        if not val_str.replace('.', '').replace('-', '').isdigit():
                            score += 1
                            valid_cols.append(val_str)
                        
                        # 包含关键字（加分项）
                        keywords = ['名称', '材料', '材质', '厚度', '数量', '零件', '图号', 
                                   'name', 'material', 'thickness', 'qty', 'quantity', 'part']
                        if any(kw in val_str.lower() for kw in keywords):
                            score += 5
                
                # 更新最佳行
                if score > best_score and len(valid_cols) >= 3:  # 至少3个有效列
                    best_score = score
                    best_row = i
            
            # 用检测到的行号重新读取
            df = pd.read_excel(file_path, header=best_row, nrows=1)
            headers = df.columns.tolist()
            
            # 过滤掉 Unnamed 列
            headers = [h for h in headers if not str(h).startswith('Unnamed')]
            
            return best_row, headers
            
        except Exception as e:
            raise Exception(f"表头检测失败: {str(e)}")
    
    def load_bom_headers(self):
        """读取BOM并智能检测表头"""
        files = list(self.bom_dir.glob("*.xlsx")) + list(self.bom_dir.glob("*.xls"))
        if not files:
            ui.notify("⚠️ 未找到Excel文件，请先放入BOM表", type='warning')
            return False
        
        try:
            self.bom_file = files[0]
            
            # 智能检测表头位置
            self.header_row, self.headers = self.detect_header_row(self.bom_file)
            
            if not self.headers:
                ui.notify("⚠️ 未能识别有效表头，请检查Excel格式", type='warning')
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
        """解析材料字符串，提取材质和厚度"""
        if not material_str or pd.isna(material_str):
            return None, None
        
        material_str = str(material_str).strip()
        
        # 匹配 "XX板 T=数字" 或 "XX板T=数字"
        pattern = r'(.+?板)\s*T=(\d+(?:\.\d+)?)'
        match = re.search(pattern, material_str)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        
        return None, None
    
    async def run_classification(self, config, progress, log):
        """执行整理逻辑"""
        if not self.bom_file:
            ui.notify("❌ 请先加载BOM表头", type='negative')
            return
        
        # 检查必填列（厚度列是可选的）
        required_fields = ['part', 'mat', 'qty']
        missing_fields = [f for f in required_fields if not config.get(f)]
        
        if missing_fields:
            field_names = {'part': '零件号列', 'mat': '材质列', 'qty': '数量列'}
            missing_names = [field_names[f] for f in missing_fields]
            ui.notify(f"⚠️ 请配置: {', '.join(missing_names)}", type='warning')
            return
        
        log.clear()
        log.push("🚀 开始执行分类任务...")
        log.push(f"📄 BOM文件: {self.bom_file.name}")
        log.push(f"📍 表头位置: 第 {self.header_row + 1} 行")
        progress.set_value(0)
        
        try:
            # 用检测到的表头行读取完整数据
            df = pd.read_excel(self.bom_file, header=self.header_row).fillna('')
            
            # 过滤掉所有列都为空的行
            df = df.dropna(how='all')
            
            log.push(f"📊 有效数据行数: {len(df)}")
            
            # 获取所有源文件
            source_files = {f.name: f for f in self.src_dir.rglob('*') if f.is_file()}
            log.push(f"📁 源文件数量: {len(source_files)}")
            
            if not source_files:
                ui.notify("⚠️ 源文件目录为空", type='warning')
                log.push("⚠️ 请在 '2_放入源文件' 文件夹中添加文件")
                return
            
            success_count = 0
            missing_count = 0
            error_count = 0
            
            total_rows = len(df)
            processed = 0
            
            for idx in range(total_rows):
                row = df.iloc[idx]
                
                # 获取各列数据
                part_name = str(row.get(config['part'], '')).strip()
                material_raw = str(row.get(config['mat'], '')).strip()
                material_backup = str(row.get(config.get('mat_backup', ''), '')).strip()  # 材质备用列
                thickness_backup = str(row.get(config.get('thk', ''), '')).strip()  # 厚度备用列
                quantity = str(row.get(config['qty'], '1')).strip()
                
                # 跳过空行
                if not part_name or part_name == 'nan':
                    continue
                
                # 解析材质和厚度（从材质列）
                material, thickness = self.parse_material(material_raw)
                
                # 材质备用逻辑
                if not material:
                    # 无法从材质列解析材质，使用备用列
                    if material_backup and material_backup != 'nan':
                        material = material_backup
                        log.push(f"💡 [{part_name}] 使用材质备用列: {material}")
                    elif material_raw and material_raw != 'nan':
                        # 如果没有备用列，使用材质列原始值
                        material = material_raw
                    else:
                        material = "未分类材质"
                
                # 厚度备用逻辑
                if not thickness:
                    # 无法从材质列解析厚度，使用备用列
                    if thickness_backup and thickness_backup != 'nan':
                        thickness = thickness_backup
                        log.push(f"💡 [{part_name}] 使用厚度备用列: {thickness}")
                    else:
                        thickness = "未知厚度"
                
                # 模糊匹配源文件
                found_file = None
                for filename, filepath in source_files.items():
                    if part_name in filename:
                        found_file = filepath
                        break
                
                if found_file:
                    try:
                        # 创建目标目录
                        dest_dir = self.out_dir / material / thickness
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 生成新文件名: (数量)原文件名
                        qty_prefix = quantity if quantity and quantity != 'nan' else '1'
                        new_name = f"({qty_prefix}){found_file.name}"
                        dest_file = dest_dir / new_name
                        
                        # 复制文件
                        shutil.copy2(found_file, dest_file)
                        success_count += 1
                        log.push(f"✅ [{success_count}] {part_name} → {material}/{thickness}/")
                        
                    except Exception as e:
                        error_count += 1
                        log.push(f"❌ {part_name} - 复制失败: {str(e)}")
                else:
                    missing_count += 1
                    log.push(f"⚠️ {part_name} - 未找到匹配文件")
                
                # 更新进度
                processed += 1
                progress.set_value(processed / total_rows)
                
                # 定期让出控制权，保持UI响应
                if processed % 5 == 0:
                    await asyncio.sleep(0.01)
            
            # 完成统计
            log.push("\n" + "=" * 60)
            log.push(f"🎉 分类完成！")
            log.push(f"✅ 成功归档: {success_count} 个文件")
            log.push(f"⚠️ 未找到源文件: {missing_count} 个")
            log.push(f"❌ 复制出错: {error_count} 个")
            log.push(f"📂 结果保存在: {self.out_dir.name}")
            log.push("=" * 60)
            
            ui.notify(f"🎉 分类完成！成功 {success_count} 个", type='positive')
            
            # 自动打开结果目录
            self._open_folder(self.out_dir)
                
        except Exception as e:
            log.push(f"\n💥 执行出错: {str(e)}")
            ui.notify(f"❌ 执行失败: {str(e)}", type='negative')


# 创建分类器实例
classifier = BOMClassifier()


@ui.page('/')
def main_page():
    # 背景样式
    ui.query('body').style('background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)')
    
    # 配置存储（增加材质备用列）
    config = {'part': '', 'mat': '', 'mat_backup': '', 'thk': '', 'qty': ''}
    
    with ui.column().classes('w-full max-w-5xl mx-auto p-8 gap-6'):
        # 标题区
        with ui.card().classes('w-full p-6 bg-white shadow-2xl'):
            ui.label('🎯 BOM智能分类助手').classes('text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600')
            ui.label('自动识别表头位置 · 智能解析材质厚度 · 快速归档工程文件').classes('text-gray-600 text-lg mt-2')
        
        # ========== 第一步：初始化目录 ==========
        with ui.card().classes('w-full p-6 bg-white shadow-xl'):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('folder_open', size='2.5rem').classes('text-blue-600')
                ui.label('第一步：准备工作目录').classes('text-2xl font-bold text-gray-800')
            
            ui.markdown(
                """
                点击下方按钮将自动创建3个文件夹：

                - **1_放入BOM表**：放入Excel格式的BOM表

                - **2_放入源文件**：放入所有需要分类的工程文件

                - **3_分类结果输出**：自动生成的分类结果
                """
            ).classes('text-gray-700 mb-4')
            
            ui.button(
                '生成工作目录并打开',
                on_click=classifier.init_folders,
                icon='create_new_folder'
            ).props('size=lg color=blue-6 no-caps').classes('w-full')
        
        # ========== 第二步：配置列映射 ==========
        with ui.card().classes('w-full p-6 bg-white shadow-xl'):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('settings', size='2.5rem').classes('text-orange-600')
                ui.label('第二步：智能识别表头').classes('text-2xl font-bold text-gray-800')
            
            with ui.row().classes('w-full items-center gap-2 mb-4'):
                ui.icon('auto_awesome', size='sm').classes('text-orange-500')
                ui.label('将BOM表放入文件夹1后，点击按钮自动识别表头位置').classes('text-gray-600')

            # 加载按钮
            def update_headers():
                if classifier.load_bom_headers():
                    # 显示表头行号
                    header_info.text = f"✨ 检测到表头在第 {classifier.header_row + 1} 行，共识别 {len(classifier.headers)} 列"
                    header_info.classes('text-sm text-green-600 font-semibold')
                    
                    # 更新所有下拉框选项
                    sel_part.options = classifier.headers
                    sel_mat.options = classifier.headers
                    sel_qty.options = classifier.headers
                    sel_mat_backup.options = classifier.headers
                    sel_thk.options = classifier.headers
                    
                    # 智能匹配列名
                    for h in classifier.headers:
                        h_lower = h.lower()
                        
                        # 零件列
                        if any(kw in h_lower for kw in ['物料', '物料描述', '零件', '图号', '名称', 'part', 'name', '部件']):
                            sel_part.value = h
                            config['part'] = h
                        
                        # 材质列（优先匹配包含"材"的列）
                        if any(kw in h_lower for kw in ['材料', '材质', 'material', '材']):
                            sel_mat.value = h
                            config['mat'] = h
                        
                        # 数量列
                        if any(kw in h_lower for kw in ['数量', '总数量', 'qty', 'quantity', '个数', '件数']):
                            sel_qty.value = h
                            config['qty'] = h
                        
                        # 厚度备用列
                        if any(kw in h_lower for kw in ['规格', '厚度', '厚', 'thickness', 't=']):
                            sel_thk.value = h
                            config['thk'] = h

                        # 材质备用列
                        if any(kw in h_lower for kw in ['名称', '材料', '材质', 'material', '材']):
                            sel_mat_backup.value = h
                            config['mat_backup'] = h
                    
                    ui.notify("🎯 列映射已自动匹配，请检查是否正确", type='info')

            with ui.row().classes('w-full gap-2'):
                ui.button(
                    '🔍 智能加载BOM表头',
                    on_click=update_headers,
                    icon='refresh'
                ).props('size=md color=orange-6 no-caps').classes('flex-grow')
                
                # 手动指定表头行（高级选项）
                with ui.dialog() as manual_dialog, ui.card().classes('p-6'):
                    ui.label('手动指定表头行号').classes('text-xl font-bold mb-4')
                    row_input = ui.number('表头行号（从1开始）', value=1, min=1, max=50).classes('w-64')
                    
                    def manual_load():
                        try:
                            classifier.header_row = int(row_input.value) - 1
                            df = pd.read_excel(classifier.bom_file, header=classifier.header_row, nrows=1)
                            classifier.headers = [h for h in df.columns if not str(h).startswith('Unnamed')]
                            update_headers()
                            manual_dialog.close()
                        except Exception as e:
                            ui.notify(f"加载失败: {e}", type='negative')
                    
                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('取消', on_click=manual_dialog.close).props('flat')
                        ui.button('确定', on_click=manual_load).props('color=primary')
                
                ui.button(
                    '手动指定',
                    on_click=manual_dialog.open,
                    icon='edit'
                ).props('flat size=md')
            
            # 表头行号显示
            header_info = ui.label('').classes('text-sm text-gray-500 mb-2')
            
            # 先定义所有下拉框（在定义 update_headers 函数之前）
            ui.separator().classes('my-4')
            ui.label('配置列映射关系：').classes('text-sm font-semibold text-gray-700 mb-2')
            ui.markdown('💡 **提示**：材质列应包含完整信息如"Q345板 T=10"，程序会自动拆分出材质和厚度。如果拆分失败，会使用备用列。').classes('text-xs text-gray-500 mb-3')
            
            with ui.grid(columns=2).classes('w-full gap-4'):
                sel_part = ui.select(
                    label='📋 零件号列 *',
                    options=[],
                    with_input=True
                ).classes('w-full').bind_value(config, 'part')
                
                sel_mat = ui.select(
                    label='🔧 材质列 *（需含"XX板 T=数字"）',
                    options=[],
                    with_input=True
                ).classes('w-full').bind_value(config, 'mat')
                
                sel_qty = ui.select(
                    label='🔢 数量列 *',
                    options=[],
                    with_input=True
                ).classes('w-full').bind_value(config, 'qty')
                
                # 空白占位，让下面两个备用列单独成行
                ui.label('').classes('hidden')
                
                sel_mat_backup = ui.select(
                    label='🛠️ 材质备用列（无法解析时使用此列）',
                    options=[],
                    with_input=True
                ).classes('w-full').bind_value(config, 'mat_backup')
                
                sel_thk = ui.select(
                    label='📏 厚度备用列（无法解析时使用此列）',
                    options=[],
                    with_input=True
                ).classes('w-full').bind_value(config, 'thk')
    
            
            # 配置预览
            with ui.expansion('🔍 查看当前配置', icon='visibility').classes('w-full mt-4 bg-gray-50'):
                config_text = ui.markdown('').classes('text-sm font-mono')
                
                def refresh_config():
                    config_md = f"""
**当前列映射配置：**

**必填项：**
- 零件号列：`{config['part'] or '未设置'}`
- 材质列：`{config['mat'] or '未设置'}`（应包含"XX板 T=数字"格式）
- 数量列：`{config['qty'] or '未设置'}`

**可选备用列：**
- 材质备用列：`{config.get('mat_backup', '') or '未设置'}`（材质列无法解析材质时使用）
- 厚度备用列：`{config.get('thk', '') or '未设置'}`（材质列无法解析厚度时使用）

**解析逻辑：**
1. 从材质列解析 "XX板 T=10" → 提取 材质="XX板", 厚度="10"
2. 如果无法解析出材质 → 使用材质备用列
3. 如果无法解析出厚度 → 使用厚度备用列
"""
                    config_text.content = config_md
                
                ui.button('刷新配置', on_click=refresh_config, icon='sync').props('flat size=sm color=grey')
        
        # ========== 第三步：执行分类 ==========
        with ui.card().classes('w-full p-6 bg-white shadow-xl border-t-4 border-green-500'):
            with ui.row().classes('w-full items-center gap-4'):
                ui.icon('rocket_launch', size='2.5rem').classes('text-green-600')
                ui.label('第三步：开始智能分类').classes('text-2xl font-bold text-gray-800')
            
            ui.label('确认配置无误后，点击下方按钮开始自动分类').classes('text-gray-600 mb-4')
            
            # 执行按钮
            ui.button(
                '🚀 开始执行分类',
                on_click=lambda: classifier.run_classification(config, progress, log),
                icon='play_arrow'
            ).props('size=xl color=green-6 no-caps').classes('w-full h-16 text-xl font-bold')
            
            # 进度条
            progress = ui.linear_progress(value=0, show_value=True).classes('w-full mt-6')
            
            # 日志区
            ui.label('📋 执行日志：').classes('text-sm font-bold text-gray-700 mt-4')
            log = ui.log(max_lines=300).classes(
                'w-full h-80 bg-gray-900 text-green-400 font-mono text-sm p-4 rounded-lg shadow-inner'
            )
        
        # 底部信息
        with ui.card().classes('w-full p-4 bg-gradient-to-r from-gray-700 to-gray-900 text-white'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('💡 智能识别表头位置 · 支持不规范BOM格式 · 材料列需包含"板"和"T="关键字').classes('text-sm')
                ui.label('v2.1 Pro').classes('text-xs opacity-70')


def handle_shutdown():
    """处理应用关闭"""
    print("👋 正在关闭应用...")
    
    current_os = platform.system()
    
    if current_os == 'Windows':
        # Windows需要强制终止所有相关进程
        try:
            current_process = psutil.Process(os.getpid())
            # 终止所有子进程
            children = current_process.children(recursive=True)
            for child in children:
                child.terminate()
            psutil.wait_procs(children, timeout=3)
            # 强制退出主进程
            os._exit(0)
        except Exception as e:
            print(f"清理进程时出错: {e}")
            os._exit(0)
    else:
        # macOS 和 Linux 可以自然退出
        pass

app.on_shutdown(handle_shutdown)

# 启动应用（添加on_air参数确保关闭时退出）
ui.run(
    title='BOM智能分类助手 Pro',
    native=True,
    window_size=(1000, 800),
    favicon='🎯',
    port=8765,
    reload=False,  # 关闭自动重载
    show=False,     # 不显示浏览器窗口（只显示native窗口）
)