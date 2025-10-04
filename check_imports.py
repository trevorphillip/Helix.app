# check_imports.py
import importlib
modules = [
  "ui","ui_plus","visuals","crisprutils","io_utils","variants","codon","msa_utils",
  "primer","structure_viewer","peptidebuilder","editor","ai_stub","offtarget",
  "sonify","motifs","protein_tools","stylekit","db","auth"
]
for m in modules:
    importlib.import_module(f"helix_core.{m}")
print("✅ helix_core imports OK")
