#!/usr/bin/python3

# pip install GitPython

import os
import sys
import json
import random
from PyQt5 import QtWidgets, QtCore
from git import Repo, GitCommandError

class CreateProjectApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Create Yolo Annotation Project")
        self.dataset_path = ""
        self.init_ui()
    
    def init_ui(self):
        # Widget central
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Toolbar exemplo (você pode adicionar actions depois)
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.addAction("Example Action")
        
        # Selecionar pasta do dataset
        self.btn_select_dataset = QtWidgets.QPushButton("Select Dataset Folder")
        self.btn_select_dataset.clicked.connect(self.select_dataset)
        layout.addWidget(self.btn_select_dataset)
        
        # Tabela de usuários e proporção
        layout.addWidget(QtWidgets.QLabel("Users and proportions:"))
        self.user_table = QtWidgets.QTableWidget(0, 2)
        self.user_table.setHorizontalHeaderLabels(["User", "Proportion"])
        self.user_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.user_table)
        
        h_layout_user = QtWidgets.QHBoxLayout()
        self.btn_add_user = QtWidgets.QPushButton("Add User")
        self.btn_add_user.clicked.connect(self.add_user_row)
        h_layout_user.addWidget(self.btn_add_user)
        
        self.btn_remove_user = QtWidgets.QPushButton("Remove user")
        self.btn_remove_user.clicked.connect(self.remove_user_row)
        h_layout_user.addWidget(self.btn_remove_user)
        layout.addLayout(h_layout_user)
        
        # --- Classes ---
        layout.addWidget(QtWidgets.QLabel("Annotation classes:"))
        self.class_table = QtWidgets.QTableWidget(0, 1)
        self.class_table.setHorizontalHeaderLabels(["Class"])
        self.class_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.class_table)
        
        h_layout_class = QtWidgets.QHBoxLayout()
        self.btn_add_class = QtWidgets.QPushButton("Add class")
        self.btn_add_class.clicked.connect(self.add_class_row)
        h_layout_class.addWidget(self.btn_add_class)
        
        self.btn_remove_class = QtWidgets.QPushButton("Remove class")
        self.btn_remove_class.clicked.connect(self.remove_class_row)
        h_layout_class.addWidget(self.btn_remove_class)
        layout.addLayout(h_layout_class)
        
        # Input URL Git
        self.input_git_url = QtWidgets.QLineEdit()
        self.input_git_url.setPlaceholderText("Git repository url")
        layout.addWidget(self.input_git_url)
        
        # Botão criar projeto (só ativa no final)
        self.btn_create = QtWidgets.QPushButton("Create project")
        self.btn_create.clicked.connect(self.create_project)
        layout.addWidget(self.btn_create)
    
    # --------------------------
    # Funções GUI
    # --------------------------
    def select_dataset(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select dataset folder")
        if folder:
            self.dataset_path = folder
            QtWidgets.QMessageBox.information(self, "Selected", f"Selected folder:\n{folder}")
    
    # Usuários
    def add_user_row(self):
        row = self.user_table.rowCount()
        self.user_table.insertRow(row)
        self.user_table.setItem(row, 0, QtWidgets.QTableWidgetItem(f"user{row+1}"))
        self.user_table.setItem(row, 1, QtWidgets.QTableWidgetItem("1"))  # proporção padrão 1
    
    def remove_user_row(self):
        row = self.user_table.currentRow()
        if row >= 0:
            self.user_table.removeRow(row)
    
    # Classes
    def add_class_row(self):
        row = self.class_table.rowCount()
        self.class_table.insertRow(row)
        self.class_table.setItem(row, 0, QtWidgets.QTableWidgetItem(f"class{row+1}"))
    
    def remove_class_row(self):
        row = self.class_table.currentRow()
        if row >= 0:
            self.class_table.removeRow(row)
    
    # --------------------------
    # Criar projeto
    # --------------------------
    def create_project(self):
        if not self.dataset_path:
            QtWidgets.QMessageBox.warning(self, "Error", "Select the dataset folder!")
            return
        
        images_path = os.path.join(self.dataset_path, "images")
        labels_path = os.path.join(self.dataset_path, "labels")
        config_path = os.path.join(self.dataset_path, "config.json")
        
        # Verifica se existem imagens
        all_images = [f for f in os.listdir(images_path) if f.lower().endswith(".png")]
        if not all_images:
            QtWidgets.QMessageBox.warning(self, "Error", "No PNG image found in the Images folder!")
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
                QtWidgets.QMessageBox.warning(self, "Error", f"Invalid proportion on the line {row+1}")
                return
            users.append(user_item.text())
            proportions.append(prop)
        
        if not users:
            QtWidgets.QMessageBox.warning(self, "Error", "Add at least one user!")
            return
        
        # Lê classes
        classes = []
        for row in range(self.class_table.rowCount()):
            class_item = self.class_table.item(row, 0)
            if class_item:
                classes.append(class_item.text())
        if not classes:
            QtWidgets.QMessageBox.warning(self, "Error", "Add at least one class!")
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
            "birth_date": QtCore.QDateTime.currentDateTime().toString(QtCore.Qt.ISODate)
        }
        for user, imgs in images_per_user.items():
            config_data[f"images_{user}"] = [ {"filename": img_fn, "approved":False } for img_fn in imgs]
        
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=4)
        
        QtWidgets.QMessageBox.information(self, "Success", "Project created successfully!\nGenerated config.json")
        
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
                repo.index.commit("Initial annotation project commit")
                
                origin = None
                try:
                    origin = repo.remote(name="origin")
                    origin.set_url(git_url)
                except ValueError:
                    origin = repo.create_remote("origin", git_url)
                
                origin.push(refspec='master:master')
                QtWidgets.QMessageBox.information(self, "Git", "Initial commit submitted to remote repository!")
            except GitCommandError as e:
                QtWidgets.QMessageBox.warning(self, "Git Error", f"Error sending to Git:\n{str(e)}")
        
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = CreateProjectApp()
    window.show()
    sys.exit(app.exec_())


