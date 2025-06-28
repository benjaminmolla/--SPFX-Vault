import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
import hashlib, os, pickle, io, sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def hash_password(password):
    return hashlib.sha512(password.encode()).digest()[:32]

def encrypt(data, key):
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    return iv + cipher.encryptor().update(data) + cipher.encryptor().finalize()

def decrypt(data, key):
    iv, ct = data[:16], data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CFB(iv), backend=default_backend())
    return cipher.decryptor().update(ct) + cipher.decryptor().finalize()

class FileNode:
    def __init__(self, name, data): self.name, self.data = name, data

class FolderNode:
    def __init__(self, name): self.name, self.children = name, {}


class Vault:
    def __init__(self): self.root = FolderNode("root")

    def save(self, path, key):
        data = pickle.dumps(self.root)
        with open(path, "wb") as f: f.write(encrypt(data, key))

    def load(self, path, key):
        with open(path, "rb") as f:
            data = f.read()
        self.root = pickle.loads(decrypt(data, key))


class VaultApp:
    def __init__(self, root):
        self.root = root
        root.title("SPFX Vault Premium+")
        self.vault = Vault(); self.key = None; self.file = None
        self.current = None; self.path = []

        self.tree = ttk.Treeview(root)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.double_click)
        self.tree.bind("<ButtonRelease-1>", self.tree_focus)

        
        self.tree_drop_bind()

        menubar = tk.Menu(root)
        menu = tk.Menu(menubar, tearoff=0)
        menu.add_command(label="New Vault", command=self.new_vault)
        menu.add_command(label="Open Vault", command=self.open_vault)
        menu.add_command(label="Save Vault", command=self.save_vault)
        menu.add_separator()
        menu.add_command(label="Add Folder", command=self.add_folder)
        menu.add_command(label="Import Files", command=self.import_files)
        menu.add_command(label="Go Back", command=self.go_back)
        menubar.add_cascade(label="Vault", menu=menu)
        root.config(menu=menubar)

    def tree_drop_bind(self):
        try:
            self.root.tk.call('tk', 'windowingsystem')
            self.tree.drop_target_register(tk.DND_FILES)
            self.tree.dnd_bind('<<Drop>>', self.handle_drop)
        except:
            pass  
    def ask_password(self):
        p = simpledialog.askstring("Password", "Enter vault password:", show="*")
        if not p: return False
        self.key = hash_password(p)
        return True

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if self.current:
            for name in sorted(self.current.children):
                self.tree.insert("", "end", text=name)

    def get_selected(self):
        i = self.tree.focus()
        if not i: return None
        name = self.tree.item(i)["text"]
        return self.current.children.get(name)

    def tree_focus(self, _): self.get_selected()

    def new_vault(self):
        if not self.ask_password(): return
        self.vault = Vault()
        self.current = self.vault.root
        self.path = []
        self.refresh_tree()

    def open_vault(self):
        path = filedialog.askopenfilename(filetypes=[("SPFX Vault", "*.spfx")])
        if path and self.ask_password():
            try:
                self.vault.load(path, self.key)
                self.current = self.vault.root
                self.path = []
                self.file = path
                self.refresh_tree()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def save_vault(self):
        if not self.key: return
        if not self.file:
            self.file = filedialog.asksaveasfilename(defaultextension=".spfx")
        if self.file: self.vault.save(self.file, self.key)

    def go_back(self):
        if self.path:
            self.current = self.path.pop()
            self.refresh_tree()

    def add_folder(self):
        name = simpledialog.askstring("Folder Name", "Enter new folder name:")
        if name:
            self.current.children[name] = FolderNode(name)
            self.refresh_tree()

    def import_files(self):
        paths = filedialog.askopenfilenames()
        for path in paths:
            with open(path, "rb") as f:
                data = f.read()
            name = os.path.basename(path)
            self.current.children[name] = FileNode(name, data)
        self.refresh_tree()

    def handle_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        for path in files:
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    data = f.read()
                name = os.path.basename(path)
                self.current.children[name] = FileNode(name, data)
        self.refresh_tree()

    def double_click(self, _):
        node = self.get_selected()
        if isinstance(node, FolderNode):
            self.path.append(self.current)
            self.current = node
            self.refresh_tree()
        elif isinstance(node, FileNode):
            ext = os.path.splitext(node.name)[1].lower()
            if ext in [".png", ".jpg", ".jpeg"]:
                img = Image.open(io.BytesIO(node.data)); img.thumbnail((600, 600))
                top = tk.Toplevel()
                preview = ImageTk.PhotoImage(img)
                lbl = tk.Label(top, image=preview)
                lbl.image = preview
                lbl.pack()
            else:
                temp = "__preview__" + ext
                with open(temp, "wb") as f: f.write(node.data)
                try: os.startfile(temp)
                except: messagebox.showinfo("Preview", "Cannot open this file.")

if __name__ == "__main__":
    root = tk.Tk()
    app = VaultApp(root)
    root.mainloop()