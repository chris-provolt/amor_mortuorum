from PyInstaller.utils.hooks import collect_data_files

# Ensure package data (assets, configs, etc.) are bundled

datas = collect_data_files('amor_mortuorum', include_py_files=False)
