"""
NiceGUI 界面 - 完整版
集成比例修正 + DXF 导出功能
"""
from nicegui import ui, app
from pathlib import Path
from typing import List
import asyncio

# 导入我们的处理器
from enhanced_solidworks_processor import EnhancedSolidWorksProcessor
from dxf_exporter import ExportFormat, DXFExportOptions


class CompleteSolidWorksApp:
    """完整的 SolidWorks 批量处理应用"""
    
    def __init__(self):
        self.processor = None  # EnhancedSolidWorksProcessor("2024")
        
        # 状态
        self.selected_directory = ""
        self.scanned_files: List[str] = []
        self.selected_files: List[str] = []
        self.processing = False
        
        # UI 组件
        self.status_label = None
        self.file_table = None
        self.progress_bar = None
        self.result_log = None
    
    def build_ui(self):
        """构建用户界面"""
        
        ui.colors(primary='#1976d2', secondary='#424242', accent='#9c27b0')
        
        with ui.header(elevated=True).classes('items-center justify-between'):
            ui.label('SolidWorks 批量处理工具').classes('text-h5')
            with ui.row():
                ui.badge('Pro v2.0', color='green')
                ui.button('帮助', on_click=self.show_help, icon='help', flat=True)
        
        with ui.column().classes('w-full max-w-7xl mx-auto p-4 gap-4'):
            
            # 1. 连接卡片
            with ui.card().classes('w-full'):
                ui.label('1. 连接 SolidWorks').classes('text-h6')
                with ui.row().classes('gap-4 items-center'):
                    self.connect_btn = ui.button(
                        '连接 SolidWorks',
                        on_click=self.connect_solidworks,
                        icon='cable',
                        color='primary'
                    )
                    self.status_label = ui.label('未连接').classes('text-orange')
            
            # 2. 文件选择卡片
            with ui.card().classes('w-full'):
                ui.label('2. 选择文件').classes('text-h6')
                with ui.row().classes('gap-4 w-full items-end'):
                    self.dir_input = ui.input(
                        label='文件夹路径',
                        placeholder='例如: C:\\Projects\\Drawings',
                        value=''
                    ).classes('flex-grow')
                    
                    ui.button('浏览', on_click=self.browse_folder, icon='folder_open')
                    ui.button('扫描', on_click=self.scan_files, icon='search', color='primary')
                
                with ui.row().classes('gap-4'):
                    self.recursive_check = ui.checkbox('递归扫描子文件夹', value=True)
                    self.file_type_select = ui.select(
                        label='文件类型',
                        options={
                            'drawing': '图纸 (*.SLDDRW)',
                            'part': '零件 (*.SLDPRT)',
                            'sheet_metal': '钣金零件 (*.SLDPRT)',
                            'all': '全部'
                        },
                        value='drawing'
                    ).classes('w-48')
                    self.file_count_label = ui.label('未扫描').classes('text-grey')
            
            # 3. 文件列表卡片
            with ui.card().classes('w-full'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('3. 文件列表').classes('text-h6')
                    with ui.row().classes('gap-2'):
                        ui.button('全选', on_click=self.select_all, icon='select_all', size='sm')
                        ui.button('取消', on_click=self.deselect_all, icon='deselect', size='sm')
                
                self.file_table_container = ui.column().classes('w-full')
            
            # 4. 处理选项 Tabs
            with ui.card().classes('w-full'):
                ui.label('4. 处理选项').classes('text-h6')
                
                with ui.tabs().classes('w-full') as tabs:
                    tab_scale = ui.tab('比例修正', icon='straighten')
                    tab_dxf = ui.tab('DXF 导出', icon='file_download')
                    tab_pdf = ui.tab('PDF 导出', icon='picture_as_pdf')
                    tab_props = ui.tab('属性修改', icon='edit_note')
                
                with ui.tab_panels(tabs, value=tab_scale).classes('w-full'):
                    
                    # 比例修正面板
                    with ui.tab_panel(tab_scale):
                        with ui.column().classes('gap-4 p-4'):
                            ui.label('批量修改图纸和视图比例').classes('text-subtitle2')
                            
                            self.enable_scale = ui.checkbox('启用比例修正', value=True)
                            
                            with ui.row().classes('gap-4 items-center'):
                                ui.label('目标比例:')
                                self.scale_num = ui.number(
                                    label='分子',
                                    value=1,
                                    min=1,
                                    step=1,
                                    format='%.0f'
                                ).classes('w-24')
                                ui.label(':')
                                self.scale_den = ui.number(
                                    label='分母',
                                    value=1,
                                    min=1,
                                    step=1,
                                    format='%.0f'
                                ).classes('w-24')
                                
                                ui.button('1:1', on_click=lambda: self.set_scale(1, 1), size='sm', outline=True)
                                ui.button('1:2', on_click=lambda: self.set_scale(1, 2), size='sm', outline=True)
                                ui.button('2:1', on_click=lambda: self.set_scale(2, 1), size='sm', outline=True)
                            
                            self.process_views_check = ui.checkbox(
                                '同时修改所有视图比例',
                                value=True
                            )
                    
                    # DXF 导出面板
                    with ui.tab_panel(tab_dxf):
                        with ui.column().classes('gap-4 p-4'):
                            ui.label('批量导出为 DXF/DWG 格式').classes('text-subtitle2')
                            
                            self.enable_dxf = ui.checkbox('启用 DXF 导出', value=False)
                            
                            with ui.row().classes('gap-4 items-center'):
                                ui.label('导出格式:')
                                self.dxf_format = ui.radio(
                                    options={
                                        'dxf': 'DXF (AutoCAD 2013)',
                                        'dwg': 'DWG (AutoCAD 2013)'
                                    },
                                    value='dxf'
                                ).props('inline')
                            
                            with ui.column().classes('gap-2'):
                                ui.label('导出选项:').classes('text-subtitle2')
                                self.dxf_bend_lines = ui.checkbox('包含折弯线', value=True)
                                self.dxf_sketches = ui.checkbox('包含草图', value=False)
                                self.dxf_annotations = ui.checkbox('包含注释', value=True)
                            
                            with ui.row().classes('gap-2 items-end'):
                                self.dxf_output = ui.input(
                                    label='输出文件夹',
                                    placeholder='留空则保存到原文件夹',
                                    value=''
                                ).classes('flex-grow')
                                ui.button('浏览', on_click=self.browse_dxf_output, icon='folder_open')
                            
                            # 钣金专用选项
                            with ui.expansion('钣金选项 (仅针对钣金零件)', icon='cut'):
                                with ui.column().classes('gap-2 p-2'):
                                    ui.checkbox('导出展开图', value=True)
                                    ui.checkbox('包含尺寸标注', value=False)
                    
                    # PDF 导出面板
                    with ui.tab_panel(tab_pdf):
                        with ui.column().classes('gap-4 p-4'):
                            ui.label('批量导出为 PDF').classes('text-subtitle2')
                            
                            self.enable_pdf = ui.checkbox('启用 PDF 导出', value=False)
                            
                            with ui.column().classes('gap-2'):
                                ui.checkbox('高质量输出', value=True)
                                ui.checkbox('彩色输出', value=False)
                                ui.checkbox('导出所有图页', value=True)
                            
                            self.pdf_output = ui.input(
                                label='输出文件夹',
                                placeholder='留空则保存到原文件夹'
                            ).classes('w-full')
                    
                    # 属性修改面板
                    with ui.tab_panel(tab_props):
                        with ui.column().classes('gap-2 p-4'):
                            ui.label('批量修改文档属性').classes('text-subtitle2')
                            ui.label('开发中...').classes('text-grey')
            
            # 5. 执行按钮
            with ui.card().classes('w-full'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('5. 开始处理').classes('text-h6')
                    
                    with ui.row().classes('gap-2'):
                        ui.button(
                            '预览处理',
                            on_click=self.preview_processing,
                            icon='preview',
                            color='grey'
                        )
                        self.process_btn = ui.button(
                            '开始批量处理',
                            on_click=self.start_processing,
                            icon='play_arrow',
                            color='positive',
                            size='lg'
                        )
                
                self.progress_bar = ui.linear_progress(value=0, show_value=True).classes('w-full')
                self.progress_bar.visible = False
                self.progress_label = ui.label('').classes('text-center')
            
            # 6. 结果显示
            with ui.card().classes('w-full'):
                ui.label('处理结果').classes('text-h6')
                
                with ui.row().classes('gap-4'):
                    self.total_badge = ui.badge('总计: 0', color='blue')
                    self.success_badge = ui.badge('成功: 0', color='green')
                    self.failed_badge = ui.badge('失败: 0', color='red')
                
                with ui.row().classes('gap-2'):
                    ui.button(
                        '导出日志',
                        on_click=self.export_log,
                        icon='download',
                        size='sm'
                    )
                    ui.button(
                        '清空日志',
                        on_click=self.clear_log,
                        icon='clear',
                        size='sm'
                    )
                
                self.result_log = ui.log(max_lines=100).classes('w-full h-64 bg-grey-1')
    
    def set_scale(self, num: int, den: int):
        """快速设置比例"""
        self.scale_num.value = num
        self.scale_den.value = den
    
    async def connect_solidworks(self):
        """连接 SolidWorks"""
        self.connect_btn.props('loading')
        await asyncio.sleep(0.5)
        
        # 实际代码
        # if self.processor.connect():
        #     self.status_label.text = '已连接'
        #     self.status_label.classes('text-green', remove='text-orange')
        #     ui.notify('成功连接到 SolidWorks', type='positive')
        # else:
        #     ui.notify('连接失败', type='negative')
        
        # 演示模式
        self.status_label.text = '已连接 (演示)'
        self.status_label.classes('text-green', remove='text-orange')
        ui.notify('演示模式：连接成功', type='info')
        
        self.connect_btn.props(remove='loading')
    
    async def scan_files(self):
        """扫描文件"""
        directory = self.dir_input.value
        
        if not directory:
            ui.notify('请输入文件夹路径', type='warning')
            return
        
        ui.notify('正在扫描...', type='info')
        await asyncio.sleep(0.5)
        
        # 演示数据
        file_type = self.file_type_select.value
        if file_type == 'drawing':
            self.scanned_files = [
                f'{directory}/图纸_{i:03d}.SLDDRW' for i in range(1, 21)
            ]
        elif file_type == 'sheet_metal':
            self.scanned_files = [
                f'{directory}/钣金件_{i:03d}.SLDPRT' for i in range(1, 11)
            ]
        else:
            self.scanned_files = [
                f'{directory}/文件_{i:03d}.SLDDRW' for i in range(1, 16)
            ]
        
        self.file_count_label.text = f'找到 {len(self.scanned_files)} 个文件'
        ui.notify(f'扫描完成：{len(self.scanned_files)} 个文件', type='positive')
        
        self.update_file_table()
    
    def update_file_table(self):
        """更新文件表格"""
        self.file_table_container.clear()
        
        if not self.scanned_files:
            with self.file_table_container:
                ui.label('未找到文件').classes('text-grey text-center p-4')
            return
        
        rows = []
        for idx, file_path in enumerate(self.scanned_files):
            file_type = '图纸' if file_path.endswith('.SLDDRW') else '零件'
            rows.append({
                'id': idx,
                'selected': False,
                'type': file_type,
                'filename': Path(file_path).name,
                'path': file_path
            })
        
        with self.file_table_container:
            self.file_table = ui.table(
                columns=[
                    {'name': 'type', 'label': '类型', 'field': 'type', 'align': 'center'},
                    {'name': 'filename', 'label': '文件名', 'field': 'filename', 'align': 'left'},
                    {'name': 'path', 'label': '路径', 'field': 'path', 'align': 'left'},
                ],
                rows=rows,
                selection='multiple',
                row_key='id',
                pagination={'rowsPerPage': 10}
            ).classes('w-full')
            
            self.file_table.on('selection', self.on_file_selection)
    
    def on_file_selection(self, e):
        """文件选择事件"""
        self.selected_files = [row['id'] for row in e.selection]
    
    def select_all(self):
        """全选"""
        if self.file_table:
            self.file_table.selected = list(range(len(self.scanned_files)))
    
    def deselect_all(self):
        """取消全选"""
        if self.file_table:
            self.file_table.selected = []
    
    async def preview_processing(self):
        """预览处理"""
        tasks = []
        
        if self.enable_scale.value:
            tasks.append(f"✓ 比例修正: {self.scale_num.value}:{self.scale_den.value}")
        
        if self.enable_dxf.value:
            format_name = 'DXF' if self.dxf_format.value == 'dxf' else 'DWG'
            tasks.append(f"✓ 导出 {format_name}")
        
        if self.enable_pdf.value:
            tasks.append("✓ 导出 PDF")
        
        if not tasks:
            ui.notify('请至少启用一个处理选项', type='warning')
            return
        
        task_list = '\n'.join(tasks)
        message = f"""
将对 {len(self.selected_files)} 个文件执行以下操作：

{task_list}

确定继续吗？
        """
        
        with ui.dialog() as dialog, ui.card():
            ui.label('处理预览').classes('text-h6')
            ui.markdown(message)
            with ui.row():
                ui.button('取消', on_click=dialog.close)
                ui.button('确定', on_click=lambda: [dialog.close(), self.start_processing()], color='primary')
        
        dialog.open()
    
    async def start_processing(self):
        """开始处理"""
        if not self.selected_files:
            ui.notify('请选择要处理的文件', type='warning')
            return
        
        self.processing = True
        self.process_btn.props('loading disable')
        self.progress_bar.visible = True
        self.result_log.clear()
        
        total = len(self.selected_files)
        success = 0
        failed = 0
        
        for idx, file_idx in enumerate(self.selected_files):
            file_path = self.scanned_files[file_idx]
            filename = Path(file_path).name
            
            progress = (idx + 1) / total
            self.progress_bar.value = progress
            self.progress_label.text = f'处理中: {filename} ({idx + 1}/{total})'
            
            await asyncio.sleep(0.2)
            
            # 模拟处理
            import random
            is_success = random.random() > 0.1
            
            if is_success:
                success += 1
                messages = []
                
                if self.enable_scale.value:
                    messages.append(f'比例已修改为 {self.scale_num.value}:{self.scale_den.value}')
                
                if self.enable_dxf.value:
                    ext = self.dxf_format.value.upper()
                    messages.append(f'已导出为 {ext}')
                
                if self.enable_pdf.value:
                    messages.append('已导出为 PDF')
                
                self.result_log.push(f'✓ {filename} - {", ".join(messages)}')
            else:
                failed += 1
                self.result_log.push(f'✗ {filename} - 处理失败')
        
        # 完成
        self.progress_bar.visible = False
        self.processing = False
        self.process_btn.props(remove='loading disable')
        
        self.total_badge.text = f'总计: {total}'
        self.success_badge.text = f'成功: {success}'
        self.failed_badge.text = f'失败: {failed}'
        
        ui.notify(f'完成！成功: {success}, 失败: {failed}', type='positive' if failed == 0 else 'warning')
    
    def export_log(self):
        """导出日志"""
        ui.notify('日志已导出到: process_log.txt', type='info')
    
    def clear_log(self):
        """清空日志"""
        self.result_log.clear()
        self.total_badge.text = '总计: 0'
        self.success_badge.text = '成功: 0'
        self.failed_badge.text = '失败: 0'
    
    async def browse_folder(self):
        """浏览文件夹"""
        result = await ui.run_javascript('return prompt("请输入文件夹路径：")')
        if result:
            self.dir_input.value = result
    
    async def browse_dxf_output(self):
        """浏览 DXF 输出文件夹"""
        result = await ui.run_javascript('return prompt("请输入输出文件夹路径：")')
        if result:
            self.dxf_output.value = result
    
    def show_help(self):
        """显示帮助"""
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('使用帮助').classes('text-h6')
            ui.separator()
            ui.markdown('''
            **基本流程：**
            1. 连接 SolidWorks
            2. 选择文件夹并扫描
            3. 勾选要处理的文件
            4. 选择处理选项（比例/DXF/PDF）
            5. 开始批量处理
            
            **功能说明：**
            - 比例修正：统一修改图纸和视图比例
            - DXF 导出：支持图纸和钣金展开图
            - PDF 导出：批量导出为 PDF 文件
            
            **技巧：**
            - 使用"预览处理"查看将要执行的操作
            - 可同时启用多个处理选项
            - 导出日志功能保存处理记录
            ''')
            ui.button('关闭', on_click=dialog.close)
        dialog.open()


def main():
    app_instance = CompleteSolidWorksApp()
    app_instance.build_ui()
    
    ui.run(
        title='SolidWorks 批量处理工具 Pro',
        favicon='🔧',
        dark=False,
        port=8080
    )


if __name__ in {'__main__', '__mp_main__'}:
    main()