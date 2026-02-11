# =========================================================
# FILE LOADERS
# =========================================================
def load_ini(entry):
    path = filedialog.askopenfilename(
        title="Select INI File", filetypes=[("INI files", "*.ini")]
    )
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)