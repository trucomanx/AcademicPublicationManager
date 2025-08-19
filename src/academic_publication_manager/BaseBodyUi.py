from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea, QPushButton, QTableWidget, QLineEdit, QMessageBox, QTextEdit, QFormLayout
from PyQt5.QtCore import Qt

import json

from academic_publication_manager.modules.customtreeview import CustomTreeWidget

class BaseBodyUi:
    def init_ui(self):
        """
        Initialize the main user interface components.
        
        This method sets up:
        - The central widget and main layout
        - A vertical splitter dividing top and bottom sections
        - A horizontal splitter in the top section for tree view and metadata panel
        - A custom tree widget for folder structure
        - A metadata panel with scrollable area
        - A bottom section with table view and filter input
        """
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

        # Use CustomTreeWidget instead of QTreeWidget
        self.tree_widget = CustomTreeWidget(self)  # Pass self as parent to access BibManager methods
        self.tree_widget.setHeaderLabel("Folder structure")
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)
        horizontal_splitter.addWidget(self.tree_widget)

        self.general_panel = QWidget()
        self.general_layout = QVBoxLayout(self.general_panel)
        
        self.metadata_panel = QWidget()
        self.general_layout.addWidget(self.metadata_panel)
        metadata_layout = QFormLayout(self.metadata_panel)
        self.metadata_fields = {}
        self.metadata_panel.setEnabled(False)


        self.save_metadata_btn = QPushButton("Save Metadata")
        self.save_metadata_btn.clicked.connect(self.save_metadata_func)
        self.general_layout.addWidget(self.save_metadata_btn)
        self.save_metadata_btn.setEnabled(False)
        

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.general_panel)
        horizontal_splitter.addWidget(scroll_area)



        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        vertical_splitter.addWidget(bottom_widget)

        TITLES = ["Title", "Year", "ID"]

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(len(TITLES))
        self.table_widget.setHorizontalHeaderLabels(TITLES)
        self.table_widget.cellClicked.connect(self.on_table_row_clicked)
        self.table_widget.setSortingEnabled(True)
        bottom_layout.addWidget(self.table_widget)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter by title or year...")
        self.filter_input.textChanged.connect(self.filter_table)
        bottom_layout.addWidget(self.filter_input)


        horizontal_splitter.setSizes([300, 300])

    def on_tree_item_clicked(self, item, column):
        """
        Handle click events on tree items.
        
        Args:
            item (QTreeWidgetItem): The clicked tree item
            column (int): The column index that was clicked
            
        This method:
        - Clears the table widget
        - If the item has associated data, loads its metadata and updates the table
        - Otherwise, disables metadata panel and loads productions for the selected folder
        """
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


    def save_metadata_func(self):
        """
        Save the current metadata to the data structure.
        
        This method:
        - Validates that a production is selected
        - Collects metadata from all fields
        - Attempts to parse JSON data if field values look like JSON
        - Updates the production data
        - Saves to file
        - Updates the tree and table views
        - Restores expanded items in the tree
        """
        if not self.current_prod_id:
            QMessageBox.warning(self, "Warning", "No production selected to save metadata.")
            return
        
        prod_id, path = self.current_prod_id
        prod = self.data["productions"].get(prod_id, {})
        
        for key, edit in self.metadata_fields.items():
        
            if isinstance(edit, QTextEdit):
                value = edit.toPlainText()
            else: 
                value = edit.text()
 
            prod[key] = value
        
        
        self.data["productions"][prod_id] = prod
        
        self.save_file()
        
        expanded_items = self.get_expanded_items()
        self.update_tree()
        self.restore_expanded_items(expanded_items)
        
        self.update_table([(prod_id, path)])

    def on_table_row_clicked(self, row, column):
        """
        Handle click events on table rows.
        
        Args:
            row (int): The clicked row index
            column (int): The clicked column index
            
        This method:
        - Gets the production ID from the clicked row
        - Loads metadata for the selected production if valid
        - Otherwise disables the metadata panel
        """
        
        ID_COL_POS = 2 # Column posicion of bibliographic publication ID 
        
        if row >= 0 and self.table_widget.item(row, ID_COL_POS):
            prod_id = self.table_widget.item(row, ID_COL_POS).text()
            path = self.get_production_path(prod_id)
            if path:
                self.load_metadata((prod_id, path))
        else:
            self.metadata_panel.setEnabled(False)
            self.save_metadata_btn.setEnabled(False)
            self.current_prod_id = None
            

    def filter_table(self):
        """
        Filter the table contents based on the filter input text.
        
        The filtering is case-insensitive and matches against both title and ID columns.
        Rows are hidden if they don't contain the filter text in either column.
        """
        filter_text = self.filter_input.text().lower()
        for row in range(self.table_widget.rowCount()):
            title   = self.table_widget.item(row, 0).text().lower() if self.table_widget.item(row, 0) else ""
            year    = self.table_widget.item(row, 1).text().lower() if self.table_widget.item(row, 1) else ""
            prod_id = self.table_widget.item(row, 2).text().lower() if self.table_widget.item(row, 2) else ""
            visible = filter_text in title or filter_text in year or filter_text in prod_id
            self.table_widget.setRowHidden(row, not visible)


    def show_context_menu(self):
        """
        Show a context menu for the tree widget.
        
        Note:
            This is an abstract method that must be implemented by subclasses.
            Raises NotImplementedError if called directly.
        """
        raise NotImplementedError("You need to implement show_context_menu() in the main class.")
