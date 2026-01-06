好的！我来教你如何查阅SolidWorks API文档，以及如何将VBA/C#代码转换为Python代码。

## 1. SolidWorks API文档位置

### 本地文档
SolidWorks安装后，API帮助文档通常在：

```
C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\help\SolidWorksApiHelp.chm
```

或者通过开始菜单：
**开始菜单 → SOLIDWORKS 2021 → SOLIDWORKS API Help**

### 在线文档
SolidWorks API官方在线文档：
```
https://help.solidworks.com/
```
选择对应版本 → API → SolidWorks API Help

## 2. 基本转换规则（VBA/C# → Python）

### 核心对应关系

| VBA/C# | Python (pywin32) | 说明 |
|--------|------------------|------|
| `Set obj = ...` | `obj = ...` | Python不需要Set |
| `Dim x As Long` | `x = 0` | Python动态类型 |
| `obj.Method()` | `obj.Method()` | 方法调用相同 |
| `obj.Property` | `obj.Property` | 属性访问相同 |
| `Nothing` | `None` | 空值 |
| `True/False` | `True/False` | 布尔值（注意大小写）|
| `ByRef param` | 返回值元组 | Python通过返回值处理 |

## 3. 实战示例对比

### 示例1：连接SolidWorks应用程序

**VBA代码：**
```vb
Dim swApp As SldWorks.SldWorks
Set swApp = CreateObject("SldWorks.Application")
swApp.Visible = True
```

**C#代码：**
```csharp
SldWorks.SldWorks swApp;
swApp = (SldWorks.SldWorks)System.Activator.CreateInstance(
    System.Type.GetTypeFromProgID("SldWorks.Application"));
swApp.Visible = true;
```

**Python代码：**
```python
import win32com.client

# 连接SolidWorks
sw_app = win32com.client.Dispatch("SldWorks.Application")
sw_app.Visible = True
```

---

### 示例2：打开文档

**VBA代码：**
```vb
Dim swModel As ModelDoc2
Dim filePath As String
Dim fileError As Long
Dim fileWarning As Long

filePath = "C:\test\part.SLDPRT"

Set swModel = swApp.OpenDoc6(filePath, swDocPART, swOpenDocOptions_Silent, _
                              "", fileError, fileWarning)

If Not swModel Is Nothing Then
    Debug.Print "文档打开成功"
Else
    Debug.Print "错误代码: " & fileError
End If
```

**Python代码：**
```python
import win32com.client

sw_app = win32com.client.Dispatch("SldWorks.Application")

# 文件路径
filepath = r"C:\test\part.SLDPRT"

# 常量定义（查文档得知）
swDocPART = 1
swOpenDocOptions_Silent = 1

# 打开文档
# 注意：ByRef参数在Python中通过返回值获取
errors = 0
warnings = 0
doc = sw_app.OpenDoc6(filepath, swDocPART, swOpenDocOptions_Silent, 
                      "", errors, warnings)

if doc is not None:
    print("文档打开成功")
    print(f"文档标题: {doc.GetTitle()}")
else:
    print(f"打开失败，错误码: {errors}")
```

---

### 示例3：创建新零件并保存

**VBA代码：**
```vb
Dim swModel As ModelDoc2
Dim templatePath As String
Dim boolStatus As Boolean

' 创建新零件
templatePath = "C:\ProgramData\SolidWorks\SOLIDWORKS 2021\templates\Part.prtdot"
Set swModel = swApp.NewDocument(templatePath, 0, 0, 0)

' 保存
boolStatus = swModel.SaveAs3("C:\test\newpart.SLDPRT", 0, 0)

If boolStatus Then
    Debug.Print "保存成功"
End If
```

**Python代码：**
```python
import win32com.client

sw_app = win32com.client.Dispatch("SldWorks.Application")
sw_app.Visible = True

# 模板路径（根据实际安装路径修改）
template_path = r"C:\ProgramData\SolidWorks\SOLIDWORKS 2021\templates\Part.prtdot"

# 创建新零件
doc = sw_app.NewDocument(template_path, 0, 0, 0)

if doc:
    print("新文档创建成功")
    
    # 保存文档
    save_path = r"C:\test\newpart.SLDPRT"
    result = doc.SaveAs3(save_path, 0, 0)
    
    if result:
        print(f"保存成功: {save_path}")
    else:
        print("保存失败")
```

---

### 示例4：获取活动文档信息

**VBA代码：**
```vb
Dim swModel As ModelDoc2
Dim modelTitle As String
Dim modelPath As String
Dim modelType As Long

Set swModel = swApp.ActiveDoc

If Not swModel Is Nothing Then
    modelTitle = swModel.GetTitle()
    modelPath = swModel.GetPathName()
    modelType = swModel.GetType()
    
    Debug.Print "标题: " & modelTitle
    Debug.Print "路径: " & modelPath
    Debug.Print "类型: " & modelType  ' 1=零件, 2=装配体, 3=工程图
End If
```

**Python代码：**
```python
import win32com.client

sw_app = win32com.client.Dispatch("SldWorks.Application")

# 获取活动文档
doc = sw_app.ActiveDoc

if doc is not None:
    title = doc.GetTitle()
    path = doc.GetPathName()
    doc_type = doc.GetType()
    
    print(f"标题: {title}")
    print(f"路径: {path}")
    
    # 类型判断
    type_names = {1: "零件", 2: "装配体", 3: "工程图"}
    print(f"类型: {type_names.get(doc_type, '未知')}")
else:
    print("没有活动文档")
```

---

### 示例5：选择对象并获取信息

**VBA代码：**
```vb
Dim swModel As ModelDoc2
Dim swSelMgr As SelectionMgr
Dim swFace As Face2
Dim selCount As Long
Dim faceArea As Double

Set swModel = swApp.ActiveDoc
Set swSelMgr = swModel.SelectionManager

selCount = swSelMgr.GetSelectedObjectCount2(-1)

If selCount > 0 Then
    ' 获取第一个选中的对象
    Set swFace = swSelMgr.GetSelectedObject6(1, -1)
    
    If Not swFace Is Nothing Then
        faceArea = swFace.GetArea()
        Debug.Print "面积: " & faceArea & " m²"
    End If
End If
```

**Python代码：**
```python
import win32com.client

sw_app = win32com.client.Dispatch("SldWorks.Application")
doc = sw_app.ActiveDoc

if doc:
    # 获取选择管理器
    sel_mgr = doc.SelectionManager
    
    # 获取选中对象数量
    sel_count = sel_mgr.GetSelectedObjectCount2(-1)
    
    print(f"选中对象数量: {sel_count}")
    
    if sel_count > 0:
        # 获取第一个选中的对象
        face = sel_mgr.GetSelectedObject6(1, -1)
        
        if face is not None:
            # 获取面积
            area = face.GetArea()
            print(f"面积: {area} m²")
```

---

### 示例6：遍历零件的所有特征

**VBA代码：**
```vb
Dim swModel As ModelDoc2
Dim swFeat As Feature
Dim featCount As Long

Set swModel = swApp.ActiveDoc

Set swFeat = swModel.FirstFeature
featCount = 0

Do While Not swFeat Is Nothing
    featCount = featCount + 1
    Debug.Print featCount & ". " & swFeat.Name & " (" & swFeat.GetTypeName2() & ")"
    
    Set swFeat = swFeat.GetNextFeature()
Loop

Debug.Print "总特征数: " & featCount
```

**Python代码：**
```python
import win32com.client

sw_app = win32com.client.Dispatch("SldWorks.Application")
doc = sw_app.ActiveDoc

if doc:
    # 获取第一个特征
    feat = doc.FirstFeature()
    feat_count = 0
    
    # 遍历所有特征
    while feat is not None:
        feat_count += 1
        feat_name = feat.Name
        feat_type = feat.GetTypeName2()
        
        print(f"{feat_count}. {feat_name} ({feat_type})")
        
        # 获取下一个特征
        feat = feat.GetNextFeature()
    
    print(f"\n总特征数: {feat_count}")
```

---

### 示例7：处理ByRef参数（重要！）

VBA中的`ByRef`参数在Python中需要特别处理。

**VBA代码：**
```vb
Dim retVal As Long
Dim errors As Long
Dim warnings As Long

' OpenDoc6有ByRef参数
Set swModel = swApp.OpenDoc6(filePath, docType, options, config, errors, warnings)

Debug.Print "错误: " & errors
Debug.Print "警告: " & warnings
```

**Python代码（两种处理方式）：**

```python
# 方式1：直接传入初始值（不推荐，无法获取返回值）
errors = 0
warnings = 0
doc = sw_app.OpenDoc6(filepath, 1, 0, "", errors, warnings)
# 注意：这里的errors和warnings不会被修改

# 方式2：使用pythoncom.Missing（推荐，但较复杂）
import pythoncom
errors = pythoncom.Missing
warnings = pythoncom.Missing
doc = sw_app.OpenDoc6(filepath, 1, 0, "", errors, warnings)

# 方式3：多数情况下直接传0即可，通过返回值判断
doc = sw_app.OpenDoc6(filepath, 1, 0, "", 0, 0)
if doc is None:
    print("打开失败")
```

---

## 4. 常用常量定义

在VBA中可以直接使用常量，但Python需要自己定义：

```python
# 文档类型
swDocNONE = 0
swDocPART = 1          # 零件
swDocASSEMBLY = 2      # 装配体
swDocDRAWING = 3       # 工程图

# 打开选项
swOpenDocOptions_Silent = 1
swOpenDocOptions_ReadOnly = 2

# 保存选项
swSaveAsOptions_Silent = 1
swSaveAsOptions_Copy = 2

# 选择类型
swSelFACES = 1
swSelEDGES = 2
swSelVERTICES = 3
swSelDATUMPLANES = 4

# 单位
swLengthUnit_Meter = 0
swLengthUnit_Millimeter = 1
swLengthUnit_Centimeter = 2
```

或者使用常量对象（如果makepy生成成功）：

```python
import win32com.client
from win32com.client import constants

sw_app = win32com.client.Dispatch("SldWorks.Application")

# 尝试使用常量
try:
    doc_type = constants.swDocPART
except:
    # 如果常量不可用，手动定义
    doc_type = 1
```

---

## 5. 完整实用示例：批量重命名零件

**VBA代码：**
```vb
Sub RenameAndSave()
    Dim swApp As SldWorks.SldWorks
    Dim swModel As ModelDoc2
    Dim oldPath As String
    Dim newPath As String
    Dim boolStatus As Boolean
    
    Set swApp = Application.SldWorks
    Set swModel = swApp.ActiveDoc
    
    If Not swModel Is Nothing Then
        oldPath = swModel.GetPathName()
        newPath = Replace(oldPath, ".SLDPRT", "_modified.SLDPRT")
        
        boolStatus = swModel.SaveAs3(newPath, 0, 0)
        
        If boolStatus Then
            MsgBox "保存成功: " & newPath
        End If
    End If
End Sub
```

**Python代码：**
```python
import win32com.client
import os

def rename_and_save_active_doc(suffix="_modified"):
    """重命名并保存活动文档"""
    sw_app = win32com.client.Dispatch("SldWorks.Application")
    doc = sw_app.ActiveDoc
    
    if doc is None:
        print("没有活动文档")
        return False
    
    # 获取当前路径
    old_path = doc.GetPathName()
    
    if not old_path:
        print("文档尚未保存")
        return False
    
    # 生成新路径
    base, ext = os.path.splitext(old_path)
    new_path = f"{base}{suffix}{ext}"
    
    # 保存
    result = doc.SaveAs3(new_path, 0, 0)
    
    if result:
        print(f"保存成功: {new_path}")
        return True
    else:
        print("保存失败")
        return False

# 使用
if __name__ == "__main__":
    rename_and_save_active_doc()
```

---

## 6. 调试技巧

```python
import win32com.client

def safe_get_attribute(obj, attr_name, default=None):
    """安全获取对象属性"""
    try:
        return getattr(obj, attr_name)()
    except:
        try:
            return getattr(obj, attr_name)
        except:
            return default

# 使用
sw_app = win32com.client.Dispatch("SldWorks.Application")
doc = sw_app.ActiveDoc

if doc:
    title = safe_get_attribute(doc, "GetTitle", "未知")
    print(f"标题: {title}")
```

---

## 7. 学习路径建议

1. **打开API文档** → 找到你需要的功能（比如"打开文档"）
2. **查看VBA/C#示例代码**
3. **按照上面的转换规则改写为Python**
4. **在IPython中测试**
5. **遇到问题就用`dir()`查看可用方法**

现在你可以尝试在API文档中找一个功能，我帮你转换成Python代码！