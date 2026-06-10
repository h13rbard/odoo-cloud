import xmlrpc.client
import mysql.connector
import sys

print("==================================================")
print("👥 MIGRACIÓN MAESTRA DE CONTACTOS Y PERSONAL A ODOO")
print("==================================================")

# 1. CONFIGURACIÓN DE CONEXIONES (Actualiza con tus datos reales)
URL = 'http://localhost:8069'
DB = 'odoo_portfolio'          
USER = 'gmunoz1151@gmail.com'   # 👈 Tu correo de Odoo
PASSWORD = 'CLOUDodoo26#' # 👈 Tu contraseña de Odoo

MYSQL_CONFIG = {
    'host': 'localhost',             
    'user': 'bashtico',
    'password': 'PATsistemas26#', # 👈 Tu contraseña de MySQL
    'database': 'db_almacen' # 👈 El nombre de tu base legacy montada
}

# Conexión con Odoo vía XML-RPC
try:
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USER, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object', allow_none=True)
    print(f"✅ Conectado a Odoo exitosamente (UID: {uid})")
except Exception as e:
    print(f"❌ Error al conectar a Odoo: {e}"); sys.exit()

# 2. CREAR O BUSCAR LA ETIQUETA "Personal Operativo" EN ODOO
try:
    tag_ids = models.execute_kw(DB, uid, PASSWORD, 'res.partner.category', 'search', [[['name', '=', 'Personal Operativo']]])
    if not tag_ids:
        TAG_OPERATIVO_ID = models.execute_kw(DB, uid, PASSWORD, 'res.partner.category', 'create', [{'name': 'Personal Operativo'}])
    else:
        TAG_OPERATIVO_ID = tag_ids[0]
    print("✅ Etiqueta 'Personal Operativo' verificada.")
except Exception as e:
    print(f"⚠️ Alerta con las etiquetas: {e}")
    TAG_OPERATIVO_ID = False

# 3. EXTRAER DATOS ACTUALIZADOS DE MYSQL
try:
    db_mysql = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = db_mysql.cursor(dictionary=True)
    
    # Consulta exacta basada en tu tabla 'persona'
    query = """
         SELECT tipo_persona, nombre, num_documento, direccion, telefono, email 
         FROM persona
    """
    cursor.execute(query)
    personas_legacy = cursor.fetchall()
    print(f"✅ MySQL leído. {len(personas_legacy)} registros listos para migrar.")
except mysql.connector.Error as err:
    print(f"❌ Error al leer MySQL: {err}"); sys.exit()

# 4. PROCESAR E INYECTAR EN ODOO
print("\n⚙️ Iniciando inserción en el modelo res.partner...")
for per in personas_legacy:
    if not per['nombre']:
        continue
        
    nombre_contacto = per['nombre'].strip()
    # Convertimos a minúsculas para evitar problemas de mayúsculas/minúsculas en el tipo
    tipo = str(per['tipo_persona']).strip().lower()
    
    # Mapeo de roles en Odoo (customer_rank y supplier_rank)
    es_cliente = 1 if tipo == 'cliente' else 0
    es_proveedor = 1 if tipo == 'proveedor' else 0
    
    # Armamos el diccionario con tus campos de MySQL
    payload_partner = {
        'name': nombre_contacto,
        'vat': per['num_documento'].strip() if per['num_documento'] else False, # Tu RFC/ID
        'street': per['direccion'].strip() if per['direccion'] else False,
        'phone': per['telefono'].strip() if per['telefono'] else False,
        'email': per['email'].strip() if per['email'] else False,
        'customer_rank': es_cliente,
        'supplier_rank': es_proveedor,
        'company_type': 'company' # Se registra como empresa/entidad comercial
    }
    
    # Si el tipo es operativo, le asociamos el Tag/Categoría especial
    if tipo == 'operativo' and TAG_OPERATIVO_ID:
        payload_partner['category_id'] = [[6, 0, [TAG_OPERATIVO_ID]]]
        tipo_str = "OPERATIVO"
    elif es_cliente:
        tipo_str = "CLIENTE"
    elif es_proveedor:
        tipo_str = "PROVEEDOR"
    else:
        tipo_str = tipo.upper()

    try:
        # Validación estricta para no duplicar datos si reinicias el script
        existe = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'search', [[['name', '=', nombre_contacto]]])
        if existe:
            print(f"   ⚠️ Saltado: '{nombre_contacto}' ya existe en Odoo (ID: {existe[0]})")
            continue
            
        # Crear el registro en Odoo
        partner_id = models.execute_kw(DB, uid, PASSWORD, 'res.partner', 'create', [payload_partner])
        print(f"   -> [✓ MIGRADO] ({tipo_str}) {nombre_contacto} -> ID Odoo: {partner_id}")
        
    except Exception as e:
        print(f"   -> [✗ ERROR] No se pudo migrar a {nombre_contacto}: {e}")

# Cierre seguro de conexiones
cursor.close()
db_mysql.close()
print("\n==================================================")
print("🎉 ¡PROCESO DE MIGRACIÓN DE CONTACTOS FINALIZADO!")
print("==================================================")
