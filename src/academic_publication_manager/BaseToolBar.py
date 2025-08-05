import json

from PyQt5.QtWidgets import QToolButton, QMessageBox, QFileDialog
from PyQt5.QtGui     import QIcon
from PyQt5.QtCore    import Qt

from academic_publication_manager.modules.wabout         import show_about_window
import academic_publication_manager.about as about

class BaseToolBar():
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

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open JSON File", "", "JSON Files (*.Publications.json)")
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
            file_name, _ = QFileDialog.getSaveFileName(self, "Save JSON File", "", "JSON Files (*.Publications.json)")
                
            if file_name:
                if not file_name.endswith(".Publications.json"):
                    file_name += ".Publications.json"
                    
                self.current_file = file_name
                with open(self.current_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)

