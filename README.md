# FastBOM

## Project Overview
FastBOM is a desktop application developed based on NiceGUI, specifically designed to intelligently categorize and organize engineering files exported from PLM systems according to BOM (Bill of Materials) tables. The tool can parse material description fields that are irregular but follow patterns, achieving automated directory structure generation and file renaming with copying.

## Core Features

1. **Directory Initialization Function**
   - Automatically creates three working directories: BOM table storage directory, source file directory, and classification result output directory
   - Provides one-click function to open working directory, making it convenient for users to operate

2. **Intelligent BOM Table Parsing**
   - Intelligent detection of header position (able to identify even when headers are not in the first row)
   - Parses material column content, identifying material and thickness information in formats like "XX板 T=number" or "XX板T=number"
   - Supports Excel file formats (.xlsx and .xls)

3. **Column Mapping Configuration**
   - Allows users to customize mapping of part number column, material column, thickness column, and quantity column in BOM tables
   - Provides automatic matching suggestions (automatically selects based on keywords in column names)

4. **File Classification Execution**
   - Classifies source files to `/material/thickness/(quantity)original_file.pdf` directory structure based on BOM table information
   - Supports fuzzy matching of file names, increasing matching success rate
   - Displays processing progress and log information in real-time

## Project Features

1. **User-friendly Interface**
   - Three-step guided interface: Set directories → Parse BOM and configure mapping → Execute classification and display progress
   - Modern UI interface built with NiceGUI, simple and intuitive operation

2. **Strong Fault Tolerance**
   - Supports spacing differences in material fields (both "A3板 T=10" and "A3板T=10" can be recognized)
   - Intelligent header detection function, adaptable to different BOM table formats
   - Supports cross-platform operation (Windows, macOS, Linux)

3. **Efficient Processing Capability**
   - Asynchronous processing mechanism to avoid interface freezing
   - Batch file processing to improve work efficiency
   - Real-time progress feedback for users to understand processing status

4. **Flexible Configuration**
   - Customizable column mapping relationships to adapt to different BOM table formats
   - Supports different types of material and thickness naming rules

## Tech Stack

1. **Frontend Framework**
   - [NiceGUI](https://github.com/zauberzeug/nicegui) - Python Web GUI framework for building user interfaces

2. **Data Processing**
   - [pandas](https://pandas.pydata.org/) - Used for processing Excel files and data tables
   - [openpyxl](https://openpyxl.readthedocs.io/) - Excel file read/write support
   - [xlrd](https://xlrd.readthedocs.io/) - Legacy Excel file support

3. **Packaging Tools**
   - [PyInstaller](https://pyinstaller.org/) - Used to package Python applications as standalone executable files
   - [pywebview](https://pywebview.flowrl.com/) - Used to create native window applications

4. **Other Dependencies**
   - [psutil](https://psutil.readthedocs.io/) - System and process monitoring tools
   - Python standard libraries (os, shutil, re, asyncio, pathlib, etc.)

## Project Structure

1. **Main Functional Modules**
   - `demo1.py` - Basic version of BOM classification tool
   - `demo2.py` - Enhanced version with intelligent header detection
   - `demo3.py` - Most complete version with additional optimization features

2. **Tool Modules**
   - `build.py` - Project packaging script for packaging applications as executable files
   - `file_maker.py` - File generation tool (possibly for testing)

3. **Configuration Files**
   - `pyproject.toml` - Project dependencies and configuration
   - `README.md` - Project documentation

## Running and Deployment

- **Development Environment**: Python 3.13+, install dependencies with `poetry install`
- **Local Run**: `python demo1.py` (or other demo files)
- **Packaging Deployment**: Use `build.py` script to package as standalone executable file

`FastBOM` is a practical tool focused on automated classification of manufacturing engineering files. Through simple three-step operations, complex BOM table-driven file classification tasks can be completed, greatly improving work efficiency.