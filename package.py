import os
import argparse
import pathlib
from sys import argv
import PyInstaller.__main__
import astunparse
import ast
import streamlit.magic as magic
import streamlit
from os.path import join, dirname, split
import glob

def preprocess_script(script_path, output_path):
    script_file = open(script_path, "r")
    a: ast.Module = magic.add_magic(script_file.read(), script_path)
    script_file.close()

    imports = []
    nonImports = []

    for node in a.body:
        if node.__class__ == ast.Import or node.__class__ == ast.ImportFrom:
            imports.append(node)
        else:
            nonImports.append(node)

    wrapper_func = ast.parse("def __streamlit_run__():\n\treturn")
    wrapper_func.body[0].body=nonImports

    build_script_file = open(output_path, "w")
    build_script_file.write(astunparse.unparse(imports))
    build_script_file.write(astunparse.unparse(wrapper_func))
    build_script_file.close()

def get_frontend_files():
    pkg_dir = split(streamlit.__file__)[0]
    static_data = []
    for file in glob.iglob(join(pkg_dir,"static", "**", "*"), recursive=True):
        relative_path = file.split(join("streamlit", "static") + os.sep, maxsplit=1)[1]
        target_file = join("frontend", relative_path)
        target_dir = dirname(target_file)
        static_data.append((file, target_dir))
    
    static_data.append(("websocketshim.js", "frontend"))
    return static_data

def print_help():
    print("Streamlit Packager - A tool for packaging Streamlit apps into offline programs")
    print("     Usage: python package.py <script> <pyinstaller options>")
    print("         <script>: The path to the Streamlit script to package")
    print("         <pyinstaller options>: Any pyinstaller options can be put here")

def run():
    if len(argv) < 2:
        print_help()
        return
    

    script_path = argv[1]

    preprocess_script(script_path, "built_streamlit_script.py")

    pyinstaller_args = []
    pyinstaller_args.append('main.py')

    pyinstaller_args.extend(argv[2:])

    frontend_files = get_frontend_files()
    for file in frontend_files:
        pyinstaller_args.append('--add-data')
        pyinstaller_args.append('%s%s%s' % (file[0], os.pathsep, file[1]))


    pyinstaller_args.extend(['--additional-hooks-dir', "hooks"])
    pyinstaller_args.append("--windowed")

    for arg in pyinstaller_args:
        print(arg)

    PyInstaller.__main__.run(pyinstaller_args)

run()