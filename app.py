import sys, json, time, datetime
from threading import Thread

from PySide6 import QtCore, QtGui, QtSvg
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QGridLayout,
    QMainWindow,
    QWidget,
    QMessageBox,
    QMenuBar,
    QMenu
)

from multicombobox import MultiComboBox
from CustomDialog import CustomDialog
from PreciseAPI import preciseApi
from GISConnector import gisHelper

class MainWindow(QMainWindow): 
    def __init__(self):
        super().__init__()
        self.__assets = []
        self.__arcgis = None
        self.__precise = None
        self.__config = None
        self.needsSetup = False
        self.preciseStatus = "Not Connected"
        self.arcgisStatus = "Not Connected"
        
        self.setMinimumSize(500, 200)
        self.setWindowTitle("Precise Arcgis Connector")
        
        self.customMenuBar = QMenuBar(self)
        self.settingsMenu = QMenu("&Settings", self)
        self.optionsAction = QtGui.QAction("&Options", self)
        self.optionsAction.triggered.connect(self.configureOptions)
        self.settingsMenu.addAction(self.optionsAction)
        self.customMenuBar.addMenu(self.settingsMenu)
        self.setMenuBar(self.customMenuBar)
        
        self.mainLayout = QGridLayout()
        
        self.mainLayout.addWidget(QLabel("Precise:"), 0, 0, alignment=QtCore.Qt.AlignRight)
        self.preciseStatusLabel = QLabel(self.preciseStatus)
        self.mainLayout.addWidget(self.preciseStatusLabel, 0, 2, alignment=QtCore.Qt.AlignCenter)
        self.preciseConfigButton = QPushButton("Configure...")
        self.preciseConfigButton.clicked.connect(self.configurePreciseApi)
        self.mainLayout.addWidget(self.preciseConfigButton, 0, 4)
        
        self.mainLayout.addWidget(QLabel("ArcGIS:"), 1, 0, alignment=QtCore.Qt.AlignRight)
        self.arcgisStatusLabel = QLabel(self.arcgisStatus)
        self.mainLayout.addWidget(self.arcgisStatusLabel, 1, 2, alignment=QtCore.Qt.AlignCenter)
        self.arcgisConfigButton = QPushButton("Configure...")
        self.arcgisConfigButton.clicked.connect(self.configureArcgisApi)
        self.mainLayout.addWidget(self.arcgisConfigButton, 1, 4)
        
        self.mainLayout.addWidget(QLabel("Assets to Sync:"), 2, 0, alignment=QtCore.Qt.AlignRight)
        self.multiComboBox = MultiComboBox()
        self.comboBoxData = []
        self.mainLayout.addWidget(self.multiComboBox, 2, 1, 1, 3)
        self.multiComboBox.selectionChanged.connect(self.changeAssetsToSync)
        self.comboBoxButton = QPushButton("Refresh List")
        self.comboBoxButton.clicked.connect(self.refreshAssetList)
        self.mainLayout.addWidget(self.comboBoxButton, 2, 4)
        
        self.syncButton = QPushButton()
        self.syncButton.setFixedSize(150, 150)
        self.syncButtonColors = {"inactive": "black", "active": "lime", "inProgress": "yellow", "error": "red"}
        self.syncButtonIcons = {
            "inactive": self.svgToPixmap("icons/Power.svg", 200, 200, QtGui.QColor(self.syncButtonColors["inactive"])),
            "active": self.svgToPixmap("icons/Power.svg", 200, 200, QtGui.QColor(self.syncButtonColors["active"])),
            "inProgress": self.svgToPixmap("icons/Power.svg", 200, 200, QtGui.QColor(self.syncButtonColors["inProgress"])),
            "error": self.svgToPixmap("icons/Power.svg", 200, 200, QtGui.QColor(self.syncButtonColors["error"]))
        }
        self.syncButtonChangeColor("inactive")
        self.syncButton.setIconSize(QtCore.QSize(100,100))
        self.syncButton.setCheckable(True)
        self.syncButton.clicked.connect(self.syncButtonPressed)
        self.mainLayout.addWidget(self.syncButton, 3, 0, 1, 5, alignment=QtCore.Qt.AlignCenter)
        
        self.setAllEnabledStatus(False)
        
        self.widget = QWidget()
        self.widget.setLayout(self.mainLayout)
        self.setCentralWidget(self.widget)
        self.show()
        self.centerOnScreen()
                
        # for threading
        self.timer = QtCore.QBasicTimer()
        self.timer.start(500, self)
        self.setUpStatus = "inProgress"
        self.setUpError = None
        self.setUpThread = Thread(target=self.setUp)
        self.setUpThread.start()
        self.syncStatus = "inactive"
        self.previousSyncStatus = "inactive"
        self.syncThread = None
        self.syncThreadStatus = "idle"
        self.syncThreadNeedsKilled = False
        self.syncThreadResults = None
    
    def timerEvent(self, event: QtCore.QTimerEvent):
        if(self.setUpStatus!="inactive"):
            self.preciseStatusLabel.setText(self.preciseStatus)
            self.arcgisStatusLabel.setText(self.arcgisStatus)
            if(self.setUpStatus=="error"):
                self.exitWithError(self.setUpError)
            elif(self.setUpStatus=="checkComplete"):
                if(self.needsSetup or self.__precise is None or self.__arcgis is None):
                    skipPage = None
                    if(self.__precise is not None):
                        skipPage = "precise"
                    elif(self.__arcgis is not None):
                        skipPage = "arcgis"
                    print(self.__precise)
                    dlg = CustomDialog("all", self.__config, skipPage=skipPage, arcgis=self.__arcgis)
                    if(dlg.exec()):
                        self.__config = dlg.config
                        if dlg.precise is not None:
                            self.__precise = dlg.precise
                        print(self.__precise)
                        self.__arcgis = dlg.arcgis
                        self.preciseStatus = "Connected"
                        self.arcgisStatus = "Connected"
                    else:
                        QApplication.quit()
                        return
                else:
                    if(self.__config["options"]["layerName"] is None):
                        self.configureOptions()
                    if(self.__config["options"]["syncInterval"] is None or self.__config["options"]["syncInterval"]<30):
                        self.__config["options"]["syncInterval"] = 120
                        with open("settings.conf", "w") as fp:
                            json.dump(self.__config, fp)
                    Thread(target = self.__arcgis.setLayer, args = (self.__config["options"]["layerName"],)).start()
                self.preciseStatusLabel.setText(self.preciseStatus)
                self.arcgisStatusLabel.setText(self.arcgisStatus)
                self.refreshAssetList()
                self.setAllEnabledStatus(True)
                self.setUpStatus = "inactive"
        if(self.syncThreadNeedsKilled and self.syncStatus != "inactive"):
            self.syncStatus = "inactive"
        if(self.syncStatus != self.previousSyncStatus):
            self.previousSyncStatus = self.syncStatus
            self.syncButtonChangeColor(self.syncStatus)
        if(self.syncThreadResults is not None):
            print("["+datetime.datetime.now().strftime("%Y-%m-%d, %I:%M:%S %p")+"] "+str(self.syncThreadResults))
            self.syncThreadResults = None
            
    def setUp(self):
        try:
            with open("settings.conf") as f:
                self.__config = json.load(f)
                self.__assets = self.__config["data"]["assetsToSync"]
            print("Settings file found.")
        except FileNotFoundError:
            self.needsSetup = True
        if(self.setUpStatus=="inactive"):
            return
        if(not self.needsSetup):
            try:
                self.preciseStatus = "Connecting..."
                self.__precise = preciseApi(
                    self.__config["precise"]["apiKey"], 
                    self.__config["precise"]["username"], 
                    self.__config["precise"]["companyId"]
                )
                print("Precise API connection established.")
                self.preciseStatus = "Connected"
            except Exception as e:
                print("Precise API connection could not be established.")
                self.preciseStatus = "Not Connected"
                if(str(e) not in ["Bad API Key", "Bad User Name", "Authorization has been denied for this request."]):
                    self.setUpError = e
                    self.setUpStatus = "error"
                    return
            if(self.setUpStatus=="inactive"):
                return
            try:
                self.arcgisStatus = "Connecting..."
                self.__arcgis = gisHelper(
                    apiKey = self.__config["arcgis"]["apiKey"], 
                    username = self.__config["arcgis"]["username"],
                    password = self.__config["arcgis"]["password"]
                )
                print("ArcGIS connection established.")
                self.arcgisStatus = "Connected"
            except Exception as e:
                print("ArcGIS connection could not be established.")
                self.arcgisStatus = "Not Connected"
                if(str(e) not in ["A general error occurred: Invalid username or password.", "Bad Api Key."]):
                    self.setUpError = e
                    self.setUpStatus = "error"
                    return
        if(self.setUpStatus!="inactive"):
            self.setUpStatus = "checkComplete"
    
    def changeAssetsToSync(self):
        self.__assets = self.multiComboBox.getSelectedValues()
        self.__config["data"]["assetsToSync"] = self.__assets
    
    def refreshAssetList(self):
        assets = self.__assets
        self.multiComboBox.clear()
        if(self.__precise is not None):
            self.comboBoxData = self.__precise.getFleetsAndAssets()
        self.multiComboBox.addItems(self.comboBoxData, selectedValues=assets)
        
    def configurePreciseApi(self):
        dlg = CustomDialog("precise", self.__config)
        if(dlg.exec()):
            self.__config = dlg.config
            self.__precise = dlg.precise
            self.refreshAssetList()
            self.preciseStatusLabel.setText("Connected")
        
    def configureArcgisApi(self):
        dlg = CustomDialog("arcgis", self.__config)
        if(dlg.exec()):
            self.__config = dlg.config
            self.__arcgis = dlg.arcgis
            self.__arcgis.setLayer(self.__config["options"]["layerName"])
            self.arcgisStatusLabel.setText("Connected")
            
    def configureOptions(self):
        dlg = CustomDialog("options", self.__config, arcgis=self.__arcgis)
        if(dlg.exec()):
            self.__config = dlg.config
            self.__arcgis = dlg.arcgis
            
    def syncButtonPressed(self, state):
        if(state==True):
            if(len(self.__assets)==0):
                QMessageBox.information(self, "Asset List Empty!", "Please select at least one asset to sync.")
                self.syncButton.setChecked(False)
                return
            self.syncStatus = "inProgress"
            self.syncThread = Thread(target=self.syncAssets)
            self.syncThread.start()
        else:
            self.syncThreadNeedsKilled = True
    
    def setAllEnabledStatus(self, enabled: bool):
        self.optionsAction.setEnabled(enabled)
        self.preciseConfigButton.setEnabled(enabled)
        self.arcgisConfigButton.setEnabled(enabled)
        self.multiComboBox.setEnabled(enabled)
        self.comboBoxButton.setEnabled(enabled)
        self.syncButton.setEnabled(enabled)
    
    def syncButtonChangeColor(self, status: str):
        self.syncButton.setIcon(self.syncButtonIcons[status])
        self.syncButton.setStyleSheet("border-radius : 75px; border: 2px solid "+ self.syncButtonColors[status] +"; background-color: gray")
    
    def svgToPixmap(self, svg_filename: str, width: int, height: int, color: QtGui.QColor) -> QtGui.QPixmap:
        #from https://stackoverflow.com/a/75443894
        renderer = QtSvg.QSvgRenderer(svg_filename)
        pixmap = QtGui.QPixmap(width, height)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        renderer.render(painter) # this is the destination, and only its alpha is used!
        painter.setCompositionMode(
            painter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        return pixmap
    
    def syncAssets(self):
        self.syncThreadStatus = "active"
        lastSync = 0
        while not self.syncThreadNeedsKilled:
            lastSync = time.time()
            self.syncThreadStatus = "syncing"
            try:
                self.syncThreadResults = self.__arcgis.updateLayer(self.__precise, assetIds=self.__assets)
                self.syncStatus = "active"
            except Exception as e:
                print("["+datetime.datetime.now().strftime("%Y-%m-%d, %I:%M:%S %p")+"] Error: "+str(e))
                self.syncStatus = "error"
            self.syncThreadStatus = "idle"
            while(lastSync+self.__config["options"]["syncInterval"]-1>time.time() and not self.syncThreadNeedsKilled):
                time.sleep(1)
            if(self.syncThreadNeedsKilled):
                break
            time.sleep(max(0.1,lastSync+self.__config["options"]["syncInterval"]-time.time()))
        self.syncThreadNeedsKilled = False
        self.syncThread = None
        self.syncStatus = "inactive"
        
    def centerOnScreen (self):
        center = QtGui.QScreen.availableGeometry(QApplication.primaryScreen()).center()
        geo = self.frameGeometry()
        geo.moveCenter(center)
        self.move(geo.topLeft())
    
    def exitWithError(self, error: Exception):
        QMessageBox.critical(
            self,
            "An error has occurred!", 
            "The app encountered an error while running. Please refer to the following error message:\n\n"+str(error)
        )
        QApplication.quit()
    
    def closeEvent(self, event: QtGui.QCloseEvent):
        if(self.setUpStatus!="inactive"):
            self.setUpStatus="inactive"
        if self.setUpError is None and self.__config is not None: 
            with open("settings.conf", 'w') as fp:
                json.dump(self.__config, fp)
        if(self.syncThread is not None and self.syncThread.is_alive()):
            self.syncThreadNeedsKilled = True
            while(self.syncThreadNeedsKilled):
                time.sleep(0.1)
        event.accept()
    
app = QApplication(sys.argv)
app.setApplicationVersion("0.1.0")
app.setApplicationName("Precise Arcgis Connector")
window = MainWindow()

app.exec()