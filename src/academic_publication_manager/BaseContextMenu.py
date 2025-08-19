from PyQt5.QtWidgets import QMenu, QMessageBox, QInputDialog, QLineEdit, QFileDialog
from PyQt5.QtGui     import QIcon
from PyQt5.QtCore    import Qt

from copy import deepcopy
import copy

from academic_publication_manager.modules.production     import bibtex_examples
from academic_publication_manager.modules.to_bibtex      import id_list_to_bibtex_string
from academic_publication_manager.modules.to_bibtex      import bibtex_to_dicts

class BaseContextMenu:
    def show_context_menu(self, position):
        """
        Displays a context menu at the specified position in the tree widget.
        
        Args:
            position (QPoint): The position where the context menu should appear.
            
        The menu items vary depending on whether the clicked item is a production (leaf node)
        or a folder (parent node).
        """
        item = self.tree_widget.itemAt(position)
        if item:
            menu = QMenu()
            
            # Delete 
            delete_action = menu.addAction( QIcon.fromTheme("edit-delete"), "Delete")
            delete_action.setStatusTip("Delete the current element")
            delete_action.triggered.connect(lambda: self.delete_item(item))
            
            # Separator
            menu.addSeparator()
            
            if item.data(0, Qt.UserRole):  # It's a production (leaf node)
                
                # Change ID
                change_id_action = menu.addAction(  QIcon.fromTheme("document-edit"), "Change ID")
                change_id_action.setStatusTip("Change the ID name of current bibliographic production")
                change_id_action.triggered.connect(lambda: self.change_production_id(item))
                
                # Duplicate
                duplicate_action = menu.addAction(  QIcon.fromTheme("edit-copy"), "Duplicate Publication")
                duplicate_action.setStatusTip("Duplicate the current bibliographic production with another ID name")
                duplicate_action.triggered.connect(lambda: self.duplicate_production(item))
                
                # Separator
                menu.addSeparator()
                
            else:  # It's a folder
                # New folder
                new_folder_action = menu.addAction( QIcon.fromTheme("folder-new"), "New folder")
                new_folder_action.setStatusTip("Create a new folder inside the current folder")
                new_folder_action.triggered.connect(lambda: self.create_new_folder(item))
                
                # Rename folder
                rename_folder_action = menu.addAction(  QIcon.fromTheme("folder-visiting"), "Rename folder")
                rename_folder_action.setStatusTip("Rename the current folder")
                rename_folder_action.triggered.connect(lambda: self.rename_folder(item))

                # new prduction
                menu_production = QMenu("New production", self)
                menu.addMenu(menu_production)
                
                # New production
                for entry_type in bibtex_examples:
                    new_production_action = menu_production.addAction( QIcon.fromTheme("document-new"), entry_type)
                    new_production_action.setStatusTip("Add a new bibliographic production of type:"+" "+entry_type)
                    new_production_action.triggered.connect(lambda: self.create_new_production(item, entry_type))

                
                # Separator
                menu.addSeparator()
                
                # load bibfile
                loadfrombib_action = menu.addAction( QIcon.fromTheme("document-open"), "Load from *.bib")
                loadfrombib_action.setStatusTip("Load many bibliographic productions from a *.bib file")
                loadfrombib_action.triggered.connect(lambda: self.loadfrombib_item(item))
            
            
            # Save bibfile
            saveasbib_action = menu.addAction( QIcon.fromTheme("document-save-as"), "Save as *.bib")
            saveasbib_action.setStatusTip("Save bibliographic productions into a *.bib file")
            saveasbib_action.triggered.connect(lambda: self.saveasbib_item(item))

            
            for action in menu.actions():
                action.hovered.connect(lambda a=action: self.statusBar().showMessage(a.statusTip(), 3000))            
            
            for action in menu_production.actions():
                action.hovered.connect(lambda a=action: self.statusBar().showMessage(a.statusTip(), 3000))            
                
            menu.exec_(self.tree_widget.viewport().mapToGlobal(position))



    def collect_production_ids(self, structure):
        """
        Recursively collects all production IDs from a given folder structure.
        
        Args:
            structure (dict): The folder structure to search through.
            
        Returns:
            list: A list of all production IDs found in the structure.
        """
        prod_ids = []
        if not isinstance(structure, dict):
            return prod_ids
        for key, value in structure.items():
            if value is None and key in self.data.get("productions", {}):
                prod_ids.append(key)
            elif isinstance(value, dict):
                prod_ids.extend(self.collect_production_ids(value))
        return prod_ids


    def delete_item(self, item):
        """
        Deletes an item (either a production or folder) from the structure.
        
        Args:
            item (QTreeWidgetItem): The item to be deleted.
            
        Shows a confirmation dialog before deletion. For folders, deletes all
        subfolders and productions recursively.
        """
        data = item.data(0, Qt.UserRole)
        item_text = item.text(0).split(" (")[0]
        path = self.get_item_path(item)

        if data:  # It's a production (leaf node)
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
        else:  # It's a folder
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
        
        expanded_items = self.get_expanded_items()
        self.update_tree()
        self.restore_expanded_items(expanded_items)
        
        self.table_widget.setRowCount(0)

    def extract_id_from_text(self, text):
        """
        Extracts the production ID from an item's text.
        
        Args:
            text (str): The text from which to extract the ID.
            
        Returns:
            str: The extracted ID, or the original text if no ID is found.
        """
        if "(" in text and text.endswith(")"):
            return text[text.rfind("(")+1:-1]
        return text


    def production_exists(self, prod_id):
        """
        Checks if a production with the given ID exists.
        
        Args:
            prod_id (str): The production ID to check.
            
        Returns:
            bool: True if the production exists, False otherwise.
        """
        return prod_id in self.data.get("productions", {})


    def find_tree_item_by_path(self, path):
        """
        Finds a tree item by its path in the structure.
        
        Args:
            path (list): The path to the item as a list of folder names.
            
        Returns:
            QTreeWidgetItem: The found item, or None if not found.
        """
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


    def change_production_id(self, item):
        """
        Changes the ID of a production.
        
        Args:
            item (QTreeWidgetItem): The production item to modify.
            
        Shows an input dialog to get the new ID, validates it, and updates
        the structure and productions if valid.
        """
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
            # Now search among children
            for i in range(new_item.childCount()):
                child = new_item.child(i)
                if self.extract_id_from_text(child.text(0)) == new_prod_id:
                    self.tree_widget.setCurrentItem(child)
                    break

        self.table_widget.setRowCount(0)
        if self.current_prod_id:
            self.load_metadata(self.current_prod_id)
            self.update_table([self.current_prod_id])

    
    def duplicate_production(self, item):
        """
        Duplicates a production with a new ID.
        
        Args:
            item (QTreeWidgetItem): The production item to duplicate.
            
        Shows an input dialog to get the new ID, validates it, creates a copy
        of the production with the new ID, and updates the structure.
        """
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

        # Copy metadata from original production
        original_prod = self.data["productions"].get(prod_id, {})
        new_prod = deepcopy(original_prod)
        self.data["productions"][new_prod_id] = new_prod

        # Add new production to the same parent folder
        current = self.data["structure"]
        for key in parent_path:
            current = current[key]
        current[new_prod_id] = None

        # Save and update interface
        self.save_file()
        
        # Preserve expanded state of the tree
        expanded_items = self.get_expanded_items()
        self.update_tree()
        self.restore_expanded_items(expanded_items)

        # Select the new production
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


    def create_new_folder(self, parent_item):
        folder_name, ok = QInputDialog.getText(self, "New tree", "Name of the new folder:")
        if ok and folder_name:
            path = self.get_item_path(parent_item)
            current = self.data["structure"]
            for key in path:
                current = current[key]
            current[folder_name] = {}
            self.save_file()
            
            expanded_items = self.get_expanded_items()
            self.update_tree()
            self.restore_expanded_items(expanded_items)
            
            new_parent_item = self.find_tree_item_by_path(path)
            if new_parent_item:
                new_parent_item.setExpanded(True)
                self.tree_widget.setCurrentItem(new_parent_item)


    def add_production_to_structure_and_productions(self, parent_path, prod_id, production):
        """
        Adds a production to both the structure and productions dictionary.
        
        Args:
            parent_path (list): The path to the parent folder.
            prod_id (str): The ID of the new production.
            production (dict): The production data to add.
        """
        current = self.data["structure"]
        for key in parent_path:
            current = current[key]
        
        current[prod_id] = None
        self.data["productions"][prod_id] = production


    def create_new_production(self, parent_item, entry_type="article"):
        """
        Creates a new production under the specified parent item.
        
        Args:
            parent_item (QTreeWidgetItem): The parent item under which to create the new production.
            
        Shows an input dialog to get the production ID, validates it, and adds
        a new production with default metadata.
        """
        while True:
            prod_id, ok = QInputDialog.getText(self, "New production", "Enter the new production ID:")
            if not ok or not prod_id:
                return
            if self.production_exists(prod_id):
                QMessageBox.warning(self, "Error", f"The ID '{prod_id}' already exists. Please choose another ID.")
                continue
            break
        
        parent_path = self.get_item_path(parent_item)

        self.add_production_to_structure_and_productions(   parent_path,
                                                            prod_id,
                                                            copy.deepcopy(bibtex_examples[entry_type]))
        
        self.save_file()
        
        expanded_items = self.get_expanded_items()
        self.update_tree()
        self.restore_expanded_items(expanded_items)
        
        new_parent_item = self.find_tree_item_by_path(parent_path)
        if new_parent_item:
            new_parent_item.setExpanded(True)
            self.tree_widget.setCurrentItem(new_parent_item)
            self.on_tree_item_clicked(new_parent_item, 0)
            
            
    def rename_folder(self, item):
        """
        Renames a folder.
        
        Args:
            item (QTreeWidgetItem): The folder item to rename.
            
        Shows an input dialog to get the new name, validates it, and updates
        the structure if valid.
        """
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
            
            expanded_items = self.get_expanded_items()
            self.update_tree()
            self.restore_expanded_items(expanded_items)
            
            new_path = path[:-1] + [new_name]
            new_item = self.find_tree_item_by_path(new_path)
            if new_item:
                new_item.setExpanded(True)
                self.tree_widget.setCurrentItem(new_item)


    def loadfrombib_item(self, item):
        """
        Loads productions from a .bib file into the specified folder.
        
        Args:
            item (QTreeWidgetItem): The folder item where productions will be added.
            
        Shows a file dialog to select a .bib file, parses it, and adds all
        productions to the folder.
        """
        data = item.data(0, Qt.UserRole)
        item_text = item.text(0)
        path = self.get_item_path(item)
        
        file_name, _ = QFileDialog.getOpenFileName(self, "Open BIB File", "", "BIB Files (*.bib)")
        if file_name:
            
            dicts = bibtex_to_dicts(file_name)

            for prod_id, production in dicts.items():
                self.add_production_to_structure_and_productions(   path,
                                                                    prod_id,
                                                                    copy.deepcopy(production))

        self.save_file()
        
        expanded_items = self.get_expanded_items()
        self.update_tree()
        self.restore_expanded_items(expanded_items)
        
        
        
    def saveasbib_item(self, item):
        """
        Saves productions from an item (folder or single production) to a .bib file.
        
        Args:
            item (QTreeWidgetItem): The item to save (either a production or folder).
            
        For folders, saves all productions in the folder and subfolders.
        For single productions, saves just that production.
        Shows a file dialog to select the save location.
        """
        data = item.data(0, Qt.UserRole)
        item_text = item.text(0).split(" (")[0]
        path = self.get_item_path(item)
        
        id_list = []
        if data:  # It's a production (leaf node)
            prod_id, parent_path = data
            
            id_list = [prod_id]
            
        else: # It's a folder
            current = self.data["structure"]
                        
            parent = current
            for key in path:
                parent = current
                current = current[key]
            
            id_list = self.collect_production_ids(current)
        
        if len(id_list)>0:
            print("prod_id:", id_list)
            
            output = id_list_to_bibtex_string(self.data["productions"],id_list)          
                
            # Open save dialog
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
                # Ensure .bib extension is present
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


