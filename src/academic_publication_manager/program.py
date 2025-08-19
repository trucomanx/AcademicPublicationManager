import sys
import json
import uuid
import os
import signal
import copy

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeWidgetItem,
                             QTableWidgetItem, QLineEdit, QFormLayout, 
                             QLabel, QTextEdit, QFileDialog, QStatusBar, 
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
    """
    Main class for the Academic Publication Manager application.
    Handles the GUI and core functionality for managing academic publications.
    """
    
    def __init__(self):
        """
        Initialize the BibManager application.
        Sets up the main window, initializes data structures, and creates UI elements.
        """
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

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def get_expanded_items(self):
        """
        Collects all currently expanded items in the tree widget.
        
        Returns:
            list: A list of paths to all expanded items, where each path is a list of strings.
        """
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
        """
        Restores the expanded state of items in the tree widget based on saved paths.
        
        Args:
            expanded_items (list): List of paths to items that should be expanded.
        """
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


    def clean_structure(self, structure):
        """
        Recursively removes empty nodes from the folder structure.
        
        Args:
            structure (dict): The folder structure to clean.
        """
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
        """
        Gets the path to a tree widget item as a list of folder names.
        
        Args:
            item (QTreeWidgetItem): The item to get the path for.
            
        Returns:
            list: The path from root to the item as a list of strings.
        """
        path = []
        while item and item != self.tree_widget.invisibleRootItem():
            text = item.text(0).split(" (")[0]
            path.append(text)
            item = item.parent()
        return path[::-1]


    def update_tree(self):
        """
        Clears and repopulates the tree widget with the current folder structure.
        """
        self.tree_widget.clear()
        self.populate_tree(self.data["structure"], self.tree_widget.invisibleRootItem())

    def populate_tree(self, structure, parent, path=None):
        """
        Recursively populates the tree widget with items from the folder structure.
        
        Args:
            structure (dict): The folder structure to display.
            parent (QTreeWidgetItem): The parent item in the tree widget.
            path (list, optional): Current path in the folder structure. Defaults to None.
        """
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
        """
        Gets all productions contained within a specific folder path.
        
        Args:
            path (list): The folder path to search within.
            
        Returns:
            list: List of tuples containing (production_id, path) for each production.
        """
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
        """
        Updates the table widget with information about the specified productions.
        
        Args:
            production_ids (list): List of tuples containing (production_id, path) to display.
        """
        self.table_widget.setRowCount(len(production_ids))
        for row, (prod_id, path) in enumerate(production_ids):
            prod = self.data["productions"].get(prod_id, {})
            if prod:
                self.table_widget.setItem(row, 0, QTableWidgetItem(prod.get("title", "")))
                self.table_widget.setItem(row, 1, QTableWidgetItem(prod.get("year", "")))
                self.table_widget.setItem(row, 2, QTableWidgetItem(prod_id))
        self.table_widget.resizeColumnsToContents()

    def load_metadata(self, prod_data):
        """
        Loads and displays metadata for a specific production in the metadata panel.
        
        Args:
            prod_data (tuple): Tuple containing (production_id, path) of the production to display.
        """
        prod_id, path = prod_data
        self.current_prod_id = prod_data
        self.metadata_panel.setEnabled(True)
        self.save_metadata_btn.setEnabled(True)
        
        prod = self.data["productions"].get(prod_id, {})
        
        form_layout = self.metadata_panel.layout()
        
        # apaga widgets anteriores
        for row in reversed(range(form_layout.rowCount())):
            label_item = form_layout.itemAt(row, QFormLayout.LabelRole)
            field_item = form_layout.itemAt(row, QFormLayout.FieldRole)

            # Se existir, pega o widget
            label = label_item.widget() if label_item else None
            field = field_item.widget() if field_item else None

            # Apaga os widgets, mas não mexe no botão de salvar
            for widget in (label, field):
                if widget and widget != self.save_metadata_btn:
                    widget.deleteLater()

            # Remove a linha do layout
            form_layout.removeRow(row)


        #
        self.metadata_fields = {}
        for key, value in prod.items():
            label = QLabel("<b>"+key + ":</b>")
            if key in ["author","title","note"] :
                edit = QTextEdit()
                edit.setPlainText(str(value))
            else:
                edit = QLineEdit()
                edit.setText(str(value))
                
            if key == 'entry-type':
                edit.setReadOnly(True)
                
            form_layout.insertRow(form_layout.count() - 1, label, edit)
            self.metadata_fields[key] = edit


    def get_production_path(self, prod_id):
        """
        Finds the folder path for a specific production ID.
        
        Args:
            prod_id (str): The production ID to search for.
            
        Returns:
            list: The folder path as a list of strings, or None if not found.
        """
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
    """
    Main entry point for the application.
    Handles command line arguments and initializes the GUI.
    """
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

