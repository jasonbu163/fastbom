import os

def clean_filename(name):
    """
    清理文件名，替换Windows系统中不允许的字符
    """
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name

def read_material_names(filename):
    """
    从文本文件中读取物料名称，每行一个[1,4](@ref)
    """
    material_names = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                # 去除空白字符并跳过空行[4](@ref)
                cleaned_line = line.strip()
                if cleaned_line:  # 只处理非空行
                    material_names.append(cleaned_line)
        print(f"成功从 {filename} 读取 {len(material_names)} 个物料名称")
        return material_names
    except FileNotFoundError:
        print(f"错误：找不到文件 {filename}，请检查文件路径和名称[6,8](@ref)")
        return []
    except PermissionError:
        print(f"错误：没有权限读取文件 {filename}[6,8](@ref)")
        return []
    except UnicodeDecodeError:
        print(f"错误：文件编码问题，尝试使用其他编码读取[8](@ref)")
        # 尝试其他常见编码
        try:
            with open(filename, 'r', encoding='gbk') as f:
                for line in f:
                    cleaned_line = line.strip()
                    if cleaned_line:
                        material_names.append(cleaned_line)
            print(f"使用GBK编码成功读取 {len(material_names)} 个物料名称")
            return material_names
        except:
            print("使用GBK编码也失败，请检查文件编码")
            return []
    except Exception as e:
        print(f"读取文件时发生未知错误：{e}[6](@ref)")
        return []

def create_material_files(source_file, output_dir="物料文件"):
    """
    从源文件读取物料列表并批量创建txt文件
    """
    # 读取物料名称
    material_names = read_material_names(source_file)
    
    if not material_names:
        print("没有读取到任何物料名称，程序结束")
        return
    
    # 创建输出目录（如果不存在）
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"创建目录: {output_dir}")
    
    created_count = 0
    existing_count = 0
    error_count = 0
    
    print("开始创建文件...")
    for i, material in enumerate(material_names, 1):
        # 清理物料名称作为文件名
        clean_name = clean_filename(material)
        filename = f"{clean_name}.txt"
        filepath = os.path.join(output_dir, filename)
        
        # 检查文件是否已存在
        if not os.path.exists(filepath):
            try:
                # 创建并写入文件内容[3](@ref)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"物料名称: {material}\n")
                    f.write("创建时间: 请在此添加相关信息\n")
                    f.write("规格参数: 请在此添加规格信息\n")
                    f.write("备注: 请在此添加备注信息\n")
                print(f"✓ [{i:3d}/{len(material_names)}] 创建文件: {filename}")
                created_count += 1
            except Exception as e:
                print(f"✗ [{i:3d}/{len(material_names)}] 创建文件失败 {filename}: {e}[6](@ref)")
                error_count += 1
        else:
            print(f"⚠ [{i:3d}/{len(material_names)}] 文件已存在: {filename}")
            existing_count += 1
    
    print(f"\n=== 完成 ===")
    print(f"成功创建文件: {created_count} 个")
    print(f"已存在文件: {existing_count} 个")
    print(f"创建失败: {error_count} 个")
    print(f"文件保存位置: {os.path.abspath(output_dir)}")

# 使用方法
if __name__ == "__main__":
    # 设置源文件名（包含物料列表的txt文件）
    source_filename = "material_list.txt"  # 请根据实际情况修改文件名
    
    # 可选：设置自定义输出目录
    output_directory = "./material_files"
    create_material_files(source_filename, output_directory)
    
    # create_material_files(source_filename)