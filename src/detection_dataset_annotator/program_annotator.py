#!/usr/bin/python3

import os
import sys
import json
import subprocess
import signal

from PyQt5 import QtWidgets, QtCore, QtGui
from git import Repo, GitCommandError
#from natsort import natsorted

from PyQt5.QtWidgets import ( QMainWindow, QGraphicsItem, QGraphicsSimpleTextItem, 
    QApplication, QSizePolicy, QWidget, QAction, QFileDialog, QGraphicsScene,
    QGraphicsRectItem, QHBoxLayout, QVBoxLayout, QGraphicsView, QSplitter, QMessageBox, 
    QTableWidgetItem, QPushButton, QInputDialog, QLabel, QTableWidget, QAbstractItemView,
    QHeaderView)
from PyQt5.QtCore import Qt, QUrl, QRectF
from PyQt5.QtGui import QDesktopServices, QIcon, QColor, QPen, QBrush, QPainter, QPixmap

import detection_dataset_annotator.about as about
import detection_dataset_annotator.modules.configure as configure 
from detection_dataset_annotator.desktop import create_desktop_file, create_desktop_directory, create_desktop_menu
from detection_dataset_annotator.modules.wabout  import show_about_window

CONFIG_PATH = os.path.join( os.path.expanduser("~"),
                            ".config",
                            about.__package__,
                            about.__program_name__+".json")

DEFAULT_CONTENT={   "toolbar_configure": "Configure",
                    "toolbar_configure_tooltip": "Open the configure Json file",
                    "toolbar_about": "About",
                    "toolbar_about_tooltip": "About the program",
                    "toolbar_coffee": "Coffee",
                    "toolbar_coffee_tooltip": "Buy me a coffee (TrucomanX)",
                    "window_width": 1200,
                    "window_height": 800,
                    "select_dataset_folder": "Select dataset folder",
                    "to_annotate": "<b>To Annotate:</b>",
                    "annotated": "<b>Annotated:</b>",
                    "commit_and_push": "Commit & Push",
                    "approve": "Approve",
                    "error": "Error",
                    "config_no_found": "No users found in config.json",
                    "select_user": "Select User",
                    "choose_your_user": "Choose your user:",
                    "remote_url": "Remote URL",
                    "enter_git_remote_url": "Enter Git remote URL:",
                    "git_remote": "origin",
                    "error_git": "Git Error",
                    "update_annotations_by": "Update annotations by",
                    "not_found": "not found!",
                    "name_git": "Git",
                    "changes_pushed": "Changes pushed!",
                    "no_save_config": "Could not save config.json:"
                }

configure.verify_default_config(CONFIG_PATH,default_content=DEFAULT_CONTENT)

CONFIG=configure.load_config(CONFIG_PATH)

# -------------------------------
# Bounding Box
# -------------------------------
class BoundingBox(QGraphicsRectItem):
    HANDLE_SIZE = 6

    def __init__(self, rect, class_name, color, parent=None):
        super().__init__(rect)
        self.setFlags(
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)  # necessário para redimensionar
        self.resizing = False
        self.resize_direction = None  # "bottom_right", etc

        self.class_name = class_name
        self.color = color
        self.text_item = QGraphicsSimpleTextItem(class_name, self)
        self.update_label_position()
        self.setPen(QPen(color, 2))
        self.setBrush(QBrush(QColor(0,0,0,0)))

    def update_label_position(self):
        rect = self.rect()
        self.text_item.setPos(rect.x(), rect.y() - 15)

    def hoverMoveEvent(self, event):
        # Detecta se o mouse está próximo do canto inferior direito
        rect = self.rect()
        br_rect = QRectF(   rect.right()-self.HANDLE_SIZE, 
                            rect.bottom()-self.HANDLE_SIZE,
                            self.HANDLE_SIZE*2, 
                            self.HANDLE_SIZE*2)
        if br_rect.contains(event.pos()):
            self.setCursor(Qt.SizeFDiagCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        rect = self.rect()
        br_rect = QRectF(   rect.right()-self.HANDLE_SIZE, 
                            rect.bottom()-self.HANDLE_SIZE,
                            self.HANDLE_SIZE*2, 
                            self.HANDLE_SIZE*2)
        if br_rect.contains(event.pos()):
            self.resizing = True
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            rect = self.rect()
            rect.setBottomRight(event.pos())
            self.setRect(rect)
            self.update_label_position()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.resizing = False
        super().mouseReleaseEvent(event)


# -------------------------------
# Custom Scene para desenhar boxes
# -------------------------------
class AnnotateScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.adding_class = None
        self.temp_rect_item = None
        self.start_pos = None
        self.box_items = []

    def set_adding_class(self, class_name):
        self.adding_class = class_name

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            # Remove todos os boxes selecionados
            for item in self.selectedItems():
                if isinstance(item, BoundingBox):
                    self.removeItem(item)
                    if item in self.box_items:
                        self.box_items.remove(item)
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if self.adding_class:
            self.start_pos = event.scenePos()
            self.temp_rect_item = QGraphicsRectItem(QRectF(self.start_pos, self.start_pos))
            self.temp_rect_item.setPen(QPen(QColor(255,0,0),2,Qt.DashLine))
            self.addItem(self.temp_rect_item)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.temp_rect_item:
            rect = QRectF(self.start_pos, event.scenePos()).normalized()
            self.temp_rect_item.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.temp_rect_item:
            rect = self.temp_rect_item.rect()
            if rect.width() > 5 and rect.height() > 5:
                color = QColor.fromHsv(hash(self.adding_class)%360, 255, 200)
                box = BoundingBox(rect, self.adding_class, color)
                self.addItem(box)
                self.box_items.append(box)
            self.removeItem(self.temp_rect_item)
            self.temp_rect_item = None
            self.adding_class = None
        else:
            super().mouseReleaseEvent(event)

# -------------------------------
# Main App
# -------------------------------
class AnnotateYoloApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(about.__program_name__)
        self.resize(CONFIG["window_width"], CONFIG["window_height"])

        ## Icon
        # Get base directory for icons
        base_dir_path = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(base_dir_path, 'icons', 'logo.png')
        self.setWindowIcon(QIcon(self.icon_path)) 
        
        self.dataset_path = ""
        self.repo = None
        self.config = {}
        self.user = ""
        self.current_image = ""
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
            "program_name": about.__program_name__,
            "author": about.__author__,
            "email": about.__email__,
            "description": about.__description__,
            "url_source": about.__url_source__,
            "url_doc": about.__url_doc__,
            "url_funding": about.__url_funding__,
            "url_bugs": about.__url_bugs__
        }
        show_about_window(data,self.icon_path)

    # -------------------------------
    # UI
    # -------------------------------
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        central.setLayout(main_layout)

        # Left panel
        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout()
        left_panel_widget.setLayout(left_panel_layout)

        self.btn_select_dataset = QPushButton(CONFIG["select_dataset_folder"])
        self.btn_select_dataset.setIcon(QIcon.fromTheme("folder-open")) 
        self.btn_select_dataset.clicked.connect(self.select_dataset)
        left_panel_layout.addWidget(self.btn_select_dataset)

        left_panel_layout.addWidget(QLabel(CONFIG["to_annotate"]))
        self.table_todo = QTableWidget(0,1)
        self.table_todo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_todo.setSelectionBehavior(QAbstractItemView.SelectItems)  # célula por célula
        self.table_todo.setSelectionMode(QAbstractItemView.ExtendedSelection)  # múltiplas seleções
        #self.table_todo.setTextElideMode(QtCore.Qt.ElideNone)  # evita cortar texto visualmente
        self.table_todo.setDragEnabled(False)
        self.table_todo.setHorizontalHeaderLabels(["Image"])
        self.table_todo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_todo.itemSelectionChanged.connect(self.display_selected_image)
        left_panel_layout.addWidget(self.table_todo)

        left_panel_layout.addWidget(QLabel(CONFIG["annotated"]))
        self.table_done = QTableWidget(0,1)
        self.table_done.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_done.setSelectionBehavior(QAbstractItemView.SelectItems)  # célula por célula
        self.table_done.setSelectionMode(QAbstractItemView.ExtendedSelection)  # múltiplas seleções
        #self.table_done.setTextElideMode(QtCore.Qt.ElideNone)  # evita cortar texto visualmente
        self.table_done.setDragEnabled(False)
        self.table_done.setHorizontalHeaderLabels(["Image"])
        self.table_done.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_done.itemSelectionChanged.connect(self.display_selected_image)
        left_panel_layout.addWidget(self.table_done)

        self.btn_commit = QPushButton(CONFIG["commit_and_push"])
        self.btn_commit.setIcon(QIcon.fromTheme("go-next")) 
        self.btn_commit.clicked.connect(self.commit_push)
        left_panel_layout.addWidget(self.btn_commit)

        # Right panel
        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout()
        right_panel_widget.setLayout(right_panel_layout)

        btn_approve = QPushButton(CONFIG["approve"])
        btn_approve.setIcon(QIcon.fromTheme("insert-object")) 
        btn_approve.clicked.connect(lambda: self.approve_image())
        right_panel_layout.addWidget(btn_approve)

        self.lbl_current_image = QLabel("...")
        self.lbl_current_image.setAlignment(Qt.AlignCenter)
        right_panel_layout.addWidget(self.lbl_current_image)

        self.scene = AnnotateScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        right_panel_layout.addWidget(self.view)

        self.class_buttons_layout = QHBoxLayout()
        right_panel_layout.addLayout(self.class_buttons_layout)

        # QSplitter para fronteira móvel
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel_widget)
        splitter.addWidget(right_panel_widget)
        splitter.setStretchFactor(0, 1)  # left panel
        splitter.setStretchFactor(1, 6)  # right panel

        main_layout.addWidget(splitter)


    def change_selected_box_class(self, new_class):       
        try:
            cls_id = self.classes.index(new_class)
        except ValueError:
            return
        
        
        for box in self.scene.selectedItems():
            if isinstance(box, BoundingBox):
                box.class_name = new_class
                box.text_item.setText(new_class)
                # Atualiza cor
                box.color = QColor(self.classes_colors[cls_id])
                box.setPen(QPen(box.color, 2))
                box.text_item.setBrush(QBrush(box.color))

    # -------------------------------
    # Dataset / User
    # -------------------------------
    def select_dataset(self):
        folder = QFileDialog.getExistingDirectory(self,CONFIG["select_dataset_folder"])
        if folder:
            self.dataset_path = folder
            self.load_config()

            users = [key.replace("images_","") for key in self.config if key.startswith("images_")]
            if not users:
                QMessageBox.warning(self,CONFIG["error"],CONFIG["config_no_found"])
                return
            user, ok = QInputDialog.getItem(self,CONFIG["select_user"],CONFIG["choose_your_user"],users,0,False)
            if not ok: return
            self.user = user

            self.init_git()
            self.populate_tables()
            self.create_class_buttons()

    # -------------------------------
    # Git
    # -------------------------------
    def init_git(self):
        try:
            if not os.path.exists(os.path.join(self.dataset_path,".git")):
                self.repo = Repo.init(self.dataset_path)
            else:
                self.repo = Repo(self.dataset_path)

            if not self.repo.remotes:
                git_url, ok = QInputDialog.getText(self,CONFIG["remote_url"],CONFIG["enter_git_remote_url"])
                if ok and git_url:
                    self.repo.create_remote(CONFIG["git_remote"],git_url)
        except GitCommandError as e:
            QMessageBox.warning(self,CONFIG["error_git"],str(e))

    def commit_push(self):
        if not self.repo: return
        try:
            self.repo.git.add("labels")
            self.repo.git.add("config.json")
            self.repo.index.commit(CONFIG["update_annotations_by"]+f" {self.user}")
            for remote in self.repo.remotes:
                branch = self.repo.active_branch
                try:
                    remote.push(refspec=f"{branch.name}:{branch.name}", set_upstream=True)
                except GitCommandError:
                    remote.push(refspec=f"{branch.name}:{branch.name}")
            QMessageBox.information(self,CONFIG["name_git"],CONFIG["changes_pushed"])
        except GitCommandError as e:
            QMessageBox.warning(self,CONFIG["error_git"],str(e))

    # -------------------------------
    # Config
    # -------------------------------
    def load_config(self):
        config_path = os.path.join(self.dataset_path, "config.json")
        if not os.path.exists(config_path):
            QMessageBox.warning(self,CONFIG["error"],"config.json "+CONFIG["not_found"])
            return
        with open(config_path,"r") as f:
            self.config = json.load(f)
        self.classes = self.config.get("classes",[])
        self.classes_colors = self.config.get("classes_colors",[])

    def save_config(self):
        config_path = os.path.join(self.dataset_path, "config.json")
        try:
            with open(config_path, "w") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, CONFIG["error"], CONFIG["no_save_config"] + f"\n{e}")

    # -------------------------------
    # Tables
    # -------------------------------
    def populate_tables(self):
        self.table_todo.setRowCount(0)
        self.table_done.setRowCount(0)
        
        user_data_images = self.config.get(f"images_{self.user}", {})
        
        #user_images = natsorted(user_images)

        for img_name in user_data_images:
            approved = user_data_images[img_name]
            
            img_path = os.path.join(self.dataset_path, "images", img_name)
            if not os.path.exists(img_path):
                continue

            # procura o txt correspondente
            label_path = os.path.join(
                self.dataset_path, "labels", img_name.replace(".png", ".txt")
            )

            table = self.table_todo if not approved else self.table_done
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(img_name))

    # -------------------------------
    # Class buttons
    # -------------------------------
    def create_class_buttons(self):
        # limpa os botões antigos
        for i in reversed(range(self.class_buttons_layout.count())):
            w = self.class_buttons_layout.itemAt(i).widget()
            if w: 
                w.setParent(None)
        
        # cria os novos botões
        for cls, color in zip(self.classes, self.classes_colors):
            btn = QPushButton(cls)
            
            # cria o quadrado colorido
            pixmap = QPixmap(24, 24)
            pixmap.fill(QColor(color))  # color pode ser "#335599" ou QColor
            icon = QIcon(pixmap)

            # adiciona o ícone ao botão
            btn.setIcon(icon)
            btn.setIconSize(QtCore.QSize(24, 24))
            
            # conecta o clique
            btn.clicked.connect(lambda checked,c=cls: self.on_class_button(c))
            
            # adiciona ao layout
            self.class_buttons_layout.addWidget(btn)


    def on_class_button(self, class_name):
        selected = self.scene.selectedItems()
        if selected:
            # Muda a classe de boxes selecionados
            self.change_selected_box_class(class_name)
        else:
            # Se nenhum box selecionado, adiciona um novo box
            self.start_adding_box(class_name)


    # -------------------------------
    # Display image
    # -------------------------------
    def display_selected_image(self):
        sender = self.sender()
        items = sender.selectedItems()
        if not items: 
            return

        img_name = items[0].text()
        self.current_image = img_name
        self.load_image_and_boxes(img_name)
        self.lbl_current_image.setText(self.current_image)
        
        if sender is self.table_todo:
            self.table_done.clearSelection()
        elif sender is self.table_done:
            self.table_todo.clearSelection()

    def load_image_and_boxes(self,img_name):
        self.scene.clear()
        self.scene.box_items = []
        img_path = os.path.join(self.dataset_path,"images",img_name)
        pixmap = QPixmap(img_path)
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.view.fitInView(self.pixmap_item,Qt.KeepAspectRatio)

        # Load YOLO labels
        label_path = os.path.join(self.dataset_path,"labels",img_name.replace(".png",".txt"))
        if os.path.exists(label_path):
            w,h = pixmap.width(), pixmap.height()
            with open(label_path,"r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts)!=5: continue
                    cls_id, cx, cy, bw, bh = parts
                    cls_id = int(cls_id)
                    cx,cy,bw,bh = float(cx),float(cy),float(bw),float(bh)
                    x = (cx-bw/2)*w
                    y = (cy-bh/2)*h
                    rect = QRectF(x,y,bw*w,bh*h)
                    color = QColor(self.classes_colors[cls_id])
                    box = BoundingBox(rect,self.classes[cls_id],color)
                    self.scene.addItem(box)
                    self.scene.box_items.append(box)

    # -------------------------------
    # Start adding box
    # -------------------------------
    def start_adding_box(self,class_name):
        self.scene.set_adding_class(class_name)

    # -------------------------------
    # Approve image
    # -------------------------------
    def approve_image(self):
        if not self.current_image: return
        label_path = os.path.join(self.dataset_path,"labels",self.current_image.replace(".png",".txt"))
        
        if self.scene.box_items:
            w = self.pixmap_item.pixmap().width()
            h = self.pixmap_item.pixmap().height()
            with open(label_path,"w") as f:
                for box in self.scene.box_items:
                    rect = box.rect()
                    cx = (rect.x()+rect.width()/2)/w
                    cy = (rect.y()+rect.height()/2)/h
                    bw = rect.width()/w
                    bh = rect.height()/h
                    cls_id = self.classes.index(box.class_name)
                    f.write(f"{cls_id} {cx} {cy} {bw} {bh}\n")
        
        # Update tables
        items = self.table_todo.findItems(self.current_image,Qt.MatchExactly)
        if items:
            row = items[0].row()
            self.table_todo.removeRow(row)
            row_done = self.table_done.rowCount()
            self.table_done.insertRow(row_done)
            self.table_done.setItem(row_done,0,QTableWidgetItem(self.current_image))

        self.config[f"images_{self.user}"][self.current_image]=True
        self.save_config()
        
# -------------------------------
# Main
# -------------------------------
def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    create_desktop_directory()    
    create_desktop_menu()
    create_desktop_file('~/.local/share/applications')
    
    for n in range(len(sys.argv)):
        if sys.argv[n] == "--autostart":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file('~/.config/autostart', overwrite=True)
            return
        if sys.argv[n] == "--applications":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file('~/.local/share/applications', overwrite=True)
            return
    
    app = QApplication(sys.argv)
    app.setApplicationName(about.__package__) 
    
    window = AnnotateYoloApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

