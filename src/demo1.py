import os
import shutil
import pandas as pd
import asyncio
from pathlib import Path
from nicegui import ui

class SmartOrganizer:
    def __init__(self):
        self.base_path = Path(os.getcwd())
        self.bom_dir = self.base_path / "1_放入BOM表"
        self.src_dir = self.base_path / "2_放入源文件"
        self.out_dir = self.base_path / "3_分类结果输出"
        
        # 存储读取到的 Excel 数据和表头
        self.df = None
        self.headers = []
        self.target_bom_path = None

    def init_folders(self):
        """创建基础目录"""
        for d in [self.bom_dir, self.src_dir, self.out_dir]:
            d.mkdir(exist_ok=True)
        ui.notify("文件夹已准备就绪", type='positive')
        os.startfile(self.base_path) # 自动打开文件夹方便操作

    def load_bom_headers(self):
        """读取BOM并获取表头"""
        files = list(self.bom_dir.glob("*.xlsx")) + list(self.bom_dir.glob("*.xls"))
        if not files:
            ui.notify("未在文件夹1中找到Excel文件", type='warning')
            return False
        
        try:
            self.target_bom_path = files[0]
            # 仅读取前0行来获取表头，速度极快
            preview_df = pd.read_excel(self.target_bom_path, nrows=0)
            self.headers = preview_df.columns.tolist()
            ui.notify(f"成功读取 BOM: {self.target_bom_path.name}")
            return True
        except Exception as e:
            ui.notify(f"读取失败: {e}", type='negative')
            return False

    async def run_logic(self, mapping, progress, log):
        """执行整理逻辑"""
        if self.target_bom_path is None:
            ui.notify("请先载入BOM！")
            return

        log.clear()
        log.push("🚀 启动任务...")
        
        try:
            # 全量读取
            df = pd.read_excel(self.target_bom_path).fillna('')
            source_files = {f.name: f for f in self.src_dir.rglob('*') if f.is_file()}
            
            for i, row in df.iterrows():
                # 从映射中获取用户选择的列名
                part = str(row.get(mapping['part'], '')).strip()
                mat = str(row.get(mapping['mat'], '未分类材质')).strip()
                thk = str(row.get(mapping['thk'], '未分类厚度')).strip()
                qty = str(row.get(mapping['qty'], '1')).strip()

                if not part: continue

                # 模糊匹配
                found = next((p for n, p in source_files.items() if part in n), None)
                
                if found:
                    dest = self.out_dir / mat / thk
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(found, dest / f"{qty}_{found.name}")
                    log.push(f"✅ 已归档: {part}")
                else:
                    log.push(f"❌ 缺失: {part}")

                progress.set_value((i + 1) / len(df))
                if i % 10 == 0: await asyncio.sleep(0.001)
            
            ui.notify("整理完成！", type='positive')
        except Exception as e:
            ui.notify(f"运行出错: {e}")

# --- UI 界面 ---
manager = SmartOrganizer()

@ui.page('/')
def main_page():
    ui.query('body').style('background-color: #f8f9fa')
    
    # 状态存储
    config = {'part': '', 'mat': '', 'thk': '', 'qty': ''}

    with ui.column().classes('w-full max-w-4xl mx-auto p-6 gap-4'):
        ui.label('BOM 智能分拣助手').classes('text-3xl font-bold text-blue-800')

        # 第一步
        with ui.card().classes('w-full p-4'):
            ui.label('第一步：准备环境').classes('text-lg font-bold')
            ui.button('生成并打开工作目录', on_click=manager.init_folders).props('no-caps icon=folder')
            ui.markdown('👉 *请将 BOM 放入文件夹1，源文件放入文件夹2*')

        # 第二步
        with ui.card().classes('w-full p-4'):
            ui.label('第二步：解析表头').classes('text-lg font-bold')
            
            # 下拉框组件
            with ui.row().classes('w-full gap-4'):
                sel_part = ui.select(label='零件号列', options=[]).classes('flex-grow').bind_value(config, 'part')
                sel_mat = ui.select(label='材质列', options=[]).classes('flex-grow').bind_value(config, 'mat')
                sel_thk = ui.select(label='厚度列', options=[]).classes('flex-grow').bind_value(config, 'thk')
                sel_qty = ui.select(label='数量列', options=[]).classes('flex-grow').bind_value(config, 'qty')

            def update_ui():
                if manager.load_bom_headers():
                    sel_part.options = manager.headers
                    sel_mat.options = manager.headers
                    sel_thk.options = manager.headers
                    sel_qty.options = manager.headers
                    # 尝试自动匹配（可选：如果表头包含特定字眼自动选上）
                    for h in manager.headers:
                        if '零件' in h or '图号' in h: sel_part.value = h
                        if '材质' in h or '材料' in h: sel_mat.value = h
                        if '厚' in h: sel_thk.value = h
                        if '数量' in h: sel_qty.value = h
                    ui.notify("表头更新成功")

            ui.button('载入并刷新表头', color='orange', on_click=update_ui).props('icon=refresh')

        # 第三步
        with ui.card().classes('w-full p-4 border-t-4 border-blue-500'):
            ui.label('第三步：开始整理').classes('text-lg font-bold')
            ui.button('点击执行', on_click=lambda: manager.run_logic(config, pg, log)).classes('w-full h-12 text-lg')
            pg = ui.linear_progress(value=0).classes('mt-4')
            log = ui.log().classes('w-full h-40 mt-4 bg-gray-900 text-green-400 text-xs p-2')

ui.run(title="Smart BOM Sort", native=True, window_size=(900, 850))