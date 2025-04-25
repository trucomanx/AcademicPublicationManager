#!/usr/bin/python3

from PyQt5.QtWidgets import QTreeWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor

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

