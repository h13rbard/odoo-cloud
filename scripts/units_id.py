import xmlrpc.client
# Conéctate temporalmente para leer los IDs reales de Odoo
common = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/common')
uid = common.authenticate('tubase', 'tuuser', 'tupass', {})
models = xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/object')

# Buscamos todas las unidades de medida instaladas
uoms = models.execute_kw('tubase', uid, 'tuuser', 'uom.uom', 'search_read', [[]], {'fields': ['id', 'name']})
#for uom in uoms:
for uom in sorted(uoms, key=lambda x: int(x['id'])):
    print(f"ID: {uom['id']} -> Nombre en Odoo: {uom['name']}")
