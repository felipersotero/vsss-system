import tkinter as tk

root = tk.Tk()
root.geometry("300x200")

# Criando um frame com borda
frame = tk.Frame(root, borderwidth=2, relief="solid", width=200, height=100)
frame.pack()

root.mainloop()
