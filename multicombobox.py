#from https://stackoverflow.com/a/77755095 and https://gis.stackexchange.com/a/351152

from PySide6.QtGui import QStandardItemModel, QStandardItem, QPalette
from PySide6.QtWidgets import QComboBox, QApplication, QTreeView
from PySide6.QtCore import Qt, QEvent, Signal
from typing import TypedDict

class nameValueDict(TypedDict):
    text: str
    name: str
    value: int | str | list

class MultiComboBox(QComboBox):
    selectionChanged = Signal()
    
    def __init__(self, parent=None, selectedValues: list | None = None):
        self.__data = {}
        self.__selected_values = []
        
        self.preSelectedValues = set([] if selectedValues is None else selectedValues)
        super().__init__(parent)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.setModel(QStandardItemModel(self))
        palette = QApplication.palette()
        palette.setBrush(QPalette.Base, palette.button())
        self.lineEdit().setPalette(palette)
        
        tree_view = QTreeView(self)
        tree_view.setStyleSheet("QTreeView{margin-left:-25px;}QTreeView::branch{border-image: url(none.png)}")
        tree_view.setHeaderHidden(True)
        tree_view.setItemsExpandable(False)
        self.setView(tree_view)

        # Connect to the dataChanged signal to update the text
        self.model().dataChanged.connect(self.updateText)
        
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False

        self.view().viewport().installEventFilter(self)
    
    def resizeEvent(self, event):
        # Recompute text to elide as needed
        self.updateText()
        super().resizeEvent(event)

    def addItem(self, data: nameValueDict, parent: QStandardItem | None = None) -> QStandardItem:
        item = QStandardItem(data['text'])
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        if(type(data['value']) is not list and data['value'] in self.preSelectedValues):
            item.setData(Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
            self.__selected_values.append(data['value'])
        else:
            item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        if(parent is None):
            self.model().appendRow(item)
            item.setUserTristate(True)
        else:
            parent.appendRow(item)
        if type(data['value'])!='list':
            self.__data[data['text']] = [data['name'], data['value']]
        return item

    def addItems(self, items_list: list[nameValueDict], parent: QStandardItem | None = None, *, selectedValues: list | None = None):
        parent_checked = None
        if(selectedValues is not None):
            self.preSelectedValues = set(selectedValues)
        for item_dict in items_list:
            item = self.addItem(item_dict, parent)
            if(parent_checked==None):
                parent_checked = item.checkState()
            elif(parent_checked!=item.checkState()):
                parent_checked = Qt.CheckState.PartiallyChecked
            if isinstance(item_dict['value'], list):
                item.setCheckState(self.addItems(item_dict['value'], item))
            

        if(parent is None):
            self.updateText()
        return parent_checked
            
    def eventFilter(self, object, event):
        if object == self.lineEdit():
            if event.type() == QEvent.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False
        
        if object == self.view().viewport():
            if event.type() == QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                parentIndex = self.model().parent(index)
                if(parentIndex.row()<0):
                    item = self.model().item(index.row())
                    checkState = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                    for i in range(item.rowCount()):
                        item.child(i).setCheckState(checkState)
                    item.setCheckState(checkState)
                else:
                    parent = self.model().item(parentIndex.row())
                    item = parent.child(index.row())
                    checkState = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                    item.setCheckState(checkState)
                    parent.setCheckState(checkState)
                    for i in range(parent.rowCount()):
                        if parent.child(i).checkState() != checkState:
                            parent.setCheckState(Qt.PartiallyChecked)
                self.selectionChanged.emit()
                return True
        return False

    def updateText(self):
        selected_items_names = []
        self.__selected_values = []
        selectionChanged = False
        for i in range(self.model().rowCount()):
            parentRow = self.model().item(i)
            for j in range(parentRow.rowCount()):
                if parentRow.child(j).checkState() == Qt.CheckState.Checked:
                    selected_items_names.append(self.__data[parentRow.child(j).text()][0])
                    self.__selected_values.append(self.__data[parentRow.child(j).text()][1])
            
        self.lineEdit().setText(", ".join(selected_items_names))

    def getSelectedValues(self):
        return self.__selected_values

    def showPopup(self):
        super().showPopup()
        self.view().expandAll()
        self.closeOnLineEditClick = True

    def hidePopup(self):
        super().hidePopup()
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event):
        # After timeout, kill timer, and reenable click on line edit
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False
        
    def clear(self):
        self.__selected_values = []
        self.__data = {}
        return super().clear()
    
    