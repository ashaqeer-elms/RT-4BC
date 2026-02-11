def load_joblib(entry):
    path = filedialog.askopenfilename(
        title="Select Classification Model", filetypes=[("Joblib files", "*.joblib")]
    )
    if path:
        entry.delete(0, tk.END)
        entry.insert(0, path)