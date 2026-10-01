"""Las pruebas nunca tocan Neon.

Se fuerza una base SQLite temporal antes de importar nada: si DATABASE_URL
apuntara a Neon, una prueba que borra datos los borraría de verdad.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Al principio, para que `import main` sea el del gateway y no el main.py del
# monolito que todavía vive en user-management.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_db_file = Path(tempfile.mkdtemp()) / "code4all-test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file.as_posix()}"

# Docente y director solo se registran con el código de su rol. Las pruebas
# usan uno inventado; nunca el de producción.
os.environ["DOCENTE_SIGNUP_CODE"] = "codigo-de-prueba-docente"
os.environ["DIRECTOR_SIGNUP_CODE"] = "codigo-de-prueba-director"
