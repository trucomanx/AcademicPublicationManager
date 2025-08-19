from PyQt5.QtGui     import QIcon

class BaseMenuBar:
    def init_menubar(self):
        menubar = self.menuBar()
        
        ##
        file_menu = menubar.addMenu("Arquive")

        open_action = file_menu.addAction(QIcon.fromTheme("document-open"), "Open tree from json")
        open_action.triggered.connect(self.open_file)
        
        save_action = file_menu.addAction(QIcon.fromTheme("document-save"), "Save tree in json")
        save_action.triggered.connect(self.save_file)
        
        new_tree_action = file_menu.addAction(QIcon.fromTheme("document-new"), "New tree")
        new_tree_action.triggered.connect(self.new_tree)

        ##
        gabout_menu = menubar.addMenu("About")
        
        about_program_action = gabout_menu.addAction(QIcon.fromTheme("help-about"), "About program")
        about_program_action.triggered.connect(self.about_func)


    def about_func(self):
        raise NotImplementedError("Você precisa implementar about_func() na classe principal.")

    def new_tree(self):
        raise NotImplementedError("Você precisa implementar new_tree() na classe principal.")

    def open_file(self):
        raise NotImplementedError("Você precisa implementar open_file() na classe principal.")
        
    def save_file(self):
        raise NotImplementedError("Você precisa implementar save_file() na classe principal.")

