import xmlrpc.client

print("=== INICIANDO PRUEBA COMPLETA ===")

# 1. Credenciales (Ajusta con tus datos reales)
URL = 'http://localhost:8069'
DB = 'tubase'
USER = 'tuuser'
PASSWORD = 'tupass'

try:
    print("Conectando a Odoo...")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASSWORD, {})
    
    if not uid:
        print("❌ Error: Credenciales incorrectas.")
        exit()
        
    print(f"✅ Conectado con éxito. UID: {uid}")
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

    # --- AQUÍ LA LLAMADA DIRECTA DE PRUEBA ---
    cuenta_a_buscar = "2.4.1.1"
    print(f"Buscando la cuenta: {cuenta_a_buscar}...")
    
    account_ids = models.execute_kw(DB, uid, PASSWORD, 'account.account', 'search', [[['code', 'like', cuenta_a_buscar]]])
    
    print(f"Resultado de la API de Odoo: {account_ids}")

except Exception as e:
    print(f"❌ Ocurrió un error en la ejecución: {e}")

print("=== FIN DE LA PRUEBA ===")
