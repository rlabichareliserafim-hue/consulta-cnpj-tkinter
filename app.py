from __future__ import annotations

import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from cnpj_service import BrasilAPIClient, CNPJError, CompanyResult, format_cnpj
from spreadsheet import export_results, extract_cnpjs


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class CNPJApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CNPJ Radar | BrasilAPI")
        self.geometry("1120x720")
        self.minsize(900, 600)
        self.configure(fg_color="#0d1117")
        self.client = BrasilAPIClient()
        self.cnpjs: list[str] = []
        self.results: list[dict[str, str]] = []
        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color="#151b24")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        ctk.CTkLabel(sidebar, text="CNPJ\nRADAR", font=ctk.CTkFont(size=28, weight="bold"), text_color="#8de1d0", justify="left").pack(anchor="w", padx=28, pady=(34, 8))
        ctk.CTkLabel(sidebar, text="Consulta cadastral em lote", text_color="#92a0b3", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=30)
        ctk.CTkFrame(sidebar, height=1, fg_color="#27313e").pack(fill="x", padx=28, pady=30)
        self.file_label = ctk.CTkLabel(sidebar, text="Nenhuma planilha carregada", text_color="#92a0b3", wraplength=200, justify="left")
        self.file_label.pack(anchor="w", padx=28, pady=(0, 18))
        self.select_button = ctk.CTkButton(sidebar, text="Selecionar planilha", command=self.select_file, height=40, fg_color="#2c8379", hover_color="#3da394")
        self.select_button.pack(fill="x", padx=28)
        self.start_button = ctk.CTkButton(sidebar, text="Iniciar consulta", command=self.start_lookup, height=40, state="disabled", fg_color="#d97941", hover_color="#ed8b50")
        self.start_button.pack(fill="x", padx=28, pady=10)
        self.pause_button = ctk.CTkButton(sidebar, text="Pausar", command=self.toggle_pause, height=36, state="disabled", fg_color="#27313e", hover_color="#354354")
        self.pause_button.pack(fill="x", padx=28)
        self.export_button = ctk.CTkButton(sidebar, text="Exportar resultados", command=self.export, height=36, state="disabled", fg_color="transparent", border_width=1, border_color="#405062", hover_color="#27313e")
        self.export_button.pack(fill="x", padx=28, pady=(10, 0))
        ctk.CTkLabel(sidebar, text="Fonte: BrasilAPI\nDados públicos de CNPJ", text_color="#657387", justify="left").pack(anchor="w", padx=28, side="bottom", pady=28)

        content = ctk.CTkFrame(self, corner_radius=0, fg_color="#0d1117")
        content.grid(row=0, column=1, sticky="nsew", padx=28, pady=26)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(content, text="Painel de consulta", font=ctk.CTkFont(size=25, weight="bold"), text_color="#edf4f2").grid(row=0, column=0, sticky="w")
        self.status_label = ctk.CTkLabel(content, text="Importe uma planilha para começar", text_color="#92a0b3")
        self.status_label.grid(row=1, column=0, sticky="w", pady=(5, 18))
        self.progress = ctk.CTkProgressBar(content, height=8, progress_color="#8de1d0", fg_color="#27313e")
        self.progress.grid(row=2, column=0, sticky="ew", pady=(0, 22))
        self.progress.set(0)

        table_frame = ctk.CTkFrame(content, fg_color="#151b24", corner_radius=10)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        columns = ("cnpj", "razao", "fantasia", "situacao", "local", "status")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", style="CNPJ.Treeview")
        headings = {"cnpj": "CNPJ", "razao": "Razão Social", "fantasia": "Nome Fantasia", "situacao": "Situação", "local": "Município / UF", "status": "Status"}
        widths = {"cnpj": 145, "razao": 245, "fantasia": 180, "situacao": 115, "local": 150, "status": 105}
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], anchor="w")
        self.table.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        scroll.grid(row=0, column=1, sticky="ns", pady=12)
        self.table.configure(yscrollcommand=scroll.set)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("CNPJ.Treeview", background="#151b24", fieldbackground="#151b24", foreground="#d9e4e1", rowheight=34, borderwidth=0)
        style.configure("CNPJ.Treeview.Heading", background="#202a36", foreground="#8de1d0", relief="flat", font=("Segoe UI", 10, "bold"))
        style.map("CNPJ.Treeview", background=[("selected", "#27544f")])

    def select_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Planilhas", "*.xlsx *.xls *.csv"), ("Todos os arquivos", "*.*")])
        if not path:
            return
        try:
            self.cnpjs = extract_cnpjs(path)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Planilha inválida", str(exc))
            return
        self.results.clear()
        self.table.delete(*self.table.get_children())
        self.file_label.configure(text=f"{Path(path).name}\n{len(self.cnpjs)} CNPJ(s) válido(s)", text_color="#d9e4e1")
        self.status_label.configure(text="Pronto para consultar")
        self.start_button.configure(state="normal")
        self.export_button.configure(state="disabled")
        self.progress.set(0)

    def start_lookup(self) -> None:
        if not self.cnpjs or (self.worker and self.worker.is_alive()):
            return
        self.results.clear()
        self.table.delete(*self.table.get_children())
        self.stop_event.clear()
        self.pause_event.set()
        self.start_button.configure(state="disabled")
        self.select_button.configure(state="disabled")
        self.pause_button.configure(state="normal", text="Pausar")
        self.status_label.configure(text=f"Consultando 0 de {len(self.cnpjs)}...")
        self.progress.set(0)
        self.worker = threading.Thread(target=self._lookup_worker, daemon=True)
        self.worker.start()

    def _lookup_worker(self) -> None:
        for index, cnpj in enumerate(self.cnpjs, start=1):
            if self.stop_event.is_set():
                break
            self.pause_event.wait()
            try:
                result = self.client.lookup(cnpj)
            except CNPJError as exc:
                result = CompanyResult(cnpj=format_cnpj(cnpj), status="Erro", detalhe=str(exc))
            row = {"cnpj": result.cnpj, "razao": result.razao_social, "fantasia": result.nome_fantasia, "situacao": result.situacao, "local": f"{result.municipio} / {result.uf}".strip(" /"), "status": result.status, "detalhe": result.detalhe}
            self.results.append(row)
            self.after(0, self._add_row, row, index)
            time.sleep(0.25)
        self.after(0, self._finish_lookup)

    def _add_row(self, row: dict[str, str], index: int) -> None:
        self.table.insert("", "end", values=tuple(row[key] for key in ("cnpj", "razao", "fantasia", "situacao", "local", "status")))
        self.progress.set(index / len(self.cnpjs))
        self.status_label.configure(text=f"Consultando {index} de {len(self.cnpjs)}...")

    def _finish_lookup(self) -> None:
        self.status_label.configure(text=f"Consulta concluída: {len(self.results)} registro(s) processado(s)")
        self.start_button.configure(state="normal")
        self.select_button.configure(state="normal")
        self.pause_button.configure(state="disabled", text="Pausar")
        self.export_button.configure(state="normal" if self.results else "disabled")

    def toggle_pause(self) -> None:
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_button.configure(text="Continuar")
            self.status_label.configure(text="Consulta pausada")
        else:
            self.pause_event.set()
            self.pause_button.configure(text="Pausar")

    def export(self) -> None:
        if not self.results:
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], initialfile="resultado_cnpj.xlsx")
        if not path:
            return
        try:
            export_results(path, self.results)
        except OSError as exc:
            messagebox.showerror("Erro ao exportar", str(exc))
            return
        messagebox.showinfo("Exportação concluída", f"Resultados salvos em:\n{path}")


if __name__ == "__main__":
    CNPJApp().mainloop()
