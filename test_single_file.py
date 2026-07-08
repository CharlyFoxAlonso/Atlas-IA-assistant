import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.vector_store import agregar_documento
from core.universal_loader import leer_archivo_con_info

file_path = 'memory/Atlas_Memory/00_Sistema/Prompts/Actualizar_Memoria_Charly.md'
print(f'Testing file: {file_path}')
res = leer_archivo_con_info(file_path)
if res['ok']:
    print('Read ok. Attempting to add to vector store...')
    chunks = agregar_documento(doc_id=file_path, texto=res['contenido'])
    print(f'Successfully added {chunks} chunks')
else:
    print(f'Read failed: {res['error']}')
