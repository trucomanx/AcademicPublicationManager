import sys
import json
import uuid
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QTableWidget, QTableWidgetItem, QLineEdit, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QTextEdit, QPushButton, QFileDialog, QScrollArea,
                             QMenu, QInputDialog, QMessageBox, QToolButton)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

class BibManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gerenciador de Produções Bibliográficas")
        self.setGeometry(100, 100, 1200, 600)
        self.data = {"structure": {"Root":{}}, "productions": {}}
        self.current_file = None
        self.current_prod_id = None
        
        self.init_toolbar()
        self.init_ui()
        
        
        self.update_tree()
        self.table_widget.setRowCount(0)
        self.metadata_panel.setEnabled(False)
        self.save_metadata_btn.setEnabled(False)
        self.current_prod_id = None

    def init_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")

        # Botão Nova Árvore
        new_tree_btn = QToolButton()
        new_tree_btn.setText("Nova Árvore")
        new_tree_btn.clicked.connect(self.new_tree)
        new_tree_btn.setIcon(QIcon.fromTheme("document-new"))
        new_tree_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.addWidget(new_tree_btn)

        # Botão Abrir
        open_btn = QToolButton()
        open_btn.setText("Abrir")
        open_btn.clicked.connect(self.open_file)
        open_btn.setIcon(QIcon.fromTheme("document-open"))
        open_btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.addWidget(open_btn)

        # Botão Salvar
        save_btn = QToolButton()
        save_btn.setText("Salvar")
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
       
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("Estrutura de Pastas")
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


        self.save_metadata_btn = QPushButton("Salvar Metadados")
        self.save_metadata_btn.clicked.connect(self.save_metadata)
        metadata_layout.addWidget(self.save_metadata_btn)
        self.save_metadata_btn.setEnabled(False)

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        vertical_splitter.addWidget(bottom_widget)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Título", "ID"])
        self.table_widget.cellClicked.connect(self.on_table_row_clicked)
        bottom_layout.addWidget(self.table_widget)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filtrar por título ou ID...")
        self.filter_input.textChanged.connect(self.filter_table)
        bottom_layout.addWidget(self.filter_input)


        horizontal_splitter.setSizes([300, 300])


        menubar = self.menuBar()
        file_menu = menubar.addMenu("Arquivo")

        open_action = file_menu.addAction("Abrir")
        open_action.triggered.connect(self.open_file)
        
        save_action = file_menu.addAction("Salvar")
        save_action.triggered.connect(self.save_file)
        
        new_tree_action = file_menu.addAction("Nova Árvore")
        new_tree_action.triggered.connect(self.new_tree)

    def show_context_menu(self, position):
        item = self.tree_widget.itemAt(position)
        if item:
            menu = QMenu()
            delete_action = menu.addAction("Apagar")
            delete_action.triggered.connect(lambda: self.delete_item(item))
            
            if item.data(0, Qt.UserRole):  # É uma produção (folha)
                change_id_action = menu.addAction("Alterar ID")
                change_id_action.triggered.connect(lambda: self.change_production_id(item))
            else:  # É uma pasta
                new_folder_action = menu.addAction("Nova Pasta")
                new_folder_action.triggered.connect(lambda: self.create_new_folder(item))
                
                new_production_action = menu.addAction("Nova Produção")
                new_production_action.triggered.connect(lambda: self.create_new_production(item))
                
                rename_folder_action = menu.addAction("Renomear Pasta")
                rename_folder_action.triggered.connect(lambda: self.rename_folder(item))
                
            menu.exec_(self.tree_widget.viewport().mapToGlobal(position))

    def new_tree(self):
        confirm = QMessageBox.question(
            self, "Nova Árvore",
            "Deseja apagar toda a estrutura atual e começar do zero?",
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
        folder_name, ok = QInputDialog.getText(self, "Nova Pasta", "Nome da nova pasta:")
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

    def create_new_production(self, parent_item):
        while True:
            prod_id, ok = QInputDialog.getText(self, "Nova Produção", "Digite o ID da nova produção:")
            if not ok or not prod_id:
                return
            if self.production_exists(prod_id):
                QMessageBox.warning(self, "Erro", f"O ID '{prod_id}' já existe. Por favor, escolha outro ID.")
                continue
            break
        
        parent_path = self.get_item_path(parent_item)
        fake_production = {
            "title": "New Publication",
            "authors": ["Author Name"],
            "year": datetime.now().year,
            "publication_name": "Sample Journal",
            "url": "https://example.com",
            "type": "article",
            "language": "English",
            "version": 1,
            "serial_numbers": [{"type": "doi", "value": "10.1000/sample"}]
        }
        current = self.data["structure"]
        for key in parent_path:
            current = current[key]
        current[prod_id] = None
        self.data["productions"][prod_id] = fake_production
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
        new_name, ok = QInputDialog.getText(self, "Renomear Pasta", "Novo nome da pasta:", QLineEdit.Normal, old_name)
        if ok and new_name and new_name != old_name:
            current = self.data["structure"]
            for key in path[:-1]:
                current = current[key]
            if new_name in current:
                QMessageBox.warning(self, "Erro", f"A pasta '{new_name}' já existe neste nível. Escolha outro nome.")
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
                                                    "Alterar ID", 
                                                    f"Digite o novo ID para '{old_prod_id}':", 
                                                    QLineEdit.Normal, 
                                                    old_prod_id)
            if not ok or not new_prod_id:
                return
            if new_prod_id == old_prod_id:
                return
            if self.production_exists(new_prod_id):
                QMessageBox.warning(self, 
                                    "Erro", 
                                    f"O ID '{new_prod_id}' já existe. Por favor, escolha outro ID.")
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

    def delete_item(self, item):
        data = item.data(0, Qt.UserRole)
        item_text = item.text(0).split(" (")[0]
        path = self.get_item_path(item)

        if data:  # É uma produção (folha)
            prod_id, parent_path = data
            confirm = QMessageBox.question(
                self, "Confirmar Exclusão",
                f"Deseja apagar a produção '{item.text(0)}'?",
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
                self, "Confirmar Exclusão",
                f"Deseja apagar a pasta '{item_text}' e todas as suas subpastas e produções?",
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
        file_name, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo JSON", "", "JSON Files (*.json)")
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
            file_name, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo JSON", "", "JSON Files (*.json)")
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
        for key, value in structure.items():
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

    def save_metadata(self):
        if not self.current_prod_id:
            QMessageBox.warning(self, "Aviso", "Nenhuma produção selecionada para salvar os metadados.")
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
        self.update_table([(prod_id, path)])
        self.update_tree()

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BibManager()
    window.show()
    sys.exit(app.exec_())
