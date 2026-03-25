import json, time
from threading import Thread

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QPushButton,
    QLabel,
    QFormLayout,
    QVBoxLayout,
    QHBoxLayout,
    QStackedLayout,
    QWidget,
    QMessageBox,
    QFrame,
    QSizePolicy
)
from PySide6.QtGui import QFont, QIntValidator
from PySide6 import QtCore

from collections.abc import Callable
from GISConnector import gisHelper

class CustomDialog(QDialog):
    def __init__(self, mode : str = "all", configJson: dict | None = None, skipPage: str | None = None, arcgis: gisHelper | None = None):
        if(mode not in ["precise", "arcgis", "options", "all"]):
            raise Exception("Mode must be precise, arcgis, options, or all.")
        super().__init__()

        self.pages = []
        self.config = configJson if configJson is not None else {
            "precise": {
                "apiKey": None,
                "username": None,
                "companyId": -1
            },
            "arcgis": {
                "apiKey": None,
                "username": None,
                "password": None
            },
            "options": {
                "layerName": None,
                "syncInterval": 120
            },
            "data": {
                "assetsToSync":[]
            }
        }
        self.precise = None
        self.arcgis = arcgis
        
        #for threading
        self.returnValueFromThread = None
        self.threadDone = False
        self.timer = QtCore.QBasicTimer()
        self.timer.start(500, self)
        self.layerNameNeedsConfirmation = False
        self.layerNameConfirmation = None
        self.layerName = None
        
        self.layout: QVBoxLayout = QVBoxLayout()
        self.stackedLayout = QStackedLayout()

        if(mode=="precise" or (mode=="all" and skipPage!="precise")):
            if(mode=="precise"):
                self.setWindowTitle("Configure Precise API...")
            self.precisePage = QWidget()
            self.precisePageLayout = QFormLayout()
            self.preciseApiKeyEdit = QLineEdit(self.config["precise"]["apiKey"])
            self.preciseUsernameEdit = QLineEdit(self.config["precise"]["username"])
            self.preciseCompanyIdEdit = QLineEdit(str(self.config["precise"]["companyId"]) 
                                                  if self.config["precise"]["companyId"] > 0 
                                                  else None)
            self.preciseCompanyIdEdit.setValidator(QIntValidator(100,999))
            self.precisePageLayout.addRow("API Key: ", self.preciseApiKeyEdit)
            self.precisePageLayout.addRow("Username: ", self.preciseUsernameEdit)
            self.precisePageLayout.addRow("Company ID: ", self.preciseCompanyIdEdit)
            self.precisePage.setLayout(self.precisePageLayout)
            self.stackedLayout.addWidget(self.precisePage)
            self.pages.append("precise")

        if(mode=="arcgis" or (mode=="all" and skipPage!="arcgis")):
            if(mode=="arcgis"):
                self.setWindowTitle("Configure ArcGIS...")
            self.arcgisPage = QWidget()
            self.arcgisPageLayout = QFormLayout()
            self.arcgisApiKeyEdit = QLineEdit(self.config["arcgis"]["apiKey"])
            self.separator = QHBoxLayout()
            self.separator1 = QFrame()
            self.separator1.setFrameShape(QFrame.HLine)
            self.separator1.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
            self.separator1.setLineWidth(1)
            self.separator2 = QFrame()
            self.separator2.setFrameShape(QFrame.HLine)
            self.separator2.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
            self.separator2.setLineWidth(1)
            self.separator.addWidget(self.separator1, stretch=1)
            self.separator.addWidget(QLabel("or"))
            self.separator.addWidget(self.separator2, stretch=1)
            self.arcgisUsernameEdit = QLineEdit(self.config["arcgis"]["username"])
            self.arcgisUsernameEdit.textChanged.connect(self.arcgisUsernameTextChanged)
            self.arcgisPasswordEdit = QLineEdit(self.config["arcgis"]["password"])
            if(self.config["arcgis"]["username"] is not None):
                self.arcgisApiKeyEdit.setEnabled(False)
            else:
                self.arcgisPasswordEdit.setEnabled(False)
            self.arcgisPasswordEdit.setEchoMode(QLineEdit.EchoMode.Password)
            self.arcgisPageLayout.addRow("API Key: ", self.arcgisApiKeyEdit)
            self.arcgisPageLayout.addRow(self.separator)
            self.arcgisPageLayout.addRow("Username: ", self.arcgisUsernameEdit)
            self.arcgisPageLayout.addRow("Password: ", self.arcgisPasswordEdit)
            self.arcgisPage.setLayout(self.arcgisPageLayout)
            self.stackedLayout.addWidget(self.arcgisPage)
            self.pages.append("arcgis")

        if(mode=="options" or mode=="all"):
            if(mode=="options"):
                self.setWindowTitle("Options")
            self.optionsPage = QWidget()
            self.optionsLayout = QFormLayout()
            self.optionsLayerNameEdit = QLineEdit(self.config["options"]["layerName"])
            self.optionsSyncIntervalEdit = QLineEdit(str(self.config["options"]["syncInterval"]) 
                                                     if self.config["options"]["syncInterval"]>=30 
                                                     else "120")
            self.optionsSyncIntervalEdit.setValidator(QIntValidator(30,999))
            self.optionsLayout.addRow("Layer Name: ", self.optionsLayerNameEdit)
            self.optionsLayout.addRow("Sync Interval (in seconds): ", self.optionsSyncIntervalEdit)
            self.optionsPage.setLayout(self.optionsLayout)
            self.stackedLayout.addWidget(self.optionsPage)
            self.pages.append("options")
        
        if(mode=="all"):
            self.setWindowTitle("Set Up")
            self.header = QLabel("")
            self.headerFont = QFont()
            self.headerFont.setPointSize(16)
            self.header.setFont(self.headerFont)
            self.layout.addWidget(self.header, alignment=QtCore.Qt.AlignCenter)
            self.changeHeader(0)
            
        self.layout.addLayout(self.stackedLayout)

        self.buttonBox = QDialogButtonBox()
            
        self.OkBtn = QPushButton("OK")
        self.buttonBox.addButton(self.OkBtn, QDialogButtonBox.AcceptRole)
        self.buttonBox.accepted.connect(self.OkBtnClicked)
            
        self.cancelBtn = QPushButton("Cancel")
        self.buttonBox.addButton(self.cancelBtn, QDialogButtonBox.RejectRole)
        self.buttonBox.rejected.connect(self.reject)
        
        if(len(self.pages)>1):
            self.OkBtn.setEnabled(False)
            self.prevBtn = QPushButton("<< Prev")
            self.prevBtn.setEnabled(False)
            self.prevBtn.clicked.connect(self.prevBtnClicked)
            self.buttonBox.addButton(self.prevBtn, QDialogButtonBox.ActionRole)
            self.nextBtn = QPushButton("Next >>")
            self.nextBtn.clicked.connect(self.nextBtnClicked)
            self.buttonBox.addButton(self.nextBtn, QDialogButtonBox.ActionRole)
        
        self.buttonBox.setStyleSheet("* { button-layout: 2 }") #KDE Layout
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
    
    def changeHeader(self, index: int):
        if(self.header is None):
            return
        if(self.pages[index]=="precise"):
            self.header.setText("Set Up Precise API")
        elif(self.pages[index]=="arcgis"):
            self.header.setText("Set Up ArcGIS")
        elif(self.pages[index]=="options"):
            self.header.setText("Additional Options")
    
    def prevBtnClicked(self):
        index = self.stackedLayout.currentIndex()-1
        self.stackedLayout.setCurrentIndex(index)
        self.changeHeader(index)
        if(index==0):
            self.prevBtn.setEnabled(False)
        if(index==len(self.pages)-2):
            self.OkBtn.setEnabled(False)
        if(not self.nextBtn.isEnabled()):
            self.nextBtn.setEnabled(True)
        
    def nextBtnClicked(self):
        index = self.stackedLayout.currentIndex()
        self.stackedLayout.setEnabled(False)
        self.nextBtn.setEnabled(False)
        thread = Thread(target=self.validateInput, args=(index,))
        thread.start()
    
    def OkBtnClicked(self):
        self.stackedLayout.setEnabled(False)
        self.OkBtn.setEnabled(False)
        thread = Thread(target=self.validateInput, args=(self.stackedLayout.currentIndex(),))
        thread.start()

    def validateInput(self, index: int) -> int:
        #returns number of invalid inputs]
        if(self.pages[index]=="precise"):
            self.returnValueFromThread = self.validatePreciseInput()
        elif(self.pages[index]=="arcgis"):
            self.returnValueFromThread = self.validateArcgisInput()
        elif(self.pages[index]=="options"):
            self.returnValueFromThread = self.validateOptionsInput()
        self.threadDone = True
    
    def timerEvent(self, event):
        if self.threadDone:
            index = self.stackedLayout.currentIndex()
            if(self.returnValueFromThread<=0):
                if(index < len(self.pages)-1):
                    index+=1
                    self.stackedLayout.setCurrentIndex(index)
                    self.changeHeader(index)
                    if(index==len(self.pages)-1):
                        self.nextBtn.setEnabled(False)
                        self.OkBtn.setEnabled(True)
                    if(not self.prevBtn.isEnabled()):
                        self.prevBtn.setEnabled(True)
                else:
                    with open('settings.conf', 'w') as fp:
                        json.dump(self.config, fp)
                    self.accept()
            self.stackedLayout.setEnabled(True)
            if(index < len(self.pages)-1):    
                self.nextBtn.setEnabled(True)
            else:
                self.OkBtn.setEnabled(True)
            self.returnValueFromThread = None
            self.threadDone = False
        if self.layerNameNeedsConfirmation:
            self.layerNameConfirmation = QMessageBox.question(
                self,
                "Update Existing Layer?", 
                "The layer named \""+self.layerName+"\" already exists. Do you want the data to be updated to the layer?"
            )
            self.layerNameNeedsConfirmation = False
    
    def validatePreciseInput(self) -> int:
        toolTipText = "This field cannot be empty."
        invalidInputCount = 0
        if(self.preciseApiKeyEdit.text()==""):
            self.showLineEditError(self.preciseApiKeyEdit, toolTipText)
            invalidInputCount+=1
        if(self.preciseUsernameEdit.text()==""):
            self.showLineEditError(self.preciseUsernameEdit, toolTipText)
            invalidInputCount+=1
        if(self.preciseCompanyIdEdit.text()==""):
            self.showLineEditError(self.preciseCompanyIdEdit, toolTipText)
            invalidInputCount+=1
        if(invalidInputCount>0):
            return invalidInputCount
        apiKey = self.preciseApiKeyEdit.text()
        username = self.preciseUsernameEdit.text()
        companyId = int(self.preciseCompanyIdEdit.text())
        from PreciseAPI import preciseApi
        try:
            self.precise = preciseApi(apiKey, username, companyId)
            self.config["precise"]["apiKey"] = apiKey
            self.config["precise"]["username"] = username
            self.config["precise"]["companyId"] = companyId
        except Exception as e:
            if(str(e)=="Bad API Key"):
                toolTipText = "API Key is invalid."
                self.showLineEditError(self.preciseApiKeyEdit, toolTipText)
                invalidInputCount+=1
            elif(str(e)=="Bad User Name"):
                toolTipText = "Username is invalid."
                self.showLineEditError(self.preciseUsernameEdit, toolTipText)
                invalidInputCount+=1
            elif(str(e)=="Authorization has been denied for this request."):
                toolTipText = "The company ID is invalid."
                self.showLineEditError(self.preciseCompanyIdEdit, toolTipText)
                invalidInputCount+=1
            else:
                invalidInputCount+=1
                raise Exception("Something went wrong while trying to authenticate Precise API. Error message: "+str(e))
        return invalidInputCount

    def validateArcgisInput(self) -> int:
        invalidInputCount = 0
        apiKey = None
        username = None
        password = None
        if(self.arcgisUsernameEdit.text()==""):
            if(self.arcgisApiKeyEdit.text()==""):
                toolTipText = "This field must be specified if the username and/or password fields are empty."
                self.showLineEditError(self.arcgisApiKeyEdit, toolTipText)
                invalidInputCount+=1
            else:
                apiKey = self.arcgisApiKeyEdit.text()
        else:
            if(self.arcgisPasswordEdit.text()==""):
                toolTipText = "This field must be specified if the username field is not empty."
                self.showLineEditError(self.arcgisPasswordEdit, toolTipText)
                invalidInputCount+=1
            else:
                username = self.arcgisUsernameEdit.text()
                password = self.arcgisPasswordEdit.text()
        if(invalidInputCount>0):
            return invalidInputCount
        try:
            self.arcgis = gisHelper(apiKey=apiKey, username=username, password=password)
            self.config["arcgis"]["apiKey"] = apiKey
            self.config["arcgis"]["username"] = username
            self.config["arcgis"]["password"] = password
        except Exception as e:
            if(str(e)=="A general error occurred: Invalid username or password."):
                toolTipText = "Invalid username and/or password."
                self.showLineEditError(self.arcgisPasswordEdit, toolTipText, self.arcgisUsernameEdit, True, self.arcgisUsernameTextChanged)
                invalidInputCount+=1
            elif(str(e)=="Bad Api Key."):
                toolTipText = "Api Key is invalid."
                self.showLineEditError(self.arcgisApiKeyEdit, toolTipText)
                invalidInputCount+=1
            else:
                invalidInputCount+=1
                raise Exception("Something went wrong while trying to authenticate Precise API. Error message: "+str(e))
        return invalidInputCount
    
    def validateOptionsInput(self) -> int:
        toolTipText = "This field cannot be empty."
        invalidInputCount = 0
        if(self.optionsLayerNameEdit.text()==""):
            self.showLineEditError(self.optionsLayerNameEdit, toolTipText)
            invalidInputCount+=1
        if(self.optionsSyncIntervalEdit.text()==""):
            self.showLineEditError(self.optionsSyncIntervalEdit, toolTipText)
            invalidInputCount+=1
        if(invalidInputCount>0):
            return invalidInputCount
        layerName = self.optionsLayerNameEdit.text()
        syncInterval = int(self.optionsSyncIntervalEdit.text())
        if(layerName != self.config["options"]["layerName"]):
            if(self.arcgis.layerExists(layerName)):
                self.layerNameNeedsConfirmation = True
                self.layerName = layerName
                while(self.layerNameNeedsConfirmation):
                    time.sleep(0.5)
                if(self.layerNameConfirmation==QMessageBox.StandardButton.No):
                    return invalidInputCount+1
            self.config["options"]["layerName"] = layerName
        self.arcgis.setLayer(layerName)
        self.config["options"]['syncInterval'] = syncInterval
        return invalidInputCount
    
    def showLineEditError(self, lineEdit: QLineEdit, toolTipText: str, relatedLineEdit: QLineEdit | None = None, relatedLineEditShowError: bool = False, relatedLineEditTextChangedSlot: Callable | None = None):
        style = lineEdit.styleSheet()
        lineEdit.setStyleSheet("border: 1px solid red;")
        lineEdit.setToolTip(toolTipText)
        lineEdit.textChanged.connect(lambda:self.clearError(lineEdit, style, relatedLineEdit, relatedLineEditShowError, relatedLineEditTextChangedSlot))
        if(relatedLineEdit is not None):
            if(relatedLineEditShowError):
                relatedLineEdit.setStyleSheet("border: 1px solid red;")
                relatedLineEdit.setToolTip(toolTipText)
            relatedLineEdit.textChanged.connect(lambda:self.clearError(lineEdit, style, relatedLineEdit, relatedLineEditShowError, relatedLineEditTextChangedSlot))

    def clearError(self, lineEdit: QLineEdit, oldStyle: str = "", relatedLineEdit: QLineEdit | None = None, relatedLineEditClearError: bool = False, relatedLineEditTextChangedSlot: Callable | None = None):
        lineEdit.setStyleSheet(oldStyle)
        lineEdit.setToolTip("")
        if(lineEdit.receivers(QtCore.SIGNAL(QtCore.QMetaMethod.fromSignal(lineEdit.textChanged).methodSignature().toStdString()))>0):
            lineEdit.textChanged.disconnect()
        if(relatedLineEdit is not None):
            if(relatedLineEditClearError):
                relatedLineEdit.setStyleSheet(oldStyle)
                relatedLineEdit.setToolTip("")
            if(relatedLineEdit.receivers(QtCore.SIGNAL(QtCore.QMetaMethod.fromSignal(relatedLineEdit.textChanged).methodSignature().toStdString()))>0):
                relatedLineEdit.textChanged.disconnect()
            if(relatedLineEditTextChangedSlot is not None):
                relatedLineEdit.textChanged.connect(relatedLineEditTextChangedSlot)
        
    def arcgisUsernameTextChanged(self, text):
        if(text==""):
            self.arcgisPasswordEdit.setEnabled(False)
            self.clearError(self.arcgisPasswordEdit)
            self.arcgisApiKeyEdit.setEnabled(True)
        else:
            self.arcgisPasswordEdit.setEnabled(True)
            self.arcgisApiKeyEdit.setEnabled(False)
            self.clearError(self.arcgisApiKeyEdit)