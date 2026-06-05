# core/dxf_processor.py

from pathlib import Path
from typing import Tuple, List
from ezdxf import zoom, addons
from ezdxf.filemanagement import readfile, new
from ezdxf.bbox import extents
from ezdxf.document import Drawing

from config.settings import DxfConfig


class DXFProcessor:
    """DXF文件处理器"""
    
    # 统一的文本配置
    TEXT_HEIGHT = 50
    TEXT_LAYER = "0"
    TEXT_COLOR = 2  # 黄色

    def __init__(self, dxf_config: DxfConfig | None = None):
        self.dxf_config = dxf_config or DxfConfig()
        self.text_height = self.dxf_config.text_height
        self.text_layer = self.dxf_config.text_layer
        self.text_color = self.dxf_config.text_color
        self.spacing = self.dxf_config.spacing
    
    def process_dxf_file(self, file_path: Path, num: int, output_dir: Path) -> Tuple[bool, str]:
        """处理DXF文件：在图层0实体上方添加文件名标注"""
        try:
            doc: Drawing = readfile(str(file_path))
            msp = doc.modelspace()
            
            if '0' not in doc.layers:
                return False, f"❌ 文件中不存在图层0: {file_path.name}"
            
            # 获取图层0实体
            layer_0_entities = [e for e in msp if hasattr(e.dxf, 'layer') and e.dxf.layer == '0']
            if not layer_0_entities:
                return False, f"❌ 图层0中没有实体: {file_path.name}"
            
            # 插入文件名标注
            try:
                entity_extent = extents(layer_0_entities)
                if entity_extent.has_data:
                    text_height = max((entity_extent.extmax.y - entity_extent.extmin.y) * 0.1, 5.0)
                    insert_pos = (0, - text_height * 1.5)
                else:
                    text_height = 10
                    insert_pos = (0, 0)

                file_name_to_insert = file_path.stem
                msp.add_text(
                    file_name_to_insert,
                    dxfattribs={
                        'layer': self.text_layer,
                        'height': text_height,
                        'color': self.text_color
                    }
                ).set_placement(insert_pos)
            except Exception as text_err:
                print(f"插入文字提示: {text_err}")
            
            # 保存文件
            zoom.extents(msp)
            output_file = output_dir / f"processed_{file_path.name}"
            doc.saveas(str(output_file))
            
            return True, f"✅ 成功处理 | 保存至: {output_file.name}"
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"详细错误信息:\n{error_detail}")
            return False, f"❌ 处理失败 [{file_path.name}]: {str(e)}"

    def merge_directory_to_dxf(self, input_dir: Path, output_file: Path) -> Tuple[bool, str]:
        """合并目录下所有DXF文件到一个文件"""
        if not input_dir.is_dir():
            return False, f"❌ 错误: {input_dir} 不是有效的目录"

        merged_doc: Drawing = new()
        merged_msp = merged_doc.modelspace()
        
        dxf_files = sorted(list(input_dir.rglob("*.dxf")))
        if not dxf_files:
            return False, "⚠️ 文件夹内没有 DXF 文件"

        current_x_offset = 0.0
        spacing = self.spacing
        success_count = 0

        for dxf_file in dxf_files:
            try:
                source_doc: Drawing = readfile(str(dxf_file))
                source_msp = source_doc.modelspace()
                
                entities = list(source_msp.query('*'))
                if not entities:
                    continue
                
                bbox = extents(entities)
                if not bbox.has_data:
                    continue

                block_name = f"block_{dxf_file.stem}_{success_count}".replace(" ", "_")[:100]
                
                new_block = merged_doc.blocks.new(name=block_name)
                importer = addons.importer.Importer(source_doc, merged_doc)
                importer.import_entities(entities, target_layout=new_block)
                importer.finalize()

                insert_point = (current_x_offset, 0, 0)
                merged_msp.add_blockref(block_name, insert_point)
                
                file_label = dxf_file.stem
                model_height = bbox.extmax.y - bbox.extmin.y
                text_y = model_height + self.text_height
                
                merged_msp.add_text(
                    file_label,
                    dxfattribs={
                        'height': self.text_height,
                        'layer': self.text_layer,
                        'color': self.text_color
                    }
                ).set_placement((current_x_offset, text_y))

                model_width = bbox.extmax.x - bbox.extmin.x
                current_x_offset += model_width + spacing

                success_count += 1

            except Exception as e:
                print(f"❌ 处理 {dxf_file.name} 失败: {e}")

        if success_count == 0:
            return False, "❌ 没有成功合并任何文件"
        
        # 隐藏其他图层
        visible_layers = {'0', '细实线层'}
        for layer in merged_doc.layers:
            if layer.dxf.name not in visible_layers:
                layer.off()

        try:
            zoom.extents(merged_msp)
            merged_doc.saveas(str(output_file))
            return True, f"✅ 成功合并 {success_count} 个文件到: {output_file.name}"
        except Exception as e:
            return False, f"❌ 保存合并文件失败: {str(e)}"

    def merge_by_thickness(self, source_dir: Path, output_dir: Path) -> Tuple[int, int, List[str]]:
        """按材料/厚度分组合并DXF文件"""
        success_count = 0
        fail_count = 0
        logs: List[str] = []

        if not source_dir.exists():
            return 0, 0, ["❌ 源目录不存在"]

        for material_dir in sorted(source_dir.iterdir()):
            if not material_dir.is_dir():
                continue
            
            for thickness_dir in sorted(material_dir.iterdir()):
                if not thickness_dir.is_dir():
                    continue
                
                logs.append(f"📦 正在合并组: {material_dir.name} - {thickness_dir.name}")
                
                output_filename = f"{material_dir.name}_{thickness_dir.name}_merged.dxf"
                target_file = output_dir / output_filename
                
                success, msg = self.merge_directory_to_dxf(thickness_dir, target_file)
                
                if success:
                    success_count += 1
                    logs.append(f"  {msg}")
                else:
                    fail_count += 1
                    logs.append(f"  {msg}")
        
        return success_count, fail_count, logs
