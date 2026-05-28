# -*- coding: utf-8 -*-
import logging
from rich.console import Console
from rich.progress import (
    Progress, 
    TextColumn, 
    BarColumn, 
    TaskProgressColumn, 
    TimeRemainingColumn,
    SpinnerColumn
)
from rich.panel import Panel
from rich.text import Text

class PipelineConsoleUI:
    """
    Monitor de Consola usando Rich para mostrar el progreso del pipeline S2-PROCESS Cloud.
    Oculta los logs técnicos y presenta una interfaz limpia y corporativa.
    """
    def __init__(self):
        self.console = Console()
        # Progreso principal (Etapas)
        self.main_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            console=self.console,
            transient=False
        )
        # Progreso secundario (Descargas S3 / Tareas largas con ETA)
        self.sub_progress = Progress(
            TextColumn("[cyan]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True
        )
        self.main_task_id = None
        self.sub_task_id = None

    def display_header(self, segment_name):
        """Muestra un panel elegante al inicio del segmento."""
        self.console.print("\n")
        panel = Panel(
            Text(f"[ SEGMENTO: {segment_name} ]", justify="center", style="bold white"),
            border_style="blue",
            expand=False
        )
        self.console.print(panel)
        self.console.print("\n")

    def start_pipeline(self, total_stages=7):
        self.main_progress.start()
        self.sub_progress.start()
        self.main_task_id = self.main_progress.add_task("Iniciando Pipeline Cloud...", total=total_stages)

    def stop_pipeline(self):
        self.sub_progress.stop()
        self.main_progress.stop()

    def update_stage(self, stage_text, stage_num=None):
        """Actualiza el texto principal de la Etapa y avanza la barra (opcional)"""
        logging.info(stage_text) # Enviar al archivo .log
        if self.main_task_id is not None:
            advance = 1 if stage_num else 0
            self.main_progress.update(self.main_task_id, description=f"[bold blue]{stage_text}", advance=advance)

    def start_subtask(self, description, total=100.0):
        """Inicia una sub-tarea donde mediremos el porcentaje"""
        if self.sub_task_id is not None:
            self.sub_progress.remove_task(self.sub_task_id)
        self.sub_task_id = self.sub_progress.add_task(description, total=total)

    def update_subtask_progress(self, current_val):
        """Actualiza el valor actual de la sub-tarea (0 a 100)"""
        if self.sub_task_id is not None:
            self.sub_progress.update(self.sub_task_id, completed=float(current_val))

    def complete_subtask(self):
        """Marca la subtarea como 100% y la borra"""
        if self.sub_task_id is not None:
            self.sub_progress.update(self.sub_task_id, completed=100.0)
            self.sub_task_id = None

    def print_success(self, msg):
        logging.info(msg)
        self.console.print(f"[bold green]✔[/bold green] {msg}")

    def print_error(self, msg):
        logging.error(msg)
        self.console.print(f"[bold red]✘ ERROR:[/bold red] {msg}")
