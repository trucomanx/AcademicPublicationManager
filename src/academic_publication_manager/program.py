import sys
import json
import uuid
import os
import signal
import copy

from PyQt5.QtWidgets import (QApplication, QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QTableWidget, QTableWidgetItem, QLineEdit, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QTextEdit, QPushButton, QFileDialog, QScrollArea,
                             QMenu, QInputDialog, QMessageBox, QToolButton)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QIcon


import academic_publication_manager.about as about
from academic_publication_manager.desktop import create_desktop_file, create_desktop_directory, create_desktop_menu
from academic_publication_manager.modules.wabout     import show_about_window
from academic_publication_manager.modules.to_bibtex  import id_list_to_bibtex_string, bibtex_to_dicts
from academic_publication_manager.modules.production import fake_production

from copy import deepcopy


class CustomTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Referência à BibManager
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        self._highlighted_item = None  # Rastrear o item destacado

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        item = self.itemAt(event.pos())
        # Limpar destaque do item anterior
        if self._highlighted_item:
            self._highlighted_item.setBackground(0, QBrush())  # Fundo transparente
            self._highlighted_item = None

        if item and item.data(0, Qt.UserRole):  # Não permitir soltar em produção
            event.ignore()
        else:
            # Destacar o item de destino válido
            target_item = item if item else self.invisibleRootItem()
            if target_item != self.invisibleRootItem():  # Não destacar a raiz diretamente
                self._highlighted_item = target_item
                self._highlighted_item.setBackground(0, QBrush(QColor("#FFFF99")))  # Amarelo claro
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        # Limpar destaque quando o arrasto sai da árvore
        if self._highlighted_item:
            self._highlighted_item.setBackground(0, QBrush())  # Fundo transparente
            self._highlighted_item = None
        event.accept()

    def dropEvent(self, event):
        source_item = self.currentItem()
        drop_pos = self.dropIndicatorPosition()
        target_item = self.itemAt(event.pos())

        # Limpar destaque ao soltar
        if self._highlighted_item:
            self._highlighted_item.setBackground(0, QBrush())  # Fundo transparente
            self._highlighted_item = None

        if not source_item:
            event.ignore()
            return

        # Determinar o item pai de destino
        if target_item:
            if drop_pos in (QTreeWidget.AboveItem, QTreeWidget.BelowItem):
                parent_item = target_item.parent() or self.invisibleRootItem()
            else:  # OnItem
                if target_item.data(0, Qt.UserRole):  # Não permitir soltar em produção
                    event.ignore()
                    return
                parent_item = target_item
        else:
            parent_item = self.invisibleRootItem()

        # Obter os caminhos do item origem e destino
        source_path = self.main_window.get_item_path(source_item)
        target_path = self.main_window.get_item_path(parent_item)

        # Verificar se o movimento é válido
        if source_path == target_path or source_path in [target_path + [source_path[-1]]]:
            event.ignore()
            return

        # Determinar se o item é uma pasta ou produção
        source_name = source_path[-1]
        is_production = bool(source_item.data(0, Qt.UserRole))

        # Para produções, extrair o ID real
        if is_production:
            source_name = self.main_window.extract_id_from_text(source_item.text(0))

        # Obter a estrutura do item origem
        current = self.main_window.data["structure"]
        for key in source_path[:-1]:
            if key not in current:
                event.ignore()
                return
            current = current[key]
        if source_name not in current:
            event.ignore()
            return
        source_data = deepcopy(current[source_name])  # Fazer cópia profunda

        # Verificar se o destino é válido
        current = self.main_window.data["structure"]
        for key in target_path:
            if key not in current:
                event.ignore()
                return
            current = current[key]
        if not isinstance(current, dict):
            event.ignore()
            return

        # Adicionar o item no destino
        if is_production:
            if source_name not in self.main_window.data["productions"]:
                event.ignore()
                return
            current[source_name] = None
        else:
            current[source_name] = source_data

        # Remover o item da origem
        current = self.main_window.data["structure"]
        for key in source_path[:-1]:
            current = current[key]
        current.pop(source_name)  # Usar source_name (ID para produções, nome para pastas)

        # Salvar o arquivo
        self.main_window.save_file()

        # Preservar o estado expandido da árvore
        expanded_items = self.main_window.get_expanded_items()

        # Atualizar a árvore com atraso
        def update_tree_later():
            self.main_window.update_tree()
            self.main_window.restore_expanded_items(expanded_items)
            new_item = self.main_window.find_tree_item_by_path(target_path + [source_name])
            if new_item:
                self.setCurrentItem(new_item)
                # Expandir a pasta destino para mostrar a produção movida
                parent_item = new_item.parent() or self.tree_widget.invisibleRootItem()
                parent_item.setExpanded(True)
            else:
                print("Moved item not found after update")
        QTimer.singleShot(100, update_tree_later)

        event.acceptProposedAction()







class BibManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(about.__program_name__)
        self.setGeometry(100, 100, 1200, 600)
        
        ## Icon
        # Get base directory for icons
        base_dir_path = os.path.dirname(os.path.abspath(__file__))
        self.icon_path = os.path.join(base_dir_path, 'icons', 'logo.png')
        self.setWindowIcon(QIcon(self.icon_path)) 
        
        
        self.data = {"structure": {"Root":{}}, "productions": {}}
        self.current_file = None
        self.current_prod_id = None
        
        self.init_menubar()
        self.init_toolbar()
        self.init_ui()
        
        
        self.update_tree()
        self.table_widget.setRowCount(0)
        self.metadata_panel.setEnabled(False)
        self.save_metadata_btn.setEnabled(False)
        self.current_prod_id = None

    def init_menubar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Arquive")

        open_action = file_menu.addAction("Open tree from json")
        open_action.triggered.connect(self.open_file)
        
        save_action = file_menu.addAction("Save tree in json")
        save_action.triggered.connect(self.save_file)
        
        new_tree_action = file_menu.addAction("New tree")
        new_tree_action.triggered.connect(self.new_tree)

        gabout_menu = menubar.addMenu("About")
        about_program_action = gabout_menu.addAction("About program")
        about_program_action.triggered.connect(self.about_func)


    def init_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")

        # Botão Nova Árvore
        about_btn = QToolButton()
        about_btn.setText("About")
        about_btn.clicked.connect(self.about_func)
        about_btn.setIcon(QIcon.fromTheme("help-about"))
        about_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.addWidget(about_btn)
        

        # Botão Nova Árvore
        new_tree_btn = QToolButton()
        new_tree_btn.setText("New tree")
        new_tree_btn.clicked.connect(self.new_tree)
        new_tree_btn.setIcon(QIcon.fromTheme("document-new"))
        new_tree_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.addWidget(new_tree_btn)

        # Botão Abrir
        open_btn = QToolButton()
        open_btn.setText("Open tree")
        open_btn.clicked.connect(self.open_file)
        open_btn.setIcon(QIcon.fromTheme("document-open"))
        open_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.addWidget(open_btn)

        # Botão Salvar
        save_btn = QToolButton()
        save_btn.setText("Save tree")
        save_btn.clicked.connect(self.save_file)
        save_btn.setIcon(QIcon.fromTheme("document-save"))
        save_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.addWidget(save_btn)




    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        vertical_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(vertical_splitter)

        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        vertical_splitter.addWidget(top_widget)

        horizontal_splitter = QSplitter(Qt.Horizontal)

        top_layout.addWidget(horizontal_splitter)

        # Usar CustomTreeWidget em vez de QTreeWidget
        self.tree_widget = CustomTreeWidget(self)  # Passar self como parent para acessar métodos de BibManager
        self.tree_widget.setHeaderLabel("Folder structure")
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        horizontal_splitter.addWidget(self.tree_widget)

        self.metadata_panel = QWidget()
        metadata_layout = QVBoxLayout(self.metadata_panel)
        self.metadata_fields = {}
        self.metadata_panel.setEnabled(False)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.metadata_panel)
        horizontal_splitter.addWidget(scroll_area)


        self.save_metadata_btn = QPushButton("Save Metadata")
        self.save_metadata_btn.clicked.connect(self.save_metadata_func)
        metadata_layout.addWidget(self.save_metadata_btn)
        self.save_metadata_btn.setEnabled(False)

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        vertical_splitter.addWidget(bottom_widget)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Title", "ID"])
        self.table_widget.cellClicked.connect(self.on_table_row_clicked)
        bottom_layout.addWidget(self.table_widget)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filtrar por título ou ID...")
        self.filter_input.textChanged.connect(self.filter_table)
        bottom_layout.addWidget(self.filter_input)


        horizontal_splitter.setSizes([300, 300])
    
    
    def show_context_menu(self, position):
        item = self.tree_widget.itemAt(position)
        if item:
            menu = QMenu()
            
            # Delete 
            delete_action = menu.addAction( QIcon.fromTheme("edit-delete"),
                                            "Delete")
            delete_action.triggered.connect(lambda: self.delete_item(item))
            
            # Separator
            menu.addSeparator()
            
            if item.data(0, Qt.UserRole):  # É uma produção (folha)
                
                # Change ID
                change_id_action = menu.addAction(  QIcon.fromTheme("document-edit"),
                                                    "Change ID")
                change_id_action.triggered.connect(lambda: self.change_production_id(item))
                
                # Duplicate
                duplicate_action = menu.addAction(  QIcon.fromTheme("edit-copy"), 
                                                    "Duplicate Publication")
                duplicate_action.triggered.connect(lambda: self.duplicate_production(item))
                
                # Separator
                menu.addSeparator()
                
            else:  # É uma pasta
                # New folder
                new_folder_action = menu.addAction( QIcon.fromTheme("folder-new"),
                                                    "New folder")
                new_folder_action.triggered.connect(lambda: self.create_new_folder(item))
                
                # New production
                new_production_action = menu.addAction( QIcon.fromTheme("document-new"),
                                                        "New production")
                new_production_action.triggered.connect(lambda: self.create_new_production(item))
                
                # Rename folder
                rename_folder_action = menu.addAction(  QIcon.fromTheme("folder-visiting"),
                                                        "Rename folder")
                rename_folder_action.triggered.connect(lambda: self.rename_folder(item))
                
                # Separator
                menu.addSeparator()
                
                # load bibfile
                loadfrombib_action = menu.addAction( QIcon.fromTheme("document-open"),
                                                "Load from *.bib")
                loadfrombib_action.triggered.connect(lambda: self.loadfrombib_item(item))
            
            
            
            # Save bibfile
            saveasbib_action = menu.addAction( QIcon.fromTheme("document-save-as"),
                                            "Save as *.bib")
            saveasbib_action.triggered.connect(lambda: self.saveasbib_item(item))
            
            
                
            menu.exec_(self.tree_widget.viewport().mapToGlobal(position))

    def about_func(self):
        data={
            "version": about.__version__,
            "package": about.__package__,
            "program_name": about.__program_name__,
            "author": about.__author__,
            "email": about.__email__,
            "description": about.__description__,
            "url_source": about.__url_source__,
            "url_funding": about.__url_funding__,
            "url_bugs": about.__url_bugs__
        }
        show_about_window(data,self.icon_path)
    
    def duplicate_production(self, item):
        prod_id, parent_path = item.data(0, Qt.UserRole)
        while True:
            new_prod_id, ok = QInputDialog.getText(self, "Duplicate Publication", 
                                                  f"Enter new ID for duplicated '{prod_id}':", 
                                                  QLineEdit.Normal, f"{prod_id}_copy")
            if not ok or not new_prod_id:
                return
            if new_prod_id == prod_id:
                QMessageBox.warning(self, "Error", 
                                   "The new ID must be different from the original ID.")
                continue
            if self.production_exists(new_prod_id):
                QMessageBox.warning(self, "Error", 
                                   f"The ID '{new_prod_id}' already exists. Please choose another ID.")
                continue
            break

        # Copiar os metadados da produção original
        from copy import deepcopy
        original_prod = self.data["productions"].get(prod_id, {})
        new_prod = deepcopy(original_prod)
        self.data["productions"][new_prod_id] = new_prod

        # Adicionar a nova produção à mesma pasta pai
        current = self.data["structure"]
        for key in parent_path:
            current = current[key]
        current[new_prod_id] = None

        # Salvar e atualizar a interface
        self.save_file()
        
        # Preservar o estado expandido da árvore
        expanded_items = self.get_expanded_items()
        self.update_tree()
        self.restore_expanded_items(expanded_items)

        # Selecionar a nova produção
        new_item = self.find_tree_item_by_path(parent_path)
        if new_item:
            new_item.setExpanded(True)
            for i in range(new_item.childCount()):
                child = new_item.child(i)
                if self.extract_id_from_text(child.text(0)) == new_prod_id:
                    self.tree_widget.setCurrentItem(child)
                    self.on_tree_item_clicked(child, 0)
                    break
        else:
            print("Parent item not found after update")

    def get_expanded_items(self):
        expanded = []
        def collect_expanded(item, path):
            # Definir text apenas para itens não-raiz
            text = None
            if item != self.tree_widget.invisibleRootItem():
                text = item.text(0).split(" (")[0]
            # Verificar se o item está expandido
            if item.isExpanded() and text:  # Só adicionar se tiver texto (exclui raiz)
                expanded.append(path + [text])
            # Iterar pelos filhos
            for i in range(item.childCount()):
                new_path = path + [text] if text else path
                collect_expanded(item.child(i), new_path)
        collect_expanded(self.tree_widget.invisibleRootItem(), [])
        return expanded

    def restore_expanded_items(self, expanded_items):
        def find_and_expand(item, path):
            if not path:
                return
            # Definir text apenas para itens não-raiz
            text = None
            if item != self.tree_widget.invisibleRootItem():
                text = item.text(0).split(" (")[0]
            if text and path[0] == text:
                item.setExpanded(True)
                next_path = path[1:]
            else:
                next_path = path
            for i in range(item.childCount()):
                find_and_expand(item.child(i), next_path)
        for path in expanded_items:
            find_and_expand(self.tree_widget.invisibleRootItem(), path)

    def new_tree(self):
        confirm = QMessageBox.question(
            self, "New tree",
            "Do you want to erase the entire current structure and start from scratch?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.data = {"structure": {"Root":{}}, "productions": {}}
            self.current_prod_id = None
            self.current_file = None
            self.metadata_panel.setEnabled(False)
            self.save_metadata_btn.setEnabled(False)
            self.tree_widget.clear()
            self.table_widget.setRowCount(0)
                        
            self.update_tree()

    def create_new_folder(self, parent_item):
        folder_name, ok = QInputDialog.getText(self, "New tree", "Name of the new folder:")
        if ok and folder_name:
            path = self.get_item_path(parent_item)
            current = self.data["structure"]
            for key in path:
                current = current[key]
            current[folder_name] = {}
            self.save_file()
            self.update_tree()
            new_parent_item = self.find_tree_item_by_path(path)
            if new_parent_item:
                new_parent_item.setExpanded(True)
                self.tree_widget.setCurrentItem(new_parent_item)

    def add_production_to_structure_and_productions(self,parent_path,prod_id,production):
        current = self.data["structure"]
        for key in parent_path:
            current = current[key]
        
        current[prod_id] = None
        self.data["productions"][prod_id] = production

    def create_new_production(self, parent_item):
        while True:
            prod_id, ok = QInputDialog.getText(self, "New production", "Enter the new production ID:")
            if not ok or not prod_id:
                return
            if self.production_exists(prod_id):
                QMessageBox.warning(self, "Erro", f"The ID '{prod_id}' already exists. Please choose another ID.")
                continue
            break
        
        parent_path = self.get_item_path(parent_item)

        self.add_production_to_structure_and_productions(   parent_path,
                                                            prod_id,
                                                            copy.deepcopy(fake_production))
        
        self.save_file()
        self.update_tree()
        new_parent_item = self.find_tree_item_by_path(parent_path)
        if new_parent_item:
            new_parent_item.setExpanded(True)
            self.tree_widget.setCurrentItem(new_parent_item)
            self.on_tree_item_clicked(new_parent_item, 0)

    def production_exists(self, prod_id):
        return prod_id in self.data.get("productions", {})

    def rename_folder(self, item):
        old_name = item.text(0).split(" (")[0]
        path = self.get_item_path(item)
        new_name, ok = QInputDialog.getText(self, "Rename folder", "New folder name:", QLineEdit.Normal, old_name)
        if ok and new_name and new_name != old_name:
            current = self.data["structure"]
            for key in path[:-1]:
                current = current[key]
            if new_name in current:
                QMessageBox.warning(self, "Error", f"The folder '{new_name}' already exists at this level. Please choose another name.")
                return
            
            current[new_name] = current.pop(old_name)
            self.save_file()
            self.update_tree()
            
            
            new_path = path[:-1] + [new_name]
            new_item = self.find_tree_item_by_path(new_path)
            if new_item:
                new_item.setExpanded(True)
                self.tree_widget.setCurrentItem(new_item)


    def change_production_id(self, item):
        #print("item.text(0)",item.text(0))
        old_prod_id, parent_path = item.data(0, Qt.UserRole)
        while True:
            new_prod_id, ok = QInputDialog.getText( self, 
                                                    "Change ID", 
                                                    f"Enter new ID for '{old_prod_id}':", 
                                                    QLineEdit.Normal, 
                                                    old_prod_id)
            if not ok or not new_prod_id:
                return
            if new_prod_id == old_prod_id:
                return
            if self.production_exists(new_prod_id):
                QMessageBox.warning(self, 
                                    "Error", 
                                    f"The ID '{new_prod_id}' already exists. Please choose another ID.")
                continue
            break

        current = self.data["structure"]
        for key in parent_path:
            current = current[key]
        current[new_prod_id] = current.get(old_prod_id)
        current.pop(old_prod_id, None)
        if old_prod_id in self.data["productions"]:
            self.data["productions"][new_prod_id] = self.data["productions"].pop(old_prod_id)

        if self.current_prod_id == (old_prod_id, parent_path):
            self.current_prod_id = (new_prod_id, parent_path)

        self.save_file()
        self.update_tree()

        new_item = self.find_tree_item_by_path(parent_path)
        if new_item:
            new_item.setExpanded(True)
            # Agora procuramos entre os filhos
            for i in range(new_item.childCount()):
                child = new_item.child(i)
                if self.extract_id_from_text(child.text(0)) == new_prod_id:
                    self.tree_widget.setCurrentItem(child)
                    break

        self.table_widget.setRowCount(0)
        if self.current_prod_id:
            self.load_metadata(self.current_prod_id)
            self.update_table([self.current_prod_id])
 
    def extract_id_from_text(self,text):
        if "(" in text and text.endswith(")"):
            return text[text.rfind("(")+1:-1]
        return text

    def loadfrombib_item(self, item):
        data = item.data(0, Qt.UserRole)
        item_text = item.text(0)
        path = self.get_item_path(item)
        
        file_name, _ = QFileDialog.getOpenFileName(self, "Open BIB File", "", "BIB Files (*.bib)")
        if file_name:
            
            with open(file_name, 'r') as myfile:
                file_content = myfile.read()
            
            dicts = bibtex_to_dicts(file_content)

            for prod_id, production in dicts.items():
                self.add_production_to_structure_and_productions(   path,
                                                                    prod_id,
                                                                    copy.deepcopy(production))

        self.save_file()
        self.update_tree()
        
    def saveasbib_item(self, item):
        data = item.data(0, Qt.UserRole)
        item_text = item.text(0).split(" (")[0]
        path = self.get_item_path(item)
        
        id_list = []
        if data:  # É uma produção (folha)
            prod_id, parent_path = data
            
            id_list = [prod_id]
            
        else: # é uma pasta
            current = self.data["structure"]
                        
            parent = current
            for key in path:
                parent = current
                current = current[key]
            
            id_list = self.collect_production_ids(current)
        
        if len(id_list)>0:
            print("prod_id:", id_list)
            
            output = id_list_to_bibtex_string(self.data["productions"],id_list)          
                
            # Abre o diálogo para salvar
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save BibTeX file",
                "",
                "BibTeX Files (*.bib);;All files (*)",
                options=options
            )

            if file_path:
                # Garante que a extensão .bib esteja presente
                if not file_path.lower().endswith(".bib"):
                    file_path += ".bib"

                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(output)
                    QMessageBox.information(self, "Success", f"File save in:\n{file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"It was not possible to save the file:\n{str(e)}")

            
        else:
            confirm = QMessageBox.question(
                self, "Warning",
                f"No productions found in '{item.text(0)}'",
                QMessageBox.Yes
            )

    def delete_item(self, item):
        data = item.data(0, Qt.UserRole)
        item_text = item.text(0).split(" (")[0]
        path = self.get_item_path(item)

        if data:  # É uma produção (folha)
            prod_id, parent_path = data
            confirm = QMessageBox.question(
                self, "Confirm Deletion",
                f"Do you want to delete the output '{item.text(0)}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if confirm == QMessageBox.No:
                return
                
            current = self.data["structure"]
            for key in parent_path:
                current = current[key]
            
            current.pop(prod_id, None)
            self.data["productions"].pop(prod_id, None)
            if self.current_prod_id == (prod_id, parent_path):
                self.current_prod_id = None
                self.metadata_panel.setEnabled(False)
                self.save_metadata_btn.setEnabled(False)
        else:  # É uma pasta
            confirm = QMessageBox.question(
                self, "Confirm Deletion",
                f"Do you want to delete the folder '{item_text}' and all its subfolders and productions?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if confirm == QMessageBox.No:
                return
            current = self.data["structure"]
                        
            parent = current
            for key in path:
                parent = current
                current = current[key]
            
            prod_ids = self.collect_production_ids(current)
            parent.pop(path[-1], None)
            for prod_id in prod_ids:
                self.data["productions"].pop(prod_id, None)
                
            if self.current_prod_id and self.current_prod_id[1][:len(path)] == path:
                self.current_prod_id = None
                self.metadata_panel.setEnabled(False)
                self.save_metadata_btn.setEnabled(False)

        self.clean_structure(self.data["structure"])
        self.save_file()
        self.update_tree()
        self.table_widget.setRowCount(0)

    def collect_production_ids(self, structure):
        prod_ids = []
        if not isinstance(structure, dict):
            return prod_ids
        for key, value in structure.items():
            if value is None and key in self.data.get("productions", {}):
                prod_ids.append(key)
            elif isinstance(value, dict):
                prod_ids.extend(self.collect_production_ids(value))
        return prod_ids

    def clean_structure(self, structure):
        if not isinstance(structure, dict):
            return
        keys_to_remove = []
        for key, value in structure.items():
            if value is None and key not in self.data.get("productions", {}):
                keys_to_remove.append(key)
            elif isinstance(value, dict):
                self.clean_structure(value)
        for key in keys_to_remove:
            structure.pop(key, None)

    def get_item_path(self, item):
        path = []
        while item and item != self.tree_widget.invisibleRootItem():
            text = item.text(0).split(" (")[0]
            path.append(text)
            item = item.parent()
        return path[::-1]

    def find_tree_item_by_path(self, path):
        current_item = self.tree_widget.invisibleRootItem()
        for name in path:
            found = False
            for i in range(current_item.childCount()):
                child = current_item.child(i)
                child_text = child.text(0).split(" (")[0]
                if child_text == name:
                    current_item = child
                    found = True
                    break
            if not found:
                return None
        return current_item

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open JSON File", "", "JSON Files (*.json)")
        if file_name:
            with open(file_name, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.current_file = file_name
            self.clean_structure(self.data["structure"])
            self.update_tree()
            self.table_widget.setRowCount(0)
            self.metadata_panel.setEnabled(False)
            self.save_metadata_btn.setEnabled(False)
            self.current_prod_id = None

    def save_file(self):
        if self.current_file:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        else:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save JSON File", "", "JSON Files (*.json)")
            if file_name:
                self.current_file = file_name
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)

    def update_tree(self):
        self.tree_widget.clear()
        self.populate_tree(self.data["structure"], self.tree_widget.invisibleRootItem())

    def populate_tree(self, structure, parent, path=None):
        if path is None:
            path = []
        if not isinstance(structure, dict):
            return
        for key, value in sorted(structure.items()):  # Ordenar para consistência
            if not key:
                continue
            item = QTreeWidgetItem(parent)
            item.setText(0, key)
            if value is None and key in self.data.get("productions", {}):
                prod_data = self.data["productions"][key]
                item.setText(0, f"{prod_data.get('title', key)} ({key})")
                item.setIcon(0, QIcon.fromTheme("text-x-generic"))
                item.setData(0, Qt.UserRole, (key, path))
            elif isinstance(value, dict):
                item.setIcon(0, QIcon.fromTheme("folder"))
                self.populate_tree(value, item, path + [key])

    def on_tree_item_clicked(self, item, column):
        self.table_widget.setRowCount(0)
        data = item.data(0, Qt.UserRole)
        if data:
            self.load_metadata(data)
            self.update_table([data])
        else:
            self.metadata_panel.setEnabled(False)
            self.save_metadata_btn.setEnabled(False)
            self.current_prod_id = None
            path = self.get_item_path(item)
            productions = self.get_productions_in_folder(path)
            self.update_table(productions)

    def get_productions_in_folder(self, path):
        productions = []
        current = self.data["structure"]
        for key in path:
            current = current[key]
        if not isinstance(current, dict):
            return productions
        
        def collect_productions(structure, current_path):
            for key, value in structure.items():
                if value is None and key in self.data.get("productions", {}):
                    productions.append((key, current_path))
                elif isinstance(value, dict):
                    collect_productions(value, current_path + [key])
        
        collect_productions(current, path)
        return productions

    def update_table(self, production_ids):
        self.table_widget.setRowCount(len(production_ids))
        for row, (prod_id, path) in enumerate(production_ids):
            prod = self.data["productions"].get(prod_id, {})
            if prod:
                self.table_widget.setItem(row, 0, QTableWidgetItem(prod.get("title", "")))
                self.table_widget.setItem(row, 1, QTableWidgetItem(prod_id))
        self.table_widget.resizeColumnsToContents()

    def filter_table(self):
        filter_text = self.filter_input.text().lower()
        for row in range(self.table_widget.rowCount()):
            title = self.table_widget.item(row, 0).text().lower() if self.table_widget.item(row, 0) else ""
            prod_id = self.table_widget.item(row, 1).text().lower() if self.table_widget.item(row, 1) else ""
            visible = filter_text in title or filter_text in prod_id
            self.table_widget.setRowHidden(row, not visible)

    def load_metadata(self, prod_data):
        prod_id, path = prod_data
        self.current_prod_id = prod_data
        self.metadata_panel.setEnabled(True)
        self.save_metadata_btn.setEnabled(True)
        
        prod = self.data["productions"].get(prod_id, {})
        
        for i in reversed(range(self.metadata_panel.layout().count())):
            widget = self.metadata_panel.layout().itemAt(i).widget()
            if widget and widget != self.save_metadata_btn:
                widget.deleteLater()

        self.metadata_fields = {}
        for key, value in prod.items():
            label = QLabel(key.capitalize() + ":")
            if isinstance(value, list):
                edit = QTextEdit()
                edit.setPlainText(json.dumps(value, indent=2, ensure_ascii=False))
            else:
                edit = QLineEdit()
                edit.setText(str(value))
            self.metadata_panel.layout().insertWidget(self.metadata_panel.layout().count() - 1, label)
            self.metadata_panel.layout().insertWidget(self.metadata_panel.layout().count() - 1, edit)
            self.metadata_fields[key] = edit

    def save_metadata_func(self):
        if not self.current_prod_id:
            QMessageBox.warning(self, "Warning", "No production selected to save metadata.")
            return
        
        prod_id, path = self.current_prod_id
        prod = self.data["productions"].get(prod_id, {})
        
        for key, edit in self.metadata_fields.items():
            value = edit.toPlainText() if isinstance(edit, QTextEdit) else edit.text()
            try:
                if value.startswith("[") or value.startswith("{"):
                    value = json.loads(value)
                prod[key] = value
            except json.JSONDecodeError:
                prod[key] = value
        
        
        self.data["productions"][prod_id] = prod
        
        self.save_file()
        self.update_tree()
        
        self.update_table([(prod_id, path)])


    def on_table_row_clicked(self, row, column):
        if row >= 0 and self.table_widget.item(row, 1):
            prod_id = self.table_widget.item(row, 1).text()
            path = self.get_production_path(prod_id)
            if path:
                self.load_metadata((prod_id, path))
        else:
            self.metadata_panel.setEnabled(False)
            self.save_metadata_btn.setEnabled(False)
            self.current_prod_id = None

    def get_production_path(self, prod_id):
        def search_path(structure, current_path):
            for key, value in structure.items():
                if key == prod_id and value is None:
                    return current_path
                if isinstance(value, dict):
                    result = search_path(value, current_path + [key])
                    if result:
                        return result
            return None
        return search_path(self.data["structure"], [])

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
    window = BibManager()
    window.show()
    sys.exit(app.exec_())
    

if __name__ == "__main__":
    main()

