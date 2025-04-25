from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSplitter, QScrollArea, QPushButton, QTableWidget, QLineEdit, QMessageBox, QTextEdit
from PyQt5.QtCore import Qt

import json

from academic_publication_manager.modules.customtreeview import CustomTreeWidget

class BaseBodyUi:
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
        
        expanded_items = self.get_expanded_items()
        self.update_tree()
        self.restore_expanded_items(expanded_items)
        
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
            

    def filter_table(self):
        filter_text = self.filter_input.text().lower()
        for row in range(self.table_widget.rowCount()):
            title = self.table_widget.item(row, 0).text().lower() if self.table_widget.item(row, 0) else ""
            prod_id = self.table_widget.item(row, 1).text().lower() if self.table_widget.item(row, 1) else ""
            visible = filter_text in title or filter_text in prod_id
            self.table_widget.setRowHidden(row, not visible)


    def show_context_menu(self):
        raise NotImplementedError("Você precisa implementar show_context_menu() na classe principal.")

