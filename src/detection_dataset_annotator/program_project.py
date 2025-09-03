#!/usr/bin/python3

import os
import sys
import json
import random
import subprocess
import signal

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QLabel, QLineEdit, QFileDialog, QSizePolicy, QMessageBox, 
    QMainWindow, QAction)
from PyQt5.QtCore import Qt, QUrl, QDateTime, QSize
from PyQt5.QtGui import QDesktopServices, QIcon
    
from git import Repo, GitCommandError

import detection_dataset_annotator.about as about
import detection_dataset_annotator.modules.configure as configure 
from detection_dataset_annotator.modules.wabout  import show_about_window

CONFIG_PATH = os.path.join( os.path.expanduser("~"),
                            ".config",
                            about.__package__,
                            about.__program_project__+".json")

DEFAULT_CONTENT={   "toolbar_configure": "Configure",
                    "toolbar_configure_tooltip": "Open the configure Json file",
                    "toolbar_about": "About",
                    "toolbar_about_tooltip": "About the program",
                    "toolbar_coffee": "Coffee",
                    "toolbar_coffee_tooltip": "Buy me a coffee (TrucomanX)",
                    "window_width": 600,
                    "window_height": 600,
                    "select_dataset_folder": "Select dataset folder",
                    "select_dataset_folder_tooltip": "Select the directory with a dataset in YOLO style, which must include a mandatory subdirectory \"images\" containing image files.",
                    "users_and_proportions": "Users and proportions:",
                    "user": "User",
                    "proportion": "Proportion",
                    "add_user": "Add user",
                    "remove_user": "Remove user",
                    "annotation_classes": "Annotation classes:",
                    "class": "Class",
                    "add_class": "Add class",
                    "remove_class": "Remove class",
                    "git_repository_url":"Git repository url",
                    "create_project": "Create project",
                    "selected_folder": "Selected folder:",
                    "selected": "Selected",
                    "error": "Error",
                    "select_the_dataset_folder": "Select the dataset folder!",
                    "no_png_image": "No PNG image found in the Images folder!",
                    "invalid_proportion_in_line": "Invalid proportion on the line",
                    "add_one_user": "Add at least one user!",
                    "add_one_class": "Add at least one class!",
                    "success": "Success",
                    "project_created": "Project created successfully!\nGenerated config.json",
                    "git_initial_commit": "Initial annotation project commit",
                    "git_remote": "origin",
                    "git_msg_title": "Git",
                    "git_msg_text": "Initial commit submitted to remote repository!",
                    "git_msg_error": "Git error",
                    "git_msg_error_text": "Error sending to Git:"
                }


configure.verify_default_config(CONFIG_PATH,default_content=DEFAULT_CONTENT)

CONFIG=configure.load_config(CONFIG_PATH)

class CreateProjectApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(about.__program_project__)
        self.resize(CONFIG["window_width"], CONFIG["window_height"])
        
        ## Icon
        # Get base directory for icons
        base_dir_path = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(base_dir_path, 'icons', 'logo.png')
        self.setWindowIcon(QIcon(self.icon_path)) 
        
        self.dataset_path = ""
        self.create_toolbar()
        self.init_ui()
        
    def create_toolbar(self):
        # Toolbar exemplo (você pode adicionar actions depois)
        self.toolbar = self.addToolBar("Main Toolbar")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        
        # Adicionar o espaçador
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        #
        self.configure_action = QAction(QIcon.fromTheme("document-properties"), CONFIG["toolbar_configure"], self)
        self.configure_action.setToolTip(CONFIG["toolbar_configure_tooltip"])
        self.configure_action.triggered.connect(self.open_configure_editor)
        
        #
        self.about_action = QAction(QIcon.fromTheme("help-about"), CONFIG["toolbar_about"], self)
        self.about_action.setToolTip(CONFIG["toolbar_about_tooltip"])
        self.about_action.triggered.connect(self.open_about)
        
        # Coffee
        self.coffee_action = QAction(QIcon.fromTheme("emblem-favorite"), CONFIG["toolbar_coffee"], self)
        self.coffee_action.setToolTip(CONFIG["toolbar_coffee_tooltip"])
        self.coffee_action.triggered.connect(self.on_coffee_action_click)
    
        self.toolbar.addWidget(spacer)
        self.toolbar.addAction(self.configure_action)
        self.toolbar.addAction(self.about_action)
        self.toolbar.addAction(self.coffee_action)
    
    def open_configure_editor(self):
        if os.name == 'nt':  # Windows
            os.startfile(CONFIG_PATH)
        elif os.name == 'posix':  # Linux/macOS
            subprocess.run(['xdg-open', CONFIG_PATH])

    def on_coffee_action_click(self):
        QDesktopServices.openUrl(QUrl("https://ko-fi.com/trucomanx"))
    
    def open_about(self):
        data={
            "version": about.__version__,
            "package": about.__package__,
            "program_name": about.__program_project__,
            "author": about.__author__,
            "email": about.__email__,
            "description": about.__description__,
            "url_source": about.__url_source__,
            "url_doc": about.__url_doc__,
            "url_funding": about.__url_funding__,
            "url_bugs": about.__url_bugs__
        }
        show_about_window(data,self.icon_path)
    
    def init_ui(self):
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        

        
        # Selecionar pasta do dataset
        self.btn_select_dataset = QPushButton(CONFIG["select_dataset_folder"])
        self.btn_select_dataset.setIcon(QIcon.fromTheme("folder-open")) 
        self.btn_select_dataset.clicked.connect(self.select_dataset)
        layout.addWidget(self.btn_select_dataset)
        
        # Tabela de usuários e proporção
        layout.addWidget(QLabel(CONFIG["users_and_proportions"]))
        self.user_table = QTableWidget(0, 2)
        self.user_table.setHorizontalHeaderLabels([CONFIG["user"], CONFIG["proportion"]])
        self.user_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.user_table)
        
        h_layout_user = QHBoxLayout()
        self.btn_add_user = QPushButton(CONFIG["add_user"])
        self.btn_add_user.setIcon(QIcon.fromTheme("list-add"))
        self.btn_add_user.clicked.connect(self.add_user_row)
        h_layout_user.addWidget(self.btn_add_user)
        
        self.btn_remove_user = QPushButton(CONFIG["remove_user"])
        self.btn_remove_user.setIcon(QIcon.fromTheme("list-remove")) 
        self.btn_remove_user.clicked.connect(self.remove_user_row)
        h_layout_user.addWidget(self.btn_remove_user)
        layout.addLayout(h_layout_user)
        
        # --- Classes ---
        layout.addWidget(QLabel(CONFIG["annotation_classes"]))
        self.class_table = QTableWidget(0, 1)
        self.class_table.setHorizontalHeaderLabels([CONFIG["class"]])
        self.class_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.class_table)
        
        h_layout_class = QHBoxLayout()
        self.btn_add_class = QPushButton(CONFIG["add_class"])
        self.btn_add_class.setIcon(QIcon.fromTheme("list-add")) 
        self.btn_add_class.clicked.connect(self.add_class_row)
        h_layout_class.addWidget(self.btn_add_class)
        
        self.btn_remove_class = QPushButton(CONFIG["remove_class"])
        self.btn_remove_class.setIcon(QIcon.fromTheme("list-remove")) 
        self.btn_remove_class.clicked.connect(self.remove_class_row)
        h_layout_class.addWidget(self.btn_remove_class)
        layout.addLayout(h_layout_class)
        
        # Input URL Git
        self.input_git_url = QLineEdit()
        self.input_git_url.setPlaceholderText(CONFIG["git_repository_url"])
        layout.addWidget(self.input_git_url)
        
        # Botão criar projeto (só ativa no final)
        self.btn_create = QPushButton(CONFIG["create_project"])
        self.btn_create.setIcon(QIcon.fromTheme("document-new")) 
        self.btn_create.setIconSize(QSize(32, 32))
        self.btn_create.setStyleSheet("font-weight: bold;")
        self.btn_create.clicked.connect(self.create_project)
        layout.addWidget(self.btn_create)
    
    # --------------------------
    # Funções GUI
    # --------------------------
    def select_dataset(self):
        folder = QFileDialog.getExistingDirectory(self, CONFIG["select_dataset_folder"])
        if folder:
            self.dataset_path = folder
            QMessageBox.information(self, CONFIG["selected"], CONFIG["selected_folder"]+f"\n{folder}")
    
    # Usuários
    def add_user_row(self):
        row = self.user_table.rowCount()
        self.user_table.insertRow(row)
        self.user_table.setItem(row, 0, QTableWidgetItem(f"user{row+1}"))
        self.user_table.setItem(row, 1, QTableWidgetItem("1"))  # proporção padrão 1
    
    def remove_user_row(self):
        row = self.user_table.currentRow()
        if row >= 0:
            self.user_table.removeRow(row)
    
    # Classes
    def add_class_row(self):
        row = self.class_table.rowCount()
        self.class_table.insertRow(row)
        self.class_table.setItem(row, 0, QTableWidgetItem(f"class{row+1}"))
    
    def remove_class_row(self):
        row = self.class_table.currentRow()
        if row >= 0:
            self.class_table.removeRow(row)
    
    # --------------------------
    # Criar projeto
    # --------------------------
    def create_project(self):
        if not self.dataset_path:
            QMessageBox.warning(self, CONFIG["error"], CONFIG["select_the_dataset_folder"]) 
            return
        
        images_path = os.path.join(self.dataset_path, "images")
        labels_path = os.path.join(self.dataset_path, "labels")
        config_path = os.path.join(self.dataset_path, "config.json")
        
        # Verifica se existem imagens
        all_images = [f for f in os.listdir(images_path) if f.lower().endswith(".png")]
        if not all_images:
            QMessageBox.warning(self, CONFIG["error"], CONFIG["no_png_image"])
            return
        
        # Ler usuários e proporções da tabela
        users = []
        proportions = []
        for row in range(self.user_table.rowCount()):
            user_item = self.user_table.item(row, 0)
            prop_item = self.user_table.item(row, 1)
            if user_item is None or prop_item is None:
                continue
            try:
                prop = int(prop_item.text())
            except ValueError:
                QMessageBox.warning(self, CONFIG["error"], CONFIG["invalid_proportion_in_line"]+f"{row+1}")
                return
            users.append(user_item.text())
            proportions.append(prop)
        
        if not users:
            QMessageBox.warning(self, CONFIG["error"], CONFIG["add_one_user"])
            return
        
        # Lê classes
        classes = []
        for row in range(self.class_table.rowCount()):
            class_item = self.class_table.item(row, 0)
            if class_item:
                classes.append(class_item.text())
        if not classes:
            QMessageBox.warning(self, CONFIG["error"], CONFIG["add_one_class"])
            return
        
        # Criar labels se não existir
        os.makedirs(labels_path, exist_ok=True)
        
        # Distribuir imagens conforme proporção
        random.shuffle(all_images)
        total_prop = sum(proportions)
        images_per_user = {user: [] for user in users}
        start_idx = 0
        for user, prop in zip(users, proportions):
            count = int(len(all_images) * prop / total_prop)
            images_per_user[user] = all_images[start_idx:start_idx+count]
            start_idx += count
        # Ajustar possíveis imagens restantes
        remaining = all_images[start_idx:]
        for i, img in enumerate(remaining):
            images_per_user[users[i % len(users)]].append(img)
        
        # Criar config.json
        config_data = {
            "classes": classes,
            "birth_date": QDateTime.currentDateTime().toString(Qt.ISODate)
        }
        for user, imgs in images_per_user.items():
            config_data[f"images_{user}"] = [ {"filename": img_fn, "approved":False } for img_fn in imgs]
        
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=4)
        
        QMessageBox.information(self, CONFIG["success"], CONFIG["project_created"])
        
        # Commit inicial no Git
        git_url = self.input_git_url.text().strip()
        if git_url:
            try:
                if not os.path.exists(os.path.join(self.dataset_path, ".git")):
                    repo = Repo.init(self.dataset_path)
                else:
                    repo = Repo(self.dataset_path)
                repo.git.add("labels")
                repo.git.add("config.json")
                repo.index.commit(CONFIG["git_initial_commit"])
                
                origin = None
                try:
                    origin = repo.remote(name=CONFIG["git_remote"])
                    origin.set_url(git_url)
                except ValueError:
                    origin = repo.create_remote(CONFIG["git_remote"], git_url)
                
                origin.push(refspec='master:master')
                QMessageBox.information(self, CONFIG["git_msg_title"], CONFIG["git_msg_text"])
            except GitCommandError as e:
                QMessageBox.warning(self, CONFIG["git_msg_error"], CONFIG["git_msg_error_text"]+f"\n{str(e)}")
        
        self.close()

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QApplication(sys.argv)
    app.setApplicationName(about.__package__) 
    
    window = CreateProjectApp()
    window.show()
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()


