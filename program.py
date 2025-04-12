from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QIcon, QFontDatabase, QFont
from PyQt5.uic import loadUi
import sys

class MyApp(QMainWindow):  

    # Konstruktor inicjalizacja zmiennych, czcionek, ikonek itp.
    def __init__(self):
        super().__init__()

        # Wczytanie Ui z pliku
        loadUi("DicomProjectGUI.ui", self)  

        # Nadanie aplikacji tytułu oraz ikonki
        self.setWindowTitle("Program do obrazowania medycznego")
        self.setWindowIcon(QIcon("Resources/icon.png"))

        # Wczytywanie czcionki - moją będzie Roboto Regular
        font_id = QFontDatabase.addApplicationFont("Resources/Fonts/Roboto-Regular.ttf")

        if font_id != -1:
            family = QFontDatabase.applicationFontFamilies(font_id)[0]
            app.setFont(QFont(family, 10))  # Używamy wczytaną czcionkę jako domyślną
        else:
            print("Nie udało się załadować czcionki.")

        # Dostęp do elementów przez objectName z Qt Designera
        self.loadDataFromCatalogButton.clicked.connect(self.on_loadDataFromCatalogButton_clicked)

    def on_loadDataFromCatalogButton_clicked(self):
        pass
        



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec_())
