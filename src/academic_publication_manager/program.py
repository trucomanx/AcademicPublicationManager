import sys
import json
import uuid
import os
import signal
import copy

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeWidgetItem,
                             QTableWidgetItem, QLineEdit,
                             QLabel, QTextEdit, QFileDialog,
                             QInputDialog, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon


import academic_publication_manager.about as about

from academic_publication_manager.desktop import create_desktop_file
from academic_publication_manager.desktop import create_desktop_directory
from academic_publication_manager.desktop import create_desktop_menu


from academic_publication_manager.BaseToolBar     import BaseToolBar
from academic_publication_manager.BaseMenuBar     import BaseMenuBar
from academic_publication_manager.BaseBodyUi      import BaseBodyUi
from academic_publication_manager.BaseContextMenu import BaseContextMenu


class BibManager(QMainWindow, BaseContextMenu, BaseToolBar, BaseMenuBar, BaseBodyUi):
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




    def production_exists(self, prod_id):
        return prod_id in self.data.get("productions", {})

 
    def extract_id_from_text(self,text):
        if "(" in text and text.endswith(")"):
            return text[text.rfind("(")+1:-1]
        return text


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
    app.setApplicationName(about.__package__) 
    window = BibManager()
    window.show()
    sys.exit(app.exec_())
    

if __name__ == "__main__":
    main()

