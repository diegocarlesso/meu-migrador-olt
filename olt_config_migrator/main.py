import sys
from PyQt6.QtWidgets import QApplication
from app.wizard import MigrationWizard
from app.styles import apply_metro_theme

def main():
    app = QApplication(sys.argv)
    apply_metro_theme(app)
    w = MigrationWizard()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
