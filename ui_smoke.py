"""Exercise real Tk layouts against a disposable database (Windows or Xvfb)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import tkinter as tk

import database
import app
from ui_theme import CapsuleNotebook


def walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from walk(child)


def main():
    with TemporaryDirectory(prefix='servix-ui-') as folder:
        database.DB = Path(folder) / 'test.db'
        app.DB = database.DB
        database.init_db()
        with database.connect() as con:
            con.execute("INSERT INTO clients(id,code,name) VALUES(1,'CLI-TEST','UI Test Client')")
            con.execute("INSERT INTO equipment(id,code,client_id,make,model) VALUES(1,'SEQ-TEST',1,'Test','Instrument')")
            con.execute("INSERT INTO services(code,client_id,equipment_id,opened,reason,complaint,warranty,amc,status) VALUES('SRV-TEST',1,1,'2026-10-01','Calibration','UI smoke test','No','No','Open')")
        def login(self):
            self.current_user = dict(id=1, username='test', display_name='UI Test', role='Administrator')
            return True
        errors = []
        with patch.object(app.Servix, 'login', login), patch.object(app.Servix, 'run_auto_backup'):
            window = app.Servix()
        window.report_callback_exception = lambda *error: errors.append(error)
        try:
            for size in ('1280x760', '1536x960'):
                window.geometry(size)
                for method in ('show_dashboard', 'show_services', 'show_new_service', 'show_clients',
                               'show_equipment', 'show_engineers', 'show_parts_inventory',
                               'show_documents', 'show_warranty', 'show_calibration',
                               'show_commercial', 'show_reports', 'show_data_management',
                               'show_users', 'show_settings'):
                    getattr(window, method)()
                    window.update()
                    assert window.sidebar.winfo_width() == 280
                    assert window.content.winfo_width() > 900
                for method, code in (('show_service_detail', 'SRV-TEST'),
                                     ('show_client_360', 'CLI-TEST'),
                                     ('show_equipment_360', 'SEQ-TEST')):
                    getattr(window, method)(code)
                    window.update()
                    for notebook in [w for w in walk(window.content) if isinstance(w, CapsuleNotebook)]:
                        for button in notebook.buttons:
                            assert button.winfo_x() + button.winfo_width() <= notebook.bar.winfo_width(), button.label
                            notebook.select(button.page)
                            window.update()
                            assert notebook.notebook.select() == button.page
                            assert window.nametowidget(button.page).winfo_ismapped()
                print(f'All modules and capsule selections passed at {size}')
            assert not errors, errors
        finally:
            window.destroy()


if __name__ == '__main__':
    main()
